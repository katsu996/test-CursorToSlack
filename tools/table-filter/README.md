# 難易度表フィルタ（songdata.db × SQL）

## できること（概要）

1. ローカルの **songdata.db**（beatoraja が生成する `song` テーブル）に対して、**WHERE 断片**で行を絞り込み、`md5` / `sha256` の集合を得る。
2. 指定した **元難易度表**（ヘッダー JSON の URL。HTML なら `bmstable` の meta から解決）を取得し、**そのハッシュが集合に含まれる行だけ**残したうえで、**beatoraja 用**の `filtered_data.json` と **Pages 用**の `filtered_data_enriched.json` を出力する。
3. ヘッダー JSON の **`data_url` を、既定ではデータファイル名のみ**（例: `filtered_data.json`）にし、beatoraja が **ヘッダーと同じディレクトリ**から取得できるようにした `filtered_header.json` を出力する（絶対 URL が必要なときは `use_relative_data_url: false` と `site_base_url` を使う）。
4. `filter_table.py` は各元表について **`sql_where` 通過後・重複マージ前**の行をレベル列別に数え、`level_stats.json` を出力する（既定ファイル名は `output_level_stats_filename`）。
5. `build_pages_table.py` が `filtered_data_enriched.json`（無ければ `filtered_data.json`）と `song` を突き合わせ `browser_rows.json` を生成する。`docs/index.html` が一覧を表示し、`docs/level-stats.html` が `level_stats.json` を読んでレベル別曲数を表示する。
6. 複数の元表をマージするとき、**各行に出自情報**（`source_table_index`・`source_table_short_names`・`source_table_names` など）を付与する。同一譜面が複数表に載っている場合は `source_table_names` / `source_table_short_names` に複数の表ラベルが入る（`source_table_index` は先勝ちの表の番号のまま）。

**運用で触る設定・手順**（SQL、URL、DB の置き場所、push、Table URL）は **[リポジトリ直下の README.md](../../README.md)** を参照してください。

## 設定ファイル

`filter_config.json` を編集します（雛形は `filter_config.example.json`）。

- **`source_header_urls`**: 推奨。元表の URL の配列（JSON 直リンクまたは難易度表 HTML）。
- **`source_header_url`**: 1 本だけのとき用（`source_header_urls` が空のときに使用）。
- **`source_table_display_names`**: 任意。`source_header_urls` と同じ長さの配列で、行の `source_table_names` と Pages メタ用の**表示名**を上書き（詳細は [docs/github-actions-songdata-table-filter.md](../../docs/github-actions-songdata-table-filter.md)）。
- **`source_table_short_names`**: 任意。同じ長さの配列で、行の `source_table_short_names`（略称）と Pages メタの略称レジェンドに使う（例: `sl` / `st`）。
- **`source_data_url`**: **単一ヘッダー時のみ**有効。データ JSON の URL でヘッダー内 `data_url` を上書き。**複数ヘッダー時は無視**（警告あり）。
- **`sql_where`**: `SELECT ... FROM song WHERE (` の直後に連結される条件式。`minbpm` / `maxbpm` は `song` の列名。
- **`use_relative_data_url`**: 既定 `true`。`true` のとき生成ヘッダーの `data_url` は **`filtered_data.json` のようなファイル名のみ**（`SITE_BASE_URL` は不要）。`false` のときだけ **`site_base_url`**（または環境変数 **`SITE_BASE_URL`**）で絶対 URL を組み立てる。
- **`site_base_url`**: `use_relative_data_url` が `false` のときに必須。`https://<owner>.github.io/<repo>/table` のような **ディレクトリ URL（末尾スラッシュなし）**。相対 `data_url` のときは空でよい。
- **`custom_level_mapping`**, **`custom_level_field`**, **`custom_level_source_key`**, **`custom_level_unmapped`**: 元表ごとのレベルを独自列に写す（詳細は [docs/github-actions-songdata-table-filter.md](../../docs/github-actions-songdata-table-filter.md)）。
- **`enabled`**, **`skip_if_no_songdata`**: フィルタのスキップ挙動。詳細は [docs/github-actions-songdata-table-filter.md](../../docs/github-actions-songdata-table-filter.md)。
- **`output_dir`**, **`output_data_filename`**, **`output_data_enriched_filename`**, **`output_header_filename`**, **`output_level_stats_filename`**: 出力先とファイル名（既定は `docs/table/` 配下、`level_stats.json` はレベル別集計用）。
- **`beatoraja_strip_chart_keys`**: beatoraja 向け `filtered_data.json` から除くキー（未指定時は `source_*` 出自列に加え `id`）。空配列なら除去しない。

## ローカル実行

```bash
# 既定（相対 data_url）なら SITE_BASE_URL は不要
python3 tools/table-filter/filter_table.py --config tools/table-filter/filter_config.json
python3 tools/table-filter/build_pages_table.py --config tools/table-filter/filter_config.json
# 絶対 URL で data_url を書きたい場合のみ:
export SITE_BASE_URL="https://あなた.github.io/リポジトリ名/table"
# かつ filter_config.json で "use_relative_data_url": false
```

事前に `data/songdata.db` を配置し、`source_header_urls`（または `source_header_url`）を埋めてください。

## SQL インジェクション対策

スクリプトは断片に `;` やコメント、`ATTACH` など一部キーワードを拒否します。それでも **信頼できる設定ファイルだけ**をリポジトリにコミットしてください。
