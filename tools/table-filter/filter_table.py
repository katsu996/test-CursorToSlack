#!/usr/bin/env python3
"""
songdata.db の song テーブルに対する WHERE 断片で許可ハッシュ集合を作り、
難易度表のヘッダー JSON / データ JSON を突き合わせてフィルタした結果を docs に書き出す。

beatoraja の songdata.db（テーブル song）を想定。実行は GitHub Actions でもローカルでも可（標準ライブラリのみ）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import urllib.request
from typing import Any, Mapping, MutableMapping
from urllib.parse import urljoin

DEFAULT_CONFIG = "tools/table-filter/filter_config.json"


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
                            inner.append(sub)
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

    site_base = (cfg.get("site_base_url") or os.environ.get("SITE_BASE_URL") or "").strip().rstrip("/")
    if not site_base:
        _die("site_base_url（設定）または環境変数 SITE_BASE_URL が必要です（data_url を書き換えるため）。")

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
    seen_keys: set[str] = set()
    base_header: dict[str, Any] | None = None
    course_parts: list[Any] = []
    total_in = 0
    total_filtered = 0

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

        for row in filtered_part:
            if not isinstance(row, dict):
                continue
            dk = _row_dedupe_key(row)
            if dk is None or dk in seen_keys:
                continue
            seen_keys.add(dk)
            merged_rows.append(row)

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

    new_header["data_url"] = f"{site_base}/{data_name}"

    _save_json(data_path, filtered_data)
    _save_json(header_path, new_header)
    print(f"書き出し: {data_path}\n書き出し: {header_path}\n公開用 Table URL 候補: {site_base}/{header_name}")


if __name__ == "__main__":
    main()
