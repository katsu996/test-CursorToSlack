# 要件定義・調査メモ: 条件付き「フォルダ」（仮想フォルダ）生成ツール

## 1. 背景と目的

**目的:** 楽曲メタデータ（BPM 以上／以下、レベル、ジャンル等）に基づく条件を指定し、その条件に合致する譜面だけが一覧される **BMS クライアント上の「フォルダ」** を用意したい。

**「フォルダ」の意味（本調査での整理）:**

| 方式 | 概要 | ファイル実体 | 主な利用クライアント |
|------|------|----------------|----------------------|
| **A. SQL 仮想フォルダ（beatoraja）** | 楽曲DB（SQLite）に対する `WHERE` 断片で曲集合を定義し、選曲画面に **CommandBar** として表示する。 | `beatoraja` インストール直下の `folder/default.json`（JSON 配列）。各要素は `name`（表示名）と `sql`（条件）、入れ子は `folder` 配列。 | beatoraja / LR2oraja 等 |
| **B. LR2 カスタムフォルダ** | ジュークボックス登録ディレクトリ配下の **`.lr2folder`** テキストで、LR2 独自の「定義項＋条件」を記述する。 | `*.lr2folder`（LR2 仕様） | Lunatic Rave 2（および互換を謳うクライアントは要個別確認） |
| **C. 物理フォルダ** | 実ディレクトリに譜面をコピー／移動／シンボリックリンクで集約する。 | 実フォルダ＋BMS ファイル | 全クライアント |

本ツールの第一候補は **方式 A**（`folder/default.json` 生成または追記）である。beatoraja 本体は `BarManager` で `folder/default.json` を読み、`CommandBar` が `SQLiteSongDatabaseAccessor.getSongDatas(sql, score, scorelog, info)` に渡す **SQL の `WHERE` 以降に相当する断片** を実行している（`CommandBar.java`）。

方式 B は LR2 利用者向けの別フォーマット変換が必要になる。方式 C はディスク使用量・同期コストが大きい。

### 1.1 確定仕様（出力形式・条件式）

以下は実装・運用の前提として確定する。

| 項目 | 内容 |
|------|------|
| 出力先・形式 | beatoraja インストール直下の **`folder/default.json`** にマージする **JSON 配列の要素**（`CommandFolder` と同一形状）。 |
| 条件 SQL（`sql` フィールド） | **`minbpm != maxbpm`**（`song` テーブルの列。ヘッダから解釈された最小 BPM と最大 BPM が異なる譜面を集める）。 |

**挙動の補足:**

- SQLite では `NULL != 値` は真にならないため、`minbpm` または `maxbpm` が NULL の行は **結果に含まれない**。
- 本体が **譜面情報 DB（`songinfo.db`）を有効**にしている場合、`getSongDatas` は `song` と `information` の **INNER JOIN** になる。`information` に行が無い譜面は **`minbpm != maxbpm` を満たしていても一覧から落ちる**（本体既存の DENSITY フォルダ等と同じ前提）。

コピー用の断片ファイル: [docs/snippets/beatoraja-default-json-snippet-changing-bpm.json](./snippets/beatoraja-default-json-snippet-changing-bpm.json)

---

## 2. データソースと参照可能な項目

### 2.1 入力として想定する DB

| DB ファイル | 内容 | ツールでの用途 |
|-------------|------|----------------|
| `songdata.db` | `song`（譜面1行）、`folder`（ディレクトリツリー） | 条件の大部分（BPM、タイトル、レベル、`path` 等） |
| `songinfo.db` | `information`（`sha256` キー、密度・`mainbpm` 等） | 高度な条件（譜面解析結果） |
| （任意）`score.db` / `scorelog.db` | スコア・ランプ・プレイ日時 | 「クリア済みかつ BPM≥n」など複合条件 |

詳細な列一覧はリポジトリ内 `docs/bms-beatoraja-song-db.md`（存在する場合）または本体 `SQLiteSongDatabaseAccessor` / `SongInformationAccessor` の `Table(...)` 定義を参照。

