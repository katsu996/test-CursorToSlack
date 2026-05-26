# songdata.db と SQL で難易度表を絞り込み、GitHub Actions で公開する（技術メモ）

## 運用手順について

**日々の手動作業**（`songdata.db` の差し替え、`filter_config.json` の SQL・URL 変更、Pages の初回設定、push、beatoraja の Table URL など）は、**リポジトリ直下の [README.md](../README.md)** にすべて集約しています。本文書は **CI・スクリプトの裏側**と設計上の注意に絞ります。

## 結論: GitHub Actions だけで実現できるか

**はい。** 次を満たせば、ランナー上で「元表を取得 → `songdata.db` に SQL → ハッシュ交差でフィルタ → `docs/table/` に JSON 出力 → `docs/` 全体を GitHub Pages にデプロイ」まで完結します。

1. 実行時に **`data/songdata.db`** がリポジトリに存在する（通常はコミット済み）。
2. 統合難易度表のヘッダーが **HTTPS で取得できる**（`filter_config.json` の **`source_tables`**（インラインまたは **`source_tables_path`** で読み込んだ別 JSON）、または後方互換の **`source_header_urls`** / **`source_header_url`**）。データ本体は各ヘッダーの `data_url`（**相対パスはヘッダー JSON の URL を基準に解決**）または単一ソース時の `source_data_url`。
3. 生成ヘッダーの `data_url` は **既定でファイル名のみ**（例: `filtered_data.json`）とし、beatoraja がヘッダーと同じディレクトリ上のデータ JSON を取得できるようにします（`SITE_BASE_URL` は不要）。**絶対 URL で出したい場合のみ** `use_relative_data_url: false` と `site_base_url` / `SITE_BASE_URL` を併用します。

**GitHub が提供していないもの:** ブラウザだけで手元の DB を渡す専用 UIはありません。DB は **リポジトリに載せて更新する** 想定です。

## CI（`Deploy GitHub Pages`）で起きること

ワークフローは [.github/workflows/pages.yml](../.github/workflows/pages.yml) です。`main` への push または手動 dispatch で実行されます。

| 順序 | 処理 | 入力 | 主な出力 |
|------|------|------|----------|
| 0 | `ruff check` / `unittest` / `check_filter_config_example_sync.py` | `tools/table-filter/` | 静的解析・テスト・設定例のキー整合 |
| 1 | `filter_table.py` | `tools/table-filter/filter_config.json`、`data/songdata.db`（存在時） | `docs/table/filtered_data.json`（beatoraja 用・拡張列除去）、`filtered_data_enriched.json`（Pages 用・出自列あり）、`filtered_header.json`、`level_stats.json`（条件によりスキップ可） |
| 2 | `build_pages_table.py` | 同上設定、`filtered_data_enriched.json`（無ければ `filtered_data.json`）、`songdata.db` | `docs/table/browser_rows.json`（トップ `index.html` の一覧表用） |
| 3 | `check_browser_rows_pages_ui.py` | `docs/table/browser_rows.json` | `meta.pages_ui` の必須キー（`index_table`・IR・Chart 等）が欠けていれば **終了コード 1** |
| 4 | `smoke_check_outputs.py` | 生成済み `docs/table/*.json` | 空データやヘッダー不備があれば **終了コード 1** |
| 5 | Pages アーティファクト | `docs/` ディレクトリ全体 | GitHub Pages にアップロード |

- **`data_url`（生成ヘッダー）:** 既定（`use_relative_data_url` 未指定または `true`）では **`filtered_data.json` のようなファイル名のみ**を書き、jbmstable-parser が **ヘッダー JSON の URL と同じディレクトリ**からデータを取得します。`use_relative_data_url: false` のときだけ `site_base_url` または環境変数 **`SITE_BASE_URL`** が必要で、`${SITE_BASE_URL}/filtered_data.json` 形式にします。
- **`filter_table.py` の終了コード 0:** 設定なし・`enabled: false`・ヘッダー URL 空・`songdata.db` 不在（`skip_if_no_songdata: true`）などでも **0 で終了**し、後段の `build_pages_table.py` が続きます。
- **beatoraja 向けデータが 0 件:** 既定の **`beatoraja_empty_rows_policy: fail`** のとき **`filter_table.py` は終了コード 1** となり、その後の `build_pages_table.py` / スモーク / デプロイは実行されません（空の難易度表を公開しない）。
- **`level_stats.json`:** フィルタが実際に走ったときのみ `docs/table/` に出力されます。各元表について、**元表データ行全体**と **`sql_where` 通過後・`md5`/`sha256` 重複マージ前**の行を、表 JSON のレベル列（既定は `custom_level_source_key` と同じく `level`）の値ごとに数えた集計です（`version` 2 以降は同一行に「SQL 前」「SQL 後」の列比較用の `level_rows` を含みます）。GitHub Pages では **`level-stats.html`** が `./table/level_stats.json` を直接読み込んで表示します。
- **`build_pages_table.py`:** `filtered_data_enriched.json` が無ければ `filtered_data.json` を読みます。どちらも無い場合は **空の `browser_rows.json`**（理由を `meta` に記録）を書き、Pages デプロイは失敗させません。

