# beatoraja 楽曲データベース（BMS）仕様メモ

Slack で共有された調査依頼の続きとして、[beatoraja の楽曲DB更新を高速化するツールに関する note 記事](https://note.com/3935/n/nb55e8ee5c858)と [beatoraja 本体ソース（exch-bms2/beatoraja）](https://github.com/exch-bms2/beatoraja)の `SQLiteSongDatabaseAccessor.java` / `SongInformationAccessor.java` を突き合わせて整理したメモです。バージョン差はあるため、厳密な挙動は実行中の本体と `PRAGMA table_info(...)` で確認してください。

## ファイル構成

| ファイル | 役割 |
|----------|------|
| `songdata.db` | フォルダ階層（`folder`）と譜面メタデータ（`song`）を格納する SQLite。選曲画面の木構造・曲一覧の主データ。 |
| `songinfo.db` | 譜面ごとの統計・解析情報（`information` テーブル）。`sha256` で `song` と対応。更新処理でデコードしたモデルから書き込まれる。 |

記事では `songdata.db` / `songinfo.db` のバックアップを推奨しており、破損時は「お気に入り・タグの再設定と再生成に時間がかかる」程度に収まる、という前提で外部ツールが触れている点にも留意します。

## 対象となる譜面ファイル拡張子

`SQLiteSongDatabaseAccessor` の走査では、次の拡張子が BMS 譜面として扱われます。

- `.bms` / `.bme` / `.bml` / `.pms` / `.bmson`

## `folder` テーブル（`songdata.db`）

フォルダツリー用。本体ソース上の列定義（`SQLiteSongDatabaseAccessor` コンストラクタ内の `Table("folder", ...)`）は概ね次のとおりです。

| 列名 | 型（ソース上） | 説明 |
|------|----------------|------|
| `title` | TEXT | フォルダ名（表示用）。 |
| `subtitle` | TEXT | サブタイトル。 |
| `command` | TEXT | コマンド用文字列。 |
| `path` | TEXT | フォルダの相対／絶対パス（末尾セパレータ付きの文字列として格納される処理がある）。 |
| `banner` | TEXT | バナー画像パス等。 |
| `parent` | TEXT | 親フォルダ識別子（後述の CRC ベース ID）。 |
| `type` | INTEGER | フォルダ種別。 |
| `date` | INTEGER | 最終更新時刻（秒単位の UNIX 時刻）。 |
| `adddate` | INTEGER | DB 登録・更新時刻。 |
| `max` | INTEGER | 関連する最大値（難易度帯などの集約に利用）。 |

親子関係は **パス文字列を `SongUtils.crc32(...)` でハッシュ化した値** を `parent` や `song.folder` などに載せる設計です（note 記事でも「パスを CRC でハッシュ化した値で親子関係を把握」と説明）。

## `song` テーブル（`songdata.db`）

1 行が 1 譜面。メタデータの大部分は BMS デコード結果（`BMSDecoder` / `BMSONDecoder` と `SongData`）から埋まります。

| 列名 | 型 | 説明 |
|------|------|------|
| `md5` | TEXT | 譜面識別用ハッシュ（レガシー）。 |
| `sha256` | TEXT | 譜面識別用ハッシュ（現行の主キー扱い）。 |
| `title` / `subtitle` / `genre` | TEXT | タイトル・サブタイトル・ジャンル。 |
| `artist` / `subartist` | TEXT | アーティスト。 |
| `tag` | TEXT | ユーザー定義タグ（更新時に既存 DB から引き継ぎ）。 |
| `path` | TEXT | 譜面ファイルへのパス。 |
| `folder` | TEXT | 所属フォルダ ID（親ディレクトリパスの CRC）。 |
| `stagefile` / `banner` / `backbmp` | TEXT | ステージファイル・バナー・背景。 |
| `preview` | TEXT | プレビュー音源ファイル名。 |
| `parent` | TEXT | 親（ひとつ上のディレクトリ）の ID。 |
| `level` / `difficulty` | INTEGER | レベル表記・難易度帯（推定ロジックあり）。 |
| `maxbpm` / `minbpm` | INTEGER | BPM 範囲。 |
| `length` | INTEGER | 演奏時間。 |
| `mode` / `judge` | INTEGER | モード・判定系フラグ。 |
| `feature` | INTEGER | 譜面特性ビットフラグ。note 記事では `#RANDOM` 使用有無が **下位ビットの一部（例: `feature & 4`）** として言及。 |
| `content` | INTEGER | フォルダ内 `.txt` の有無などコンテンツ由来のフラグ（後述の差分注意）。 |
| `date` | INTEGER | 譜面ファイルの最終更新時刻（秒）。 |
| `favorite` | INTEGER | お気に入り（更新時に `sha256` キーで引き継ぎ）。 |
| `adddate` | INTEGER | DB に載った日時。 |
| `notes` | INTEGER | ノーツ数。 |
| `charthash` | TEXT | チャート用ハッシュ。 |

### 更新処理で特に効く挙動（ソース＋記事の要点）

1. **ルート走査**  
   設定の BMS ルート（リソースタブの BMS Path）などから、再帰的にディレクトリを開き、上記拡張子のファイルとサブフォルダを列挙します。ルートごとに **並列** で走査する実装になっています。

2. **フォルダ単位の DB 照合**  
   各フォルダについて、`song` から `folder = ?`（CRC でエンコードされたフォルダ ID）に一致する行を読み、`folder` テーブルから子フォルダ行を読みます。ディスク上の一覧と突き合わせ、不要行は `DELETE`、更新が必要な譜面はデコードして `INSERT` します。

3. **「更新不要」と判定された譜面**  
   パス一致かつ `date`（ファイル mtime）が一致する場合、譜面の再デコードをスキップし、**プレビュー音ファイル名だけ**が変わっていれば `UPDATE song SET preview=...` する分岐があります。

4. **プレビュー音**  
   フォルダ内で `preview` で始まり拡張子が `.wav` / `.ogg` / `.mp3` / `.flac` の最初のファイルを自動検出します。デコード結果に `#PREVIEW` が無い場合はこのファイル名を補完します。

5. **`.txt` と `content`**  
   フォルダ内に `.txt` が 1 つでもあれば `txt` フラグが立ち、`SongData` 生成時に `content` に反映されます。記事で指摘されているとおり、**後から差分で .txt が増えた場合**、同じフォルダ内の別譜面の `content` が「再構築」と「差分更新」で一致しないことがあり得ますが、選曲には致命的ではない、という整理です。

6. **`#RANDOM` を使わない譜面で数値が微妙に違う**  
   記事では `jbms-parser` のバージョン差やデコード結果の差として言及。選曲用途では軽微とされています。

## `information` テーブル（`songinfo.db`）

`SongInformationAccessor` により、`sha256` を主キーとする行が維持されます。列はソース上おおむね次のとおりです。

| 列名 | 型 | 説明 |
|------|------|------|
| `sha256` | TEXT (PK) | 対応する譜面。 |
| `n` / `ln` / `s` / `ls` | INTEGER | 通常ノーツ、LN、スクラッチ等のカウント系。 |
| `total` / `density` / `peakdensity` / `enddensity` / `mainbpm` | REAL | 統計・密度・代表 BPM。 |
| `distribution` / `speedchange` / `lanenotes` | TEXT | 分布や速度変化、レーンごとの情報をシリアライズした文字列。 |

楽曲更新が `SongInformationAccessor` を伴う場合、デコード済み `BMSModel` から `SongInformation` が生成され `insert` されます。

## パフォーマンス・ツール連携（記事からの設計知見）

note 記事で外部ツール（songdata-updater）が採った主な方針は次のとおりです。本体に取り込むかは別として、**DB を触るツールを自作する際のチェックリスト**として有用です。

- **SQL 回数削減**: フォルダごとの `SELECT` をやめ、事前に `song` / `folder` を一括取得してハッシュマップ化する。
- **書き込み**: `PreparedStatement` の再利用と `executeBatch` によるバッチ INSERT。
- **線形探索の排除**: パスをキーにしたマップで突合。
- **早期リターン**: フォルダの mtime が変わっていない場合、BMS が 1 つ見つかった時点で列挙を打ち切る（**ファイル内容を直接編集した更新を見逃す**トレードオフあり）。
- **Everything 連携（Windows）**: ルート以下の BMS / `.txt` 有無 / プレビュー音を少数回の検索でまとめ取得し、ディスク走査 I/O を削減。
- **整合性確認**: 本体がフル再構築した DB と、ツールが生成した DBを `EXCEPT` / `UNION` で比較し、選曲に必要な列集合で差分ゼロを確認する手法が紹介されている。

## 本体実装を読むときの入口

- 楽曲DB更新の中核: [`SQLiteSongDatabaseAccessor.java`](https://github.com/exch-bms2/beatoraja/blob/master/src/bms/player/beatoraja/song/SQLiteSongDatabaseAccessor.java)（内部クラス `SongDatabaseUpdater` / `BMSFolder`）
- 譜面情報DB: [`SongInformationAccessor.java`](https://github.com/exch-bms2/beatoraja/blob/master/src/bms/player/beatoraja/song/SongInformationAccessor.java)
- インターフェース: [`SongDatabaseAccessor.java`](https://github.com/exch-bms2/beatoraja/blob/master/src/bms/player/beatoraja/song/SongDatabaseAccessor.java)

## 参考リンク

- [BMS] beatorajaのDB更新を高速化できるかも知れないツール — note: https://note.com/3935/n/nb55e8ee5c858  
- beatoraja リポジトリ: https://github.com/exch-bms2/beatoraja  
