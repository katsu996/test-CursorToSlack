# beatoraja と派生（LR2oraja / LR2oraja Endless Dream）の違い

調査時点の公開 README・リリース情報に基づく整理です。バージョンで差異があるため、導入前は各リポジトリの最新リリースノートを確認してください。

## 関係図（派生の重なり）

```text
beatoraja (exch-bms2/beatoraja)
    └── LR2oraja (wcko87/lr2oraja)  … LR2 系ゲージ・判定へ寄せた fork
            └── LR2oraja ~Endless Dream~ (seraxis/lr2oraja-endlessdream)
                    … LR2oraja をベースに QoL・追加機能・性能改善
```

- **LR2oraja:** 本体 beatoraja の **JAR を差し替える**形（配布は `beatoraja.jar` のみの説明が README にある）。
- **Endless Dream:** 同様に **公式 beatoraja 0.8.8 同梱版をベースに JAR を差し替え**（README では `beatoraja.jar` にリネームして配置）。**Java 8 → 17 への要件変更**が 0.3.0 以降で注意書きされている。

---

## 一覧: vanilla beatoraja との差（何が「be と違うか」）

| 観点 | beatoraja（本流） | LR2oraja | LR2oraja ~Endless Dream~ |
|------|-------------------|----------|---------------------------|
| **目的・位置づけ** | クロスプラットフォームの標準 BMS プレイヤー（独自ゲージ・判定がデフォルト）。 | 「最新の beatoraja を **LR2 のゲージ・判定**でコンパイルしたもの」（README 原文の趣旨）。 | 本流に無い **QoL・拡張・修正**を集約したコミュニティ fork（LR2oraja ベース）。 |
| **ゲージ** | beatoraja 既定のゲージ仕様。 | **全キーモードで LR2 のゲージがデフォルト**（7K / 5K / 10K / 14K / 9K / 24K / 48K 等）。ASSIST EASY / EX-HARD は README 記載の独自解釈で LR2 寄せ。 | LR2oraja を踏襲（＝ゲージは LR2 系がベース）。 |
| **判定窓（EASY〜VERYHARD）** | beatoraja の窓。プラクティス等では **線形スケール**の説明が README にある。 | **LR2 の EASY / NORMAL / HARD / VERYHARD の窓に置き換え**。プラクティスでは LR2 窓同士の **補間**になる（100/75/50/25% が LR2 の離散レベルに対応するイメージ）。VERYEASY は LR2 扱いに合わせ NORMAL と同じ 75% 等。 | 判定まわりは LR2oraja ベース（本流 be と同じではない）。 |
| **スクラッチ** | beatoraja 既定。 | **通常ノーツと同じタイミング窓**（LR2 寄せ）。 | （README 上は個別記載なし → LR2oraja 踏襲とみなす。） |
| **HARD / EXHARD ゲージの減少・死亡** | beatoraja の仕様。 | **LR2 に合わせて変更**（0.8.3〜）：ゲージ減少緩和が **残り厳密に 32% 未満**から、失敗が **2% 未満**で発生等（README 数値）。 | LR2oraja 踏襲。 |
| **LN 解放の扱い** | 早解放は POOR 等、beatoraja の LN ロジック。 | **LR2 寄せ: 早解放は BAD**。許容は「GOOD 窓相当」等（README 詳細）。 | LR2oraja 踏襲。 |
| **TOTAL 未指定時の式** | beatoraja の既定式。 | **LR2 と同じ式に変更**（0.8.3〜、`160 + (N + clamp(...))*0.16` 形式が README に記載）。 | LR2oraja 踏襲。 |
| **ウィンドウタイトル / F6 スクショ** | beatoraja 表記。 | **「LR2oraja」表記**（スコア投稿の識別用、README）。 | 配布 JAR 名は `lr2oraja.*.jar` だが、配置時は `beatoraja.jar` にリネーム（README）。表記はリリースを確認。 |
| **IR（インターネットランキング）** | 各種 IR と連携する前提の利用者が多い。 | **IR 向けではない**旨が README FAQ に明記（beatoraja IR / LR2IR の意図した動作は想定外）。 | 開発用に `useIR` プロパティの言及あり（README）。一般利用者は各 IR の対応表を確認。 |
| **追加機能（本流にないもの）** | ー | 上記の判定・ゲージ・TOTAL 等に限定。 | **曲ダウンローダー、LR2 GBATTLE、osu 譜面、レート／周波数の on-the-fly、libGDX グラフィックバックエンド更新による性能、テーブル処理高速化、F5/Insert の Mod メニュー** 等（README Key Features）。 |
| **Java 要件** | 公式同梱版の JRE に準拠（時期により 8 等）。 | 差し替え元の beatoraja に準拠。 | **JDK 17（JavaFX 同梱の Full JDK 推奨）** がビルド README に記載。0.3.0 から 8→17 の注意。 |
| **`folder/default.json` 等の楽曲DB周り** | 仕様の基準。 | **beatoraja と同じ構成のインストールに JAR 差し替え**のため、**仮想フォルダ SQL・songdata.db の概念は本流と同一視してよい**（独自仕様の記載は README に無い）。 | **beatoraja 0.8.8 インストール互換**と README に明記。**SQL フォルダ・DB 周りは本流ベース**で、差分は主にプレイ周辺・拡張機能。 |

---

## LR2oraja だけの要点（README「Changes from the original beatoraja」要約）

1. 全キーモードで **LR2 ゲージがデフォルト**（プラクティスも同様）。スクラッチ窓を通常ノーツに合わせる。  
2. **HARD / EXHARD** の減衰開始・失敗ラインを LR2 に合わせる（本流との数値差あり）。  
3. **判定**を LR2 の EASY〜VERYHARD に差し替え（プラクティスでの窓の補間挙動は本流の線形スケールと異なる）。  
4. **LN 早解放**を LR2 寄せ（BAD 等）。  
5. タイトル表記で **LR2oraja** と分かるようにする。  
6. **TOTAL 自動計算**を LR2 式に変更。  
7. **複製しない**と README が挙げるもの: 極近接ノートの S-RANDOM 差、速度変化の細部、`#DEFEXRANK` と LR2 の差異など。

出典: https://github.com/wcko87/lr2oraja/blob/readme/README.md

---

## Endless Dream だけの要点（本流 be との差分の言い方）

- **本流 beatoraja との差**ではなく、まず **「LR2oraja までの差（LR2 寄せ）」をすべて含む**上で、  
- **Endless Dream 独自**として README が列挙するのは主に: 曲 DL、GBATTLE、osu、レート mod、描画・テーブル性能、Mod メニュー、0.8.8 配置互換、Java 17 移行など **プレイ体験・インフラ寄り**。

譜面解釈のコア（BMS デコード）や `folder/default.json` の SQL 結合の基本形が本流から大きく変わっているという公式説明は README に無いため、**「default.json での `minbpm != maxbpm` 等」は三派生とも実用上は同じ考え方でよい**が、**IR 連携・スコアの扱い**だけは LR2oraja README の注意（IR 非想定）を踏まえる。

出典: https://github.com/seraxis/lr2oraja-endlessdream/blob/main/README.md

---

## 参考リンク

- beatoraja: https://github.com/exch-bms2/beatoraja  
- LR2oraja: https://github.com/wcko87/lr2oraja  
- LR2oraja ~Endless Dream~: https://github.com/seraxis/lr2oraja-endlessdream  
- beatoraja English Guide（セットアップ等）: https://github.com/wcko87/beatoraja-english-guide/wiki  
