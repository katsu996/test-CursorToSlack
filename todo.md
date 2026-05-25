# 保守・改善バックログ

以前ここに列挙していた **P0〜P3 の項目は実装済み**です（モジュール分割・SQL ガード・HTTP リトライ・CI の ruff / unittest / スモークテスト・Pages 用 CSS 共通化・`page_title` 分離・ドキュメント整備など）。詳細は該当コミットの差分を参照してください。

| 優先度 | 意味 |
|--------|------|
| **P0** | 放置すると障害・セキュリティ・beatoraja 互換破壊につながりやすい |
| **P1** | 回帰を防ぐためのテストや CI |
| **P2** | 可読性・分割・設定の整理 |
| **P3** | UX やドキュメント、あればよいが必須ではない |

---

## 定期メンテ（カレンダーではなくトリガーで実施）

- **beatoraja / LR2oraja の新バージョン**が出たら: 難易度表まわりの挙動を確認し、必要なら [`docs/beatoraja-jbmstable-table-json.md`](docs/beatoraja-jbmstable-table-json.md) とユニットテストを更新する。  
- **`source_tables.json`（または `source_tables_path`）を差し替えたとき**: 元表の JSON キー変更で `custom_level_source_key` や level 集計がずれていないか確認する。  
- **GitHub の Actions / Pages の仕様変更**: `pages.yml` の `actions/*` メジャー更新時はリリースノートを読んでからマージする。

---

## バックログ（未着手・任意）

直近の UI 変更後も、次は**必須ではない**が手を入れると運用や保守が楽になる候補です。着手したら優先度を見直し、完了したら**該当行を削除**してください。

| 優先度 | 内容 |
|--------|------|
| **P3** | GitHub Pages の「並び替え・絞り込み・列の表示」パネルの開閉状態を `sessionStorage` に保存し、再訪問時に復元する。 |
| **P3** | `docs/table/` に短文の `index.html` を置き、`filtered_header.json` / `filtered_data.json` / `bmstable.html` への直リンクと beatoraja 登録時の注意を一覧する。 |
| **P2** | `ubuntu-latest` のランナーで `actions/setup-python` の **3.14.3** が取れない場合の代替（利用可能なマイナーへの一時ピン、`allow-prerelease` 等）を `docs/github-actions-songdata-table-filter.md` に追記する。 |

---

## 完了したら

新しいバックログ項目を追加するときは優先度を付け、完了したら**該当行を削除**するか `## 完了済み` に移し、**いつ・どの PR で**終わったかを一行メモすると、あとから見た人が迷いません。
