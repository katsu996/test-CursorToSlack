# `filter_config.json` スキーマ（キー一覧）

`tools/table-filter/filter_config.json` のキー意味です。**例ファイル**は [`filter_config.example.json`](../tools/table-filter/filter_config.example.json) です。キー集合の CI 検証は [`check_filter_config_example_sync.py`](../tools/table-filter/check_filter_config_example_sync.py) の `EXPECTED_KEYS` と同期してください。

| キー | 必須 | 説明 |
|------|------|------|
| `enabled` | 任意 | `false` でフィルタ全体をスキップ |
| `skip_if_no_songdata` | 任意 | `songdata.db` 不在時にスキップするか |
| `songdata_db` | 任意 | DB パス（既定 `data/songdata.db`） |
| `beatoraja_empty_rows_policy` | 任意 | `fail`（既定）で beatoraja 向け 0 件時に `filter_table.py` が終了コード 1。`warn` / `allow` 等で緩和 |
| `sql_where_preset` | 任意 | 非空なら固定プリセットのみ使用（`const_bpm` / `var_bpm`）。**設定時は `sql_where` は無視** |
| `sql_where` | 条件付き | `sql_where_preset` 未使用時の `song` WHERE 断片 |
| `sql_where_disable_identifier_whitelist` | 任意 | `true` で識別子ホワイトリスト検証を無効（自己責任） |
| `source_tables` | 条件付き | **推奨。** 難易度表ソースの配列。各要素はオブジェクトで **`header_url`**（または **`url`**）必須、任意で **`display_name`**・**`short_name`**。並びが `custom_level_mapping` のインデックスと対応 |
| `source_header_urls` | 条件付き | **後方互換。** `source_tables` が空のときのみ有効。ヘッダーまたは HTML の URL 配列 |
| `source_table_display_names` | 任意 | **後方互換。** `source_header_urls` と同じ長さの表示名配列（`source_tables` 未使用時） |
| `source_table_short_names` | 任意 | **後方互換。** 略称配列（`source_tables` 未使用時） |
| `source_header_url` | 任意 | 単一 URL の後方互換 |
| `source_data_url` | 任意 | 単一ソース時のみデータ JSON を上書き |
| `output_dir` | 任意 | 生成先（既定 `docs/table`） |
| `output_data_filename` | 任意 | beatoraja 向けデータ JSON 名 |
| `output_data_enriched_filename` | 任意 | Pages 向け拡張列付き JSON 名 |
| `output_header_filename` | 任意 | 合成ヘッダー JSON 名 |
| `output_header_name` | 任意 | beatoraja の表名（`filtered_header.json` の `name`） |
| `page_title` | 任意 | GitHub Pages の `<title>` / `h1`（未設定時は `output_header_name`） |
| `output_level_stats_filename` | 任意 | レベル集計 JSON 名 |
| `browser_rows_filename` | 任意 | `build_pages_table.py` の出力名 |
| `site_base_url` | 条件付き | `use_relative_data_url: false` のとき必須 |
| `use_relative_data_url` | 任意 | 既定 `true` で `data_url` はファイル名のみ |
| `http_fetch_timeout_seconds` | 任意 | 外部取得タイムアウト秒 |
| `http_fetch_retries` | 任意 | 取得リトライ回数 |
| `http_fetch_backoff_seconds` | 任意 | 再試行の指数バックオフの底 |
| `custom_level_mapping` | 任意 | ソース順（`source_tables` または正規化後の URL 列）に対応するレベルマップ配列 |
| `custom_level_field` | 任意 | 出力列名 |
| `custom_level_source_key` | 任意 | 元表の難易度列名（既定 `level`） |
| `custom_level_unmapped` | 任意 | マップ外の扱い |
| `beatoraja_strip_chart_keys` | 任意 | beatoraja 向け JSON から除外するキー。`null` で既定 |
