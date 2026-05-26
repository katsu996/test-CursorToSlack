#!/usr/bin/env python3
"""
filter_config.example.json のトップレベルキーが、想定スキーマ集合と一致するか検証する。
（_ で始まる説明用キーは除外）
"""

from __future__ import annotations

import json
import os
import sys

# docs/filter-config-schema.md と同期すること（キー追加時は両方更新）
EXPECTED_KEYS: frozenset[str] = frozenset(
    {
        "enabled",
        "skip_if_no_songdata",
        "songdata_db",
        "sql_where",
        "sql_where_preset",
        "sql_where_disable_identifier_whitelist",
        "source_tables",
        "source_tables_path",
        "source_header_url",
        "source_data_url",
        "output_dir",
        "output_data_filename",
        "output_data_enriched_filename",
        "output_header_filename",
        "output_header_name",
        "page_title",
        "output_level_stats_filename",
        "browser_rows_filename",
        "pages_ui_config_path",
        "site_base_url",
        "use_relative_data_url",
        "custom_level_mapping",
        "custom_level_field",
        "custom_level_source_key",
        "custom_level_unmapped",
        "beatoraja_strip_chart_keys",
        "beatoraja_empty_rows_policy",
        "http_fetch_timeout_seconds",
        "http_fetch_retries",
        "http_fetch_backoff_seconds",
    }
)


def main() -> int:
    root = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(root, "config", "filter_config.example.json")
    with open(path, encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        print("example がオブジェクトではありません", file=sys.stderr)
        return 1
    keys = {k for k in obj if not str(k).startswith("_")}
    missing = sorted(EXPECTED_KEYS - keys)
    extra = sorted(keys - EXPECTED_KEYS)
    if missing:
        print("example に不足キー:", ", ".join(missing), file=sys.stderr)
    if extra:
        print("example に未登録のキー（EXPECTED_KEYS を更新）:", ", ".join(extra), file=sys.stderr)
    if missing or extra:
        return 1
    print("check: filter_config.example.json のキー集合は EXPECTED_KEYS と一致しています。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