## `filter_table.py` のモジュール分割

取得・SQL 検証・beatoraja 向け整形・レベル集計の補助は次に分割しています（`filter_table.py` がオーケストレーションします）。

| ファイル | 役割 |
|----------|------|
| `http_fetch.py` | 外部 JSON/HTML の取得（タイムアウト・リトライ・指数バックオフ・stderr ログ） |
| `sql_where_guard.py` | `sql_where_preset` / 自由記述 `sql_where` の解決、`;` 等の禁止、**識別子ホワイトリスト**（`sql_where_disable_identifier_whitelist` で無効化可） |
| `beatoraja_rows.py` | 行の正規化・厳格条件チェック・ヘッダー `course` 空配列の除去・`beatoraja_strip_chart_keys` |
| `level_stats.py` | `level_stats.json` 用のレベルバケット化・ソート・比較行の生成 |

## `filter_table.py` のデータフロー（概要）

1. **`sql_where`**（または **`sql_where_preset`**）を解決し、検証したうえで `SELECT DISTINCT md5, sha256 FROM song WHERE (<断片>)` で **許可ハッシュ集合**を得る。
2. 各 **元ヘッダー**を取得（URL が `.html` のときは `<meta name="bmstable">` からヘッダー JSON URL を解決）。
3. ヘッダーの **`data_url`** を取得（相対ならヘッダー URL に `urljoin`）。単一ソースかつ **`source_data_url`** があればそちらを優先。
4. データ配列の各行について **`md5` / `sha256`** が許可集合に含まれる行だけ残す。
5. 各ソースについて、**元表データの全行**をレベル列でバケット化した件数（SQL 条件前）と、**フィルタ通過行**について同様の集計（SQL 条件後）を作り、**重複マージより前**の意味で `level_stats.json` の `sources` に書き留める（`level_rows` で同一レベル行に前後件数を並べる。単一ヘッダーでも同様）。
6. **複数ヘッダー**のときは、通過行を **`md5` / `sha256` で重複除去**して 1 本のデータ配列にマージ。`course` は各ヘッダー由来を **配列として連結**。合成ヘッダーは **先頭ヘッダーをベース**にし、`data_url` は既定で **`filtered_data.json` などファイル名のみ**（ヘッダーと同じ公開ディレクトリ上のデータを指す）。
7. マージ時、データ行の各オブジェクトに **出自の難易度表**を示すフィールドを付与する（下記「出自」節）。
8. **各ソースの `custom_level_mapping`**（または後方互換のトップレベル **`custom_level_mapping` 配列**）が設定されているときは、**新規に採用した行**（ハッシュありで `row_by_key` に初めて入る行、およびハッシュなしの行）について、**そのループの元ヘッダーインデックス**に対応するマップで、元のレベル列（既定: `level`）を引き、**`custom_level` 列（名前は `custom_level_field`）**に書き込む（下記「独自レベル」節）。

## beatoraja（jbmstable-parser）との互換

