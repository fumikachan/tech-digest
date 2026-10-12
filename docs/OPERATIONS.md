# 操作ガイド

tech-digest をふだん動かすときのコマンド・接続方法・トラブル対処をまとめた手元用のメモ。
コマンドはすべてプロジェクトのフォルダ（`~/projects/tech-digest`）で実行する。

## 目次

1. [実行する](#1-実行する)
2. [DB を起動・停止する](#2-db-を起動停止する)
3. [DB の中を見る](#3-db-の中を見る)
4. [設定（.env）](#4-設定env)
5. [開発のチェック](#5-開発のチェック)
6. [Git と PR の流れ](#6-git-と-pr-の流れ)
7. [データを消してやり直す](#7-データを消してやり直す)
8. [困ったとき](#8-困ったとき)

---

## 1. 実行する

ふだんは **compose（PostgreSQL）** を使う。

| 方法 | コマンド | DB |
|---|---|---|
| **compose（ふだんはこれ）** | `docker compose run --rm app` | PostgreSQL（ボリューム `tech-digest_db-data`） |
| uv で直接 | `uv run tech-digest run` | SQLite（`data/tech-digest.db`） |
| uv で直接 + PostgreSQL | `DATABASE_URL="postgresql://tech_digest:<パスワード>@localhost:5432/tech_digest" uv run tech-digest run` | compose の PostgreSQL（db の起動が必要） |

- ダイジェストは `digests/YYYY-MM-DD.md` に出力される
- サブコマンド: `run`（取得 + 出力）/ `fetch`（取得だけ）/ `build --date 2026-10-12`（指定日を作り直す）
  - compose なら `docker compose run --rm app build --date 2026-10-12` のように末尾に付ける
- アプリのコードを変えたら、compose のイメージを作り直す: `docker compose build app`

## 2. DB を起動・停止する

PostgreSQL はコンテナで動く。**DB に接続するには db が起動している必要がある。**

```bash
docker compose up -d db     # db だけをバックグラウンドで起動
docker compose ps           # 状態を確認（STATUS が healthy なら接続できる）
docker compose down         # 止める（データはボリュームに残る）
```

| こんなとき | db の状態 |
|---|---|
| `docker compose run --rm app` の後 | **動いたまま**（app だけ終了する） |
| `docker compose down` の後 | 止まる（データは残る） |
| PC の再起動・`wsl --shutdown` の後 | 止まっている → `docker compose up -d db` で起動 |

Docker 本体は WSL の起動時に自動で起動する（systemd で有効化済み）。

## 3. DB の中を見る

### A5:SQL Mk-2（Windows）

先に `docker compose up -d db` で起動しておく。「PostgreSQL に直接接続」で次のように設定する。

| 項目 | 値 |
|---|---|
| ホスト | `localhost` |
| ポート | `5432`（`.env` で `DB_PORT` を変えた場合はその値） |
| データベース | `tech_digest` |
| ユーザー | `tech_digest` |
| パスワード | `.env` の `POSTGRES_PASSWORD` |

- ポートは `127.0.0.1` にだけ公開しているので、この PC からしか接続できない
- WSL2 が WSL 内の `127.0.0.1` を Windows の `localhost` に中継している

### コマンドで見る（psql）

```bash
docker compose exec db psql -U tech_digest                       # 対話モード（\q で終了）
docker compose exec db psql -U tech_digest -c "select source, count(*) from articles group by source"
```

コンテナの中からの接続なのでパスワードは不要。

### SQLite（uv で直接実行したとき）

A5:SQL で SQLite のデータベースとして次のファイルを開く。

```
\\wsl.localhost\Ubuntu-24.04\home\amneru\projects\tech-digest\data\tech-digest.db
```

### テーブル

`articles` テーブル 1 つだけ。

| 列 | 内容 |
|---|---|
| `source` | 取得元（`qiita` / `zenn` / `hatena`） |
| `url` | 記事の URL（`source` と合わせて主キー） |
| `title` / `author` / `tags` | タイトル・著者・タグ（タグは JSON 配列の文字列） |
| `score` | いいね数・ブックマーク数（Zenn は空） |
| `published_at` | 投稿日時（UTC の ISO 8601 文字列） |
| `digest_date` | 初めてダイジェストに載った日（JST、`YYYY-MM-DD`） |
| `updated_at` | 最後に取得した日時（UTC） |

## 4. 設定（.env）

`.env` に書いた値は、compose が自動で読む。**`.env` はコミットしない**（`.gitignore` 済み）。

| 変数 | 必須 | 内容 |
|---|---|---|
| `POSTGRES_PASSWORD` | compose では必須 | PostgreSQL のパスワード |
| `QIITA_TOKEN` | 任意 | Qiita のアクセストークン（なしだと 60 リクエスト/時） |
| `DB_PORT` | 任意 | 手元に公開するポート（既定 5432） |

`.env` がないときの作り方（既にあれば何もしない）:

```bash
[ -e .env ] || { cp .env.example .env && sed -i "s/^POSTGRES_PASSWORD=$/POSTGRES_PASSWORD=$(openssl rand -hex 16)/" .env; }
```

> **注意**: `POSTGRES_PASSWORD` が使われるのは **DB のボリュームを初めて作るときだけ**。
> あとから `.env` だけ変えても DB 側は古いパスワードのまま。変えるときは DB 側も合わせる:
> `docker compose up -d --wait db && docker compose exec db psql -U tech_digest -c "ALTER USER tech_digest PASSWORD '新しいパスワード'"`

アプリが読む環境変数の一覧は [README](../README.md#環境変数) を参照。

## 5. 開発のチェック

PR を出す前にすべて通す。GitHub Actions でも同じものが動く（Phase 2 以降）。

```bash
uv run ruff check --fix && uv run ruff format   # lint と整形
uv run pyright                                  # 型チェック
uv run pytest                                   # テスト（PostgreSQL の分は skip される）
```

PostgreSQL のテストも手元で動かすとき:

```bash
docker run -d --rm --name tech-digest-testdb -e POSTGRES_PASSWORD=test -p 127.0.0.1:55432:5432 postgres:18.6-trixie
TEST_DATABASE_URL=postgresql://postgres:test@127.0.0.1:55432/postgres uv run pytest
docker stop tech-digest-testdb   # --rm なので止めると消える
```

## 6. Git と PR の流れ

main は保護されていて、**直接 push できない**。変更は必ず PR を通す。

```bash
git switch main && git pull                 # main を最新にする
git switch -c feat/<内容>                   # 作業用のブランチを作る
# ... 編集してコミット ...
git push -u origin feat/<内容>
gh pr create                                # PR を作る
gh pr merge <番号> --squash --delete-branch # 確認してマージ（ブラウザでも可）
git switch main && git pull                 # マージ後に main を最新にする
git branch -d feat/<内容>                   # 手元のブランチを消す
```

| よく使う | コマンド |
|---|---|
| PR の一覧 | `gh pr list` |
| PR の CI の結果 | `gh pr checks <番号>` |
| PR をブラウザで開く | `gh pr view <番号> --web` |

## 7. データを消してやり直す

**元に戻せない操作。** 中身は記事を取得し直せば再現できる。

| 消したいもの | コマンド |
|---|---|
| compose の PostgreSQL | `docker compose down -v`（ボリュームごと削除） |
| uv で作った SQLite | `rm data/tech-digest.db` |
| ダイジェスト | `rm digests/*.md` |

## 8. 困ったとき

| 症状 | 原因と対処 |
|---|---|
| `required variable POSTGRES_PASSWORD is missing a value` | `.env` がない、またはパスワードが空。[4. 設定](#4-設定env) の手順で作る |
| `password authentication failed for user "tech_digest"` | `.env` のパスワードと DB 側が違う。[4. 設定](#4-設定env) の「注意」の手順で DB 側を合わせる |
| A5:SQL で接続できない | db が止まっている → `docker compose ps` で確認し `docker compose up -d db` |
| `port is already allocated`（5432） | ほかのソフトが 5432 を使っている → `.env` に `DB_PORT=15432` と書き、A5:SQL のポートも合わせる |
| `digests/` に書き込めない（Permission denied） | `digests/` を Docker に作らせると root の持ち物になる → `sudo chown -R $USER: digests` |
| コードを変えたのに compose の結果が変わらない | イメージが古い → `docker compose build app` |
| `uv sync --locked` でビルドが失敗する | `pyproject.toml` を変えたのに `uv.lock` が古い → `uv lock` して両方コミット |
| エディタに「インポートを解決できません」 | pyright が古い設定のまま → VS Code で Claude Code のセッションを開き直す |
| `git push` が拒否される（main） | main は保護されている。ブランチを作って PR を出す |
