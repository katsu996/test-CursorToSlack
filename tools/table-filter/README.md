# 難易度表フィルタ（songdata.db × SQL）

## できること（概要）

1. ローカルの **songdata.db**（beatoraja が生成する `song` テーブル）に対して、**WHERE 断片**で行を絞り込み、`md5` / `sha256` の集合を得る。
2. 指定した **元難易度表**（ヘッダー JSON の URL。HTML なら `bmstable` の meta から解決）を取得し、**そのハッシュが集合に含まれる行だけ**残した `filtered_data.json` を出力する。
3. ヘッダー JSON の **`data_url` を GitHub Pages 上の新しい JSON の URL** に差し替えた `filtered_header.json` を出力する。
4. `build_pages_table.py` が `filtered_data.json` と `song` を突き合わせ、`browser_rows.json` を生成する。`docs/index.html` が Pages のトップでこれを表表示する。
5. 複数の元表をマージするとき、**各行に出自情報**（`source_table_index`・`source_table_names` など）を付与する。同一譜面が複数表に載っている場合は `source_table_names` に複数の表名が入る（`source_table_index` は先勝ちの表の番号のまま）。

**運用で触る設定・手順**（SQL、URL、DB の置き場所、push、Table URL）は **[リポジトリ直下の README.md](../../README.md)** を参照してください。

## 設定ファイル

`filter_config.json` を編集します（雛形は `filter_config.example.json`）。

- **`source_header_urls`**: 推奨。元表の URL の配列（JSON 直リンクまたは難易度表 HTML）。
- **`source_header_url`**: 1 本だけのとき用（`source_header_urls` が空のときに使用）。
- **`source_table_display_names`**: 任意。`source_header_urls` と同じ長さの配列で、行の `source_table_names` と Pages メタ用の**表示名**を上書き（詳細は [docs/github-actions-songdata-table-filter.md](../../docs/github-actions-songdata-table-filter.md)）。
- **`source_data_url`**: **単一ヘッダー時のみ**有効。データ JSON の URL でヘッダー内 `data_url` を上書き。**複数ヘッダー時は無視**（警告あり）。
- **`sql_where`**: `SELECT ... FROM song WHERE (` の直後に連結される条件式。`minbpm` / `maxbpm` は `song` の列名。
- **`site_base_url`**: ローカル実行時は `https://<owner>.github.io/<repo>/table` のような **ディレクトリ URL（末尾スラッシュなし）** を書く。GitHub Actions では **`SITE_BASE_URL` 環境変数**をワークフローが渡すため空でよい。
- **`custom_level_mapping`**, **`custom_level_field`**, **`custom_level_source_key`**, **`custom_level_unmapped`**: 元表ごとのレベルを独自列に写す（詳細は [docs/github-actions-songdata-table-filter.md](../../docs/github-actions-songdata-table-filter.md)）。
- **`enabled`**, **`skip_if_no_songdata`**: フィルタのスキップ挙動。詳細は [docs/github-actions-songdata-table-filter.md](../../docs/github-actions-songdata-table-filter.md)。

## ローカル実行

```bash
export SITE_BASE_URL="https://あなた.github.io/リポジトリ名/table"
python3 tools/table-filter/filter_table.py --config tools/table-filter/filter_config.json
python3 tools/table-filter/build_pages_table.py --config tools/table-filter/filter_config.json
```

事前に `data/songdata.db` を配置し、`source_header_urls`（または `source_header_url`）を埋めてください。

## SQL インジェクション対策

スクリプトは断片に `;` やコメント、`ATTACH` など一部キーワードを拒否します。それでも **信頼できる設定ファイルだけ**をリポジトリにコミットしてください。
