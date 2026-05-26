# `songdata.db` を GitHub Releases のアセットとして配布する

リポジトリに `songdata.db` をコミットせず、**Release にバイナリを載せて** GitHub Actions やローカルから取得する手順です。GitHub の Web からのファイル追加は **100MB 未満**の制限があります（[Adding a file to a repository](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository)）。Release アセットも同様に **100MB 未満**である必要があります。25MB 超で「コンソールからのコミット」が困難な場合でも、**API や GitHub CLI でのアップロード**なら同じ枠内であれば問題なく運用できます。

## 前提

- アセット名の例: **`songdata.db`**（ワークフローとドキュメントはこの名前を想定しています）
- 同じリポジトリ内の Release から取得する場合、Actions では **`GITHUB_TOKEN`** で API にアクセスできます（同一リポジトリの `contents: read` で足ります）
- **プライベートリポジトリ**では、ブラウザの匿名 URL では取得できないため、**トークン付き**の取得が必要です

## 推奨: GitHub CLI（`gh`）でアップロード

ローカルで [GitHub CLI](https://cli.github.com/) を使うのが簡単です。事前に `gh auth login` 済みであること。

```bash
# 例: タグ songdata-2026-05-26 でドラフト Release を作り、ファイルを載せる
gh release create songdata-2026-05-26 data/songdata.db \
  --repo OWNER/REPO \
  --title "songdata.db (2026-05-26)" \
  --notes "beatoraja songdata.db のスナップショット"

# 既存のタグにファイルだけ追加（同名アセットがあると失敗するので先に削除が必要な場合あり）
gh release upload songdata-2026-05-26 data/songdata.db --repo OWNER/REPO --clobber
```

`--clobber` は `gh` のバージョンによっては未対応の場合があります。そのときは Release 上で古いアセットを削除してから再アップロードしてください。

## Windows: REST API バッチ（`scripts/upload-songdata-github-release.bat`）

**GitHub REST API**（[Create a release](https://docs.github.com/en/rest/releases/releases#create-a-release) / [Upload a release asset](https://docs.github.com/en/rest/releases/assets#upload-a-release-asset)）を **PowerShell 5.1+** から呼び出します。`.bat` はリポジトリルートに `cd` してから同梱の `.ps1` を実行するラッパーです。

### 認証とリポジトリ（推奨: `local.ps1`）

**コマンドプロンプト用の `.bat` には日本語や UTF-8 のみの文字を入れないでください。** 環境によっては **`%` の誤解釈**で `GITHUB_TOKEN` が壊れ、 `'H_TOKEN'` のように別コマンド扱いになることがあります。

トークンは次のいずれかで渡します（優先順）。

1. **`scripts/upload-songdata-github-release.local.ps1`**（リポジトリでは **`.gitignore`** 済み）  
   `scripts/upload-songdata-github-release.local.ps1.example` をコピーして同フォルダに `upload-songdata-github-release.local.ps1` として保存し、**例どおり `$env:GITHUB_TOKEN` と `$env:GITHUB_REPOSITORY` を編集**してください。単行は **ASCII** のみにすると安全です。トークンは **単引用符** `'ghp_...'` で囲むとよいです。
2. 環境変数 **`GITHUB_TOKEN`** / **`GH_TOKEN`** と **`GITHUB_REPOSITORY`**
3. PowerShell 引数 **`-Token`** / **`-Repo`**（非対話バッチでは秘密が履歴に残りやすいので非推奨）

### 例（コマンドプロンプト）

```bat
cd C:\path\to\this-repo
copy scripts\upload-songdata-github-release.local.ps1.example scripts\upload-songdata-github-release.local.ps1
rem Edit local.ps1: set GITHUB_TOKEN and GITHUB_REPOSITORY, then:
scripts\upload-songdata-github-release.bat songdata-2026-05-26
```

既定のローカルファイルは **`data/songdata.db`** です。別パスにする場合は `-SongdataPath` を指定します。

```bat
scripts\upload-songdata-github-release.bat songdata-2026-05-26 -SongdataPath D:\beatoraja\songdata.db
```

- 指定タグの **Release が無い場合は新規作成**します（タグがリモートに無い場合は GitHub が既定ブランチ先に lightweight タグを作る挙動になります。通常は先に `git tag` / `git push origin <tag>` 済みにしてください）
- **同名アセット `songdata.db` が既にある場合は削除してから再アップロード**します

## REST API でアップロード（バッチや `curl` 向け）

公式手順: [Upload a release asset](https://docs.github.com/en/rest/releases/assets?apiVersion=2022-11-28#upload-a-release-asset)

流れは次の 2 段階です。

1. **Release を作成する**（または既存の `release_id` を使う）  
   [Create a release](https://docs.github.com/en/rest/releases/releases?apiVersion=2022-11-28#create-a-release) の応答に **`upload_url`** が含まれます（`{?name,label}` というテンプレート付き）
2. **`upload_url` に `?name=songdata.db` を付けて POST**（本文は生のファイルバイト、`Content-Type: application/octet-stream`）

認証は **`Authorization: Bearer TOKEN`**（細粒度トークンまたは classic の `repo` など、Release 作成・資産アップロード権限が必要）。

### `curl` の例（Release は既に存在し `UPLOAD_URL` が分かっている場合）

`UPLOAD_URL` は API の `upload_url` から **`{?name,label}` を除いた URL** にします（多くのクライアントは `?name=songdata.db` を付与）。

```bash
curl -sS -X POST \
  -H "Authorization: Bearer ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  -H "Content-Type: application/octet-stream" \
  --data-binary "@data/songdata.db" \
  "${UPLOAD_URL}?name=songdata.db"
```

## ダウンロード URL（公開リポジトリ）

タグ `TAG` の Release に `songdata.db` がある場合、次の形式で **匿名 GET** できます（レート制限は GitHub 共通ポリシーに従います）。

```text
https://github.com/OWNER/REPO/releases/download/TAG/songdata.db
```

## GitHub Actions（本リポジトリのワークフロー）

`.github/workflows/pages.yml` では、リポジトリ変数 **`SONGDATA_RELEASE_TAG`** に上記の **タグ名**（例: `songdata-2026-05-26`）を設定すると、チェックアウト直後に **`gh release download`** で `data/songdata.db` を取得し、存在・非空を検証します。変数が空のときは **Release からの取得を行いません**（手元で `data/songdata.db` を置いた場合や、フィルタをスキップする用途向け）。

設定場所: **Settings → Secrets and variables → Actions → Variables** で `SONGDATA_RELEASE_TAG` を追加。

プライベートリポジトリでも、既定の `GITHUB_TOKEN` で同一リポジトリの Release を取得できます。

## ローカルで取得する例

```bash
gh release download songdata-2026-05-26 -p songdata.db -O data/songdata.db --repo OWNER/REPO
```

`curl` のみの場合は、[List release assets](https://docs.github.com/en/rest/releases/assets?apiVersion=2022-11-28#list-release-assets) で `browser_download_url` を取得してから `curl -L` するか、公開リポジトリなら上記の固定 URL を使います。

## 注意

- **タグ名とファイル名**を Actions 変数・ドキュメント・実際の Release で揃える
- **100MB 以上**の単一アセットは GitHub の制限に抵触するため、その場合はオブジェクトストレージ（S3 互換など）を検討してください
- Release を消すと **そのタグに紐づくダウンロード URL も無効**になります。長期運用するならタグの命名規則を決め、**上書き用の別タグ**にするか、履歴として残すかを決めてください
