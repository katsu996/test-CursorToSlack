# test-CursorToSlack

beatoraja の `songdata.db` と難易度表 JSON を組み合わせ、GitHub Actions で絞り込み JSON を生成し、GitHub Pages で公開する実験用リポジトリです。

---

## あなたが手動で行う作業（一覧）

以降の作業は、**GitHub の Web 画面**と**ローカル（または Codespace）のエディタ**、必要に応じて **git** で行います。自動で済む処理（Python やワークフロー）は [docs/github-actions-songdata-table-filter.md](docs/github-actions-songdata-table-filter.md) にまとめています。

### 1. 初回のみ: GitHub Pages の公開元を「GitHub Actions」にする

1. リポジトリの **Settings → Pages**
2. **Build and deployment** の **Source** で **GitHub Actions** を選ぶ

これをしないと `.github/workflows/pages.yml` のデプロイがサイトに反映されません。

### 2. `songdata.db` を差し替える（更新のたび）

1. PC の beatoraja データフォルダから **`songdata.db`** をコピーする
2. 本リポジトリの **`data/songdata.db`** に上書きする（パスをずらさない）
3. 変更をリポジトリに載せる  
   - **Git**: `git add data/songdata.db` → `git commit` → `git push`  
   - **GitHub Web**: **Add file → Upload files** で `data/songdata.db` を置き換えてコミット

**補足:** `songdata.db` は **Pages のサイト上には出ません**。Actions のランナー上でフィルタにだけ使われます。ファイルが大きい場合は [data/README.md](data/README.md) の注意も読んでください。

### 3. フィルタ用 SQL（`sql_where`）を変える

1. **`tools/table-filter/filter_config.json`** を開く
2. **`sql_where`** を編集する（`song` テーブルにそのまま `WHERE (...)` の括弧内として連結されます）

例:

- **等速 BPM（min と max が同じ）:**  
  `minbpm IS NOT NULL AND maxbpm IS NOT NULL AND minbpm = maxbpm`
- **変速 BPM（min と max が異なる）:**  
  `minbpm IS NOT NULL AND maxbpm IS NOT NULL AND minbpm != maxbpm`

**NULL 行:** `minbpm` / `maxbpm` が NULL の譜面は上記のように `IS NOT NULL` を付けないと条件に入らないことがあります。

**セキュリティ:** スクリプトは `;` や `ATTACH` など一部パターンを拒否しますが、**信頼できる内容だけ**をコミットしてください。

### 4. 元難易度表の URL を変える・足す

1. 同じく **`tools/table-filter/filter_config.json`** の **`source_header_urls`**（配列）を編集する  
2. 各要素は次のどちらでも可です。  
   - **ヘッダー JSON の HTTPS URL**（例: `https://example.com/header.json`）  
   - **難易度表の HTML の URL**（`<meta name="bmstable" content="...">` からヘッダー JSON を自動解決）

**1 本だけ指定する場合:** `source_header_urls` を空配列 `[]` にし、**`source_header_url`** に文字列で 1 本書いても動きます（後方互換）。

**単一ソース時のみ:** **`source_data_url`** にデータ JSON の URL を書くと、ヘッダー内の `data_url` の代わりに使われます。**複数ヘッダー**（`source_header_urls` が 2 件以上）のときは **各ヘッダーの `data_url` のみ**が使われ、`source_data_url` は無視されます（警告が出ます）。

マージ後の各行には **`source_table_index` / `source_table_short_names` / `source_table_names`** など、どの元難易度表の譜面として採用されたかが付きます（詳細は [docs/github-actions-songdata-table-filter.md](docs/github-actions-songdata-table-filter.md) の「出自の難易度表」節）。

**Pages に出す表の表示名（任意）:** **`source_table_display_names`** を `source_header_urls` と同じ長さの文字列配列で書くと、行の「出自（フル）」列と、Pages トップのメタ「元難易度表（表示名）」にその名前が使われます（stellabms の SL / ST を「Satellite」「Stella」などに変えたいとき）。**`source_table_short_names`** も同じ長さの配列で書くと、行の「シンボル」列（例: `sl` / `st`）とメタ「元難易度表（略称）」に使われます（空の要素はそのインデックスの略称なし）。**`source_table_display_names`** の空要素だけ、ヘッダー JSON の `name` / `title` にフォールバックします。Pages の **`browser_rows.json` には元 URL を載せません**（取得元 URL はこの `filter_config.json` を参照）。

**合成難易度表ヘッダーの `name`（任意）:** **`output_header_name`** に文字列を書くと、**`filtered_header.json` の `name`**（beatoraja に表示される表名）と **Pages トップ（`index.html`）のタイトル**に使われます。空のときは元ヘッダーの `name` がそのまま使われ、それも空ならスクリプト既定の英語名になります。beatoraja は **`name` が空の表を拒否**します。

