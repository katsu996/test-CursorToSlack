#!/usr/bin/env python3
"""
songdata.db の song テーブルに対する WHERE 断片で許可ハッシュ集合を作り、
難易度表のヘッダー JSON / データ JSON を突き合わせてフィルタした結果を docs に書き出す。

処理の分割先: http_fetch / sql_where_guard / beatoraja_rows / level_stats。
beatoraja の songdata.db（テーブル song）を想定。実行は GitHub Actions でもローカルでも可（標準ライブラリのみ）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from typing import Any, Mapping, MutableMapping, Sequence
from urllib.parse import urljoin

from beatoraja_rows import (
    normalize_beatoraja_chart_row,
    row_passes_beatoraja_strict_decoder,
    sanitize_chart_row_for_beatoraja,
    sanitize_header_for_beatoraja,
    strip_keys_cfg,
    validate_json_field_name,
)
from http_fetch import fetch_bytes
from level_stats import level_bucket_for_stats, merge_level_compare_rows, sort_level_stat_keys
from source_tables import (
    effective_custom_level_maps,
    extract_source_table_entries,
    load_resolved_filter_config,
    normalize_level_map,
    normalize_source_tables,
    uses_explicit_source_table_objects,
)
from sql_where_guard import die as _die
from sql_where_guard import resolve_sql_where, validate_sql_where

DEFAULT_CONFIG = "tools/table-filter/filter_config.json"


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _json_from_http_body(raw: bytes, *, kind: str, url: str) -> Any:
    """GET 本文を JSON として読む。HTML や壊れた JSON のときは分かりやすく終了する。"""
    text = raw.decode("utf-8", errors="replace").lstrip("\ufeff \t\r\n")
    if text.startswith("<"):
        _die(
            f"{kind} の取得結果が HTML です（JSON ではありません）。"
            f" Cloudflare や URL 誤りの可能性があります: {url}"
        )
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        preview = text[:200].replace("\n", " ")
        _die(f"{kind} の JSON 解析に失敗しました: {url}\n  先頭: {preview!r}\n  {exc}")


def _resolve_bmstable_header_url(page_or_json_url: str) -> str:
    """
    ヘッダー JSON の URL を返す。

    - ``*.json`` はそのまま（1 回目の GET は main 側で行う）。
    - それ以外（``*.html`` やディレクトリ URL など）は 1 回 GET し、
      HTML なら ``<meta name="bmstable">`` からヘッダー相対 URL を解決する。
      JSON 本文なら（拡張子なしの直リンク想定）同じ URL を返す。
    """
    u = page_or_json_url.strip()
    low = u.lower()
    if low.endswith(".json"):
        return u

    raw = fetch_bytes(u).decode("utf-8", errors="replace")
    stripped = raw.lstrip("\ufeff \t\r\n")
    if stripped.startswith("<"):
        m = re.search(
            r'<meta\s+name=["\']bmstable["\']\s+content=["\']([^"\']+)["\']',
            stripped,
            re.IGNORECASE,
        )
        if not m:
            m = re.search(
                r'<meta\s+content=["\']([^"\']+)["\']\s+name=["\']bmstable["\']',
                stripped,
                re.IGNORECASE,
            )
        if not m:
            _die(f"HTML から bmstable の meta が取得できません: {u}")
        rel = m.group(1).strip()
        return urljoin(u, rel)

    try:
        json.loads(stripped)
    except json.JSONDecodeError as exc:
        preview = stripped[:160].replace("\n", " ")
        _die(
            "ヘッダー URL が JSON として解釈できず、HTML（bmstable）でもありません。"
            f" Cloudflare 等でブロックされている可能性があります: {u}\n"
            f"  先頭: {preview!r}  エラー: {exc}"
        )
    return u


def _header_display_name(header_obj: Mapping[str, Any], idx: int) -> str:
    for key in ("name", "Name", "title", "Title"):
        v = header_obj.get(key)
        if v is not None:
            s = str(v).strip()
            if s:
                return s
    return f"表 {idx + 1}"


def _merge_course_parts(parts: list[Any]) -> Any:
    merged: list[Any] = []
    for p in parts:
        if p is None:
            continue
        if isinstance(p, list):
            merged.extend(p)
        else:
            merged.append(p)
    return merged if merged else None


def _row_dedupe_key(row: Mapping[str, Any]) -> str | None:
    sha = row.get("sha256")
    md5 = row.get("md5")
    if sha:
        s = str(sha).strip().lower()
        if re.fullmatch(r"[0-9a-f]{64}", s):
            return "sha256:" + s
    if md5:
        m = str(md5).strip().lower()
        if re.fullmatch(r"[0-9a-f]{32}", m):
            return "md5:" + m
    return None


def _query_allowed_hashes(db_path: str, sql_where: str, *, strict_identifiers: bool) -> tuple[set[str], set[str]]:
    validate_sql_where(sql_where, strict_identifiers=strict_identifiers)
    md5s: set[str] = set()
    sha256s: set[str] = set()
    sql = f"SELECT DISTINCT md5, sha256 FROM song WHERE ({sql_where})"
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        cur = con.cursor()
        cur.execute(sql)
        for row in cur.fetchall():
            raw_md5, raw_sha = row[0], row[1]
            if raw_md5:
                m = str(raw_md5).strip().lower()
                if re.fullmatch(r"[0-9a-f]{32}", m):
                    md5s.add(m)
            if raw_sha:
                s = str(raw_sha).strip().lower()
                if re.fullmatch(r"[0-9a-f]{64}", s):
                    sha256s.add(s)
    finally:
        con.close()
    return md5s, sha256s


def _chart_row_allowed(row: Mapping[str, Any], md5s: set[str], sha256s: set[str]) -> bool:
    sha = row.get("sha256")
    md5 = row.get("md5")
    if sha:
        s = str(sha).strip().lower()
        if re.fullmatch(r"[0-9a-f]{64}", s) and s in sha256s:
            return True
    if md5:
        m = str(md5).strip().lower()
        if re.fullmatch(r"[0-9a-f]{32}", m) and m in md5s:
            return True
    return False


def _filter_data_array(data: Any, md5s: set[str], sha256s: set[str]) -> list[Any]:
    if not isinstance(data, list):
        _die("データ JSON のトップレベルは配列である必要があります。")
    out: list[Any] = []
    for row in data:
        if isinstance(row, dict) and _chart_row_allowed(row, md5s, sha256s):
            out.append(row)
    return out


def _filter_course_object(obj: MutableMapping[str, Any], md5s: set[str], sha256s: set[str]) -> MutableMapping[str, Any] | None:
    charts = obj.get("charts")
    if not isinstance(charts, list):
        return obj
    kept = [c for c in charts if isinstance(c, dict) and _chart_row_allowed(c, md5s, sha256s)]
    if not kept:
        return None
    new_obj = dict(obj)
    new_obj["charts"] = kept
    return new_obj


def _row_level_lookup_keys(raw_lvl: Any) -> list[str]:
    if raw_lvl is None:
        return []
    keys: list[str] = []
    if isinstance(raw_lvl, bool):
        keys.append(str(raw_lvl).lower())
        return keys
    if isinstance(raw_lvl, int):
        keys.append(str(raw_lvl))
        return keys
    if isinstance(raw_lvl, float):
        if raw_lvl.is_integer():
            keys.append(str(int(raw_lvl)))
        else:
            keys.append(str(raw_lvl).strip())
        return keys
    s = str(raw_lvl).strip()
    if s:
        keys.append(s)
        try:
            f = float(s)
            if f.is_integer():
                keys.append(str(int(f)))
        except ValueError:
            pass
    out: list[str] = []
    seen: set[str] = set()
    for k in keys:
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def _apply_custom_level(
    row: MutableMapping[str, Any],
    source_idx: int,
    maps_list: Sequence[Mapping[str, Any]],
    cfg: Mapping[str, Any],
) -> None:
    if source_idx < 0 or source_idx >= len(maps_list):
        return
    m = dict(maps_list[source_idx]) if maps_list[source_idx] else {}
    if not m:
        return

    out_key = str(cfg.get("custom_level_field") or "custom_level").strip() or "custom_level"
    src_key = str(cfg.get("custom_level_source_key") or "level").strip() or "level"
    validate_json_field_name(out_key, "custom_level_field")
    validate_json_field_name(src_key, "custom_level_source_key")

    raw_lvl = row.get(src_key)
    for lk in _row_level_lookup_keys(raw_lvl):
        if lk in m:
            row[out_key] = m[lk]
            return

    fallback = str(cfg.get("custom_level_unmapped") or "omit").strip().lower()
    if fallback in ("source", "original"):
        row[out_key] = raw_lvl
    elif fallback == "null":
        row[out_key] = None


def _filter_course_structure(course: Any, md5s: set[str], sha256s: set[str]) -> Any:
    if isinstance(course, list):
        out: list[Any] = []
        for item in course:
            if isinstance(item, list):
                inner: list[Any] = []
                for sub in item:
                    if isinstance(sub, dict) and "charts" in sub:
                        fo = _filter_course_object(sub, md5s, sha256s)
                        if fo is not None:
                            inner.append(fo)
                    else:
                        inner.append(sub)
                if inner:
                    out.append(inner)
            elif isinstance(item, dict) and "charts" in item:
                fo = _filter_course_object(item, md5s, sha256s)
                if fo is not None:
                    out.append(fo)
            else:
                out.append(item)
        return out
    return course


def _empty_rows_policy_fail(cfg: Mapping[str, Any]) -> bool:
    raw = str(cfg.get("beatoraja_empty_rows_policy", "fail")).strip().lower()
    if raw in ("fail", "error", "true", "1", "yes", "on"):
        return True
    if raw in ("warn", "warning", "allow", "ignore", "skip", "0", "false", "no", "off"):
        return False
    if raw == "auto":
        return os.environ.get("GITHUB_ACTIONS") == "true"
    print(f"警告: 不明な beatoraja_empty_rows_policy: {raw!r}（fail とみなします）", file=sys.stderr)
    return True


def main() -> None:
    ap = argparse.ArgumentParser(description="songdata.db と難易度表 JSON を突き合わせてフィルタする")
    ap.add_argument("--config", default=os.environ.get("FILTER_CONFIG", DEFAULT_CONFIG), help="設定 JSON のパス")
    args = ap.parse_args()

    cfg_path = args.config
    if not os.path.isfile(cfg_path):
        print(f"設定ファイルが無いためスキップします: {cfg_path}", file=sys.stderr)
        raise SystemExit(0)

    cfg = load_resolved_filter_config(cfg_path)
    if not cfg.get("enabled", True):
        print("filter_config の enabled が false のためスキップします。", file=sys.stderr)
        raise SystemExit(0)

    header_urls_cfg, disp_cfg, short_cfg = normalize_source_tables(cfg)
    if not header_urls_cfg:
        print(
            "source_tables が空、または source_header_urls / source_header_url が空のためスキップします（難易度表フィルタは行いません）。",
            file=sys.stderr,
        )
        raise SystemExit(0)

    resolved_json_urls = [_resolve_bmstable_header_url(u) for u in header_urls_cfg]
    multi_source = len(resolved_json_urls) > 1
    uses_source_tables_objects = uses_explicit_source_table_objects(cfg)
    level_maps = effective_custom_level_maps(cfg)
    n_src = len(resolved_json_urls)
    legacy_maps = cfg.get("custom_level_mapping")
    if isinstance(legacy_maps, list) and legacy_maps and n_src:
        if len(legacy_maps) < n_src:
            print(
                "警告: custom_level_mapping（トップレベル配列）の要素数が元ヘッダー数より少ないです（足りないインデックスはマップ無し）。",
                file=sys.stderr,
            )
        if len(legacy_maps) > n_src:
            print(
                "警告: custom_level_mapping（トップレベル配列）の要素数が元ヘッダー数より多いです（余った要素は無視されます）。",
                file=sys.stderr,
            )
    entries = extract_source_table_entries(cfg)
    has_embedded = any(
        isinstance(e.get("custom_level_mapping"), dict) and bool(normalize_level_map(e.get("custom_level_mapping")))
        for e in entries
    )
    if has_embedded and isinstance(legacy_maps, list) and any(
        isinstance(x, dict) and bool(normalize_level_map(x)) for x in legacy_maps
    ):
        print(
            "注意: 各ソースの custom_level_mapping を優先します（トップレベル custom_level_mapping は、"
            "エントリ側が空のインデックスのフォールバックのみ）。",
            file=sys.stderr,
        )

    if not uses_source_tables_objects:
        disp_warn = cfg.get("source_table_display_names")
        if isinstance(disp_warn, list) and disp_warn and resolved_json_urls:
            if len(disp_warn) < len(resolved_json_urls):
                print(
                    "警告: source_table_display_names の要素数が元ヘッダー数より少ないです（足りない分はヘッダー名にフォールバック）。",
                    file=sys.stderr,
                )
            if len(disp_warn) > len(resolved_json_urls):
                print(
                    "警告: source_table_display_names の要素数が元ヘッダー数より多いです（余った要素は無視されます）。",
                    file=sys.stderr,
                )

        short_warn = cfg.get("source_table_short_names")
        if isinstance(short_warn, list) and short_warn and resolved_json_urls:
            if len(short_warn) < len(resolved_json_urls):
                print(
                    "警告: source_table_short_names の要素数が元ヘッダー数より少ないです（足りない分は略称なし）。",
                    file=sys.stderr,
                )
            if len(short_warn) > len(resolved_json_urls):
                print(
                    "警告: source_table_short_names の要素数が元ヘッダー数より多いです（余った要素は無視されます）。",
                    file=sys.stderr,
                )

    use_relative_data_url = cfg.get("use_relative_data_url", True)
    if not isinstance(use_relative_data_url, bool):
        use_relative_data_url = str(use_relative_data_url).strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

    site_base = (cfg.get("site_base_url") or os.environ.get("SITE_BASE_URL") or "").strip().rstrip("/")
    if not use_relative_data_url and not site_base:
        _die(
            "use_relative_data_url が false のときは site_base_url（設定）または "
            "環境変数 SITE_BASE_URL が必要です（data_url を絶対 URL で書くため）。"
        )

    songdata = cfg.get("songdata_db", "data/songdata.db")
    if not os.path.isfile(songdata):
        if cfg.get("skip_if_no_songdata", True):
            print(f"songdata.db が無いためスキップします: {songdata}", file=sys.stderr)
            raise SystemExit(0)
        _die(f"songdata.db が見つかりません: {songdata}")

    sql_where = resolve_sql_where(cfg)
    strict_id = not bool(cfg.get("sql_where_disable_identifier_whitelist"))
    md5s, sha256s = _query_allowed_hashes(songdata, sql_where, strict_identifiers=strict_id)
    print(f"許可ハッシュ数: md5={len(md5s)}, sha256={len(sha256s)} (WHERE {sql_where!r})")

    merged_rows: list[dict[str, Any]] = []
    row_by_key: dict[str, dict[str, Any]] = {}
    base_header: dict[str, Any] | None = None
    course_parts: list[Any] = []
    total_in = 0
    total_filtered = 0
    level_field = str(cfg.get("custom_level_source_key") or "level").strip() or "level"
    per_source_level_stats: list[dict[str, Any]] = []

    if (cfg.get("source_data_url") or "").strip() and multi_source:
        print(
            "警告: 複数ヘッダー指定時は各ヘッダーの data_url を使います（source_data_url は無視）。",
            file=sys.stderr,
        )

    fetch_timeout = float(cfg.get("http_fetch_timeout_seconds") or 120.0)
    fetch_retries = int(cfg.get("http_fetch_retries") or 3)
    fetch_backoff = float(cfg.get("http_fetch_backoff_seconds") or 2.0)

    for idx, header_json_url in enumerate(resolved_json_urls):
        raw_header = fetch_bytes(
            header_json_url,
            timeout=fetch_timeout,
            retries=fetch_retries,
            backoff_seconds=fetch_backoff,
        )
        header_obj = _json_from_http_body(raw_header, kind="ヘッダー", url=header_json_url)
        if not isinstance(header_obj, dict):
            _die(f"ヘッダー JSON のトップレベルはオブジェクトである必要があります: {header_json_url}")

        ov_disp = disp_cfg[idx] if idx < len(disp_cfg) else ""
        display_name = ov_disp if ov_disp else _header_display_name(header_obj, idx)
        short_label = short_cfg[idx] if idx < len(short_cfg) else ""

        if base_header is None:
            base_header = dict(header_obj)

        if (cfg.get("source_data_url") or "").strip() and not multi_source:
            data_url_raw = str(cfg.get("source_data_url") or "").strip()
        else:
            data_url_raw = str(header_obj.get("data_url") or "").strip()
        if not data_url_raw:
            _die(f"データ JSON の URL が取得できません: {header_json_url}")

        if re.match(r"^https?://", data_url_raw, re.IGNORECASE):
            data_url = data_url_raw
        else:
            data_url = urljoin(header_json_url, data_url_raw)

        raw_data = fetch_bytes(data_url, timeout=fetch_timeout, retries=fetch_retries, backoff_seconds=fetch_backoff)
        data_obj = _json_from_http_body(raw_data, kind="データ", url=data_url)
        if not isinstance(data_obj, list):
            _die(f"データ JSON のトップレベルは配列である必要があります: {data_url}")
        filtered_part = _filter_data_array(data_obj, md5s, sha256s)
        total_in += len(data_obj)
        total_filtered += len(filtered_part)
        print(
            f"[{idx + 1}/{len(resolved_json_urls)}] {header_json_url} データ: {len(data_obj)} -> {len(filtered_part)}"
        )

        by_level: dict[str, int] = {}
        for row in filtered_part:
            if not isinstance(row, dict):
                continue
            b = level_bucket_for_stats(row.get(level_field))
            by_level[b] = by_level.get(b, 0) + 1
        by_level_all: dict[str, int] = {}
        for row in data_obj:
            if not isinstance(row, dict):
                continue
            b = level_bucket_for_stats(row.get(level_field))
            by_level_all[b] = by_level_all.get(b, 0) + 1
        total_all = sum(by_level_all.values())

        sorted_level_keys = sort_level_stat_keys(list(by_level.keys()))
        by_level_ordered = {k: by_level[k] for k in sorted_level_keys}
        sorted_all_keys = sort_level_stat_keys(list(by_level_all.keys()))
        by_level_all_ordered = {k: by_level_all[k] for k in sorted_all_keys}
        level_rows = merge_level_compare_rows(by_level, by_level_all)
        per_source_level_stats.append(
            {
                "index": idx + 1,
                "display_name": display_name,
                "short_name": short_label,
                "total_filtered": len(filtered_part),
                "total_all": total_all,
                "by_level": by_level_ordered,
                "by_level_all": by_level_all_ordered,
                "level_rows": level_rows,
            }
        )

        page_or_cfg_url = header_urls_cfg[idx] if idx < len(header_urls_cfg) else ""

        for row in filtered_part:
            if not isinstance(row, dict):
                continue
            dk = _row_dedupe_key(row)
            new_row = dict(row)

            _apply_custom_level(new_row, idx, level_maps, cfg)

            if dk is None:
                new_row["source_table_index"] = idx + 1
                new_row["source_table_names"] = [display_name]
                new_row["source_table_short_names"] = [short_label] if short_label else []
                if page_or_cfg_url:
                    new_row["source_table_register_url"] = page_or_cfg_url
                new_row["source_header_json_url"] = header_json_url
                merged_rows.append(new_row)
                continue

            if dk in row_by_key:
                prev = row_by_key[dk]
                names = prev.get("source_table_names")
                if not isinstance(names, list):
                    names = []
                    prev["source_table_names"] = names
                if display_name not in names:
                    names.append(display_name)
                shorts = prev.get("source_table_short_names")
                if not isinstance(shorts, list):
                    shorts = []
                    prev["source_table_short_names"] = shorts
                if short_label and short_label not in shorts:
                    shorts.append(short_label)
                continue

            new_row["source_table_index"] = idx + 1
            new_row["source_table_names"] = [display_name]
            new_row["source_table_short_names"] = [short_label] if short_label else []
            if page_or_cfg_url:
                new_row["source_table_register_url"] = page_or_cfg_url
            new_row["source_header_json_url"] = header_json_url
            row_by_key[dk] = new_row
            merged_rows.append(new_row)

        if "course" in header_obj:
            course_parts.append(_filter_course_structure(header_obj["course"], md5s, sha256s))

    if base_header is None:
        _die("ヘッダーを 1 件も読み込めませんでした。")

    new_header: dict[str, Any] = dict(base_header)
    merged_course = _merge_course_parts(course_parts)
    if merged_course is not None:
        new_header["course"] = merged_course
    else:
        new_header.pop("course", None)

    filtered_data = merged_rows
    print(
        f"データ行（全ソース合算・重複除去後）: 入力 {total_in} 行、条件通過 {total_filtered}、ユニーク {len(filtered_data)}"
    )

    out_dir = cfg.get("output_dir", "docs/table")
    data_name = cfg.get("output_data_filename", "filtered_data.json")
    header_name = cfg.get("output_header_filename", "filtered_header.json")
    os.makedirs(out_dir, exist_ok=True)
    data_path = os.path.join(out_dir, data_name)
    header_path = os.path.join(out_dir, header_name)

    if use_relative_data_url:
        new_header["data_url"] = os.path.basename(data_name)
    else:
        new_header["data_url"] = f"{site_base}/{data_name}"

    sanitize_header_for_beatoraja(new_header, cfg)

    strip_keys = strip_keys_cfg(cfg)
    enriched_name = (
        str(cfg.get("output_data_enriched_filename") or "filtered_data_enriched.json").strip()
        or "filtered_data_enriched.json"
    )
    enriched_path = os.path.join(out_dir, enriched_name)
    _save_json(enriched_path, filtered_data)

    dropped = 0
    beatoraja_rows: list[dict[str, Any]] = []
    for r in filtered_data:
        clean = sanitize_chart_row_for_beatoraja(r, strip_keys)
        normalize_beatoraja_chart_row(clean)
        if row_passes_beatoraja_strict_decoder(clean):
            beatoraja_rows.append(clean)
        else:
            dropped += 1
    if dropped:
        print(
            f"警告: beatoraja 厳格デコードに合わない行を {dropped} 件スキップしました（{enriched_name} には残します）。",
            file=sys.stderr,
        )

    if not beatoraja_rows:
        print(
            "エラー: beatoraja 向けデータ行が 0 件です。"
            " 本体は TableData.validate() で失敗し「難易度表の値が不正です」になります。"
            " songdata.db を更新するか sql_where を見直し、"
            " 元表とハッシュが交差する行が少なくとも 1 件残るようにしてください。",
            file=sys.stderr,
        )
        if os.environ.get("GITHUB_ACTIONS") == "true":
            print("::error title=難易度表フィルタ::beatoraja 向けデータ行が 0 件です", file=sys.stderr)

    policy_fail = _empty_rows_policy_fail(cfg)
    if not beatoraja_rows and policy_fail:
        raise SystemExit(1)

    _save_json(data_path, beatoraja_rows)
    _save_json(header_path, new_header)
    stats_name = str(cfg.get("output_level_stats_filename") or "level_stats.json").strip() or "level_stats.json"
    stats_path = os.path.join(out_dir, stats_name)
    stats_payload: dict[str, Any] = {
        "version": 2,
        "level_field": level_field,
        "sql_where": sql_where,
        "sources": per_source_level_stats,
    }
    _save_json(stats_path, stats_payload)
    print(f"書き出し: {stats_path}")
    if use_relative_data_url:
        table_url_hint = (
            f"Table URL にはヘッダー JSON（例: …/table/{header_name}）を登録してください。"
            f" data_url はヘッダー URL からの相対パス: {new_header.get('data_url')!r}"
        )
    else:
        table_url_hint = f"公開用 Table URL 候補: {site_base}/{header_name}"
    print(
        f"書き出し: {enriched_path}（Pages 用・拡張列あり）\n"
        f"書き出し: {data_path}（beatoraja 用・拡張列除去）\n"
        f"書き出し: {header_path}\n{table_url_hint}"
    )


if __name__ == "__main__":
    main()
