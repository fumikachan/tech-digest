# tech-digest

Qiita・Zenn などの技術記事を日次で収集・整形・通知するバッチアプリ。
**主目的はインフラ学習**（Docker / CI/CD / AWS / Terraform / 監視）。アプリ部分はシンプルに保つ。

## 技術スタック
- Python 3.13、パッケージ管理は uv（`pip` は使わない）
- lint / format: ruff（編集後に hook で自動実行される）
- テスト: pytest
- フロント（`web/`）: TypeScript + Vite、テストは vitest。Node は nvm で入れた 24（`web/.nvmrc`）、パッケージは npm（`web/.npmrc` でインストール時のスクリプトを止めている）

## よく使うコマンド
- 依存追加: `uv add <pkg>`（開発用は `uv add --dev <pkg>`）
- 実行: `uv run tech-digest run`（`fetch` / `build --date YYYY-MM-DD` で個別実行）
- テスト: `uv run pytest`（PostgreSQL でも試すときは `TEST_DATABASE_URL` を設定。一時的な DB は `docker run --rm -e POSTGRES_PASSWORD=test -p 127.0.0.1:55432:5432 postgres:18.6-trixie`）
- 型チェック: `uv run pyright`
- Docker: `docker build -t tech-digest .` / compose: `docker compose run --rm app`（詳細は README）
  - DynamoDB Local: `docker compose run --rm app-dynamodb create-table`（初回）→ `docker compose run --rm app-dynamodb`
  - 依存を変えたら `uv.lock` も更新する（イメージは `uv sync --locked` で入れるので、ずれるとビルドが失敗する）
- フロント: `cd web && npm ci`（依存の追加は `npm install --save-dev <pkg>@<版>`）→ `npm run dev` / `npm run typecheck` / `npm test` / `npm run build`
  - nvm はシェルの関数なので、コマンドから使うときは先に `. ~/.nvm/nvm.sh` で読み込む
- lint: `uv run ruff check --fix && uv run ruff format`
  - 編集時の hook は未使用 import（F401）を消さないので、作業の最後に必ず `ruff check` を通す

## 構成
- `src/tech_digest/cli.py` サブコマンド（fetch / build / run）
- `src/tech_digest/sources/` 取得元。`fetch(client, digest_date, settings) -> list[Article]` を持つモジュールを作り `SOURCES` に登録する。HTTP 部分と `parse()` を分け、テストは `parse()` と `httpx.MockTransport` で書く
- `src/tech_digest/storage/` DB。どれも `Store`（`save` / `load` / `close`）を満たす。主キーは (source, url)、`digest_date` は初めて載った日で更新しない
  - `sql.py`: `DATABASE_URL` があれば PostgreSQL、なければ SQLite。SQL は両方で動く共通の書き方だけを使う
  - `dynamodb.py`: `DYNAMODB_TABLE` があれば使う（最優先）。設計は `docs/API_DESIGN.md`。テストは moto
- `src/tech_digest/api/` 読み取り専用の API（API Gateway + Lambda）。`routes.py` に処理（`ROUTES` のキーは API Gateway のルートキー）、`lambda_handler.py` が Lambda の入口、`devserver.py` はローカル用。DynamoDB だけを使う
- `src/tech_digest/render.py` Markdown 生成
- `src/tech_digest/archive.py` 1 日分の記事の JSON 書き出し・読み込み（data ブランチの `daily/` に置く）
- `src/tech_digest/site.py` + `templates/` + `static/` 静的サイト（GitHub Pages）
  - HTML は必ず Jinja2 テンプレート（自動エスケープ）で出す。URL は `render.safe_url` を通す
  - JavaScript で外部の文字列を出すときは `textContent` だけ（`innerHTML` 禁止）。CSP で外部スクリプトとインラインスクリプトを禁止している
- `web/` SPA（API から読む。AWS に API ができるまでは公開しない）。ハッシュルーティング（`#/days/...`）
  - 外部の文字列は `dom.ts` の `h()` でテキストとしてだけ入れる（`innerHTML` 禁止）。外部の URL は `externalLink` を通す
  - API の型は `src/api.ts`。API を変えたら合わせて直す
- `tests/` テスト（ネットワークに出ない）
- `infra/terraform/` インフラ定義（Phase 4 以降）

## Git の運用
- **main に直接コミット・push しない。** 作業は main の最新から新しいブランチを作って行う
  - 名前の例: `phase1-docker`、`feat/<内容>`、`fix/<内容>`、`docs/<内容>`
- コミットしたらブランチを push し、`gh pr create` で PR を作る。本文には変更内容と確認方法を書く
- **マージはユーザーが行う。** Claude は PR を作るところまで
- 次の作業の前に `git switch main && git pull` で main を最新にする

## ドキュメント
- `docs/OPERATIONS.md`: 実行・DB 接続・トラブル対処の手順。コマンドや設定を変えたら合わせて更新する
- `docs/API_DESIGN.md`: DynamoDB のテーブルと API の設計。キーや API を変えたら合わせて更新する

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
