# 作業計画

やることと、まだ決めていないことの一覧。タスクが終わったらチェックを付け、決まったことは「決定事項」に移す。
フェーズの概要は [README](../README.md#ロードマップ) を参照。

## 現在地

**Phase 2 の途中**: CI（lint・型チェック・テスト・Docker ビルド）を追加。次は GHCR への push と定期実行

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
- [ ] ブランチ保護に「CI が通らないとマージできない」を追加
- [ ] Docker イメージを build して GHCR に push
- [ ] `schedule:` で毎日実行してみる（無料でできる最初の定期実行）
- [ ] Dependabot で依存の更新を自動化
- [ ] Claude Code に `github@claude-plugins-official` を追加
- [ ] **要約の方法を決める**（下の「未決定事項」）

## Phase 3: AWS へ手動デプロイ

学ぶこと: IAM（最小権限）、VPC、Secrets Manager / SSM、定期実行

- [ ] **最初に**: AWS Budgets で予算アラート、root ユーザーに MFA
- [ ] 作業用の IAM ユーザー（または IAM Identity Center）を作る
- [ ] 構成を決める（下の「未決定事項」）。作る前に概算の月額と削除方法を確認する
- [ ] EventBridge Scheduler で毎朝実行
- [ ] `QIITA_TOKEN` などの秘密情報を Secrets Manager / SSM に置く
- [ ] Claude Code に `aws-core`、`deploy-on-aws` を追加

## Phase 4: Terraform

学ぶこと: 宣言的なインフラ管理、state、plan / apply

- [ ] Phase 3 で手作業で作ったものを Terraform で作り直す（`infra/terraform/`）
- [ ] tfstate を S3 で管理、`dev` / `prod` を分ける
- [ ] GitHub Actions から OIDC で AWS にデプロイ（アクセスキーを使わない）
- [ ] Claude Code に `terraform@claude-plugins-official` を追加

## Phase 5: 公開と監視

学ぶこと: CDN、DNS、TLS、オブザーバビリティ

- [ ] Markdown → HTML 変換（**変換側でも生の HTML を無効化・サニタイズする**。render.py のエスケープと二重に守る）
- [ ] S3 + CloudFront で配信
- [ ] （任意）Route 53 + ACM で独自ドメインと HTTPS
- [ ] Slack / Discord に毎朝通知
- [ ] ログを構造化（JSON）、CloudWatch アラームで失敗を通知（`fetch` は取得元が1つでも失敗すると終了コード 1）

## 未決定事項

| 項目 | 選択肢 | 決める時期 |
|---|---|---|
| 記事の要約 | LLM API で要約 / 記事の description を使う / 要約しない / その他（検討中） | Phase 2〜3 |
| AWS の実行基盤 | Lambda（安い、月数十円程度） / ECS Fargate + RDS（一般的、月 2,000〜4,000 円程度） | Phase 3 の前 |
| AWS の DB | DynamoDB / S3 に SQLite / RDS PostgreSQL | Phase 3 の前 |
| 通知先 | Slack / Discord | Phase 5 |
| 独自ドメイン | 取るか（年 1,000〜2,000 円程度） | Phase 5 |

## 決定事項

- 2026-10-12: Phase 0 は記事一覧のみ。要約は Phase 2〜3 で追加し、方法は別途検討する
- 2026-10-12: 記事取得は公式 API / RSS のみ（スクレイピングしない）
- 2026-10-12: リポジトリは private で始める
- 2026-10-12: 公開してはいけない情報がなければ public にする（全履歴を点検し、問題なしを確認済み）
- 2026-10-12: 作業はブランチを作り、PR で main に取り込む。マージはユーザーが行う

## 申し送り（いつかやること）

- [x] リポジトリを public に切り替える（2026-10-12、ユーザーが実行）
- [ ] main をルールセットで保護する（PR 必須・直接 push と削除と force push を禁止。**ユーザーが実行**。Claude の自動モードではリポジトリのルール変更が止められる）。Phase 2 で CI 通過も必須にする

- [ ] 2つ目のプロジェクトを作るときに、`ENABLE_STOP_REVIEW` と `permissions.deny` をプロジェクト設定からユーザー設定（`~/.claude/settings.json`）へ移す
- [ ] 定期実行を始める前に Qiita のアクセストークンを発行して `.env` に置く（60 → 1000 リクエスト/時）
- [ ] gh のトークンは `~/.config/gh/hosts.yml` に平文で保存されている。PC を手放すときは `gh auth logout`

## アイデア（やるかは未定）

- 取得元を増やす（Hacker News API など。公式 API / RSS があるものに限る）
- 興味のあるタグだけに絞る設定
- 過去のダイジェストを検索できるようにする
