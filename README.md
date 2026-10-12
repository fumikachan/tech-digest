# data ブランチ

tech-digest のサイトに載せる過去の記録。GitHub Actions の「Daily digest」が毎朝 1 ファイルずつ追加する。

- `daily/YYYY-MM-DD.json`: その日のダイジェストに載った記事（タイトル・URL・スコア・タグなど）
- サイトはこのファイルから組み立てる（`tech-digest site --data daily`）
- コードは main ブランチにある。このブランチは記録専用で、main にはマージしない
