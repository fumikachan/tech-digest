# 作業計画

やることと、まだ決めていないことの一覧。タスクが終わったらチェックを付け、決まったことは「決定事項」に移す。
フェーズの概要は [README](../README.md#ロードマップ) を参照。

## 現在地

**Phase 2 完了・サイトを GitHub Pages で公開中** → Phase 3-1（AWS を使わずにローカルで作る）。次は `storage.py` の DynamoDB 版

## Phase 0: ローカル CLI ✅（2026-10-12）

- [x] Qiita API / Zenn RSS / はてなブックマーク RSS から取得
- [x] SQLite に保存（(source, url) で重複排除、初めて載った日を記録）
- [x] Markdown のダイジェストを出力（`tech-digest run`）
- [x] 外部データのエスケープ（XSS・リンク偽装の対策）
- [x] テスト・型チェック・lint

## Phase 1: Docker / compose ✅（2026-10-12）

学ぶこと: イメージとコンテナの違い、レイヤーキャッシュ、ボリューム、ネットワーク

- [x] `Dockerfile`（マルチステージ、uv で依存を入れる、root 以外のユーザーで実行）
- [x] `.dockerignore`（`.venv`、`data/`、`.env` をイメージに入れない）
- [x] `compose.yaml`（アプリ + PostgreSQL、DB はボリュームで永続化、healthcheck）
- [x] storage を PostgreSQL に対応（`DATABASE_URL` で SQLite と切り替え）
- [x] ダイジェストの出力先をボリュームにマウント（`docker run -v "$PWD/digests:/output"`）
- [x] README に Docker / compose での実行方法を追記

## Phase 2: GitHub Actions

学ぶこと: CI パイプライン、Secrets、コンテナレジストリ

- [x] push / PR で lint・型チェック・テストを実行（PostgreSQL はサービスコンテナで用意し、`TEST_DATABASE_URL` を渡す）
- [x] PR で Docker イメージがビルドできるか確認（push はしない）
- [x] ブランチ保護に「CI が通らないとマージできない」を追加（2026-10-12）
- [x] Docker イメージを build して GHCR に push（main へのマージ時、`publish.yml`）
- [x] `schedule:` で毎日実行してみる（毎朝 7:00 JST、`daily.yml`。DB は actions/cache で引き継ぎ、ダイジェストは Artifacts）
- [x] Dependabot で依存の更新を自動化（uv・Actions・Dockerfile・compose を毎週）
- [ ] マージ後に Actions の画面から「Daily digest」を手動実行して動作確認
- [ ] GitHub の Secrets に `QIITA_TOKEN` を登録（ランナーは IP を共有しているので、トークンなしだと制限に当たりやすい）
- [ ] Claude Code に `github@claude-plugins-official` を追加
- [ ] **要約の方法を決める**（下の「未決定事項」）

## Phase 3: AWS へ手動デプロイ（DynamoDB + Lambda + API Gateway）

学ぶこと: IAM（最小権限）、Lambda、API Gateway、DynamoDB のキー設計、Secrets Manager / SSM、定期実行

構成: 収集バッチ（Lambda）→ DynamoDB ← API（Lambda + API Gateway の HTTP API）← サイト（SPA）。
Lambda と DynamoDB は VPC の外に置く（VPC 内の Lambda が外部 API に出るには NAT Gateway が要り、月 6,000 円以上かかるため）

設計: [API_DESIGN.md](API_DESIGN.md)（テーブル・API・ローカルでの動かし方）

### 3-1. ローカルで作る（AWS を使わない。費用 0 円）

- [x] ページごとに必要なデータ（問い合わせの形）を決め、DynamoDB のキー設計（パーティションキー・ソートキー・GSI）を決める（2026-10-13、[API_DESIGN.md](API_DESIGN.md)）
- [ ] `storage.py` に DynamoDB 版を追加（`DYNAMODB_TABLE` で切り替え。SQLite / PostgreSQL もそのまま動くようにする）。テストは moto
- [ ] compose に DynamoDB Local を追加し、ローカルでテーブルを作るコマンドを用意する
- [ ] API のハンドラーを作る（`src/tech_digest/api/`。フレームワークを使わず、API Gateway のイベントを直接扱う）。テストは偽のイベントを渡す
- [ ] ハンドラーを包む開発用サーバーで、ローカルから API を呼べるようにする
- [ ] `web/` に SPA を作る（TypeScript + Vite。外部の文字列は `textContent` だけ。ローカルでは Vite のプロキシでローカルの API を呼ぶ）
- [ ] CI に `web/` のジョブ（型チェック・ビルド）を追加し、Dependabot に npm を追加
- [ ] 収集バッチを Lambda のハンドラーから呼べるようにする（中身は `tech-digest fetch` と同じ）

公開中の GitHub Pages のサイトは、AWS の API ができるまで今のまま（静的サイト）にしておく。先に SPA に置き換えると、呼ぶ API がないので表示されなくなる。

### 3-2. AWS に作る

- [ ] **最初に**: AWS Budgets で予算アラート、root ユーザーに MFA
- [ ] 作業用の IAM ユーザー（または IAM Identity Center）を作る
- [ ] 作る前に概算の月額と削除方法を確認する（目安: 無料枠内でほぼ 0 円〜数十円）
- [ ] DynamoDB のテーブルを作る（容量モードを先に決める）
- [ ] 収集バッチを Lambda で動かし、EventBridge Scheduler で毎朝実行
- [ ] `QIITA_TOKEN` などの秘密情報を Secrets Manager / SSM に置く
- [ ] API を Lambda + API Gateway（HTTP API）で公開する。スロットリングと Lambda の同時実行数の上限を設定し、CORS はサイトのオリジンだけ許可
- [ ] IAM ロールを分ける（バッチは書き込みだけ、API は読み取りだけ。どちらにもテーブルを作る権限は渡さない）
- [ ] 公開サイトを SPA に切り替える（今の `templates/` と `static/` を消す。CSP の `connect-src` に API を追加）
- [ ] Claude Code に `aws-core`、`deploy-on-aws` を追加

## Phase 4: Terraform

学ぶこと: 宣言的なインフラ管理、state、plan / apply

- [ ] Phase 3 で手作業で作ったもの（DynamoDB・Lambda 2 つ・API Gateway・EventBridge Scheduler・IAM）を Terraform で作り直す（`infra/terraform/`）
- [ ] CI に paths フィルターを入れ、バッチ / API / `web/` の変更ごとに必要なジョブだけ実行する
- [ ] tfstate を S3 で管理、`dev` / `prod` を分ける
- [ ] GitHub Actions から OIDC で AWS にデプロイ（アクセスキーを使わない）
- [ ] Claude Code に `terraform@claude-plugins-official` を追加

## Phase 5: 公開と監視

学ぶこと: CDN、DNS、TLS、オブザーバビリティ

- [x] HTML のサイトを生成（Jinja2 の自動エスケープ + CSP。JavaScript は textContent のみ）。2026-10-12、先に GitHub Pages で公開
- [ ] S3 + CloudFront で配信（GitHub Pages から移す。違いを比べる）
- [ ] API の前にも CloudFront を置いてキャッシュする（Lambda の呼び出し回数を減らす）
- [ ] （任意）Route 53 + ACM で独自ドメインと HTTPS
- [ ] Slack / Discord に毎朝通知
- [ ] ログを構造化（JSON）、CloudWatch アラームで失敗を通知（`fetch` は取得元が1つでも失敗すると終了コード 1）

## 未決定事項

| 項目 | 選択肢 | 決める時期 |
|---|---|---|
| 記事の要約 | LLM API で要約 / 記事の description を使う / 要約しない / その他（検討中） | Phase 2〜3 |
| DynamoDB の容量モード | プロビジョンド（無料枠内なら 0 円。検索が続くとスロットリング） / オンデマンド（使った分だけ。検索 1 回 0.01 円程度） | AWS にテーブルを作る前 |
| Lambda のパッケージ形式 | zip / コンテナイメージ（ECR） | 収集バッチを Lambda に移す前 |
| data ブランチの JSON | DynamoDB に移った後もバックアップとして続ける / やめる | 収集バッチを Lambda に移した後 |
| 通知先 | Slack / Discord | Phase 5 |
| 独自ドメイン | 取るか（年 1,000〜2,000 円程度） | Phase 5 |

## 決定事項

- 2026-10-12: Phase 0 は記事一覧のみ。要約は Phase 2〜3 で追加し、方法は別途検討する
- 2026-10-12: 記事取得は公式 API / RSS のみ（スクレイピングしない）
- 2026-10-12: リポジトリは private で始める
- 2026-10-12: 公開してはいけない情報がなければ public にする（全履歴を点検し、問題なしを確認済み）
- 2026-10-12: 作業はブランチを作り、PR で main に取り込む。マージはユーザーが行う
- 2026-10-12: 収集した記事を見られるサイトを GitHub Pages で公開する（機能: アーカイブ・絞り込み・検索・並べ替え）。過去の記録は data ブランチの JSON に残す
- 2026-10-12: インフラ学習のため、API Gateway + Lambda で API を作る。DB は DynamoDB（期限なしの無料枠でほぼ 0 円。RDS は月 3,000 円〜で、VPC 内の Lambda から外部に出るための NAT Gateway も高い）
- 2026-10-12: 収集バッチも Lambda で動かす（API と実行基盤をそろえる）。ECS Fargate と RDS は使わない
- 2026-10-12: サイトは全体を API から読む SPA に作り替える（フロントとバックの分離を学ぶため）
- 2026-10-12: API とフロントは別のリポジトリにせず、tech-digest の中でディレクトリを分ける（`src/tech_digest/api/`、`web/`）。書く側（バッチ）と読む側（API・サイト）が DynamoDB のキー設計と記事の形を共有するので、1 つの PR でまとめて変えられるようにする
- 2026-10-13: AWS を使う前に、デプロイ以外をローカルで作る（Phase 3-1）。費用をかけずに進めるため
- 2026-10-13: テストの DynamoDB は moto、手元で動かすときは DynamoDB Local（compose）。今の「普段のテストは SQLite、PostgreSQL はコンテナ」と同じ考え方
- 2026-10-13: `web/` の SPA は TypeScript + Vite で作る

## 申し送り（いつかやること）

- [ ] GitHub Pages を有効にする（Settings → Pages → Source を「GitHub Actions」。**ユーザーが実行**）
- [ ] DB のキャッシュが消えたとき、data ブランチの JSON から DB を復元できるようにする（今は消えると、トレンドの記事が翌日もう一度載る）。Phase 3 で DynamoDB に移れば不要になる

- [x] リポジトリを public に切り替える（2026-10-12、ユーザーが実行）
- [x] main をルールセットで保護する（PR 必須・直接 push と削除と force push を禁止。**ユーザーが実行**。Claude の自動モードではリポジトリのルール変更が止められる）。Phase 2 で CI 通過も必須にする

- [ ] 2つ目のプロジェクトを作るときに、`ENABLE_STOP_REVIEW` と `permissions.deny` をプロジェクト設定からユーザー設定（`~/.claude/settings.json`）へ移す
- [ ] 定期実行を始める前に Qiita のアクセストークンを発行して `.env` に置く（60 → 1000 リクエスト/時）
- [ ] gh のトークンは `~/.config/gh/hosts.yml` に平文で保存されている。PC を手放すときは `gh auth logout`

## アイデア（やるかは未定）

- 取得元を増やす（Hacker News API など。公式 API / RSS があるものに限る）
- 興味のあるタグだけに絞る設定
- 過去のダイジェストを検索できるようにする
