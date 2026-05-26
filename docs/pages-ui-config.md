# Pages トップ用 UI 設定（`docs/table/pages_ui_config.json`）

GitHub Pages のトップ（`docs/index.html` と `docs/assets/pages-index-*.js`）が参照する **列の既定幅**、**列チェックの既定 ON/OFF**、**列順・ラベル・IR/Chart リンク**を、主にこの JSON で調整できます。

同梱の `docs/table/pages_ui_config.json` では、`column_widths` / `column_visible_defaults` の **オブジェクト内のキー順**をトップの表の **左から右**（`index_table.table_column_order` の先頭に **独自レベル `custom_level`**、続けてアルファベット順の追加列、`index_table.db_column_order`、**IR**（`ir_subcolumns` の `colgroup_key` 順）、**`chart_column.colgroup_key`（通常 `chart`）**、空でないときのみ **`trailing_table_columns`**（IR・Chart の**さらに右**））に合わせています。

## 読み込み

`tools/table-filter/build_pages_table.py` がこのファイルを読み、`browser_rows.json` の **`meta.pages_ui`** に埋め込みます。`filter_config.json` の **`pages_ui_config_path`** でパスを変えられます（未指定・空なら `docs/table/pages_ui_config.json`）。

トップ一覧（`docs/index.html`）では、フィルタ・並び替え・列表示などの状態を **URL クエリ**に同期できます（`history.replaceState`）。パラメータの意味はリポジトリ直下の [README.md](../README.md)（「一覧の URL クエリ」）を参照してください（**独自レベル**の絞り込みは **`cl`**）。

## JSONC 風コメント（`//` / `/* */`）

同梱ファイルの先頭や各オブジェクト内に、**`//` から行末まで**、または **`/*` … `*/`** のコメントを書けます。ビルド時に `tools/table-filter/pages_ui_json.py` が文字列リテラル以外のコメントだけを除去してから `json.loads` します。

- **列幅**: 使わない列は `// "d:genre": "12ch",` のようにコメントアウトしたテンプレート行として置いてあります。使うときは行頭の `//` を外し、直前の行の末尾にカンマがあるか確認してください。**コメント行だけが続く直前のプロパティ**には **末尾カンマを付けない**でください（`//` 除去後に不正なトレーリングカンマが残ります）。
- **列の既定表示**: `song` テーブルの全列と、一覧に現れうる難易度表側の列を **`true` / `false` で明示**しています。足りない列だけ、ファイル内のテンプレ用 `//` 行を参考に追記してください。

## `column_widths`

`<colgroup>` の既定幅。キーは表の列が **`t:` + 列名**（先頭は **`t:custom_level`**）、DB 列が **`d:` + 列名**、IR 列（LR2IR / MinIR / Mocha）が **`ir:lr2ir`** / **`ir:minir`** / **`ir:mocha`**、Chart 列が **`chart`**、任意で **`trailing_table_columns`** に列した表列（IR・Chart の右）です。

例:

```json
"column_widths": {
  "t:custom_level": "7ch",
  "t:title": "50ch",
  "t:note": "55ch",
  "d:genre": "12rem",
  "ir:lr2ir": "4.5rem",
  "ir:minir": "4.5rem",
  "ir:mocha": "4.5rem",
  "chart": "4.5rem"
}
```

**`title` / `note`** のように JSON に無い列は、従来どおり表側の「長文列」には約 `50ch`、**`ir:*`** と **`chart`** は約 `4.5rem` がフォールバックです。ユーザーがヘッダーをドラッグで変えた幅は引き続き `localStorage`（`k-original-col-widths-v2`）が優先されます。

## `column_visible_defaults`

列表示パネルの **初期チェック** です。`table` / `db` に加え、**`ir`** / **`chart`**（IR 3 列まとめて・Chart 1 列）を **`true` / `false`** で指定できます（未指定時は `true`）。

リポジトリ同梱の `docs/table/pages_ui_config.json` では、`index_table.column_hidden_fallback` および DB 側の既定非表示（`title` / `artist` / `md5` / `sha256`）と整合するよう、多くの列を **`false` として明示**しています。運用で既定を変えたいときはこのオブジェクトを編集してください。将来列が増えたとき用の **`// "key": true,` 形式のテンプレ行**も同梱しています。

ここに **無い列** は、`index_table.column_hidden_fallback`（`docs/assets/pages-index-column-runtime.js` の既定とマージ）および上記 DB 4 列の既定オフにフォールバックします。新しい列キーがデータに現れた場合も、未指定なら従来どおり表示されます。**`ir` / `chart`** は `table` / `db` とは別トップレベルキーです。

## `index_table`（列定義の単一ソース）

トップ表の **難易度表 / DB の優先列順**（`table_column_order` / `db_column_order`）、**表データの末尾にだけ出したい列**（**`trailing_table_columns`**。IR・Chart の**さらに右**。同梱設定では **空配列**で、独自レベルは `table_column_order` の先頭に置いています）、**見出しラベル**、**長文折り返し対象**（`table_clamp_keys`）、**既定で隠す列**（`column_hidden_fallback`）、**1 段目グループ見出し**（`trailing` は末尾列があるときのみ表示）、**IR 各列**（`ir_subcolumns`）、**Chart 列**（`chart_column`）をまとめます。`build_pages_table.py` が `meta.pages_ui` に埋め込むため、**`browser_rows.json` を取得すればフロントは追加の fetch なし**で解決できます。

古い `browser_rows.json` だけ手元に残っている場合は、`pages-index-column-runtime.js` 内の **`DEFAULT_INDEX_TABLE`** が同等の既定値にフォールバックします（リポジトリの `index_table` と同期しておくこと）。

## バージョン

トップレベルの **`version`**（数値）は将来の互換用に予約しており、現状のスクリプトは未使用です。
