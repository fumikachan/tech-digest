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

記事の要約は Phase 2〜3 のあたりで追加する予定（方法は検討中）。

細かいタスク、未決定事項、申し送りは [docs/PLAN.md](docs/PLAN.md) にまとめている。

## 使い方

```bash
uv run tech-digest run              # 取得して今日のダイジェストを digests/YYYY-MM-DD.md に出力
uv run tech-digest fetch            # 取得して DB に保存するだけ
uv run tech-digest build --date 2026-10-12   # DB から指定日のダイジェストを作り直す
```

### ダイジェストに載る記事

ダイジェストの日付は実行した日（日本時間）。

| 取得元 | 載る記事 | 並び順 |
|---|---|---|
| Qiita（API v2） | 前日に投稿された記事 | いいね数 |
| Zenn（トレンド RSS） | その日に初めてトレンドに載った記事 | 投稿日時 |
| はてなブックマーク（IT 人気エントリー RSS） | その日に初めて人気エントリーに載った記事 | ブックマーク数 |

記事は DB に「初めて載った日」と一緒に保存するので、何日もトレンドに残る記事が毎日重複して載ることはない。同じ日に何度実行しても結果は変わらない。

### 環境変数

| 変数 | 既定値 | 説明 |
|---|---|---|
| `DATABASE_URL` | なし | `postgresql://ユーザー:パスワード@ホスト:5432/DB名`。設定すると PostgreSQL を使う |
| `TECH_DIGEST_DB_PATH` | `data/tech-digest.db` | `DATABASE_URL` がないときに使う SQLite の DB ファイル |
| `TECH_DIGEST_OUTPUT_DIR` | `digests` | ダイジェストの出力先 |
| `QIITA_TOKEN` | なし | Qiita のアクセストークン（任意。なしだと 60 リクエスト/時の制限） |

`.env` に書いた場合は `uv run --env-file .env tech-digest run` で読み込める。

## Docker で動かす

```bash
docker build -t tech-digest .
mkdir -p digests   # 先に作っておく（Docker に作らせると root の持ち物になり、書き込めない）
docker run --rm -v tech-digest-data:/data -v "$PWD/digests:/output" tech-digest
```

| マウント | 中身 | 種類 |
|---|---|---|
| `tech-digest-data:/data` | SQLite の DB | 名前付きボリューム（Docker が管理。コンテナを消しても残る） |
| `$PWD/digests:/output` | ダイジェストの Markdown | バインドマウント（ホストのディレクトリ） |

- サブコマンドは末尾に書く: `docker run --rm -v tech-digest-data:/data -v "$PWD/digests:/output" tech-digest build --date 2026-10-12`
- 環境変数を渡す: `--env-file .env` を `docker run` に付ける
- コンテナ内のユーザーは UID 1000（WSL の最初のユーザーと同じ）。ホストの UID が違う場合は `docker build --build-arg APP_UID=$(id -u) -t tech-digest .`
- DB を消して最初からやり直す: `docker volume rm tech-digest-data`

## compose で動かす（PostgreSQL）

```bash
# .env がなければ作り、パスワードにランダムな値を入れる（既にあれば何もしない）
[ -e .env ] || { cp .env.example .env && sed -i "s/^POSTGRES_PASSWORD=$/POSTGRES_PASSWORD=$(openssl rand -hex 16)/" .env; }
mkdir -p digests
docker compose run --rm app        # db を起動し、準備できてから app を 1 回実行する
docker compose down                # 止める（DB のデータはボリューム tech-digest_db-data に残る）
```

- DB の中を見る: `docker compose exec db psql -U tech_digest -c "select source, count(*) from articles group by source"`
- アプリのコードを変えたら `docker compose build app` でイメージを作り直す
- DB を消して最初からやり直す: `docker compose down -v`（**ボリュームごと削除する**）
- `POSTGRES_PASSWORD` が使われるのは **DB のボリュームを初めて作るときだけ**。あとから `.env` だけ変えても DB 側は変わらない。変えるときは DB 側も合わせる:
  `docker compose up -d --wait db && docker compose exec db psql -U tech_digest -c "ALTER USER tech_digest PASSWORD '新しいパスワード'"`
- db のポートはホストに公開していない（app からは compose のネットワーク内でホスト名 `db` で接続する）

## 開発

```bash
uv sync                 # 依存のインストール
uv run pytest           # テスト（PostgreSQL のテストは TEST_DATABASE_URL があるときだけ実行）
uv run pyright          # 型チェック
uv run ruff check --fix && uv run ruff format   # lint / format
```

新しい取得元を足すときは、`src/tech_digest/sources/` に `fetch(client, digest_date, settings)` を持つモジュールを作り、`sources/__init__.py` の `SOURCES` に追加する。
