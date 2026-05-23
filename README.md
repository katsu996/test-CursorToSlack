# test-CursorToSlack

## ドキュメント

- [beatoraja 楽曲データベース（BMS）仕様メモ](docs/bms-beatoraja-song-db.md) — `songdata.db` / `songinfo.db` のテーブル概要と更新挙動の整理
- [条件付き BMS 仮想フォルダ生成ツール — 要件定義・調査](docs/requirements-filtered-bms-folder-tool.md)
- [beatoraja `default.json` 断片例: `minbpm != maxbpm`](examples/beatoraja-default-json-snippet-changing-bpm.json)
- [beatoraja と LR2oraja / Endless Dream の違い](docs/beatoraja-vs-lr2oraja-derivatives.md)
- [beatoraja: 難易度表の URL 公開・追加と、条件で絞った表の再公開](docs/beatoraja-difficulty-table-url-and-filtered-publish.md)
- [songdata.db × GitHub Actions で難易度表を絞り込む](docs/github-actions-songdata-table-filter.md)

## GitHub Pages と難易度表フィルタ

**GitHub Pages** に静的ファイルを載せる手順と、**`songdata.db` + SQL** で元難易度表を絞り込んだ JSON を **GitHub Actions** で生成して同じサイトに載せる仕組みです。

| 内容 | ドキュメント / パス |
|------|----------------------|
| Pages の詳細手順 | [docs/github-pages-publish-guide.md](docs/github-pages-publish-guide.md) |
| Actions × songdata.db × 難易度表 | [docs/github-actions-songdata-table-filter.md](docs/github-actions-songdata-table-filter.md) |
| フィルタ設定・ローカル実行 | [tools/table-filter/README.md](tools/table-filter/README.md) |
| `songdata.db` の置き場所 | [data/README.md](data/README.md) |
| ワークフロー | [.github/workflows/pages.yml](.github/workflows/pages.yml) |
| 公開ルート | [docs/](docs/)（`.nojekyll` と `index.html`） |

### クイックスタート

1. **初回のみ**: GitHub の **Settings → Pages → Build and deployment** で **Source を「GitHub Actions」**にする（このリポジトリの `Deploy GitHub Pages` ワークフローがデプロイするため）。
2. `data/songdata.db` をコミットする（Web の **Add file → Upload files** で `data/songdata.db` を上書きしてもよい。更新のたびに差し替え）。
3. （任意）難易度表を Actions で絞り込む場合は、`tools/table-filter/filter_config.json` の `source_header_url` に元表のヘッダー JSON の URL を書く。空のままならフィルタはスキップされ、`docs/` の静的ファイルだけが公開される。
4. `main` に push（または **Actions → Deploy GitHub Pages → Run workflow**）→ 成功後、**Settings → Pages** に表示されるサイト URL で `docs/index.html` などが開ける。

beatoraja の Table URL には `https://<owner>.github.io/<repo>/table/filtered_header.json` を登録します。

別リポジトリでは、**Settings → Pages → Source: GitHub Actions** を選び、上記のワークフローと `docs/`・`tools/table-filter/` などをコピーすれば同様に公開できます。
