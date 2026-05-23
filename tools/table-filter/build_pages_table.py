#!/usr/bin/env python3
"""
難易度表フィルタ後の filtered_data.json 各行を songdata.db の song と突き合わせ、
GitHub Pages のトップページ用にブラウザ向け JSON（表の列＋DB列）を書き出す。

filter_table.py の後に実行することを想定（標準ライブラリのみ）。
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from typing import Any

DEFAULT_CONFIG = "tools/table-filter/filter_config.json"


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _norm_hash(s: Any) -> str:
    return str(s or "").strip().lower()


def main() -> None:
    ap = argparse.ArgumentParser(description="filtered_data と songdata.db を突合し browser_rows.json を出力")
    ap.add_argument("--config", default=os.environ.get("FILTER_CONFIG", DEFAULT_CONFIG), help="filter_config.json のパス")
    args = ap.parse_args()
    cfg_path = args.config
    default_out = os.path.join("docs", "table", "browser_rows.json")

    if not os.path.isfile(cfg_path):
        print(f"設定が無いためスキップ: {cfg_path}", file=sys.stderr)
        _save_json(default_out, {"meta": {"reason": "設定ファイルなし"}, "rows": []})
        return

    cfg = _load_json(cfg_path)
    out_dir = cfg.get("output_dir", "docs/table")
    data_name = cfg.get("output_data_filename", "filtered_data.json")
    filtered_path = os.path.join(out_dir, data_name)
    songdata_path = cfg.get("songdata_db", "data/songdata.db")
    browser_name = cfg.get("browser_rows_filename", "browser_rows.json")
    browser_path = os.path.join(out_dir, browser_name)

    if not os.path.isfile(filtered_path):
        print(f"filtered_data が無いため空の browser_rows を出力: {filtered_path}", file=sys.stderr)
        _save_json(
            browser_path,
            {
                "meta": {
                    "reason": "filtered_data.json が無い（フィルタ未実行またはスキップ）",
                    "filtered_path": filtered_path,
                },
                "rows": [],
            },
        )
        return

    filtered = _load_json(filtered_path)
    if not isinstance(filtered, list):
        print("filtered_data のトップレベルが配列ではありません。", file=sys.stderr)
        _save_json(browser_path, {"meta": {"reason": "invalid filtered_data"}, "rows": []})
        return

    md5s: set[str] = set()
    shas: set[str] = set()
    for r in filtered:
        if not isinstance(r, dict):
            continue
        m = _norm_hash(r.get("md5"))
        s = _norm_hash(r.get("sha256"))
        if len(m) == 32:
            md5s.add(m)
        if len(s) == 64:
            shas.add(s)

    song_by_sha: dict[str, dict[str, Any]] = {}
    song_by_md5: dict[str, dict[str, Any]] = {}

    if os.path.isfile(songdata_path) and (md5s or shas):
        con = sqlite3.connect(f"file:{songdata_path}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        try:
            cur = con.cursor()
            params: list[str] = []
            parts: list[str] = []
            if shas:
                ph = ",".join("?" * len(shas))
                parts.append(f"LOWER(TRIM(sha256)) IN ({ph})")
                params.extend(shas)
            if md5s:
                phm = ",".join("?" * len(md5s))
                parts.append(f"LOWER(TRIM(md5)) IN ({phm})")
                params.extend(md5s)
            sql = "SELECT * FROM song WHERE " + " OR ".join(parts)
            cur.execute(sql, params)
            for row in cur.fetchall():
                d = {k: row[k] for k in row.keys()}
                sha = _norm_hash(d.get("sha256"))
                md = _norm_hash(d.get("md5"))
                if len(sha) == 64:
                    song_by_sha[sha] = d
                if len(md) == 32:
                    song_by_md5[md] = d
        finally:
            con.close()

    rows_out: list[dict[str, Any]] = []
    for r in filtered:
        if not isinstance(r, dict):
            continue
        t = dict(r)
        sha = _norm_hash(t.get("sha256"))
        md = _norm_hash(t.get("md5"))
        db: dict[str, Any] | None = None
        if len(sha) == 64 and sha in song_by_sha:
            db = dict(song_by_sha[sha])
        elif len(md) == 32 and md in song_by_md5:
            db = dict(song_by_md5[md])
        rows_out.append({"table": t, "db": db})

    meta = {
        "row_count": len(rows_out),
        "matched_songdata": sum(1 for x in rows_out if x["db"] is not None),
        "sql_where": str(cfg.get("sql_where", "")).strip(),
        "source_header_url": str(cfg.get("source_header_url", "")).strip(),
    }
    _save_json(browser_path, {"meta": meta, "rows": rows_out})
    print(f"書き出し: {browser_path} （{len(rows_out)} 行、DB 一致 {meta['matched_songdata']}）")


if __name__ == "__main__":
    main()
