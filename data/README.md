# `data/songdata.db`

beatoraja がローカルで生成する **`songdata.db`** を、このパスに置いて使います。**Git にコミットしない**運用にする場合でも、ローカルや CI のランナー上ではこのパスにファイルがあればスクリプトは動作します。

## 手動での更新手順

**差し替え・Release へのアップロード・サイズの注意**など、運用上の手順は **[リポジトリ直下の README.md](../README.md)** の「`songdata.db` を更新して配布する」を参照してください。

## GitHub Releases にだけ載せる場合

**Release のアセットとして `songdata.db` を配布し**、GitHub Actions が **Latest Release** から取得する方法は **[docs/github-releases-songdata.md](../docs/github-releases-songdata.md)** にまとめています。

## サイズが大きい場合

Git LFS、**GitHub Releases アセット**（上記）、別オブジェクトストレージ、リポジトリを表公開専用に分ける、などを検討してください。Actions で Release 取得を使わない場合は、ランナー上で **`data/songdata.db` が存在する**必要があります。
