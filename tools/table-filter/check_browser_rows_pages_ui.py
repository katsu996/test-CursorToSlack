#!/usr/bin/env python3
"""
browser_rows.json の meta.pages_ui を検証し、Pages トップが壊れにくい形かを CI で早期検知する。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any


def _load_json(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate_pages_ui(pages_ui: Any) -> list[str]:
    errs: list[str] = []
    if not isinstance(pages_ui, dict):
        return ["meta.pages_ui がオブジェクトではありません"]
    for key in ("index_table", "column_widths", "column_visible_defaults"):
        if key not in pages_ui:
            errs.append(f"meta.pages_ui に必須キー '{key}' がありません")
    if errs:
        return errs
    it = pages_ui.get("index_table")
    if not isinstance(it, dict):
        return errs + ["meta.pages_ui.index_table がオブジェクトではありません"]
    for k in ("table_column_order", "db_column_order", "ir_subcolumns", "chart_column"):
        if k not in it:
            errs.append(f"index_table に必須キー '{k}' がありません")
    ir = it.get("ir_subcolumns")
    if not isinstance(ir, list) or len(ir) < 1:
        errs.append("index_table.ir_subcolumns は 1 要素以上の配列である必要があります")
    else:
        for i, col in enumerate(ir):
            if not isinstance(col, dict):
                errs.append(f"ir_subcolumns[{i}] がオブジェクトではありません")
                continue
            for ck in ("colgroup_key", "href_template", "hash_kind"):
                if ck not in col:
                    errs.append(f"ir_subcolumns[{i}] に '{ck}' がありません")
    cc = it.get("chart_column")
    if not isinstance(cc, dict):
        errs.append("index_table.chart_column がオブジェクトではありません")
    else:
        for ck in ("colgroup_key", "href_template", "hash_kind"):
            if ck not in cc:
                errs.append(f"chart_column に '{ck}' がありません")
    tt = it.get("trailing_table_columns")
    if tt is not None:
        if not isinstance(tt, list):
            errs.append("index_table.trailing_table_columns は配列である必要があります")
        else:
            for i, x in enumerate(tt):
                if not isinstance(x, str) or not x.strip():
                    errs.append(f"trailing_table_columns[{i}] は非空の文字列である必要があります")
    lt = it.get("leading_table_columns")
    if lt is not None:
        if not isinstance(lt, list):
            errs.append("index_table.leading_table_columns は配列である必要があります")
        else:
            for i, x in enumerate(lt):
                if not isinstance(x, str) or not x.strip():
                    errs.append(f"leading_table_columns[{i}] は非空の文字列である必要があります")
    cw = pages_ui.get("column_widths")
    if not isinstance(cw, dict):
        errs.append("column_widths がオブジェクトではありません")
    vis = pages_ui.get("column_visible_defaults")
    if not isinstance(vis, dict):
        errs.append("column_visible_defaults がオブジェクトではありません")
    else:
        for sec in ("table", "db"):
            if sec in vis and not isinstance(vis[sec], dict):
                errs.append(f"column_visible_defaults.{sec} がオブジェクトではありません")
    return errs


def validate_browser_rows(data: Any) -> list[str]:
    errs: list[str] = []
    if not isinstance(data, dict):
        return ["browser_rows.json のトップレベルがオブジェクトではありません"]
    if "meta" not in data:
        errs.append("meta がありません")
    meta = data.get("meta")
    if not isinstance(meta, dict):
        return errs + ["meta がオブジェクトではありません"]
    pu = meta.get("pages_ui")
    errs.extend(validate_pages_ui(pu))
    if "rows" not in data:
        errs.append("rows がありません")
    elif not isinstance(data.get("rows"), list):
        errs.append("rows が配列ではありません")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser(description="browser_rows.json の meta.pages_ui を検証")
    ap.add_argument("--path", default="docs/table/browser_rows.json", help="browser_rows.json のパス")
    args = ap.parse_args()
    path = args.path
    if not os.path.isfile(path):
        print(f"check_browser_rows: スキップ（ファイルなし）: {path}", file=sys.stderr)
        return 0
    try:
        data = _load_json(path)
    except (OSError, json.JSONDecodeError) as e:
        print(f"check_browser_rows: エラー: {path}: {e}", file=sys.stderr)
        return 1
    errs = validate_browser_rows(data)
    if errs:
        for e in errs:
            print(f"check_browser_rows: エラー: {e}", file=sys.stderr)
        if os.environ.get("GITHUB_ACTIONS") == "true":
            print("::error title=browser_rows::meta.pages_ui の検証に失敗しました", file=sys.stderr)
        return 1
    print(f"check_browser_rows: OK（{path}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
