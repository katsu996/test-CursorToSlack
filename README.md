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

**プリセット SQL:** **`sql_where_preset`** に `const_bpm`（等速）または `var_bpm`（変速）を書くと、**固定の安全な SQL だけ**を使います（このとき **`sql_where` は無視**されます）。

**識別子の制限:** 既定では `sql_where` に現れる識別子は **`song` テーブルの列名**に限定されます。複雑な式が必要なときだけ **`sql_where_disable_identifier_whitelist` を `true`** にしてください（**信頼できる内容のみ**コミットすること）。

**セキュリティ:** スクリプトは `;` や `ATTACH` など一部パターンを拒否しますが、上記のとおり**信頼できる内容だけ**をコミットしてください。

**beatoraja が 0 件のとき:** **`beatoraja_empty_rows_policy`** が **`fail`（既定）**のとき、`filter_table.py` は **終了コード 1** となり Actions が失敗します（空の難易度表をデプロイしない）。緩めたい場合のみ `warn` などに変更してください。

### 4. 取り込む難易度表の URL を変える・足す（`source_tables` / `source_tables_path`）

1. **推奨:** **`tools/table-filter/source_tables.json`**（または任意の名前の JSON）に、**難易度表ソースの配列**を書きます。`filter_config.json` の **`source_tables_path`** に、そのファイルへの相対パス（`filter_config.json` と同じディレクトリ基準）を指定します。**`source_tables_path` が非空のときはファイルが優先**され、インラインの **`source_tables`** は上書きされます。  
2. **インラインで書く場合:** **`tools/table-filter/filter_config.json`** の **`source_tables`**（オブジェクトの配列）を直接編集しても構いません（`source_tables_path` は空にするか省略）。**1 要素 = 1 本の難易度表**で、URL・表示名・略称の対応が一目で分かります。  
3. 各オブジェクトのフィールド:  
   - **`header_url`**（必須）: **ヘッダー JSON の HTTPS URL**、または **難易度表 HTML**（`<meta name="bmstable" content="...">` からヘッダーを解決）。**`url`** でも同じ意味で指定できます。  
   - **`display_name`**（任意）: 行の「出自（フル）」や Pages メタの凡例に使います。空のときはヘッダー JSON の `name` / `title` にフォールバックします。  
   - **`short_name`**（任意）: 「シンボル」列や絞り込み用（例: `sl` / `st`）。空なら略称なし扱いです。  
   - **`custom_level_mapping`**（任意）: そのソースだけの「元レベル文字列 → 独自レベル」のオブジェクト（詳細は §10）。

