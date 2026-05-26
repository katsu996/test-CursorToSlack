# GitHub Actions: Pages デプロイの流れ（CI）

**手動で触る作業**（DB の配布、SQL、URL、Table URL、push）は **[ルートの README.md](../README.md)**。**Release へ `songdata.db` を載せる手順**は **[github-releases-songdata.md](./github-releases-songdata.md)**。

本文書は **`.github/workflows/pages.yml` がランナー上で何をするか**だけをまとめます。フィルタのアルゴリズムや JSON の列定義は **[github-actions-songdata-table-filter.md](./github-actions-songdata-table-filter.md)**（データフロー・出自メタ・beatoraja 互換など）へ分離しています。

## ワークフロー概要

定義ファイル: [.github/workflows/pages.yml](../.github/workflows/pages.yml)

| ジョブ | 役割 |
|--------|------|
| **build** | チェックアウト → `songdata.db` 取得 → `ruff` / ユニットテスト / 設定検証 → `filter_table.py` → `build_pages_table.py` → `browser_rows` 検証 → スモーク → `configure-pages` → `upload-pages-artifact` |
| **deploy** | `needs: build`。`actions/deploy-pages` のみ（[actions/deploy-pages](https://github.com/actions/deploy-pages) が推奨する **build / deploy 分離**。[starter-workflows の Pages 例](https://github.com/actions/starter-workflows/tree/main/pages) と同型） |

トリガー: `main` への **push**、または **Actions → Deploy GitHub Pages → Run workflow**（`workflow_dispatch`）。

## `songdata.db` の取得（毎回）

`build` ジョブの先頭で、**同一リポジトリの Latest GitHub Release** から GitHub CLI でアセット名 **`songdata.db`** だけを取得し、**リポジトリ直下の `songdata.db`** に保存します（`gh release download` の **タグ省略**＝ Latest と同じ解決）。

- **`gh release view`** でログ用にタグ名を表示
- **`test -s songdata.db`** で **非空**を必須化（取得失敗・空ファイルは **ワークフロー失敗**）

**Latest** は GitHub の定義どおり **プレリリースでない通常 Release** のうち最新です。プレリリースのみだと取得に失敗し得ます。詳細は [github-releases-songdata.md](./github-releases-songdata.md) の「GitHub Actions」節。

## `build` ジョブ内の処理順

| 順序 | 処理 | 入力 | 主な出力 |
|------|------|------|----------|
| 0 | `ruff check` / `unittest` / `check_filter_config_example_sync.py` | `tools/table-filter/` | 静的解析・テスト・`config/filter_config.example.json` のキー整合 |
| 1 | `filter_table.py` | `tools/table-filter/config/filter_config.json`、**`songdata.db`（CI では必須）** | `docs/table/filtered_data.json`、`filtered_data_enriched.json`、`filtered_header.json`、`level_stats.json`（フィルタが走った場合） |
| 2 | `build_pages_table.py` | 同上、`filtered_data_enriched.json`（無ければ `filtered_data.json`）、`songdata.db` | `docs/table/browser_rows.json` |
| 3 | `check_browser_rows_pages_ui.py` | `browser_rows.json` | `meta.pages_ui` 不備なら **終了コード 1** |
| 4 | `smoke_check_outputs.py` | 生成済み `docs/table/*.json` | 空データ・ヘッダー不備なら **終了コード 1** |
| 5 | `configure-pages` / `upload-pages-artifact` | `docs/` 全体 | Pages 用アーティファクト |
| 6 | **deploy ジョブ** の `deploy-pages` | 上記アーティファクト | サイト公開 |

### 終了コード・DB 周りの要点

- **`filter_table.py`:** `enabled: false`・ヘッダー URL 空などでは **0 で終了**し、その後の `build_pages_table.py` は続きます。**`songdata.db` が無い場合**は **ローカル**では `skip_if_no_songdata: true`（既定）なら **0 でスキップ**。**GitHub Actions**（`GITHUB_ACTIONS=true`）では **エラー終了**（生成物の主要 JSON は `.gitignore` のため、静かにスキップすると空表がデプロイされるのを防ぐため）。例外としてワークフローに **`FILTER_CI_ALLOW_MISSING_SONGDATA=1`** を付けたときのみスキップ可能。
- **`beatoraja_empty_rows_policy: fail`（既定）:** beatoraja 向けデータが 0 件なら **`filter_table.py` は終了コード 1**。
- **`build_pages_table.py`:** 入力データ JSON が両方無い場合は **空の `browser_rows.json`**（理由を `meta` に記録）を書き、**そのステップ自体は**失敗させません（前段で `filter_table` が落ちていればそこで止まる想定）。

## 「Failed to queue workflow run. Please try again.」

GitHub UI で手動実行しようとしたときの **汎用エラー**です。多くは **一時的なキュー障害**。[GitHub Status](https://www.githubstatus.com/) を確認し、再試行してください。

それでも続く場合: (1) `concurrency: group: pages` の **別 run が長時間キュー／実行中**で詰まっていないか、(2) **Settings → Pages** の **Source が GitHub Actions** か、(3) 組織ポリシーで **環境 `github-pages` や `workflow_dispatch` が制限**されていないか、を確認してください。

## 関連リンク

- [github-releases-songdata.md](./github-releases-songdata.md) — Release アップロード、PAT、`secrets.txt`、Latest の注意
- [github-actions-songdata-table-filter.md](./github-actions-songdata-table-filter.md) — フィルタ内部、出自メタ、`browser_rows.json` の `meta`、beatoraja 互換
- [filter-config-schema.md](./filter-config-schema.md) — `filter_config.json` のキー一覧
