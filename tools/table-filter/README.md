# 難易度表フィルタ（songdata.db × SQL）

## できること

1. ローカルの **songdata.db**（beatoraja が生成する `song` テーブル）に対して、**WHERE 断片**（例: 等速 BPM `minbpm = maxbpm`、変速 `minbpm != maxbpm`）で行を絞り込み、`md5` / `sha256` の集合を得る。
2. 指定した **元難易度表**（ヘッダー JSON の URL。必要ならデータ JSON も URL で上書き）を取得し、**そのハッシュが集合に含まれる行だけ**残した `filtered_data.json` を出力する。
3. ヘッダー JSON の **`data_url` を GitHub Pages 上の新しい JSON の URL** に差し替えた `filtered_header.json` を出力する。
4. （GitHub Actions 同梱）`build_pages_table.py` が `filtered_data.json` と `song` を突き合わせ、`browser_rows.json` を生成する。`docs/index.html` が Pages のトップでこれを表表示する。

## 設定

`filter_config.json` を編集します（雛形は `filter_config.example.json`）。

- **source_header_url**: 必須（空だと Actions ではスキップ）。元表のヘッダー JSON の HTTPS URL。
- **source_data_url**: 省略時はヘッダー内の `data_url` を使う。`score_rec.json` のように **相対 URL のときは `source_header_url` を基準に解決**される。
- **sql_where**: `SELECT ... FROM song WHERE (` の直後にそのまま連結される条件式。`minbpm` / `maxbpm` は `song` の列名。
- **site_base_url**: ローカル実行時はここに `https://<owner>.github.io/<repo>/table` のような **ディレクトリ URL（末尾スラッシュなし）** を書く。GitHub Actions ではワークフローが `SITE_BASE_URL` を渡すため空でよい。

## ローカル実行

```bash
export SITE_BASE_URL="https://あなた.github.io/リポジトリ名/table"
python3 tools/table-filter/filter_table.py --config tools/table-filter/filter_config.json
```

事前に `data/songdata.db` を配置し、`source_header_urls`（または `source_header_url`）を埋めてください。

## SQL インジェクション対策

スクリプトは断片に `;` やコメント、`ATTACH` など一部キーワードを拒否します。それでも **信頼できる設定ファイルだけ**をリポジトリにコミットしてください。
