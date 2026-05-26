# `songdata.db` を GitHub Releases のアセットとして配布する

リポジトリに `songdata.db` をコミットせず、**Release にバイナリを載せて** GitHub Actions やローカルから取得する手順です。

## 運用チェックリスト（最短）

1. **アセット名は必ず `songdata.db`**（CI はこの名前だけをダウンロードします）。
2. **通常の Release** として公開し、GitHub の **Latest** になるようにする（**プレリリースのみ**だと Latest に載らず CI が失敗し得ます）。
3. **`main` へ push** するか **Deploy GitHub Pages** を手動実行すると、ワークフローが **Latest から毎回** `songdata.db` を取得します（リポジトリ変数は不要。旧 **`SONGDATA_RELEASE_TAG`** は削除して問題ありません）。
4. Windows でアップロードする場合は **`scripts/upload-songdata-github-release.*`** を `songdata.db` と同じフォルダへコピーし、**`upload-songdata-github-release.secrets.txt`** の書き方は下記「`secrets.txt` の書き方」を参照（**UTF-8**・1 行目に PAT 全文）。
5. CI の全体像は **[ci-github-pages-workflow.md](./ci-github-pages-workflow.md)**、フィルタの挙動は **[github-actions-songdata-table-filter.md](./github-actions-songdata-table-filter.md)** を参照。

以下、制限・CLI・REST API・トラブルシュートの詳細です。GitHub の Web からのファイル追加は **100MB 未満**の制限があります（[Adding a file to a repository](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository)）。Release アセットも同様に **100MB 未満**である必要があります。25MB 超で「コンソールからのコミット」が困難な場合でも、**API や GitHub CLI でのアップロード**なら同じ枠内であれば問題なく運用できます。

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