### 5. フィルタそのものをオフにしたい・難易度表取得を止めたい

次のいずれかで、**外部表の取得と `docs/table/` への生成**はスキップされます（Pages の `docs/` 静的ファイルのデプロイは続きます）。

- **`enabled`** を `false` にする  
- **`source_header_urls`** を `[]` にし、**`source_header_url`** も空にする  

この場合、`filter_table.py` は何も出力せず、その後の **`build_pages_table.py`** は空の **`browser_rows.json`** を出します（トップの表は空になります）。

### 6. `songdata.db` が無いときの挙動を変えたい

- **`skip_if_no_songdata`: `true`（既定）** — `data/songdata.db` が無いとフィルタはスキップ（エラーにしない）  
- **`false`** — DB が無いと **Actions が失敗**します（厳格にしたいとき）

### 7. 変更を GitHub に反映する（デプロイのトリガー）

- **`main` へ push** する  
  または  
- **Actions → Deploy GitHub Pages → Run workflow**（手動実行）

成功したら **Settings → Pages** に表示される **サイト URL** で `index.html` が開きます。

**元難易度表別の曲数（集計のみ）:** 同じサイトの **`level-stats.html`**（例: `https://<ユーザー>.github.io/<リポジトリ名>/level-stats.html`）を開きます。データは `table/level_stats.json` で、フィルタがスキップされたビルドではファイルが無くエラーになることがあります。

### 8. beatoraja に「絞り込み後の難易度表」を登録する

**Table URL**（設定 → リソース）に、次のような **`.json` で終わる HTTPS URL** を追加し、**難易度表読み込み**を実行します。

`https://<あなたのユーザー名>.github.io/<リポジトリ名>/table/filtered_header.json`

（`<owner>` と `<repo>` は実際の値に置き換えてください。）

**サイトのトップだけ**（例: `https://<ユーザー>.github.io/<リポジトリ名>/`）を Table URL に入れると、beatoraja は **HTML モード**でページを取得します。トップの **`docs/index.html` に `<meta name="bmstable" content="table/filtered_header.json">` を入れてある**ため、この URL でもヘッダー JSON に辿り着けます。ただし **末尾スラッシュ無し**（`…/repo`）の URL では jbmstable-parser の相対解決がずれることがあるため、**末尾 `/` 付き**か、確実には上記の **`filtered_header.json` 直リンク**を推奨します。

生成される `filtered_header.json` の **`data_url` は既定で `filtered_data.json` のみ**（ヘッダーと同じパス上の相対指定）です。`SITE_BASE_URL` の誤りでデータが取れない問題を避けるための挙動です。**絶対 URL で出したい場合**は `tools/table-filter/filter_config.json` で **`use_relative_data_url` を `false`** にし、**`site_base_url`**（またはローカルでは環境変数 **`SITE_BASE_URL`**）をセットしてください。

**HTML 経由が必要なクライアント**では、同じ `docs/table/` にある **`bmstable.html`** の URL（例: `…/table/bmstable.html`）を Table URL に試すこともできます（`<meta name="bmstable" content="filtered_header.json">` でヘッダーを解決します）。

**読み込みで「難易度表の値が不正です」になる主な理由:** 本体の `TableData.validate()` は、表の **`name` が空でないこと**と、**フォルダまたは段位に有効な譜面が 1 件以上あること**を要求します。`filtered_data.json` が **空配列**（`songdata.db` と元表のハッシュが交差しない、`sql_where` で全落ち、厳格条件で全スキップなど）のときは、ヘッダーだけ取得できても **必ず失敗**します。Actions のログに `beatoraja 向けデータ行が 0 件` のメッセージが出ていないかも確認してください。

### 9. 結果がおかしいときに手動で確認すること

- **Actions が赤い:** ログで `filter_table.py`（外部 URL 取得・SQL）のエラーを確認する  
- **表の行が 0 件:**  
  - 元表の `md5` / `sha256` と **`songdata.db` の `song` に存在する行**の交差だけが残るため、**DB を更新していない譜面**は落ちます  
  - **`sql_where`** に合わない BPM の譜面も落ちます  
- **beatoraja で「難易度表の値が不正です」:**  
  - **`filtered_data.json` が空**（上記の交差ゼロ・条件で全落ちなど）だと、本体の `TableData.validate()` で必ず失敗します。Actions ログに **`beatoraja 向けデータ行が 0 件`** が出ていないか確認してください  
  - Table URL に **サイトのトップ**だけを入れている場合は、**`docs/index.html` の `bmstable` meta**（`table/filtered_header.json` への相対）がデプロイに含まれているか確認してください（**末尾スラッシュ無しの `…/repo`** は相対解決がずれることがあります）  
