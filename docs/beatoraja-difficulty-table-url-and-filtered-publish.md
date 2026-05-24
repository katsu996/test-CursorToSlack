# beatoraja: 難易度表を自作して URL 公開・追加する方法（＋既存表を `minbpm != maxbpm` で絞って再公開する）

質問の「forder」は **難易度表（Difficulty Table）** の誤記と解釈し、beatoraja の **Table URL（難易度表 URL）** について整理する。BPM 条件は前後の文脈どおり **`minbpm != maxbpm`** とする（`minbpm != minbpm` は常に偽になるため誤記とみなす）。

---

## 1. beatoraja に難易度表 URL を追加する手順（公式 UI）

1. **beatoraja-config**（ランチャー）を開く。  
2. **リソース（Resources）** タブへ移動。  
3. **Table URL**（難易度表 URL）一覧の空行に、追加したい表の **URL を貼り付け**、右側の **「＋」** で登録する。  
4. 画面下部の **「難易度表読み込み」（Load difficulty table）** を押し、ネットワーク経由で取得・キャッシュする。  
5. 本体を起動すると選曲画面に難易度表が現れる。

登録だけでは読み込まれない点、読み込み後に選曲で **F2** でも更新できる旨はコミュニティ解説に多い（例: [beatorajaに難易度表を追加する - ぶろぐ](https://lntakeshi.hateblo.jp/entry/2018/02/05/174446)）。

**英語公式寄りの説明:** [beatoraja English Guide — Difficulty Tables — Using difficulty tables in beatoraja](https://github.com/wcko87/beatoraja-english-guide/wiki/Difficulty-Tables#using-difficulty-tables-in-beatoraja)

---

## 2. URL の形式（`.json` 直指定か、それ以外か）

beatoraja 本体 `TableDataAccessor.DifficultyTableAccessor#read` の実装では、大きく次のように分岐する。

- URL が **`.json` で終わる** → その URL を **ヘッダ JSON（難易度表の定義）の URL** として `DifficultyTableParser` に渡す。  
- **それ以外** → **ソース URL**（表配布サイトのトップ URL 等）としてパーサに渡し、サイト側の仕組みでヘッダ・ボディを解決する想定（従来の glassist / BeMusicSeeker 系ホスティングと互換）。

自作して公開する場合は、**HTTPS で届く `header.json`（または表用 JSON 全体）の URL を `.json` で終わる形にする**のが素直で、クライアント側の解釈も一意になる。

---

## 3. ローカルファイルを URL として登録する

beatoraja-config の UI ではファイルパスが入力できない場合がある、という注意がコミュニティにある（例: [PMS Database — ローカルで難易度表](https://pmsdifficulty.xxxxxxxx.jp/column_local_table.html)）。

**回避:** プレイヤー用 `config.json` の `tableURL` 配列に、次のような **`file:///` URL** を手で追記する（パス・スラッシュ・エンコーディングは OS 依存なので同記事の例を参照）。

```text
file:///C:/Users/.../my_table/header.json
```

編集前は **config.json のバックアップ**を推奨。

---

## 4. 自分で表を「公開」するには（ホスティング）

難易度表は **譜面本体ではなく、譜面を指すメタデータ（MD5 / SHA256、タイトル、レベル、ダウンロード URL 等）のリスト**である（[English Guide — What are Difficulty Tables?](https://github.com/wcko87/beatoraja-english-guide/wiki/Difficulty-Tables#what-are-difficulty-tables)）。

公開手順の典型:

1. **表用 JSON**（パーサが解ける形式）を用意する。  
2. **HTTPS で静的配信**できる場所に置く。  
   - **GitHub Pages**（リポジトリの `docs/` や `gh-pages` ブランチ）  
   - **Neocities**、自サイトの `public/`、オブジェクトストレージの公開 URL など  
3. ブラウザで **その JSON の URL に直接アクセスして中身が返る**ことを確認する。  
4. beatoraja-config の **Table URL** にその **フル URL**（できれば `.../something.json`）を追加し、**難易度表読み込み**を実行する。

キャッシュは本体の **table ディレクトリ**（設定の tablepath）下に、URL の SHA-256 由来のファイル名で **`.bmt`**（gzip されたキャッシュ）として保存される（`TableDataAccessor#write` / `getFileName`）。

---

## 5. 「他の難易度表を `minbpm != maxbpm` で絞った新しい表」を作るときの現実

### 5.1 難易度表は SQL や `folder/default.json` では絞れない

- **`folder/default.json` の `sql`** は、**ローカル `songdata.db` に対する CommandBar 用**の WHERE 断片である（別ドキュメント参照）。  
- **難易度表**は、**ホストされた JSON（等）に列挙されたチャート一覧**であり、beatoraja はその一覧を読み、**ローカル DB の `sha256` / `md5` と照合**して所持状況を表示する。  
- したがって **「既存の公開難易度表 URL だけを書き換えて、サーバ側で minbpm!=maxbpm フィルタ」** のようなことは **標準ではできない**。  
  **あなたが新しい JSON を生成して、新しい URL で公開する**必要がある。

### 5.2 推奨パイプライン（オフライン・ワンショット or 定期 CI）

1. **元表を取得**  
   - beatoraja で一度「難易度表読み込み」済みなら、キャッシュ `.bmt` を `TableData.read` 相当で展開するか、元サイトが配っている **生の JSON / ソース**をダウンロードする。  
2. **元表に含まれる各チャートの `sha256`（または `md5`）** を列挙する。  
3. **ローカル `songdata.db` の `song` テーブル**に対し、例えば次の条件で残すチャートだけを抽出する。  

   ```sql
   SELECT sha256 FROM song
   WHERE sha256 IN (...元表のハッシュ一覧...)
     AND minbpm IS NOT NULL AND maxbpm IS NOT NULL
     AND minbpm != maxbpm;
   ```

   - `NULL` 行は `!=` では真にならないため、意図に応じて **`IS NOT NULL` を付けるか**はポリシーで決める。  
4. **元表の各エントリのうち、手順 3 の集合に残ったものだけ**をコピーし、**新しい `TableData` / DifficultyTable 互換 JSON** を組み立てる（レベル帯フォルダ構造は元表を踏襲するか、単一フォルダにまとめるかは任意）。  
5. その JSON を **新しい URL** でホストし、beatoraja の Table URL に追加する。

**段位（コース）** を元表からコピーする場合、**1 曲でも除外されるとコースが成立しなくなる**ことがある。コースを含めるなら、**コース内の全譜が条件を満たすコースだけ残す**等のルールが必要。

### 5.3 参照ツール（実装のヒント）

- 表とローカル DB を組み合わせてファイル操作する例: [wcko87/bms-table-pack-maker](https://github.com/wcko87/bms-table-pack-maker)（表からパック生成。フィルタ付き再出力の参考になる）。  
- 本体に **難易度表エディタ**（`TableEditorView`）があり、ローカルで `TableData` を編集・保存する UI も存在する（配布形式は用途に合わせて `.json` / `.bmt`）。

### 5.4 法務・運用

- 統合難易度表の **利用規約・再配布可否** を確認する。多くは **クレジット表記・改変禁止** 等がある。  
- **自作は「元データの再利用許諾の範囲内」で**行う。

---

## 6. 本体ソース上の根拠（調査メモ）

| 内容 | ファイル・処理 |
|------|------------------|
| Table URL の読み込み・`.json` 分岐 | `bms.player.beatoraja.TableDataAccessor.DifficultyTableAccessor#read` |
| URL → キャッシュ `.bmt` ファイル名 | `TableDataAccessor#getFileName`（URL 文字列の SHA-256 ヘックス） |
| 設定 UI の Table URL 配列 | `ResourceConfigurationView`（`config.setTableURL`） |
| 難易度表のメモリ構造 | `TableData`（`name`, `url`, `tag`, `folder[]`, `course[]`）、`TableFolder` は `name` + `SongData[]` |

---

## 7. 参考リンクまとめ

- beatoraja English Guide — Difficulty Tables: https://github.com/wcko87/beatoraja-english-guide/wiki/Difficulty-Tables  
- 難易度表の一覧例: https://darksabun.github.io/table/tablelist.html（ドメイン移転のリダイレクトあり。最新は一覧サイト側を確認）  
- ローカル `file:///` 追記の手順例: https://pmsdifficulty.xxxxxxxx.jp/column_local_table.html  
- Table URL 操作のブログ例: https://lntakeshi.hateblo.jp/entry/2018/02/05/174446  