本体が使う [jbmstable-parser](https://github.com/exch-bms2/jbmstable-parser) の `DifficultyTableParser.decodeJSONTableData(..., accept=false)` は次を満たさない**データ行を黙って捨てます**（`level` が JSON `null` の行、`md5` / `sha256` の文字列長が 24 以下の行など）。

- **`filtered_data.json`:** 上記に合わない行は書き出し前に除外し、GitHub Pages 用に付けた **`source_*` 系キー**も除いたオブジェクトだけを載せます。さらに **`id`（整数の LR2 用 ID など）**は既定で除外し、`level` / `title` / `artist` などは **文字列として正規化**して SongData 検証やソートでの例外を避けます。`custom_level` を beatoraja 向けから落としたい場合は **`beatoraja_strip_chart_keys`** に追加してください。
- **`filtered_data_enriched.json`:** マージ直後の行オブジェクト（出自列などを含む）のまま保存し、**`build_pages_table.py`** がこちらを優先して読み込みます。
- **ヘッダ `course`:** 空配列 `[]` のとき jbmstable-parser は `get(0)` で落ちるため、**空なら `course` キーごと削除**します。
- **`beatoraja_strip_chart_keys`:** `filter_config.json` で、beatoraja 向けデータから除外するキーを配列で上書きできます。**未指定なら** `source_table_index` / `source_table_names` / `source_table_short_names` / `source_header_json_url` / `source_table_register_url` / `id` を除きます。**空配列 `[]`** なら除外しません。

### HTML 入口（`docs/table/bmstable.html` とサイトのトップ）

beatoraja は多くの場合 **ヘッダー JSON の URL**（`…/table/filtered_header.json`）を Table URL に足せば足ります。環境によっては **HTML の meta 経由**の方が安定する場合があるため、**`docs/table/bmstable.html`** に `<meta name="bmstable" content="filtered_header.json">` を置いています。必要なら Table URL に **`…/table/bmstable.html`** を登録してください。

**サイトのトップ（`…/`）を Table URL にした場合:** URL が **`.json` で終わらない**と本体は **HTML モード**になり、ページ内の **`<meta name="bmstable" content="...">`** からヘッダー JSON を探します。GitHub Pages の **`docs/index.html`** にも **`content="table/filtered_header.json"`** の meta を入れてあるため、ユーザーが誤って **リポジトリのトップ URL**だけを登録してもヘッダーに辿り着けます。相対解決の都合で **`https://…/repo`（末尾スラッシュ無し）**は避け、**`…/repo/`** または **`filtered_header.json` の直リンク**を推奨します。

**「難易度表の値が不正です」:** `bms.player.beatoraja.TableDataAccessor.DifficultyTableAccessor.read` 内で `TableData.validate()` が偽を返したときに投げられます。典型例は (1) **HTML に bmstable が無く**ヘッダーが解決できない、(2) **`filtered_data.json` が空**でフォルダに有効な譜面が 1 件も無い、(3) **ヘッダーの `name` が空**、などです。(1) は上記 meta で、(2) は Actions ログの `beatoraja 向けデータ行が 0 件` で気付けます。(3) は `filter_table.py` が **`output_header_name`**（設定）または既定名で `name` を補完します。

## `filtered_data_enriched.json` / `filtered_data.json` 各行の「出自の難易度表」メタデータ

`filter_table.py` は、GitHub Pages の一覧で行がどの元表由来か分かるよう、次のキーを **データ行オブジェクトに追加**します（**enriched のみ**に残し、beatoraja が読む `filtered_data.json` からは既定で除去します）。

| キー | 型 | 意味 |
|------|-----|------|
| `source_table_index` | 整数 | **`source_tables`（または `source_header_urls`）の並び**で見たときの表番号（**1 始まり**）。同一譜面が複数表に載っている場合は、**先にマージされた表**（重複除去で採用された側）の番号が残ります。 |
| `source_table_short_names` | 文字列の配列 | 設定の略称（`source_tables[].short_name` または後方互換の `source_table_short_names[i]`）が非空ならその略称（例: `sl`）。無ければ **空配列**になり得ます。複数表に同一譜面があると **`source_table_names` と同様に**後続の略称を追記します。 |
| `source_table_names` | 文字列の配列 | 設定の **`display_name`**（または後方互換の `source_table_display_names[i]`）が非空ならそれを、無ければ各ヘッダー JSON の `name` / `Name` / `title` / `Title`（なければ `表 N`）から得た **表示名**。複数表に同一譜面があると **複数要素**になります。 |
| `source_table_register_url` | 文字列（任意） | 設定に書いた **登録用 URL**（例: `table_rec.html`）。`source_tables[].header_url` または `source_header_urls` の同じインデックスの値。 |
| `source_header_json_url` | 文字列 | 実際に取得した **ヘッダー JSON の HTTPS URL**（HTML から `bmstable` で解決した後の URL）。 |

**重複譜面:** `md5` / `sha256` が同じ行は **1 行にまとめ**、`source_table_names` と `source_table_short_names` にだけ後続の表の表示名・略称を追記します。`source_table_index` は更新しません（先勝ち）。

**GitHub Pages の `index.html`:** 列が煩雑にならないよう、`source_header_json_url` と `source_table_register_url` は **画面上は非表示**にしていますが、**`filtered_data_enriched.json`**（および `browser_rows.json` の `table`）には残ります。**`url` / `url_diff`** も Pages の表では既定でオフ（列表示のチェックボックスでオンにできる）です。**beatoraja が読む `filtered_data.json`** からは出自列を除き、元表の `url` / `url_diff` はそのまま残します。**シンボル**（`source_table_short_names`）と**出自（フル）**は別列です。**表 ID**・**出自表（番号）**・**出自（フル）**・**フォルダID**（`song.folder`）も既定でオフです。

### `source_tables` / `source_tables_path`（推奨）

難易度表ソースは **`source_tables`**（オブジェクトの配列）で指定します。一覧が長くなる場合は **`source_tables_path`** に別 JSON のパス（`filter_config.json` と同じディレクトリ基準の相対パス可）を書き、**トップが配列**、または **`{"source_tables": [...]}`** のファイルを置くと、`filter_table.py` が起動時に読み込んで **`source_tables` として扱います**（**パスが非空ならファイルが優先**され、インラインの `source_tables` は上書きされます）。

各要素に **`header_url`**（または **`url`**）を書き、任意で **`display_name`**（出自フル名）、**`short_name`**（シンボル列・絞り込み用）、**`custom_level_mapping`**（オブジェクト。元レベル文字列 → 独自レベル）を **同じオブジェクト内**にまとめられます。

### `source_table_display_names`（後方互換・任意）

`source_tables` を使わず **`source_header_urls`** だけ並べる場合に、表示名を **別配列**で渡すためのキーです。`source_header_urls`（正規化後の **本数と同じ順・同じ長さ推奨**）として書くと、上記 **`source_table_names`** の各要素は **設定の文字列を優先**します。要素が空文字のインデックスは、従来どおりヘッダー JSON の `name` / `title` にフォールバックします。要素数がヘッダー数とずれると Actions ログに警告が出ます。

### `source_table_short_names`（後方互換・任意）

`source_tables` を使わない場合の略称配列です。同じく **`source_header_urls` と同じ長さ**で書くと、行の **`source_table_short_names`**（略称の配列）にその文字列が入ります（例: `sl` / `st`）。要素数がずれると Actions ログに警告が出ます。

## `browser_rows.json` の `meta`（Pages 向け）

`build_pages_table.py` が書き出す **`browser_rows.json`** の `meta` には、**GitHub Pages のトップで URL を出さない**方針のため、**`source_header_urls` / `source_header_url` は含めません**。代わりに次を含みます。

| キー | 意味 |
|------|------|
| `source_table_display_names` | 設定どおりの表示名配列（未設定インデックスは空文字）。 |
| `source_table_short_names` | 設定どおりの略称配列（未設定インデックスは空文字）。 |
| `source_table_legend` | `["1. 表示名A", ...]` 形式（互換・デバッグ用）。 |
| `source_table_legend_short` | `["1. sl", ...]` 形式（互換用）。 |
| `table_rows_source_file` | `build_pages_table.py` が読んだデータ JSON のファイル名（`filtered_data_enriched.json` または `filtered_data.json`）。 |
| `pages_ui` | [`table/pages_ui_config.json`](./table/pages_ui_config.json) の内容を埋め込み（仕様は [pages-ui-config.md](./pages-ui-config.md)）。列幅・列の既定表示を制御。`//` / `/* */` コメント可。 |
| `pages_ui_config_path` | 読み込んだ UI 設定ファイルの相対パス（ログ・デバッグ用）。 |

詳細は **[Pages 用 UI 設定](pages-ui-config.md)** を参照してください。

**Pages トップの UI:** `docs/index.html` はマークアップのみとし、処理は **`docs/assets/pages-index-*.js`**（`defer` 読み込み）に分割しています。`browser_rows.json` の **`meta.pages_ui.index_table`** で列順・ラベル・IR/Chart の URL 形式をまとめています（単一ソースは `docs/table/pages_ui_config.json`）。**優先順位 1〜3 までの複合並び替え**（各段で列と昇順／降順を指定。すべて「（なし）」のときは元の行順。**優先 1 の既定は独自レベル昇順**）、**キーワード／難易度表チェック／独自レベル（`custom_level`）チェック・列の表示**を **1 つの折りたたみパネル**（「並び替え・絞り込み・列の表示」）にまとめています（既定は閉じた状態）。フッターから **`table/filtered_header.json` へのリンク**があり、beatoraja 登録用ヘッダーをブラウザで直接開けます。**全列をチェックボックスで表示／非表示**できます（既定は `meta.pages_ui.column_visible_defaults` と組み込み既定の合成）。**列の既定幅**は同じく `meta.pages_ui.column_widths`（`t:custom_level` / `t:title` / `d:列名` / `ir:lr2ir` / `ir:minir` / `ir:mocha` / `chart` など）で調整します。**難易度表ブロックの左端は独自レベル（`custom_level`）**で、その右にその他の表列、続いて DB、**IR**（**LR2IR** / **MinIR** / **Mocha** の 3 列）、**Chart** の順です。IR 各列は行の **`md5`**（32 桁 hex）から [LR2IR](http://www.dream-pro.info/~lavalse/LR2IR/search.cgi) のランキング URL、**`sha256`**（64 桁 hex）から [MinIR](https://www.gaftalk.com/minir/) と [Mocha-Repository](https://mocha-repository.info/) へのリンクを生成します（ハッシュが無効なときは「—」）。**Chart** 列は **`md5`** から [bms-score-viewer](https://bms-score-viewer.pages.dev/)（`view?md5=…`）です。**表タイトル**・**表メモ**列は `column_widths` 未指定時でも約 `50ch` の既定幅があり、**各列ヘッダー右端をドラッグ**して列幅を変更できます（ブラウザの `localStorage` に保存し、ドラッグ値が `column_widths` より優先）。メタ情報の「難易度表」は **`sl(Satellite) · st(Stella)`** のように略称と表示名を 1 行にまとめています。出自フィルタの見出しは **「難易度表（1つ以上チェックした表のみ表示。すべてオフのときは行を表示しません）」** で、チェックは **`sl(Satellite)`** 形式です。**独自レベル**は行の `custom_level` の値ごとにチェックが並び、**すべてオフのときは行を表示しません**。共有用の URL クエリ **`cl`** の形式は [README.md](../README.md)（「一覧の URL クエリ」）を参照してください。

**統合難易度表別の曲数サマリー:** `filter_table.py` が `level_stats.json` に書き出す集計を、**`level-stats.html`**（`./table/level_stats.json` を fetch）で表示します。トップの `index.html` は難易度表の一覧のみです。集計対象の列名は `level_stats.json` の `level_field`（設定の `custom_level_source_key`、既定 `level`）です。各元表カードの表は、同一レベルについて **曲数（SQL 後）**（`songdata.db` の条件でハッシュ交差した行）と **曲数（SQL 前）**（元表 JSON の全データ行）を並べて比較できます。フィルタがスキップされたビルドでは `level_stats.json` が無いことがあり、その場合は当該ページでエラー表示になります。

## 独自レベル（`custom_level_mapping`）

**目的:** 難易度表 A の「レベル 12」と難易度表 B の「レベル 1」を、**同じ独自スケール上の数値（またはラベル）**に揃えたい場合に使います。

- **推奨:** 各 **`source_tables[]` 要素**（または **`source_tables_path`** で読んだ JSON の各要素）に **`custom_level_mapping`** オブジェクトを書きます。**キー = 元表のレベルの文字列表現**、**値 = 独自レベル**（数値・文字列・`null` の値側は JSON 任意）。
- **後方互換:** `filter_config.json` のトップレベル **`custom_level_mapping`** に、ソースと **同じ順の配列**を置く方法も残しています。**エントリ側にオブジェクトがあるインデックスではそちらが優先**され、トップレベルは **エントリにマップが無いインデックスのフォールバック**としてだけ使われます。
- **`custom_level_field`:** 出力 JSON に載せるキー名（既定 `custom_level`）。英字または `_` で始まり英数字と `_` のみ。
- **`custom_level_source_key`:** 元表の行から読むレベル列名（既定 `level`）。
- **`custom_level_unmapped`:** マップにキーが無かったとき。`omit`（既定） / `source` または `original` / `null`。
- **重複行:** 複数ソースで同一ハッシュが出た場合は **先勝ち**のソースインデックスだけがマップに使われます（2 枚目以降は `source_table_names` / `source_table_short_names` にだけ表名・略称が足され、`custom_level` は上書きしません）。
- **`course` 内のチャート行**には現状マップを適用していません（データ配列のメイン行のみ）。
- **既定の K Original 対応表:** [`tools/table-filter/source_tables.json`](../tools/table-filter/source_tables.json) の各ソースに **`custom_level_mapping`** を入れており、☆（通常）・▽（第2通常）・sr（Starlight）・sl（Satellite）の **元表 `level` 文字列**を、運用上の **統合スケール 1〜31** に寄せています。表記ゆれ対策で ☆ 表には **`"☆12"` のように記号付きキー**も重ねてあります。Satellite の **`0`〜`12`** は表の後半ブロック（`sl0`〜`sl12` に相当する帯）を優先したマッピングです。行ごとの解釈を変えたい場合は同ファイルを編集してコミットしてください。

## 例: stellabms（HTML からヘッダー JSON を解決）

stellabms の難易度表入口ページ（例: [Satellite の `table.html`](https://stellabms.xyz/sl/table.html)）は `<meta name="bmstable" content="header.json" />` のように **`bmstable` の `content` が指す JSON** をヘッダーとして読みます（`table_rec.html` など別入口のときは `content` が `header_rec.json` になる場合もあります）。既定の **`tools/table-filter/source_tables.json`**（`filter_config.json` の **`source_tables_path`** から読み込み）では、Starlight（`sr/table.html`）・Satellite（`sl/table.html`）・[通常難易度表（☆）](https://darksabun.club/table/archive/normal1/)（ディレクトリ URL から HTML を取得して `bmstable` を解決）・[第2通常難易度表（▽）](https://bmsnormal2.syuriken.jp/table.html) の **4 本**を列挙しています（Stella 等を足す場合は同ファイルにオブジェクトを追加し、`filter_config.json` の `source_tables_path` を維持してください）。

**通常難易度表（☆）の注意:** [darksabun.club](https://darksabun.club/table/archive/normal1/) は **Cloudflare により GitHub Actions のランナーから取得できない**ことがあります。その場合は `filter_table.py` が失敗し、ワークフローが止まります。対処としては、(1) 当該 `source_tables` 要素を一時的に削除する、(2) **ヘッダー JSON の HTTPS 直 URL** やミラーに差し替える、のいずれかが必要です。ディレクトリ URL（末尾 `/`）だけを書くと、ツールは **HTML として 1 回取得して `bmstable` を探す**ため、チャレンジ用 HTMLしか返らない URLは失敗します。

**フィルタ後の行数が 0 に近い場合:** 元表のハッシュと **`songdata.db` の `song` に存在する行**の交差だけが残ります。さらに **`sql_where`** で BPM などを絞るため、**DB に無い譜面**や **条件不一致**は落ちます。表を埋めたい場合は **beatoraja で譜面を読み込んだうえで DB を更新**し、再度コミットしてください。

## 制限・注意

- **フィルタ結果は「元表に載っている譜面」のみ**です。`songdata.db` にしか無い曲は難易度表 JSON には出ません。
- **段位コース（`course`）**は、譜面が落ちて要件を満たさなくなると **コース定義が壊れる**可能性があります。`charts` が空のノードは削除しますが、運用仕様は各自で確認してください。
- **外部表の取得**はネットワーク依存です。相手サーバの障害・レート制限で失敗する場合があります。
- **`sql_where` は信頼できる設定のみ**をコミットしてください（簡易的な禁止キーワードチェックのみ）。

## 関連ファイル

| ファイル | 説明 |
|----------|------|
| [tools/table-filter/filter_table.py](../tools/table-filter/filter_table.py) | フィルタ本体（Python 標準ライブラリのみ） |
| [tools/table-filter/build_pages_table.py](../tools/table-filter/build_pages_table.py) | フィルタ結果と `song` をマージし `browser_rows.json` を生成 |
| [tools/table-filter/filter_config.json](../tools/table-filter/filter_config.json) | 実際に読む設定（URL・SQL 等） |
| [tools/table-filter/README.md](../tools/table-filter/README.md) | CLI・設定キーの短い説明 |
| [.github/workflows/pages.yml](../.github/workflows/pages.yml) | 上記スクリプト実行後に `docs/` を Pages へデプロイ |

## 参考（beatoraja 側）

- `song` テーブルに `md5`, `sha256`, `minbpm`, `maxbpm` などが格納される（ローカルスキャン結果）。
- 難易度表の JSON はコミュニティ表ごとに細部は異なるが、多くは **データ配列の各要素に `sha256` / `md5`** を持つ。
