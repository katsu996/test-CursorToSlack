# `docs/` ディレクトリ（GitHub Pages の公開ルート）

ここに置いたファイルが `https://<ユーザー>.github.io/<リポジトリ名>/` から配信されます。

- **トップページ**（`index.html`）: Actions 実行後、`table/browser_rows.json` を読み込み、難易度表＋`songdata.db` の列を表形式で表示します。列幅・列の既定表示は `meta.pages_ui`（ビルド時に [`table/pages_ui_config.json`](./table/pages_ui_config.json) を読み込み）で調整します。仕様は [pages-ui-config.md](./pages-ui-config.md)。**並び替え（優先 1〜3）・絞り込み・列の表示**は 1 つの折りたたみパネルです。フッターから **`table/filtered_header.json`**（beatoraja 用ヘッダー）を開けます。
- **統合難易度表別の曲数**（`level-stats.html`）: `table/level_stats.json` を読み込み、統合難易度表ごとにレベル別件数（SQL 条件の前後で比較）を表示します。
- **Jekyll を無効にする:** `.nojekyll`

## 運用（手動作業）

**DB の差し替え、SQL・URL の編集、Pages の初回設定、beatoraja の Table URL** など、人が行う作業の一覧は **[ルートの README.md](../README.md)** に集約しています。

## 技術ドキュメント索引

| 内容 | ファイル |
|------|----------|
| GitHub Pages の仕組み・別リポジトリへのコピー | [github-pages-publish-guide.md](./github-pages-publish-guide.md) |
| Actions・フィルタスクリプトの処理内容 | [github-actions-songdata-table-filter.md](./github-actions-songdata-table-filter.md) |
| beatoraja 向け難易度表 JSON の前提 | [beatoraja-jbmstable-table-json.md](./beatoraja-jbmstable-table-json.md) |
| `filter_config.json` キー一覧 | [filter-config-schema.md](./filter-config-schema.md) |
| Pages トップの UI 設定（列幅・既定表示） | [pages-ui-config.md](./pages-ui-config.md) |
| フロント移行の判断材料 | [frontend-migration-costs.md](./frontend-migration-costs.md) |
| beatoraja 楽曲 DB 仕様 | [bms-beatoraja-song-db.md](./bms-beatoraja-song-db.md) |
| 仮想フォルダ要件 | [requirements-filtered-bms-folder-tool.md](./requirements-filtered-bms-folder-tool.md) |
| 難易度表 URL・自作公開 | [beatoraja-difficulty-table-url-and-filtered-publish.md](./beatoraja-difficulty-table-url-and-filtered-publish.md) |
| LR2oraja 系との差分 | [beatoraja-vs-lr2oraja-derivatives.md](./beatoraja-vs-lr2oraja-derivatives.md) |
