# 難易度表フィルタ（songdata.db × SQL）

## できること（概要）

1. ローカルの **songdata.db**（beatoraja が生成する `song` テーブル）に対して、**WHERE 断片**で行を絞り込み、`md5` / `sha256` の集合を得る。
2. **`source_tables`**（または **`source_tables_path`** で読む別 JSON）で指定した各難易度表（ヘッダー JSON の URL。HTML なら `bmstable` の meta から解決）を取得し、**そのハッシュが集合に含まれる行だけ**残したうえで、**beatoraja 用**の `filtered_data.json` と **Pages 用**の `filtered_data_enriched.json` を出力する。
3. ヘッダー JSON の **`data_url` を、既定ではデータファイル名のみ**（例: `filtered_data.json`）にし、beatoraja が **ヘッダーと同じディレクトリ**から取得できるようにした `filtered_header.json` を出力する（絶対 URL が必要なときは `use_relative_data_url: false` と `site_base_url` を使う）。
4. `filter_table.py` は各元表について **`sql_where` 通過後・重複マージ前**の行をレベル列別に数え、あわせて **SQL 条件を掛ける前の元表データ行**も同じレベル列で数え、`level_stats.json`（`level_rows` で前後を同一表の行に並べる）を出力する（既定ファイル名は `output_level_stats_filename`）。
5. `build_pages_table.py` が `filtered_data_enriched.json`（無ければ `filtered_data.json`）と `song` を突き合わせ `browser_rows.json` を生成する。`docs/index.html` と `docs/assets/pages-index-*.js` が一覧を表示し、`docs/level-stats.html` が `level_stats.json` を読んで統合難易度表別のレベル別件数を表示する。
6. 複数の元表をマージするとき、**各行に出自情報**（`source_table_index`・`source_table_short_names`・`source_table_names` など）を付与する。同一譜面が複数表に載っている場合は `source_table_names` / `source_table_short_names` に複数の表ラベルが入る（`source_table_index` は先勝ちの表の番号のまま）。

**運用で触る設定・手順**（SQL、URL、DB の置き場所、push、Table URL）は **[リポジトリ直下の README.md](../../README.md)** を参照してください。

## 設定ファイル

`filter_config.json` を編集します（雛形は `filter_config.example.json`）。

- **`source_tables_path`**: 任意。`filter_config.json` と同じディレクトリ基準の相対パスで、**難易度表ソース配列だけ**を書いた JSON を指す。非空なら **ファイルが優先**されインラインの `source_tables` は上書きされる。
- **`source_tables`**: **推奨。** オブジェクトの配列。各要素に **`header_url`**（または **`url`**）、任意で **`display_name`**・**`short_name`**・**`custom_level_mapping`** をまとめて書く（[`docs/filter-config-schema.md`](../../docs/filter-config-schema.md)）。
- **`source_header_urls`**: 後方互換。URL だけの配列（`source_tables` が空かつ `source_tables_path` も空のときに使用）。
- **`source_header_url`**: 1 本だけのとき用（`source_tables` が空で `source_header_urls` も空のときに使用）。
- **`source_table_display_names`**: 後方互換。`source_header_urls` と同じ長さの配列で表示名を上書き（`source_tables` 未使用時）。
- **`source_table_short_names`**: 後方互換。同じ長さの配列で略称（`source_tables` 未使用時）。
- **`source_data_url`**: **単一ヘッダー時のみ**有効。データ JSON の URL でヘッダー内 `data_url` を上書き。**複数ヘッダー時は無視**（警告あり）。
- **`sql_where`**, **`sql_where_preset`**, **`sql_where_disable_identifier_whitelist`**: `SELECT ... FROM song WHERE (` の断片。プリセット指定時は固定 SQL のみ。既定では識別子ホワイトリストあり（詳細は [docs/filter-config-schema.md](../../docs/filter-config-schema.md)）。
- **`use_relative_data_url`**: 既定 `true`。`true` のとき生成ヘッダーの `data_url` は **`filtered_data.json` のようなファイル名のみ**（`SITE_BASE_URL` は不要）。`false` のときだけ **`site_base_url`**（または環境変数 **`SITE_BASE_URL`**）で絶対 URL を組み立てる。
- **`site_base_url`**: `use_relative_data_url` が `false` のときに必須。`https://<owner>.github.io/<repo>/table` のような **ディレクトリ URL（末尾スラッシュなし）**。相対 `data_url` のときは空でよい。
- **`custom_level_mapping`**: 後方互換のトップレベル配列。**推奨は各 `source_tables[]` の `custom_level_mapping` オブジェクト**（詳細は [docs/github-actions-songdata-table-filter.md](../../docs/github-actions-songdata-table-filter.md)）。**`custom_level_field`**, **`custom_level_source_key`**, **`custom_level_unmapped`**: 独自レベル列の名前・元列・未マップ時の挙動。
- **`enabled`**, **`skip_if_no_songdata`**: フィルタのスキップ挙動。詳細は [docs/github-actions-songdata-table-filter.md](../../docs/github-actions-songdata-table-filter.md)。
- **`output_dir`**, **`output_data_filename`**, **`output_data_enriched_filename`**, **`output_header_filename`**, **`output_level_stats_filename`**: 出力先とファイル名（既定は `docs/table/` 配下、`level_stats.json` は統合難易度表別・レベル別集計用）。
- **`output_header_name`**: 任意。合成ヘッダー JSON の **`name`**（beatoraja の表名）。空なら元ヘッダーまたはスクリプト既定。
- **`page_title`**: 任意。GitHub Pages の `<title>` / 見出し（未設定時は `output_header_name`）。
- **`beatoraja_empty_rows_policy`**: 任意。`fail`（既定）で beatoraja 向け 0 件時に `filter_table.py` が終了コード 1。
- **`http_fetch_timeout_seconds`**, **`http_fetch_retries`**, **`http_fetch_backoff_seconds`**: 外部 URL 取得のタイムアウト・再試行。
- **`beatoraja_strip_chart_keys`**: beatoraja 向け `filtered_data.json` から除くキー（未指定時は `source_*` 出自列に加え `id`）。空配列なら除去しない。
- **`pages_ui_config_path`**: 任意。Pages トップ用 UI 設定 JSON のパス（空なら `docs/table/pages_ui_config.json`）。`build_pages_table.py` が `browser_rows.json` の `meta.pages_ui` に埋め込む（[docs/pages-ui-config.md](../../docs/pages-ui-config.md)）。

## ローカル実行

```bash
# 既定（相対 data_url）なら SITE_BASE_URL は不要
python3 tools/table-filter/filter_table.py --config tools/table-filter/filter_config.json
python3 tools/table-filter/build_pages_table.py --config tools/table-filter/filter_config.json
# 絶対 URL で data_url を書きたい場合のみ:
export SITE_BASE_URL="https://あなた.github.io/リポジトリ名/table"
# かつ filter_config.json で "use_relative_data_url": false
```

事前に `data/songdata.db` を配置し、`source_tables`（または `source_header_urls` / `source_header_url`）を埋めてください。

## SQL インジェクション対策

スクリプトは断片に `;` やコメント、`ATTACH` など一部キーワードを拒否し、**既定では `song` 列名以外の識別子**も拒否します。それでも **信頼できる設定ファイルだけ**をリポジトリにコミットしてください。高度な式が必要なときだけ **`sql_where_disable_identifier_whitelist`: true** を検討してください。
