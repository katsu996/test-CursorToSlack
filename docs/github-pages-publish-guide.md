# 別リポジトリで GitHub Pages に公開する手順

**本リポジトリで日々行う手動作業**（DB 差し替え、SQL、URL、push、Table URL 登録など）は **[ルートの README.md](../README.md)** に集約しています。本文書は **Pages の公開の仕組み**と、**別の空リポジトリにこのテンプレートを複製する**ときの手順に重点を置きます。

beatoraja の難易度表 JSON などを **HTTPS で直リンク**できる場所に置く用途を想定しています。公開用リポジトリは **公開（Public）** にすると、無料の GitHub Pages で誰でも取得できます。

## 前提

- 公開用 GitHub アカウントと、空または専用の **リポジトリ**（例: `username/bms-difficulty-tables`）
- 難易度表の URL は本体側の仕様上、**`https://...` で `.json` で終わる**パスが扱いやすいです（例: `https://username.github.io/bms-difficulty-tables/my-table.json`）

## 方式の選び方

| 方式 | 向いていること |
|------|----------------|
| **GitHub Actions でデプロイ**（本リポジトリ同梱のワークフロー） | `main` へ push するたびに自動公開。設定はリポジトリ内で完結。 |
| **ブランチ「Deploy from a branch」** | Actions を使わず、`gh-pages` ブランチや `main` の `/docs` をそのまま公開。 |

以下では **GitHub Actions** を推奨手順として書きます（別リポジトリへこのファイル一式をコピーすれば再現できます）。

## 手順（新しい公開用リポジトリ）

### 1. リポジトリを作成

GitHub で **Public** リポジトリを作成します。名前は任意（例: `bms-difficulty-tables`）。

### 2. このテンプレートのファイルをコピー

公開用リポジトリのルートに、次を置きます（本リポジトリからコピー）。

| パス | 役割 |
|------|------|
| `.github/workflows/pages.yml` | `docs/` を GitHub Pages にデプロイ（`ruff` / `unittest` / 設定例検証 → **Latest Release から `songdata.db` を取得** → 難易度表フィルタ → スモーク → build/deploy 分割） |
| `docs/.nojekyll` | Jekyll を無効化し、**そのまま静的ファイル**として配信する |
| `docs/` 以下の JSON や HTML | 公開したい中身（難易度表 JSON はここに配置、または Actions で `docs/table/` に生成） |
| `tools/table-filter/`（任意） | `songdata.db` と SQL で元表を絞り込む場合にコピー |

### 3. GitHub Pages のソースを「GitHub Actions」にする

1. リポジトリの **Settings → Pages**
2. **Build and deployment** の **Source** で **GitHub Actions** を選択

初回はワークフロー実行後に反映されます。

### 4. `main` に push する

```bash
git add .
git commit -m "Add GitHub Pages workflow and static files"
git push -u origin main
```

**Actions** タブで `Deploy GitHub Pages` が成功すると、**Settings → Pages** に表示される **サイトの URL**（例: `https://<user>.github.io/<repo>/`）で公開されます。

### 5. beatoraja に URLを登録

公開した JSON の **フル URL**（`https://.../something.json`）を、beatoraja の **設定 → リソース → Table URL** に追加し、**難易度表読み込み**を実行します。

- ファイルを `docs/my-table.json` に置いた場合の URL の例:  
  `https://<user>.github.io/<repo>/my-table.json`

## 難易度表の自動生成（songdata.db × SQL）

`tools/table-filter/` を同梱し、`data/songdata.db` と `filter_config.json` を用意すると、push 時に **元表を取得してフィルタした JSON** を `docs/table/` に出力し、続けて **`browser_rows.json`**（表＋DB マージ）を生成してから Pages 公開できます。サイトの **`index.html`** がトップでそのデータを表形式表示し、**`level-stats.html`** が **`table/level_stats.json`** から統合難易度表別のレベル別件数（SQL 前後の比較列つき）を別ページで表示します。

- **あなたが触るファイル・設定:** [README.md](../README.md) の「手動で行う作業」
- **Actions とスクリプトの裏側:** [ci-github-pages-workflow.md](./ci-github-pages-workflow.md)（ジョブ順・DB 取得）、[github-actions-songdata-table-filter.md](./github-actions-songdata-table-filter.md)（フィルタ内部）

## ローカルでのファイル配置のコツ

- **サイトのルート**は `docs/` です。`docs/foo.json` → `https://<user>.github.io/<repo>/foo.json`
- リポジトリ直下に JSON を置いても、**このワークフローでは公開されません**（アップロード対象は `docs/` のみ）。JSON は `docs/` に置くか、Actions で `docs/` 以下に生成してください。
- 大きなバイナリや生成物を Pages に載せる場合は、リポジトリサイズと利用規約に注意してください。

## トラブルシューティング

- **404 になる**: デプロイ完了まで数分待つ。`Actions` が緑か確認する。URL のパスが `docs` 内の相対パスと一致しているか確認する。
- **JSON がダウンロードされない / 変な MIME**: `docs/.nojekyll` があるか確認する（Jekyll がファイルを触らないようにする）。
- **プライベートリポジトリ**: Pages の無料利用は公開サイトになるため、**Private リポジトリの Pages** は GitHub のプランによって挙動が異なります。難易度表を世界中に読ませる用途なら **Public リポジトリ**が簡単です。

## 参考（GitHub 公式）

- [GitHub Pages のドキュメント](https://docs.github.com/ja/pages/getting-started-with-github-pages/github-pages-basics)
- [静的サイトを GitHub Pages に公開する](https://docs.github.com/ja/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site#publishing-with-a-custom-github-actions-workflow)
