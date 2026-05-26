# 保守・改善バックログ

このファイルは **「いつ・何を見直すか」** と **「任意の拡張候補」** を一覧化するためのものです。実装の詳細はコードと [`docs/README.md`](docs/README.md) の索引を正とし、ここは **判断・方針・抜け漏れ防止** に絞ります。

## 保守の軸（拡張するときに崩れやすい境界）

| 境界 | 片側 | もう片側 | 触ったら確認すること |
|------|------|----------|----------------------|
| **A** | `filter_table.py` の出力 JSON | `build_pages_table.py` | 入力ファイル名・列・`meta` の前提 |
| **B** | `browser_rows.json`（`meta.pages_ui`） | `docs/assets/pages-index-*.js` | 列 ID・表示既定・ツールバー |
| **C** | `pages.yml`（取得・検証・デプロイ順） | [`docs/ci-github-pages-workflow.md`](docs/ci-github-pages-workflow.md) | 手順・制限の説明が一致しているか |
| **D** | Latest GitHub Release の `songdata.db` | [`docs/github-releases-songdata.md`](docs/github-releases-songdata.md) / `scripts/upload-*` | Latest の定義、PAT、空ファイル検知 |

---

## Todo No（`T001` 形式）について

- **Todo No はリポジトリ全体で一意**です（優先度ごとに振り直しません）。
- PR や Issue で「`T00x`」と参照できるように番号を付けます。
- 新規項目は **未使用の最小番号**か、**現在の最大番号の次**（例: `T031` まで使っていれば `T032`）を使ってください。
- 完了した行は **削除**するか `## 完了済み` に **一行メモ**（PR 番号・日付）で移してください。**番号の欠番は再利用しない**方が安全です。

| 優先度 | 意味 |
|--------|------|
| **P0** | 放置すると障害・誤デプロイ・互換破壊につながりやすい |
| **P1** | 回帰防止（テスト・CI・ドキュメント同期） |
| **P2** | 可読性・モジュール分割・設定・運用の整理 |
| **P3** | UX・任意機能・調査タスク |

---

## 定期メンテ（カレンダーではなくトリガーで実施）

| Todo No | 内容 |
|---------|------|
| **T001** | **beatoraja / LR2oraja の新バージョン**が出たら: 難易度表まわりの挙動を確認し、必要なら [`docs/beatoraja-jbmstable-table-json.md`](docs/beatoraja-jbmstable-table-json.md) とユニットテストを更新する。 |
| **T002** | **`source_tables.json`（または `source_tables_path`）を差し替えたとき**: 元表の JSON キー変更で `custom_level_source_key` や level 集計がずれていないか確認する。 |
| **T003** | **GitHub（Actions / Pages / CLI）の仕様・推奨構成の変更**: `pages.yml` の `actions/*` や `gh release` の挙動をリリースノートで確認してから更新する。[`docs/ci-github-pages-workflow.md`](docs/ci-github-pages-workflow.md) と差が出たら同じ PR で直す。 |
| **T032** | **Release 運用の健全性**: 「Latest」に **`songdata.db` が載っているか**（プレリリースのみの最新だと `gh release download` が失敗し得る）、アセットが **空でないか**、組織リポジトリなら **権限・SSO** を確認する（手順は [`docs/github-releases-songdata.md`](docs/github-releases-songdata.md)）。 |

---

## バックログ（未着手・任意）

着手したら **優先度を見直し**、完了したら **行を削除**してください。

| Todo No | 優先度 | 内容 |
|---------|--------|------|
| **T004** | **P0** | **複数ソース取得の部分失敗**: 一部の `source_tables` だけ取得失敗したときに、ビルド全体を止めるか・成功分だけで続行するか・リトライ方針を決め、`filter_table.py` と CI の挙動を揃える。 |
| **T005** | **P1** | **`songdata.db` の肥大化と配布経路**: GitHub Release の [アセット制限](https://docs.github.com/repositories/releasing-projects-on-github/about-releases) 内での運用、将来しきい値を超える場合の候補（分割・別ストレージ・取得キャッシュ）を方針として `docs/` に短く残す。 |
| **T010** | **P1** | **Dependabot / Actions の更新方針**: アクションのピン留めと更新頻度、マージ前の確認項目（`build`/`deploy` の smoke、`gh` ステップ）を `docs/ci-github-pages-workflow.md` か専用短節にまとめる。 |
| **T013** | **P2** | **`ubuntu-latest` で `actions/setup-python` の 3.14.3 が取れない場合**の代替（利用可能なマイナーへの一時ピン等）を [`docs/ci-github-pages-workflow.md`](docs/ci-github-pages-workflow.md) に追記する。 |
| **T014** | **P2** | **`source_tables.json` の CI 検証**: スキーマ検証に加え、到達性チェックをどこまで行うか方針を決めて実装する。 |
| **T025** | **P1** | **ワークフローと CI ドキュメントの同期ルール**: `pages.yml` を変えた PR では必ず [`docs/ci-github-pages-workflow.md`](docs/ci-github-pages-workflow.md) の表（処理順・権限・環境変数）を更新する、を CONTRIBUTING か PR テンプレに一行で書く。 |
| **T028** | **P2** | **Release アセットの整合性（任意）**: SHA256 などを Release 本文または別ファイルで公開し、`pages.yml` で取得後に検証する設計が必要になったら導入する（現状は `test -s` のみ）。 |
| **T015** | **P3** | GitHub Pages の「並び替え・絞り込み・列の表示」パネルの開閉状態を `sessionStorage` に保存し、再訪問時に復元する。 |
| **T018** | **P3** | **CSV エクスポート**: 表示中の行をダウンロードできる UI を検討する。 |
| **T024** | **P3** | **i18n**: 文言の外部化や英語切替の可否を検討する（工数とメンテコストのトレードオフ）。 |
