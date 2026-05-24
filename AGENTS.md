# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

beatoraja の `songdata.db` と難易度表 JSON を組み合わせ、GitHub Actions で絞り込み JSON を生成し GitHub Pages で公開するツール。Python 3.12 + 標準ライブラリのみ（サードパーティ依存なし）。

### Running the scripts locally

```bash
export SITE_BASE_URL="https://example.github.io/test-CursorToSlack/table"
python3 tools/table-filter/filter_table.py --config tools/table-filter/filter_config.json
python3 tools/table-filter/build_pages_table.py --config tools/table-filter/filter_config.json
```

- `filter_table.py` はネットワークアクセスが必要（stellabms.xyz から難易度表 JSON を取得）。
- `build_pages_table.py` は `filter_table.py` の出力（`docs/table/filtered_data.json`）を前提とする。順序に注意。
- `SITE_BASE_URL` 環境変数は必須。設定ファイル内の `site_base_url` でも代用可。

### Serving the HTML viewer

```bash
cd docs && python3 -m http.server 8080
```

`http://localhost:8080/index.html` と `http://localhost:8080/level-stats.html` で確認。

### Lint

プロジェクトに lint 設定は含まれないが、`ruff` を用いて Python コードをチェックできる:

```bash
python3 -m ruff check tools/table-filter/
```

### Key files

| File | Purpose |
|------|---------|
| `tools/table-filter/filter_table.py` | メインフィルタスクリプト |
| `tools/table-filter/build_pages_table.py` | Pages 用 browser_rows.json 生成 |
| `tools/table-filter/filter_config.json` | 実行時設定（SQL, URL 等） |
| `data/songdata.db` | beatoraja の楽曲データベース（SQLite） |
| `docs/` | GitHub Pages 公開ルート（HTML/CSS/JS） |
| `.github/workflows/pages.yml` | CI/CD ワークフロー定義 |

### Notes

- `data/songdata.db` はリポジトリにコミットされている（約 11MB）。テスト時に差し替え不要。
- Python スクリプトは標準ライブラリのみ使用。`pip install` は不要。
- 生成されるファイル（`docs/table/*.json`）は `.gitignore` に入っていないため、テスト後に `git checkout -- docs/table/` でクリーンアップする。
