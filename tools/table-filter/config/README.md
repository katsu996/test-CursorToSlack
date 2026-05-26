# ユーザー向け設定 JSON（このフォルダだけ）

難易度表フィルタで**直接編集する想定の JSON**は、この `config/` にまとめています。

| ファイル | 用途 |
|----------|------|
| `filter_config.json` | 実行時設定（SQL・出力先・`source_tables_path` など）。`python3 tools/table-filter/filter_table.py --config tools/table-filter/config/filter_config.json` の `--config` で指定します。 |
| `source_tables.json` | 難易度表ソース一覧（`filter_config.json` の `source_tables_path` から読み込み。相対パスは `filter_config.json` と同じディレクトリ基準） |
| `filter_config.example.json` | 利用可能なキー一式の説明用サンプル（CI でキー集合を検証） |
| `source_tables.example.json` | ソース配列の小さな例 |

`pages_ui_config.json`（Pages トップの列表示など）は `docs/table/` にあります（`filter_config.json` の `pages_ui_config_path` で変更可）。