### 2.2 BPM 関連で使える列（重要）

| 列・概念 | 所在 | 型の目安 | 意味・注意 |
|----------|------|-----------|------------|
| `maxbpm` / `minbpm` | `song` | INTEGER | 譜面ヘッダから解釈された **表示用 BPM 範囲**。「180BPM 以上」など素朴な条件に使いやすい。**ソフランや途中変速の厳密な演奏BPMとは一致しない場合がある。** |
| `mainbpm` | `information`（`songinfo.db`） | REAL | 解析結果としての代表 BPM。`#RANDOM` や複雑な定義では `song` 側と差が出うる（既存メモ参照）。 |
| `speedchange` 等 | `information` | TEXT | 速度変化のシリアライズデータ。高度フィルタ用。解析済み DB が必須。 |

**BPM 系の確定条件:** 本ツールの第1条件は **`minbpm != maxbpm`** とする（上記 §1.1）。数値閾値（例: `maxbpm >= 180`）を追加する場合は同一 `sql` 内で `AND` 連結すればよい（例: `minbpm != maxbpm AND maxbpm >= 180`）。

### 2.3 `folder/default.json` の `sql` が実際に載るクエリ（beatoraja）

`songinfo.db` が有効なとき（本体設定で譜面情報 DB を参照できるとき）、概ね次の形になる（`SQLiteSongDatabaseAccessor.getSongDatas(String sql, ...)` より）。

```sql
SELECT DISTINCT md5, song.sha256 AS sha256, title, ... , maxbpm, minbpm, ...
FROM song
INNER JOIN (
  information
  LEFT OUTER JOIN (score LEFT OUTER JOIN scorelog ON ...)
  ON information.sha256 = score.sha256
) ON song.sha256 = information.sha256
WHERE <ここに default.json の sql が入る>
```

**示唆:**

- `density` / `peakdensity` / `enddensity` / `n` / `ln` / `s` / `ls` / `mainbpm` 等は **`information` 側の列**として `WHERE` に書ける（本体同梱 `folder/default.json` の DENSITY・FEATURE 節がその例）。
- `songinfo.db` が無効／未生成の環境では **INNER JOIN 経路が使われず**、別 SQL になるため（`info == null` の分岐）、**同じ `sql` 断片がそのままでは動かない**可能性がある。ツールは「songinfo 必須」「song のみモード」の切り替えか、生成する SQL をモード別に出し分ける必要がある。
- `song` の列と衝突しないよう、曖昧な場合は **`song.maxbpm` のようにテーブル修飾**すると安全（`default.json` の LEVEL 節では `song.mode` のように修飾されている）。

### 2.4 その他、条件に使いやすい `song` 列（例）

- `level`, `difficulty`, `mode`, `notes`, `length`
- `title`, `subtitle`, `genre`, `artist`, `subartist`, `tag`（文字列は `LIKE`）
- `favorite`, `feature`, `content`, `adddate`, `charthash`

スコア連動は `score.*` / `scorelog.*`（列名は `default.json` の MY BEST、CLEAR TYPE 等を参照）。

---

## 3. 機能要件（案）

### 3.1 必須

1. **条件ビルダー**  
   - 単一条件: 例 `maxbpm >= 180`、`minbpm <= 120`、`mainbpm >= 180`（songinfo 利用時）  
   - 複合条件: `AND` / `OR`、括弧、数値比較、文字列 `LIKE`（必要なら `NOT`）
2. **出力**  
   - **beatoraja 向け:** `CommandFolder` 互換の JSON 片（または `folder/default.json` へのマージ方針をドキュメント化した完全ファイル）  
   - 表示名 `name`（フォルダ名）の指定
3. **検証**  
   - 生成 SQL を SQLite で試実行し、件数・先頭数行の `path` を表示（オプション）
4. **ドキュメント**  
   - バックアップ推奨（`default.json` 上書き前）、本体バージョン差による非互換の注意