**注意（Cloudflare 等）:** 入口 URL が **ボット検証用の HTML だけ**を返し、**ヘッダー JSON が取れない**と `filter_table.py` は失敗します（GitHub Actions のランナーで起きやすい）。**既定の `source_tables.json` には** [通常難易度表（☆）](https://darksabun.club/table/archive/normal1/) を **含めています**。Actions で失敗する場合は、一時的に当該要素を外すか、**ヘッダー JSON の HTTPS 直 URL**（HTML の `<meta name="bmstable">` を経由しない）や手元で取得可能なミラーに差し替えてください。

**後方互換:** `source_tables` が空かつ **`source_tables_path` も空**のときは、従来どおり **`source_header_urls`**（URL のみの配列）と、任意の **`source_table_display_names`** / **`source_table_short_names`**（**同じインデックスで対応**）でも動きます。

**1 本だけ指定する場合:** `source_tables` を `[]` にし、**`source_tables_path` も空**にして、**`source_header_url`** に文字列で 1 本書いても動きます。

**単一ソース時のみ:** **`source_data_url`** にデータ JSON の URL を書くと、ヘッダー内の `data_url` の代わりに使われます。**複数ヘッダー**（`source_tables` が 2 要素以上、または `source_tables_path` で読んだ配列が 2 件以上、または `source_header_urls` が 2 件以上）のときは **各ヘッダーの `data_url` のみ**が使われ、`source_data_url` は無視されます（警告が出ます）。

マージ後の各行には **`source_table_index` / `source_table_short_names` / `source_table_names`** などが付き、**複数の入力表をマージしたときにどの表由来の譜面として残ったか**が分かります（詳細は [docs/github-actions-songdata-table-filter.md](docs/github-actions-songdata-table-filter.md) の「出自の難易度表」節）。

**合成難易度表ヘッダーの `name`（任意）:** **`output_header_name`** に文字列を書くと、**`filtered_header.json` の `name`**（beatoraja に表示される表名）に使われます。空のときは元ヘッダーの `name` がそのまま使われ、それも空ならスクリプト既定の英語名になります。beatoraja は **`name` が空の表を拒否**します。

**Pages のタイトルだけ変えたい（任意）:** **`page_title`** に文字列を書くと、GitHub Pages の **`<title>` とトップの見出し**に使われます（未設定時は `output_header_name` と同じ）。

### Pages トップの列幅・列の既定表示（任意）

1. **`docs/table/pages_ui_config.json`** の **`column_widths`**（例: `t:title` / `d:genre` / `chart`）と **`column_visible_defaults`**（`table` / `db` ごとの列キー → 表示なら `true`）を編集します。同梱ファイルでは `//` コメントで列幅テンプレや将来列用の雛形を置いてあり、ビルド時に除去されます（詳細は [docs/pages-ui-config.md](docs/pages-ui-config.md)）。`song` の全列と難易度表側の想定列は `true` / `false` で明示しています。  
2. 別パスに置きたい場合は **`tools/table-filter/filter_config.json`** の **`pages_ui_config_path`** にそのパスを書きます（空なら上記の既定パスです）。  
3. **`build_pages_table.py` が走るビルド**（`main` への push など）のあと、`browser_rows.json` の **`meta.pages_ui`** に反映されます。

詳細は **[docs/pages-ui-config.md](docs/pages-ui-config.md)** を参照してください。

### 5. フィルタそのものをオフにしたい・難易度表取得を止めたい

次のいずれかで、**外部表の取得と `docs/table/` への生成**はスキップされます（Pages の `docs/` 静的ファイルのデプロイは続きます）。

- **`enabled`** を `false` にする  
- **`source_tables_path` も空**で **`source_tables` を `[]` にし、かつ **`source_header_urls`** が空（または無い）で **`source_header_url`** も空にする  

この場合、`filter_table.py` は何も出力せず、その後の **`build_pages_table.py`** は空の **`browser_rows.json`** を出します（トップの表は空になります）。

### 6. `songdata.db` が無いときの挙動を変えたい

- **`skip_if_no_songdata`: `true`（既定）** — `data/songdata.db` が無いとフィルタはスキップ（エラーにしない）  
- **`false`** — DB が無いと **Actions が失敗**します（厳格にしたいとき）

### 7. 変更を GitHub に反映する（デプロイのトリガー）

- **`main` へ push** する  
  または  
- **Actions → Deploy GitHub Pages → Run workflow**（手動実行）

成功したら **Settings → Pages** に表示される **サイト URL** で `index.html` が開きます。

**統合難易度表別の曲数（集計のみ）:** 同じサイトの **`level-stats.html`**（例: `https://<ユーザー>.github.io/<リポジトリ名>/level-stats.html`）を開きます。データは `table/level_stats.json` で、フィルタがスキップされたビルドではファイルが無くエラーになることがあります。

### 8. beatoraja に「絞り込み後の難易度表」を登録する

**Table URL**（設定 → リソース）に、次のような **`.json` で終わる HTTPS URL** を追加し、**難易度表読み込み**を実行します。

`https://<あなたのユーザー名>.github.io/<リポジトリ名>/table/filtered_header.json`

（`<owner>` と `<repo>` は実際の値に置き換えてください。）

**Pages のトップ:** `index.html` のフッターに、上記と同じパスの **`filtered_header.json` を開くリンク**があります（新しいタブで JSON が表示されます）。Table URL の確認や共有に使えます。一覧表の右端の **Chart** 列は、難易度表行の **`md5`** から [bms-score-viewer](https://bms-score-viewer.pages.dev/)（`view?md5=…`）へのリンクです。

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

複数の入力難易度表を **`source_tables`**（または **`source_tables_path`** で読む別 JSON、従来の **`source_header_urls`**）に並べているとき、**各ソースごと**に「元のレベル値 → 独自レベル」の対応表を持てます（例: 1 番目の表のレベル 12 は独自 12、2 番目の表のレベル 1 は独自 13）。

1. **`tools/table-filter/source_tables.json`**（またはインラインの **`source_tables`**）の **該当要素に `custom_level_mapping` オブジェクト**を書く（推奨）。**キーが元表のレベル（文字列）**、**値が独自レベル**（数値でも文字列でも可）。  
2. **後方互換:** **`tools/table-filter/filter_config.json`** のトップレベル **`custom_level_mapping`** に、**ソースと同じ順の配列**を置く方法もあります（短い場合は足りない分だけマップ無し、長い場合は余りは無視。警告が Actions ログに出ます）。**エントリ側にマップがあるソースではそちらが優先**され、トップレベルは **エントリにマップが無いインデックスのフォールバック**です。  
3. 出力される列名は既定で **`custom_level`**。変えたい場合は **`custom_level_field`**（英数字とアンダースコアのみ）  
4. 元表から読む列名が `level` 以外のときは **`custom_level_source_key`** を合わせる  
5. マップに無いレベルが来たときは **`custom_level_unmapped`** で制御する  
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
| beatoraja 向け難易度表 JSON の前提（回帰防止） | [docs/beatoraja-jbmstable-table-json.md](docs/beatoraja-jbmstable-table-json.md) |
| `filter_config.json` のキー一覧（スキーマ） | [docs/filter-config-schema.md](docs/filter-config-schema.md) |
| 静的 UI から Vite+React 移行を検討するときの整理 | [docs/frontend-migration-costs.md](docs/frontend-migration-costs.md) |
| 保守・改善バックログ（優先度の意味と定期メンテ） | [todo.md](todo.md) |

ワークフロー定義: [.github/workflows/pages.yml](.github/workflows/pages.yml)
