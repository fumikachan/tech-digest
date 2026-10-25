# syntax=docker/dockerfile:1

# ベースイメージはパッチバージョンまで固定する（いつビルドしても同じ Python になるように）。
# 2 つのステージで同じものを使う。ARG にまとめると Dependabot が読めず更新されないので、直接書く

# ---- ビルド用ステージ: 依存とアプリを /app/.venv にインストールする ----
FROM python:3.15.0-slim-trixie AS builder

COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /bin/uv

# UV_COMPILE_BYTECODE: 起動を速くするため .pyc を事前に作る
# UV_LINK_MODE: キャッシュはマウントなので、ハードリンクではなくコピーで入れる
# UV_PYTHON_DOWNLOADS: イメージの Python を使い、別の Python をダウンロードしない
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# 先に依存だけを入れる。ソースを変えてもこのレイヤーはキャッシュが効く
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# アプリ本体を入れる。--no-editable で .venv の中にコピーし、実行時にソースを不要にする
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# ---- 実行用ステージ: .venv だけを持ってくる（uv やビルドの途中のファイルは入れない） ----
FROM python:3.15.0-slim-trixie

# WSL の最初のユーザーと同じ UID にして、ホストのディレクトリをマウントしても書き込めるようにする
ARG APP_UID=1000
RUN groupadd --gid ${APP_UID} app \
    && useradd --uid ${APP_UID} --gid app --no-create-home --shell /usr/sbin/nologin app \
    && mkdir -p /data /output \
    && chown app:app /data /output

COPY --from=builder --chown=app:app /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    TECH_DIGEST_DB_PATH=/data/tech-digest.db \
    TECH_DIGEST_OUTPUT_DIR=/output

# root で動かさない（コンテナを破られたときの被害を小さくする）
USER app
WORKDIR /app

# DB とダイジェストはコンテナの外に置く（コンテナを消しても残るように）
VOLUME ["/data", "/output"]

ENTRYPOINT ["tech-digest"]
CMD ["run"]
