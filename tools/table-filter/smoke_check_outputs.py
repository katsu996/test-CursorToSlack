#!/usr/bin/env python3
"""
デプロイ前の軽い検証: filtered_header.json / filtered_data.json の JSON 形式と
beatoraja が読みやすい最低限の条件（空配列でないことなど）。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from source_tables import normalize_source_tables


def _load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="tools/table-filter/filter_config.json")
    args = ap.parse_args()
    cfg_path = args.config
    if not os.path.isfile(cfg_path):
        print(f"smoke: 設定なしのためスキップ: {cfg_path}", file=sys.stderr)
        return 0

    cfg = _load_json(cfg_path)
    if not cfg.get("enabled", True):
        print("smoke: enabled=false のためスキップ", file=sys.stderr)
        return 0

    header_urls, _, _ = normalize_source_tables(cfg)
    has_src = bool(header_urls)
    if not has_src:
        print("smoke: 元表 URL が空のためフィルタ未実行想定でスキップ", file=sys.stderr)
        return 0

    out_dir = str(cfg.get("output_dir", "docs/table"))
    header_name = str(cfg.get("output_header_filename", "filtered_header.json"))
    data_name = str(cfg.get("output_data_filename", "filtered_data.json"))
    header_path = os.path.join(out_dir, header_name)
    data_path = os.path.join(out_dir, data_name)

    if not os.path.isfile(header_path):
        print(f"smoke: ヘッダーが無いためスキップ: {header_path}", file=sys.stderr)
        return 0

    header = _load_json(header_path)
    if not isinstance(header, dict):
        print("smoke: エラー: ヘッダー JSON のトップレベルがオブジェクトではありません。", file=sys.stderr)
        return 1

    name = str(header.get("name") or "").strip()
    if not name:
        print("smoke: エラー: filtered_header.json の name が空です。", file=sys.stderr)
        return 1

    data_url = header.get("data_url")
    if not isinstance(data_url, str) or not data_url.strip():
        print("smoke: エラー: data_url が無いか文字列ではありません。", file=sys.stderr)
        return 1
    if "://" in data_url.strip():
        print(
            "smoke: 警告: data_url が絶対 URL です（相対運用でない場合は意図どおりか確認してください）。",
            file=sys.stderr,
        )

    if not os.path.isfile(data_path):
        print(f"smoke: エラー: データ JSON が無い: {data_path}", file=sys.stderr)
        return 1

    data = _load_json(data_path)
    if not isinstance(data, list):
        print("smoke: エラー: filtered_data.json のトップレベルは配列である必要があります。", file=sys.stderr)
        return 1

    if len(data) == 0:
        print(
            "smoke: エラー: filtered_data.json が空配列です。"
            " beatoraja は TableData.validate() で失敗します。",
            file=sys.stderr,
        )
        if os.environ.get("GITHUB_ACTIONS") == "true":
            print("::error title=smoke::filtered_data.json が空です", file=sys.stderr)
        return 1

    print(f"smoke: OK（{header_name} / {data_name}、データ {len(data)} 行）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
