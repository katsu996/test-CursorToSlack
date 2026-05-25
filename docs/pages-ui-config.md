# Pages トップ用 UI 設定（`docs/table/pages_ui_config.json`）

GitHub Pages の `index.html` が参照する **列の既定幅** と **列チェックの既定 ON/OFF** を、JSON だけで調整できます。

## 読み込み

`tools/table-filter/build_pages_table.py` がこのファイルを読み、`browser_rows.json` の **`meta.pages_ui`** に埋め込みます。`filter_config.json` の **`pages_ui_config_path`** でパスを変えられます（未指定・空なら `docs/table/pages_ui_config.json`）。

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

ここに **無い列** は、従来の組み込み既定（`HIDDEN_KEYS` と DB の `title` / `artist` / `md5` / `sha256` の既定オフ）に従います。JSON に書いたキーだけがその値で上書きされます。

## バージョン

トップレベルの **`version`**（数値）は将来の互換用に予約しており、現状の `index.html` は未使用です。