### 3.2 任意

- GUI または CLI（YAML／JSON で条件セットを渡す）
- 既存 `folder/default.json` を読み込み、指定ノード下に子 `folder` を挿入
- LR2 `.lr2folder` への変換（定義項マッピング表が別途必要。コミュニティ解説: [LR2カスタムフォルダ用コマンド（fc2）](http://analogmania.blog35.fc2.com/blog-entry-162.html) 等を参照し、**LR2 公式仕様書の一次情報があるか**は未確認）
- `SongUtils.crc32` に依存する **`folder` テーブル直接操作** による仮想ツリー（実装コスト・本体アップデート耐性が悪いため非推奨）

### 3.3 対象外（初期）の候補

- ゲーム内検索バー（`SearchWordBar`）の自動登録
- 譜面ファイルの移動・コピー（方式 C）— 必要なら別ツール化

---

## 4. 非機能要件・リスク

| 項目 | 内容 |
|------|------|
| 安全性 | `sql` はユーザー入力をそのまま連結しない。**プレースホルダ＋ホワイトリスト列名**、または構造化条件からのみ SQL を生成する。 |
| 互換性 | beatoraja バージョンで JOIN 列集合が変わる可能性。 |
| データ鮮度 | `song` の BPM は DB 更新時のデコード結果に依存。譜面修正後は「楽曲読み込み」が必要。 |
| songinfo | `information` 行が無い譜面は **INNER JOIN で結果から落ちる**。「全曲対象」のフォルダでは不整合になるため、ツールで **LEFT JOIN 相当を本体に追加できない**以上、**song のみの条件**に限定するか、事前に楽曲DB更新で `songinfo` を埋める運用を前提にする必要がある。 |

**※ `songinfo` 無し時のクエリ**では `song LEFT OUTER JOIN (...score...)` となり、`information` は JOIN されない。そのため **`mainbpm` / `density` だけを使うフォルダ定義は songinfo 必須**と明記する。

---

## 5. 実装アプローチ比較

| アプローチ | メリット | デメリット |
|------------|----------|------------|
| **JSON 断片生成のみ** | 本体を壊さない、差分レビューしやすい | ユーザーが `default.json` を手でマージする必要 |
| **マージツール** | 運用が楽 | JSON パース・重複名検出・バックアップ必須 |
| **songdata 直接 INSERT** | ファイルシステムに依存しない | `SongUtils.crc32`・`parent` 整合が必要で脆弱 |

---

## 6. 調査で確定した参照実装

- **CommandBar:** `beatoraja/src/bms/player/beatoraja/select/bar/CommandBar.java` — `getSongDatas(sql, scoredb, scorelogdb, songinfo.db)`
- **JSON スキーマ実体:** `beatoraja/folder/default.json` — `name` / `sql` / 入れ子 `folder` / `showall`
- **BarManager:** `CommandFolder` クラスと `createCommandBar` — `folder/default.json` の読み込み

---

## 7. 未確定・フォローアップ

1. **LR2 原生**で同じ条件セットを使う必要があるか。必要なら `.lr2folder` の定義項と beatoraja 列の対応表を別タスクで作成する。  
2. **songinfo 無し**環境で `density` 条件をどう扱うか（エラーにする／song 列のみにフォールバックする等）。  
3. **`minbpm != maxbpm` のみでは捉えられない変速**（ヘッダ上は一定 BPM だが演奏中に変速する譜面）を `information.speedchange` 等で拾う必要があるか。

---

## 8. 参考リンク

- beatoraja: https://github.com/exch-bms2/beatoraja  
- `folder/default.json`（同梱例）: リポジトリ内 `folder/default.json`  
- LR2 カスタムフォルダ解説（非公式）: http://analogmania.blog35.fc2.com/blog-entry-162.html  

以上を、実装タスクに落とす際の **要件定義 v0.2**（§1.1 に出力形式・SQL を確定）として利用できる。
