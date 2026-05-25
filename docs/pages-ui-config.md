# Pages トップ用 UI 設定（`docs/table/pages_ui_config.json`）

GitHub Pages の `index.html` が参照する **列の既定幅** と **列チェックの既定 ON/OFF** を、JSON だけで調整できます。

## 読み込み

`tools/table-filter/build_pages_table.py` がこのファイルを読み、`browser_rows.json` の **`meta.pages_ui`** に埋め込みます。`filter_config.json` の **`pages_ui_config_path`** でパスを変えられます（未指定・空なら `docs/table/pages_ui_config.json`）。

## JSONC 風コメント（`//` / `/* */`）

同梱ファイルの先頭や各オブジェクト内に、**`//` から行末まで**、または **`/*` … `*/`** のコメントを書けます。ビルド時に `tools/table-filter/pages_ui_json.py` が文字列リテラル以外のコメントだけを除去してから `json.loads` します。

- **列幅**: 使わない列は `// "d:genre": "12ch",` のようにコメントアウトしたテンプレート行として置いてあります。使うときは行頭の `//` を外し、直前の行の末尾にカンマがあるか確認してください。
- **列の既定表示**: `song` テーブルの全列と、一覧に現れうる難易度表側の列を **`true` / `false` で明示**しています。足りない列だけ、ファイル内のテンプレ用 `//` 行を参考に追記してください。

## `column_widths`

`<colgroup>` の既定幅。キーは表の列が **`t:` + 列名**、DB 列が **`d:` + 列名**、Chart 列が **`chart`** です。

例:

```json
"column_widths": {
  "t:title": "50ch",
  "t:note": "55ch",
  "d:genre": "12rem",
  "chart": "4.5rem"
}
```

**`title` / `note`** のように JSON に無い列は、従来どおり表側の「長文列」には約 `50ch`、**`chart`** は約 `4.5rem` がフォールバックです。ユーザーがヘッダーをドラッグで変えた幅は引き続き `localStorage`（`k-original-col-widths-v2`）が優先されます。

## `column_visible_defaults`

列表示パネルの **初期チェック** です。`table` / `db` ごとに、列キー → **`true`（表示）** / **`false`（非表示）** を書きます。

リポジトリ同梱の `docs/table/pages_ui_config.json` では、従来 `index.html` の `HIDDEN_KEYS` および DB 側の既定非表示（`title` / `artist` / `md5` / `sha256`）と同じ列を **`false` としてすべて列挙**しています。運用で既定を変えたいときはこのオブジェクトを編集してください。将来列が増えたとき用の **`// "key": true,` 形式のテンプレ行**も同梱しています。

ここに **無い列** は、組み込みの `HIDDEN_KEYS`（および上記 DB 4 列の既定オフ）にフォールバックします。新しい列キーがデータに現れた場合も、未指定なら従来どおり表示されます。

## バージョン

トップレベルの **`version`**（数値）は将来の互換用に予約しており、現状の `index.html` は未使用です。