**GitHub REST API**（[Create a release](https://docs.github.com/en/rest/releases/releases#create-a-release) / [Upload a release asset](https://docs.github.com/en/rest/releases/assets#upload-a-release-asset)）を **PowerShell 5.1+** から呼び出します。

### 想定する置き場所（リポジトリ外でも可）

多くの場合、**beatoraja など `songdata.db` があるフォルダ**に、次のファイルだけコピーして使います（**Git 管理下である必要はありません**）。

| ファイル | 説明 |
|----------|------|
| `upload-songdata-github-release.bat` | ラッパー（**ASCII のみ**。日本語や UTF-8 だけの行を入れないでください） |
| `upload-songdata-github-release.ps1` | 本体 |
| `songdata.db` | アップロードする DB（**`.ps1` と同じフォルダ**に置くと自動検出） |
| 認証用ファイル（どちらか一方） | 下記「認証」参照 |

`.bat` は **自分と同じフォルダに `cd` してから** `.ps1` を実行します。`songdata.db` は **同じフォルダに `songdata.db` という名前で置く**のが最も簡単です（別パスなら `-SongdataPath`）。

リポジトリ内の **`scripts/`** に置いたまま使う場合も同様で、そのときは **`scripts` の隣の `data/songdata.db`** を既定で探します（従来どおり）。

### 認証とリポジトリ

**`.bat` にトークンを書かないでください。** 環境によっては **`%` の誤解釈**で変数が壊れます。

次の **`.ps1` と同じディレクトリ** に置いたファイルが読み込まれます（**上にあるほど先**に読み、後から読む設定で上書きできます）。

1. **`upload-songdata-github-release.secrets.txt`**（推奨・編集が簡単）  
   リポジトリの `scripts/upload-songdata-github-release.secrets.txt.example` をコピーし、**`upload-songdata-github-release.secrets.txt`** にリネームして編集します。  
   - **1 行目:** Personal Access Token（必須）  
   - **2 行目:** `owner/repo`（省略可。省略時は環境変数 `GITHUB_REPOSITORY` か `local.ps1` で指定）  
   - `#` で始まる行はコメントとして無視  
   - 内容は **ASCII のみ**推奨（トークン・リポジトリ名は ASCII です）
2. **`upload-songdata-github-release.local.ps1`**  
   `scripts/upload-songdata-github-release.local.ps1.example` をコピーし、**同じフォルダに** `upload-songdata-github-release.local.ps1` として保存し、`$env:GITHUB_TOKEN` と `$env:GITHUB_REPOSITORY` を編集します。トークンは **単引用符** `'ghp_...'` が安全です。
3. 環境変数 **`GITHUB_TOKEN`** / **`GH_TOKEN`** と **`GITHUB_REPOSITORY`**
4. PowerShell 引数 **`-Token`** / **`-Repo`**（履歴に残りやすいので非推奨）

リポジトリでは **`upload-songdata-github-release.secrets.txt`** と **`upload-songdata-github-release.local.ps1`** は **`.gitignore`** 済みです。

### `secrets.txt` の書き方（詳細・手順）

サンプル **`scripts/upload-songdata-github-release.secrets.txt.example`** には、ダミーの **`ghp_REPLACE_ME`** と **`owner/repo`** が書いてあります。ここでいう「1 行目にトークンを書く」とは、**そのダミー文字列を消して、代わりにあなたが GitHub で発行した本物のトークンだけを 1 行目に置く**という意味です。

| やること | 説明 |
|----------|------|
| **置き場所** | **`upload-songdata-github-release.ps1` と同じフォルダ**に、`upload-songdata-github-release.secrets.txt` という名前で保存する（名前の typo に注意）。 |
| **1 行目** | **プレースホルダを残さない。** `ghp_REPLACE_ME` という文字列ごと削除し、その行に **GitHub が一度だけ表示する PAT** を貼り付ける。前後にスペースや全角スペースを付けない。 |
| **2 行目** | アップロード先の **`ユーザー名または組織名/リポジトリ名`**（例: `katsu996/test-CursorToSlack`）。`owner/repo` は例なので、**必ず自分のリポジトリに書き換える**。 |
| **コメント行** | `#` で始まる行は無視される。トークン行の先頭に `#` を付けない。 |
| **引用符** | 通常は不要。付けるなら **`'ghp_...'`** のように **一重だけ**（スクリプトが外側の引用符を 1 組は剥がす）。 |
| **`KEY=value` 形式** | 次の形式も 1・2 行目で使える: `GITHUB_TOKEN=...` / `GH_TOKEN=...`、リポジトリは `GITHUB_REPOSITORY=owner/repo` または `REPO=owner/repo`。 |
| **文字コード** | **UTF-8** で保存（メモ帳なら「名前を付けて保存」→ **文字コード: UTF-8**。**UTF-16（Unicode）** だとトークンが壊れ **401** になりやすい）。 |

**「`ghp_REPLACE_ME` を消してトークンを書く」＝「`ghp_REPLACE_ME` という文字列はファイルに残さず、そこに本物のトークンを上書きする」**で合っています。`ghp_REPLACE_ME` の **`REPLACE_ME` だけ**を消して **`ghp_` に自分のトークンの続きを足す**、のような編集はしないでください（無効なトークンになります）。

#### トークン（PAT）の作り方（GitHub 上）

1. GitHub にログインし、右上の自分のアイコン → **Settings**（個人アカウントの設定）。
2. 左メニュー一番下付近 → **Developer settings** → **Personal access tokens**。
3. **Fine-grained tokens** または **Tokens (classic)** のどちらかで **Generate**。
4. 権限の目安:
   - **Classic（プライベートリポジトリ）:** **`repo`** にチェック。
   - **Classic（パブリックのみ）:** 多くの場合 **`public_repo`** で足りることがあります（足りない場合は `repo` を検討）。
   - **Fine-grained:** 対象リポジトリを選び、**Repository permissions → Contents を Read and write**（メタデータ読み取りは通常デフォルトで可）。
5. 生成直後に表示されるトークンを **コピー**し、**すぐ** `secrets.txt` の **1 行目**に貼り付けて保存（あとから GitHub の画面では全文は再表示されません）。
6. **組織のリポジトリ**で SAML SSO を使っている場合: トークン一覧からそのトークンの **Configure SSO** で組織を **Authorize** しないと **401** になることがあります。

#### 動作確認の目安

- バッチ実行直後に **`API target repository: あなたのowner/あなたのrepo`** と出る。ここが意図と違うなら **2 行目**を修正。
- **`401 Unauthorized`** のときは、**トークンが無効・期限切れ・権限不足・UTF-16 保存・プレースホルダのまま**などが多いです。上表と PAT 権限を再確認してください。

### タグ名

- **引数を省略**した場合、タグは自動で **`songdata-YYYY-MM-DD`**（実行日の日付）になります。
- **固定タグ**にしたい場合は第 1 引数または `-Tag` で指定します（GitHub の **Latest Release** はタグ名に依存しないため、Actions 用の変数と揃える必要はありません）。

```bat
upload-songdata-github-release.bat
upload-songdata-github-release.bat songdata-latest
```

### 例（`songdata.db` があるフォルダにコピーした場合）

```bat
cd /d F:\path\to\folder-with-songdata
copy \\path\to\repo\scripts\upload-songdata-github-release.bat .
copy \\path\to\repo\scripts\upload-songdata-github-release.ps1 .
copy \\path\to\repo\scripts\upload-songdata-github-release.secrets.txt.example upload-songdata-github-release.secrets.txt
rem Edit secrets txt: line 1 = token, line 2 = owner/repo
upload-songdata-github-release.bat
```

### 例（リポジトリの `scripts` から実行する場合）

```bat
cd C:\path\to\this-repo
copy scripts\upload-songdata-github-release.secrets.txt.example scripts\upload-songdata-github-release.secrets.txt
rem Edit secrets txt, then:
scripts\upload-songdata-github-release.bat
```

別パスのアップロード元を指定する例:

```bat
scripts\upload-songdata-github-release.bat -SongdataPath D:\beatoraja\songdata.db
```

- 指定タグの **Release が無い場合は新規作成**します。リモートにタグが無い場合、API の `target_commitish` に **`main`** を渡します（既定ブランチが `master` などの場合は `-DefaultBranch master` を指定してください）。
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

ジョブの順序・`gh release download` の挙動・キューエラー時の切り分けは **[ci-github-pages-workflow.md](./ci-github-pages-workflow.md)** を参照してください。

ここでは運用上の要点だけ再掲します。

- チェックアウト直後に **Latest Release** から **`songdata.db`** を `data/songdata.db` に取得し、**非空**を検証（失敗時はワークフロー全体がエラー）。
- **Latest Release に `songdata.db` が無い**と `filter_table.py` も **Actions 上でエラー**になります（[github-actions-songdata-table-filter.md](./github-actions-songdata-table-filter.md) の「CI でのジョブ順」も参照）。
- 難易度表が更新されないときは、**通常 Release か**、**Latest バッジが付いているか**、**アセット名が `songdata.db` か**を確認してください。**プレリリースのみ**だと Latest に載らず取得に失敗し得ます。

リポジトリ変数 **`SONGDATA_RELEASE_TAG`** は **不要**です（以前の版で使っていた場合は削除して問題ありません）。

プライベートリポジトリでも、既定の `GITHUB_TOKEN` で同一リポジトリの Release を取得できます。

## ローカルで取得する例

```bash
# Latest（タグ省略）から取得
gh release download -p songdata.db -O data/songdata.db --repo OWNER/REPO

# 特定タグから取得
gh release download songdata-2026-05-26 -p songdata.db -O data/songdata.db --repo OWNER/REPO
```

`curl` のみの場合は、[List release assets](https://docs.github.com/en/rest/releases/assets?apiVersion=2022-11-28#list-release-assets) で `browser_download_url` を取得してから `curl -L` するか、公開リポジトリなら上記の固定 URL を使います。

## 注意

- **アセット名**は **`songdata.db`**（ワークフロー・CI はこの名前のみを取得します）
- **100MB 以上**の単一アセットは GitHub の制限に抵触するため、その場合はオブジェクトストレージ（S3 互換など）を検討してください
- Release を消すと **そのタグに紐づくダウンロード URL も無効**になります。長期運用するならタグの命名規則を決め、**上書き用の別タグ**にするか、履歴として残すかを決めてください
