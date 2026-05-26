# `docs/` ディレクトリ（GitHub Pages の公開ルート）

ここに置いたファイルが `https://<ユーザー>.github.io/<リポジトリ名>/` から配信されます。

- **生成物の案内**（[`table/index.html`](./table/index.html)）: ビルド後の JSON への直リンクと beatoraja 登録時の注意（索引はこの `docs/README.md`）。
- **トップ**（`index.html`）: `table/browser_rows.json` を読み、難易度表＋DB 列を表示。列設定は `meta.pages_ui`（ビルド時に [`table/pages_ui_config.json`](./table/pages_ui_config.json) を埋め込み）。仕様は [pages-ui-config.md](./pages-ui-config.md)。
- **統合難易度表別の曲数**（`level-stats.html`）: `table/level_stats.json` を読み込みます。
- **Jekyll を無効:** `.nojekyll`

## ドキュメントの読み方（推奨順）

| 目的 | ドキュメント |
|------|----------------|
| 日々の手動作業（SQL、URL、DB、push、Table URL） | **[ルート README.md](../README.md)** |
| **CI が何をするか**（ジョブ分割、`songdata.db` の取得、キューエラー） | [ci-github-pages-workflow.md](./ci-github-pages-workflow.md) |
| **Release へ DB を載せる**（`gh`、Windows スクリプト、`secrets.txt`） | [github-releases-songdata.md](./github-releases-songdata.md) |
| **フィルタの内部**（データフロー、出自メタ、beatoraja 互換） | [github-actions-songdata-table-filter.md](./github-actions-songdata-table-filter.md) |
| **`tools/table-filter/config/filter_config.json` のキー一覧** | [filter-config-schema.md](./filter-config-schema.md)（一覧は [../tools/table-filter/config/README.md](../tools/table-filter/config/README.md)） |
| **Pages トップの列・UI JSON** | [pages-ui-config.md](./pages-ui-config.md) |

## その他の索引

| 内容 | ファイル |
|------|----------|
| GitHub Pages の仕組み・別リポジトリへ複製 | [github-pages-publish-guide.md](./github-pages-publish-guide.md) |
| beatoraja 向け難易度表 JSON の前提 | [beatoraja-jbmstable-table-json.md](./beatoraja-jbmstable-table-json.md) |
| フロント移行の判断材料 | [frontend-migration-costs.md](./frontend-migration-costs.md) |
| beatoraja 楽曲 DB 仕様 | [bms-beatoraja-song-db.md](./bms-beatoraja-song-db.md) |
| 仮想フォルダ要件 | [requirements-filtered-bms-folder-tool.md](./requirements-filtered-bms-folder-tool.md) |
| 難易度表 URL・自作公開（beatoraja UI 補足） | [beatoraja-difficulty-table-url-and-filtered-publish.md](./beatoraja-difficulty-table-url-and-filtered-publish.md) |
| LR2oraja 系との差分 | [beatoraja-vs-lr2oraja-derivatives.md](./beatoraja-vs-lr2oraja-derivatives.md) |
