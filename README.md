# tech-digest

技術ブログ（Qiita・Zenn・はてなブックマーク IT など）の新着記事を毎日自動で集めて、ダイジェストにまとめるバッチアプリ。

アプリ自体は小さく保ち、Docker・CI/CD・AWS・Terraform・監視といったインフラを一通り学ぶための題材にしている。

## 仕組み（予定）

```
定期実行（毎朝）
  └─ 各サイトの公式 API / RSS から前日の記事を取得
      └─ DB に保存（URL で重複を除外）
          ├─ Markdown / HTML のダイジェストを生成 → Web で公開
          └─ Slack / Discord に通知
```

## ロードマップ

| Phase | 内容 | 学ぶこと |
|---|---|---|
| 0 | ローカル CLI（取得 → SQLite → Markdown） | Linux、git、uv |
| 1 | Docker / compose（PostgreSQL） | コンテナ、ボリューム、ネットワーク |
| 2 | GitHub Actions（lint・test・イメージ build） | CI/CD、シークレット管理 |
| 3 | AWS へデプロイ（定期実行） | IAM、VPC、Lambda / ECS |
| 4 | Terraform 化 | IaC、state 管理 |
| 5 | S3 + CloudFront で公開、監視 | CDN、DNS、TLS、オブザーバビリティ |

## 開発

```bash
uv sync                 # 依存のインストール
uv run tech-digest      # 実行
uv run pytest           # テスト
uv run ruff check --fix && uv run ruff format   # lint / format
```
