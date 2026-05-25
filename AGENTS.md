# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

beatoraja の `songdata.db` と難易度表 JSON を組み合わせ、GitHub Actions で絞り込み JSON を生成し GitHub Pages で公開するツール。Python **3.14.3**（CI）／ローカルは利用可能な Python 3 で可。`tools/table-filter/` のスクリプトは**標準ライブラリのみ**（サードパーティ依存なし）。CI では `ruff` を `pip install` して静的解析に使用する。

### Running the scripts locally

```bash
python3 tools/table-filter/filter_table.py --config tools/table-filter/filter_config.json
python3 tools/table-filter/build_pages_table.py --config tools/table-filter/filter_config.json
```

- `filter_table.py` はネットワークアクセスが必要（元表の URL から難易度表 JSON を取得）。
- `build_pages_table.py` は `filter_table.py` の出力（`docs/table/filtered_data.json` または `filtered_data_enriched.json`）を前提とする。順序に注意。
- 生成ヘッダーの `data_url` は既定で**ファイル名のみ**（相対）のため、**`SITE_BASE_URL` は不要**。絶対 URL で出す場合のみ `use_relative_data_url: false` と `site_base_url` または環境変数 **`SITE_BASE_URL`** を使う。

### Serving the HTML viewer

```bash
cd docs && python3 -m http.server 8080
```

`http://localhost:8080/index.html` と `http://localhost:8080/level-stats.html` で確認。

### Lint / tests

```bash
python3 -m pip install ruff
python3 -m ruff check tools/table-filter/
cd tools/table-filter && python3 -m unittest discover -s tests -v
```

### Key files

| File | Purpose |
|------|---------|
| `tools/table-filter/source_tables.py` | `source_tables` 設定の正規化（後方互換の分割配列も解釈） |
| `tools/table-filter/filter_table.py` | メインフィルタ CLI（マージ・書き出し） |
| `tools/table-filter/http_fetch.py` | HTTP 取得（リトライ） |
| `tools/table-filter/sql_where_guard.py` | `sql_where` / プリセットの検証 |
| `tools/table-filter/beatoraja_rows.py` | beatoraja 向け行・ヘッダー整形 |
| `tools/table-filter/level_stats.py` | レベル集計用ヘルパ |
| `tools/table-filter/build_pages_table.py` | Pages 用 browser_rows.json 生成 |
| `tools/table-filter/smoke_check_outputs.py` | デプロイ前の生成物スモークテスト |
| `tools/table-filter/filter_config.json` | 実行時設定（SQL, URL 等） |
| `data/songdata.db` | beatoraja の楽曲データベース（SQLite） |
| `docs/table/pages_ui_config.json` | Pages トップの列幅・列の既定表示（`build_pages_table.py` が `meta.pages_ui` に埋め込み） |
| `docs/pages-ui-config.md` | 上記 JSON のキー説明 |
| `.github/workflows/pages.yml` | CI/CD ワークフロー定義 |

### Notes

- `data/songdata.db` はリポジトリにコミットされている（約 11MB）。テスト時に差し替え不要。
- Python スクリプト（`tools/table-filter/*.py` の本処理）は標準ライブラリのみ使用。`pip install` は不要（CI の ruff のみ）。
- 生成されるファイル（`docs/table/*.json`）は `.gitignore` に入っていないため、テスト後に `git checkout -- docs/table/` でクリーンアップする。
