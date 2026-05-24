#!/usr/bin/env python3
"""
songdata.db の song テーブルに対する WHERE 断片で許可ハッシュ集合を作り、
難易度表のヘッダー JSON / データ JSON を突き合わせてフィルタした結果を docs に書き出す。

複数元表をマージするときは各行に source_table_index / source_table_names などを付与する。
`source_table_display_names` があれば `source_table_names` のラベルに優先して使う。
`source_table_short_names` があれば `source_table_short_names`（略称の配列）に優先して使う。

beatoraja の songdata.db（テーブル song）を想定。実行は GitHub Actions でもローカルでも可（標準ライブラリのみ）。

成功時、難易度表データに加え、元表ごとのレベル別曲数（SQL 条件通過後と、元表データ行全体）を
`output_level_stats_filename`（既定: `level_stats.json`）にも書き出す。

beatoraja（jbmstable-parser）はデータ行に厳格な条件があるため、`output_data_filename`（既定 `filtered_data.json`）には
出自メタ等を除いた行だけを書き、GitHub Pages 用の拡張列付きは `output_data_enriched_filename`（既定 `filtered_data_enriched.json`）に保存する。
生成ヘッダーの `data_url` は既定でファイル名のみ（ヘッダー JSON と同じディレクトリから解決）とし、
`use_relative_data_url: false` のときだけ `site_base_url` / `SITE_BASE_URL` で絶対 URL を組み立てる。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import urllib.request
from typing import Any, Mapping, MutableMapping, Sequence
from urllib.parse import urljoin

DEFAULT_CONFIG = "tools/table-filter/filter_config.json"

# beatoraja / jbmstable-parser の decodeJSONTableData(..., accept=false) が要求する行条件に合わせ、
# また Pages 用に付与した拡張キーはデータ部から除外する（仕様: exch-bms2/jbmstable-parser）。
_DEFAULT_BEATORAJA_STRIP_CHART_KEYS: frozenset[str] = frozenset(
    (
        "source_table_index",
        "source_table_names",
        "source_table_short_names",
        "source_header_json_url",
        "source_table_register_url",
        # LR2 用の数値 id など、仕様外で型が揺れると不具合の原因になり得るため除外
        "id",
    )
)


def _die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _fetch_url(url: str, timeout: float = 120.0) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "beatoraja-table-filter/1.0 (GitHub Actions; +https://github.com)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _normalize_cfg_header_urls(cfg: Mapping[str, Any]) -> list[str]:
    urls_raw = cfg.get("source_header_urls")
    if isinstance(urls_raw, list):
        out = [str(u).strip() for u in urls_raw if str(u).strip()]
        if out:
            return out
    single = str(cfg.get("source_header_url") or "").strip()
    return [single] if single else []


def _resolve_bmstable_header_url(page_or_json_url: str) -> str:
    """
    難易度表登録用 HTML（<meta name="bmstable" content="header.json">）または
    ヘッダー JSON の URL を受け取り、ヘッダー JSON の絶対 URL を返す。
    """
    u = page_or_json_url.strip()
    low = u.lower()
    if low.endswith(".htm") or low.endswith(".html"):
        raw = _fetch_url(u).decode("utf-8", errors="replace")
        m = re.search(
            r'<meta\s+name=["\']bmstable["\']\s+content=["\']([^"\']+)["\']',
            raw,
            re.IGNORECASE,
        )
        if not m:
            m = re.search(
                r'<meta\s+content=["\']([^"\']+)["\']\s+name=["\']bmstable["\']',
                raw,
                re.IGNORECASE,
            )
        if not m:
            _die(f"HTML から bmstable の meta が取得できません: {u}")
        rel = m.group(1).strip()
        return urljoin(u, rel)
    return u


def _header_display_name(header_obj: Mapping[str, Any], idx: int) -> str:
    """ヘッダー JSON の name / title などから、マージ後の行に付与する表ラベルを決める。"""
    for key in ("name", "Name", "title", "Title"):
        v = header_obj.get(key)
        if v is not None:
            s = str(v).strip()
            if s:
                return s
    return f"表 {idx + 1}"


def _table_display_label(cfg: Mapping[str, Any], idx: int, header_obj: Mapping[str, Any]) -> str:
    """
    source_table_names / Pages 向けの表ラベル。
    filter_config の source_table_display_names[i] が非空ならそれを優先し、
    無ければヘッダー JSON の name / title などにフォールバックする。
    """
    raw = cfg.get("source_table_display_names")
    if isinstance(raw, list) and idx < len(raw):
        s = str(raw[idx]).strip()
        if s:
            return s
    return _header_display_name(header_obj, idx)


def _table_short_label(cfg: Mapping[str, Any], idx: int) -> str:
    """
    行の source_table_short_names に入れる略称（1 表あたり 1 文字列）。
    source_table_short_names[i] が非空ならそれを、無ければ空（Pages 側は表番号などにフォールバック可）。
    """
    raw = cfg.get("source_table_short_names")
    if isinstance(raw, list) and idx < len(raw):
        return str(raw[idx]).strip()
    return ""


def _merge_course_parts(parts: list[Any]) -> Any:
    """複数ヘッダーの course をトップレベル配列として連結（空は None）。"""
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


def _validate_sql_where(fragment: str) -> None:
    if not fragment or not fragment.strip():
        _die("設定 sql_where が空です。例: minbpm IS NOT NULL AND maxbpm IS NOT NULL AND minbpm = maxbpm")
    frag = fragment.strip()
    if len(frag) > 500:
        _die("sql_where が長すぎます（上限 500 文字）。")
    lower = frag.lower()
    banned_sub = (";", "--", "/*", "*/")
    for b in banned_sub:
        if b in frag:
            _die(f"sql_where に禁止部分 '{b}' が含まれています。")
    banned_words = (
        "attach",
        "detach",
        "pragma",
        "sqlite_",
        "drop ",
        "delete ",
        "insert ",
        "update ",
        "create ",
        "replace ",
        "trigger ",
        "vacuum",
    )
    for w in banned_words:
        if w in lower:
            _die(f"sql_where に禁止キーワードに該当する部分が含まれています: {w.strip()!r}")


def _query_allowed_hashes(db_path: str, sql_where: str) -> tuple[set[str], set[str]]:
    _validate_sql_where(sql_where)
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


def _validate_json_field_name(name: str, label: str) -> None:
    if not name:
        _die(f"{label} が空です。")
    if len(name) > 64:
        _die(f"{label} が長すぎます（上限 64 文字）。")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        _die(f"{label} は英字またはアンダースコアで始まり、英数字とアンダースコアのみ使えます: {name!r}")


def _normalize_level_map(raw: Any) -> dict[str, Any]:
    """custom_level_mapping の各要素（オブジェクト）をレベル文字列キーへ正規化する。"""
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for k, v in raw.items():
        key = str(k).strip()
        if key:
            out[key] = v
    return out


def _row_level_lookup_keys(raw_lvl: Any) -> list[str]:
    """表 JSON のレベル値からマップ検索用キーの候補（型の揺れを吸収）。"""
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


_UNSET_LEVEL_LABEL = "(未設定)"


def _level_bucket_for_stats(raw_lvl: Any) -> str:
    """
    レベル別件数集計用のバケット文字列。表 JSON の level の型揺れをできるだけ同じ桶に寄せる。
    """
    if raw_lvl is None:
        return _UNSET_LEVEL_LABEL
    if isinstance(raw_lvl, bool):
        return str(raw_lvl).lower()
    if isinstance(raw_lvl, int):
        return str(raw_lvl)
    if isinstance(raw_lvl, float):
        if raw_lvl.is_integer():
            return str(int(raw_lvl))
        s = str(raw_lvl).strip()
        return s if s else _UNSET_LEVEL_LABEL
    s = str(raw_lvl).strip()
    if not s:
        return _UNSET_LEVEL_LABEL
    try:
        f = float(s.replace(",", ""))
        if f.is_integer():
            return str(int(f))
    except ValueError:
        pass
    return s


def _sort_level_stat_keys(keys: list[str]) -> list[str]:
    """数値らしいキーを先に昇順、最後に (未設定)。"""

    def sort_key(k: str) -> tuple[int, float, str]:
        if k == _UNSET_LEVEL_LABEL:
            return (2, 0.0, k)
        try:
            return (0, float(int(k)), k)
        except ValueError:
            pass
        try:
            return (1, float(k), k)
        except ValueError:
            return (1, 0.0, k)

    return sorted(keys, key=sort_key)


def _merge_level_compare_rows(by_sql: dict[str, int], by_all: dict[str, int]) -> list[dict[str, Any]]:
    """SQL 条件後・条件前のレベル別件数を同一行に並べる（Pages 用）。"""
    keys = _sort_level_stat_keys(list(set(by_sql.keys()) | set(by_all.keys())))
    return [{"level": k, "after_sql": by_sql.get(k, 0), "before_sql": by_all.get(k, 0)} for k in keys]


def _apply_custom_level(row: MutableMapping[str, Any], source_idx: int, cfg: Mapping[str, Any]) -> None:
    """
    source_header_urls の並びと同じインデックスのマップで、元表のレベルを独自レベル列に書き込む。
    custom_level_mapping[i] は {元レベル文字列: 独自レベル（数値または文字列）} 形式のオブジェクト。
    """
    maps_raw = cfg.get("custom_level_mapping")
    if not isinstance(maps_raw, Sequence) or isinstance(maps_raw, (str, bytes)):
        return
    if source_idx < 0 or source_idx >= len(maps_raw):
        return
    m = _normalize_level_map(maps_raw[source_idx])
    if not m:
        return

    out_key = str(cfg.get("custom_level_field") or "custom_level").strip() or "custom_level"
    src_key = str(cfg.get("custom_level_source_key") or "level").strip() or "level"
    _validate_json_field_name(out_key, "custom_level_field")
    _validate_json_field_name(src_key, "custom_level_source_key")

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
    """course は配列の配列や単一配列など差異があるため、dict で charts を持つノードだけを対象に再帰する。"""
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


def _strip_keys_cfg(cfg: Mapping[str, Any]) -> frozenset[str]:
    """
    beatoraja 向けデータ JSON から除外するキー。
    None（未指定）なら既定（出自メタ等）。空配列なら除外なし。
    """
    raw = cfg.get("beatoraja_strip_chart_keys")
    if raw is None:
        return _DEFAULT_BEATORAJA_STRIP_CHART_KEYS
    if isinstance(raw, list):
        return frozenset(str(x).strip() for x in raw if str(x).strip())
    return _DEFAULT_BEATORAJA_STRIP_CHART_KEYS


def _sanitize_chart_row_for_beatoraja(row: Mapping[str, Any], strip_keys: frozenset[str]) -> dict[str, Any]:
    return {k: v for k, v in row.items() if k not in strip_keys}


def _normalize_beatoraja_chart_row(row: MutableMapping[str, Any]) -> None:
    """
    jbmstable-parser / beatoraja が想定する文字列中心の形に寄せる。
    数値の level や空タイトルは SongData.validate や getElements のソートで落ちやすい。
    """
    lv = row.get("level")
    if lv is not None and not isinstance(lv, str):
        row["level"] = str(lv).strip()

    for key in ("artist", "url", "url_diff"):
        v = row.get(key)
        if v is None:
            row[key] = ""
        elif not isinstance(v, str):
            row[key] = str(v)

    t = row.get("title")
    if t is None:
        row["title"] = "（無題）"
    elif not isinstance(t, str):
        row["title"] = str(t)
    if not str(row.get("title", "")).strip():
        row["title"] = "（無題）"

    for hkey in ("md5", "sha256"):
        hv = row.get(hkey)
        if hv is not None and not isinstance(hv, str):
            row[hkey] = str(hv)


def _row_passes_beatoraja_strict_decoder(row: Mapping[str, Any]) -> bool:
    """
    jbmstable-parser の DifficultyTableParser.decodeJSONTableData(..., accept=false)
    と同様に、level 必須かつ md5 または sha256 の文字列表現が長さ 24 超であること。
    """
    if row.get("level") is None:
        return False
    md5 = row.get("md5")
    sha = row.get("sha256")
    md5_ok = md5 is not None and len(str(md5).strip()) > 24
    sha_ok = sha is not None and len(str(sha).strip()) > 24
    return md5_ok or sha_ok


def _sanitize_header_for_beatoraja(header: MutableMapping[str, Any], cfg: Mapping[str, Any]) -> None:
    """
    course が空配列のヘッダは jbmstable-parser が IndexOutOfBounds するためキーごと削除。
    name が空だと beatoraja の TableData.validate() が失敗し「難易度表の値が不正です」になるため補完する。
    """
    c = header.get("course")
    if isinstance(c, list) and len(c) == 0:
        header.pop("course", None)

    forced = str(cfg.get("output_header_name") or "").strip()
    if forced:
        header["name"] = forced
    else:
        name = str(header.get("name") or "").strip()
        if not name:
            fb = "Filtered difficulty table (songdata)"
            header["name"] = fb


def main() -> None:
    ap = argparse.ArgumentParser(description="songdata.db と難易度表 JSON を突き合わせてフィルタする")
    ap.add_argument("--config", default=os.environ.get("FILTER_CONFIG", DEFAULT_CONFIG), help="設定 JSON のパス")
    args = ap.parse_args()

    cfg_path = args.config
    if not os.path.isfile(cfg_path):
        print(f"設定ファイルが無いためスキップします: {cfg_path}", file=sys.stderr)
        raise SystemExit(0)

    cfg = _load_json(cfg_path)
    if not cfg.get("enabled", True):
        print("filter_config の enabled が false のためスキップします。", file=sys.stderr)
        raise SystemExit(0)

    header_urls_cfg = _normalize_cfg_header_urls(cfg)
    if not header_urls_cfg:
        print(
            "source_header_urls / source_header_url が空のためスキップします（難易度表フィルタは行いません）。",
            file=sys.stderr,
        )
        raise SystemExit(0)

    resolved_json_urls = [_resolve_bmstable_header_url(u) for u in header_urls_cfg]
    multi_source = len(resolved_json_urls) > 1

    maps_raw_warn = cfg.get("custom_level_mapping")
    if isinstance(maps_raw_warn, list) and len(maps_raw_warn) > 0 and resolved_json_urls:
        if len(maps_raw_warn) < len(resolved_json_urls):
            print(
                "警告: custom_level_mapping の要素数が元ヘッダー数より少ないです（足りないインデックスはマップ無し）。",
                file=sys.stderr,
            )
        if len(maps_raw_warn) > len(resolved_json_urls):
            print(
                "警告: custom_level_mapping の要素数が元ヘッダー数より多いです（余った要素は無視されます）。",
                file=sys.stderr,
            )

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

    sql_where = str(cfg.get("sql_where", "")).strip()
    md5s, sha256s = _query_allowed_hashes(songdata, sql_where)
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

    for idx, header_json_url in enumerate(resolved_json_urls):
        raw_header = _fetch_url(header_json_url)
        header_obj = json.loads(raw_header.decode("utf-8"))
        if not isinstance(header_obj, dict):
            _die(f"ヘッダー JSON のトップレベルはオブジェクトである必要があります: {header_json_url}")

        display_name = _table_display_label(cfg, idx, header_obj)
        short_label = _table_short_label(cfg, idx)

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

        raw_data = _fetch_url(data_url)
        data_obj = json.loads(raw_data.decode("utf-8"))
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
            b = _level_bucket_for_stats(row.get(level_field))
            by_level[b] = by_level.get(b, 0) + 1
        by_level_all: dict[str, int] = {}
        for row in data_obj:
            if not isinstance(row, dict):
                continue
            b = _level_bucket_for_stats(row.get(level_field))
            by_level_all[b] = by_level_all.get(b, 0) + 1
        total_all = sum(by_level_all.values())
        sorted_level_keys = _sort_level_stat_keys(list(by_level.keys()))
        by_level_ordered = {k: by_level[k] for k in sorted_level_keys}
        sorted_all_keys = _sort_level_stat_keys(list(by_level_all.keys()))
        by_level_all_ordered = {k: by_level_all[k] for k in sorted_all_keys}
        level_rows = _merge_level_compare_rows(by_level, by_level_all)
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

            _apply_custom_level(new_row, idx, cfg)

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
        # 元表と同様にファイル名のみ。beatoraja / jbmstable-parser はヘッダー JSON の URL を基準に解決する。
        new_header["data_url"] = os.path.basename(data_name)
    else:
        new_header["data_url"] = f"{site_base}/{data_name}"

    _sanitize_header_for_beatoraja(new_header, cfg)

    strip_keys = _strip_keys_cfg(cfg)
    enriched_name = (
        str(cfg.get("output_data_enriched_filename") or "filtered_data_enriched.json").strip()
        or "filtered_data_enriched.json"
    )
    enriched_path = os.path.join(out_dir, enriched_name)
    _save_json(enriched_path, filtered_data)

    dropped = 0
    beatoraja_rows: list[dict[str, Any]] = []
    for r in filtered_data:
        clean = _sanitize_chart_row_for_beatoraja(r, strip_keys)
        _normalize_beatoraja_chart_row(clean)
        if _row_passes_beatoraja_strict_decoder(clean):
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