- **トップの表が空:** 上記の「フィルタスキップ」や `filtered_data_enriched.json` / `filtered_data.json` 未生成の状態で `browser_rows.json` が空になっている可能性があります

### 10. 元表ごとにレベルを「独自難易度」へ写す（`custom_level_mapping`）

複数の元難易度表を `source_header_urls` に並べているとき、**配列の何番目の表か**に応じて「元のレベル値 → 独自レベル」の対応表を持てます（例: 1 番目の表のレベル 12 は独自 12、2 番目の表のレベル 1 は独自 13）。

1. **`tools/table-filter/filter_config.json`** を開く  
2. **`custom_level_mapping`** に、**`source_header_urls` と同じ長さの配列**を用意する（短い場合は足りない分だけマップ無し、長い場合は余りは無視。警告が Actions ログに出ます）  
3. 各要素は JSON オブジェクトで、**キーが元表のレベル（文字列）**、**値が独自レベル**（数値でも文字列でも可）  
4. 出力される列名は既定で **`custom_level`**。変えたい場合は **`custom_level_field`**（英数字とアンダースコアのみ）  
5. 元表から読む列名が `level` 以外のときは **`custom_level_source_key`** を合わせる  
6. マップに無いレベルが来たときは **`custom_level_unmapped`** で制御する  
   - **`omit`（既定）:** `custom_level` 列を付けない（その行だけ欠損）  
   - **`source`** または **`original`:** 元のレベル値をそのまま `custom_level` にコピー  
   - **`null`:** JSON の `null` を入れる  

**重複譜面:** 複数表で同じ `md5` / `sha256` が出た場合は **先に列挙したヘッダー側の行だけが残り**、独自レベルもそのソースのマップだけが使われます。

**beatoraja の Table JSON:** `filtered_data.json` は beatoraja（jbmstable-parser）向けに、出自メタ列・`id` を除き、かつパーサが弾く行を落としたものです（`level` / `title` / `artist` などは文字列に正規化）。GitHub Pages の表は **`filtered_data_enriched.json`**（同じ行に出自列などが残る）を元に `browser_rows.json` が生成されます。`custom_level` は既定では beatoraja 向けにも残ります。不要なら `beatoraja_strip_chart_keys` に `custom_level` を追加してください。`beatoraja_strip_chart_keys` で beatoraja 側から除外するキーを上書きできます（詳細は [docs/github-actions-songdata-table-filter.md](docs/github-actions-songdata-table-filter.md)）。

詳細なデータフローは [docs/github-actions-songdata-table-filter.md](docs/github-actions-songdata-table-filter.md) を参照してください。

---

## ドキュメント（仕様・裏側の処理）

手動チェックリスト以外の説明（DB 仕様、Actions のデータフロー、仮想フォルダ要件など）は **`docs/`** にあります。

| 内容 | パス |
|------|------|
| beatoraja 楽曲 DB（`songdata.db` / `songinfo.db`）の整理 | [docs/bms-beatoraja-song-db.md](docs/bms-beatoraja-song-db.md) |
| 条件付き仮想フォルダ（`folder/default.json`）の要件・調査 | [docs/requirements-filtered-bms-folder-tool.md](docs/requirements-filtered-bms-folder-tool.md) |
| `default.json` 断片の例（`minbpm != maxbpm`） | [examples/beatoraja-default-json-snippet-changing-bpm.json](examples/beatoraja-default-json-snippet-changing-bpm.json) |
| beatoraja と LR2oraja / Endless Dream の違い | [docs/beatoraja-vs-lr2oraja-derivatives.md](docs/beatoraja-vs-lr2oraja-derivatives.md) |
| 難易度表の URL 公開・自作表の考え方 | [docs/beatoraja-difficulty-table-url-and-filtered-publish.md](docs/beatoraja-difficulty-table-url-and-filtered-publish.md) |
| GitHub Pages の仕組み・別リポジトリへのコピー手順 | [docs/github-pages-publish-guide.md](docs/github-pages-publish-guide.md) |
| **Actions・Python スクリプトの処理内容**（フィルタ、マージ、制限） | [docs/github-actions-songdata-table-filter.md](docs/github-actions-songdata-table-filter.md) |
| `docs/` ディレクトリの役割（公開ルート） | [docs/README.md](docs/README.md) |
| フィルタの CLI・設定キーの開発者向けメモ | [tools/table-filter/README.md](tools/table-filter/README.md) |

ワークフロー定義: [.github/workflows/pages.yml](.github/workflows/pages.yml)
