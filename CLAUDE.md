# tech-digest

Qiita・Zenn などの技術記事を日次で収集・整形・通知するバッチアプリ。
**主目的はインフラ学習**（Docker / CI/CD / AWS / Terraform / 監視）。アプリ部分はシンプルに保つ。

## 技術スタック
- Python 3.13、パッケージ管理は uv（`pip` は使わない）
- lint / format: ruff（編集後に hook で自動実行される）
- テスト: pytest

## よく使うコマンド
- 依存追加: `uv add <pkg>`（開発用は `uv add --dev <pkg>`）
- 実行: `uv run tech-digest run`（`fetch` / `build --date YYYY-MM-DD` で個別実行）
- テスト: `uv run pytest`（PostgreSQL でも試すときは `TEST_DATABASE_URL` を設定。一時的な DB は `docker run --rm -e POSTGRES_PASSWORD=test -p 127.0.0.1:55432:5432 postgres:18.6-trixie`）
- 型チェック: `uv run pyright`
- Docker: `docker build -t tech-digest .` / compose: `docker compose run --rm app`（詳細は README）
  - 依存を変えたら `uv.lock` も更新する（イメージは `uv sync --locked` で入れるので、ずれるとビルドが失敗する）
- lint: `uv run ruff check --fix && uv run ruff format`
  - 編集時の hook は未使用 import（F401）を消さないので、作業の最後に必ず `ruff check` を通す

## 構成
- `src/tech_digest/cli.py` サブコマンド（fetch / build / run）
- `src/tech_digest/sources/` 取得元。`fetch(client, digest_date, settings) -> list[Article]` を持つモジュールを作り `SOURCES` に登録する。HTTP 部分と `parse()` を分け、テストは `parse()` と `httpx.MockTransport` で書く
- `src/tech_digest/storage.py` DB。`DATABASE_URL` があれば PostgreSQL、なければ SQLite。SQL は両方で動く共通の書き方だけを使う。主キーは (source, url)、`digest_date` は初めて載った日で更新しない
- `src/tech_digest/render.py` Markdown 生成
- `tests/` テスト（ネットワークに出ない）
- `infra/terraform/` インフラ定義（Phase 4 以降）

## Git の運用
- **main に直接コミット・push しない。** 作業は main の最新から新しいブランチを作って行う
  - 名前の例: `phase1-docker`、`feat/<内容>`、`fix/<内容>`、`docs/<内容>`
- コミットしたらブランチを push し、`gh pr create` で PR を作る。本文には変更内容と確認方法を書く
- **マージはユーザーが行う。** Claude は PR を作るところまで
- 次の作業の前に `git switch main && git pull` で main を最新にする

## 計画
- タスク・未決定事項・申し送りは `docs/PLAN.md` にある。作業を始める前に読む
- タスクが終わったらチェックを付け、「現在地」を更新する。決まったことは日付付きで「決定事項」に移す
- 未決定事項はユーザーが決める。勝手に決めて実装しない（特に記事の要約の方法）

## 方針
- 設定は環境変数から読む（ローカル・Docker・クラウドで同じコードが動くように）
- 記事取得は公式 API / RSS のみ（スクレイピングしない）。同じ日を再実行しても結果が変わらないこと（URL で重複排除）
- 秘密情報は `.env` にだけ置き、コードやコミットに含めない
- インフラ作業（Dockerfile、CI、AWS、Terraform）では「なぜそうするか」も説明する
- 課金が発生する AWS リソースを作る前に、概算コストと削除方法を示す
