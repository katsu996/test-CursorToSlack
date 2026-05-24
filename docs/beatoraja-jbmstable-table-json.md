# beatoraja / jbmstable-parser が想定する難易度表 JSON（回帰防止メモ）

本リポジトリの `filter_table.py` は、**exch-bms2/jbmstable-parser** の `decodeJSONTableData(..., accept=false)` と **beatoraja** の `TableData.validate()` に合わせて出力を整形します。以下は**スナップショットとして固定したい前提**です（本体更新時はユニットテストとこの節を見直してください）。

## データ行（`filtered_data.json` の各要素）

1. **`level` が JSON `null` の行は破棄**される（accept=false）。
2. **`md5` または `sha256` の文字列表現の長さが 24 超**であること（パーサ実装の条件）。実運用では 32 / 64 桁の 16 進が大半。
3. **`title` が空**だとソートや検証で問題になり得るため、ツールは **`（無題）`** に置き換える。
4. **`artist` / `url` / `url_diff`** は文字列化し、欠損は空文字に寄せる。
5. **Pages 専用の拡張キー**（`source_table_*` 等）は beatoraja 向け `filtered_data.json` から**除去**し、`filtered_data_enriched.json` にのみ残す。

## ヘッダー（`filtered_header.json`）

1. **`name` が空**だと `TableData.validate()` が失敗する。`output_header_name` で補完する。
2. **`course` が空配列 `[]`** のとき、パーサが例外になるため **キーごと削除**する。

## 運用メモ

- **0 件の `filtered_data.json`** は validate で必ず失敗する。CI では `beatoraja_empty_rows_policy: fail`（既定）と `smoke_check_outputs.py` で早期検知する。
- **Table URL** が `.json` で終わらない場合は HTML モードになり、`<meta name="bmstable" content="...">` が必要（サイトトップ `index.html` に設定済み）。
