# tech-digest

Qiita・Zenn などの技術記事を日次で収集・整形・通知するバッチアプリ。
**主目的はインフラ学習**（Docker / CI/CD / AWS / Terraform / 監視）。アプリ部分はシンプルに保つ。

## 技術スタック
- Python 3.13、パッケージ管理は uv（`pip` は使わない）
- lint / format: ruff（編集後に hook で自動実行される）
- テスト: pytest

## よく使うコマンド
- 依存追加: `uv add <pkg>`（開発用は `uv add --dev <pkg>`）
- 実行: `uv run tech-digest`
- テスト: `uv run pytest`
- lint: `uv run ruff check --fix && uv run ruff format`

## 構成
- `src/tech_digest/` アプリ本体（取得元は `sources/` に共通インターフェースで追加する）
- `tests/` テスト
- `infra/terraform/` インフラ定義（Phase 4 以降）

## ロードマップ
0. ローカル CLI（取得 → SQLite → Markdown）
1. Docker / compose（PostgreSQL）
2. GitHub Actions（lint・test・イメージ build）
3. AWS へ手動デプロイ
4. Terraform 化
5. 公開（S3 + CloudFront）と監視

## 方針
- 設定は環境変数から読む（ローカル・Docker・クラウドで同じコードが動くように）
- 記事取得は公式 API / RSS のみ（スクレイピングしない）。同じ日を再実行しても結果が変わらないこと（URL で重複排除）
- 秘密情報は `.env` にだけ置き、コードやコミットに含めない
- インフラ作業（Dockerfile、CI、AWS、Terraform）では「なぜそうするか」も説明する
- 課金が発生する AWS リソースを作る前に、概算コストと削除方法を示す
