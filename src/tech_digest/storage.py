"""記事を DB に保存する。DATABASE_URL があれば PostgreSQL、なければ SQLite を使う。

digest_date は「その記事が初めて載ったダイジェストの日付」。
同じ記事を後日また取得しても digest_date は変えないので、
トレンドに何日も残る記事が毎日重複して載らない。

SQL は両方の DB で共通のものだけを使う（ON CONFLICT と NULLS LAST はどちらも対応している）。
違いはパラメータの書き方だけ。SQL は SQLite 式の :name で書き、
PostgreSQL では %(name)s に変換する。
"""

import json
import re
import sqlite3
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal, LiteralString, cast

import psycopg
from psycopg.rows import DictRow, dict_row

from tech_digest.config import Settings
from tech_digest.models import Article

# 日時やタグは両方の DB で同じように扱えるよう TEXT で持つ
# （ISO 8601 の文字列は辞書順に並べると日時順になる）
SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    source       TEXT NOT NULL,
    url          TEXT NOT NULL,
    title        TEXT NOT NULL,
    author       TEXT,
    published_at TEXT NOT NULL,  -- ISO 8601（UTC）
    score        INTEGER,
    tags         TEXT NOT NULL,  -- JSON 配列
    digest_date  TEXT NOT NULL,  -- YYYY-MM-DD（JST）
    updated_at   TEXT NOT NULL,
    PRIMARY KEY (source, url)
);
CREATE INDEX IF NOT EXISTS idx_articles_digest_date ON articles (digest_date);
"""

UPSERT = """
INSERT INTO articles
    (source, url, title, author, published_at, score, tags, digest_date, updated_at)
VALUES
    (:source, :url, :title, :author, :published_at, :score, :tags, :digest_date, :updated_at)
ON CONFLICT (source, url) DO UPDATE SET
    title = excluded.title,
    author = excluded.author,
    score = excluded.score,
    tags = excluded.tags,
    updated_at = excluded.updated_at
"""

SELECT_BY_DIGEST_DATE = """
SELECT * FROM articles
WHERE digest_date = :digest_date
ORDER BY score DESC NULLS LAST, published_at DESC
"""


class Database:
    """SQLite と PostgreSQL の接続を同じ使い方にする薄いラッパー。"""

    def __init__(
        self,
        conn: sqlite3.Connection | psycopg.Connection[DictRow],
        kind: Literal["sqlite", "postgres"],
    ) -> None:
        self.conn = conn
        self.kind = kind

    def execute(self, query: LiteralString, params: Mapping[str, Any] | None = None) -> list[Any]:
        cur = self.conn.cursor()
        cur.execute(self._sql(query), params or {})
        return cur.fetchall() if cur.description else []

    def executemany(self, query: LiteralString, rows: Sequence[Mapping[str, Any]]) -> None:
        self.conn.cursor().executemany(self._sql(query), rows)

    def commit(self) -> None:
        self.conn.commit()

    def rollback(self) -> None:
        self.conn.rollback()

    def close(self) -> None:
        self.conn.close()

    def _sql(self, query: LiteralString) -> LiteralString:
        if self.kind == "sqlite":
            return query
        # psycopg は SQL インジェクション対策として LiteralString
        # （コードに直接書いた文字列）を求める。
        # 変換元はモジュール定数の SQL で、外部からの値は含まないので cast してよい
        return cast(LiteralString, re.sub(r":(\w+)", r"%(\1)s", query))


def connect(settings: Settings) -> Database:
    if settings.database_url:
        return connect_postgres(settings.database_url)
    return connect_sqlite(settings.db_path)


def connect_sqlite(path: Path) -> Database:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return _init(Database(conn, "sqlite"))


def connect_postgres(url: str) -> Database:
    # 行を dict で受け取る（SQLite の Row と同じ使い方）。
    # 型に DictRow を明示しないと、型チェッカーは行を tuple として扱う
    conn = psycopg.Connection[DictRow].connect(url, row_factory=dict_row)
    return _init(Database(conn, "postgres"))


def _init(db: Database) -> Database:
    for statement in SCHEMA.split(";"):
        if statement.strip():
            db.execute(statement)
    db.commit()
    return db


def save(db: Database, articles: Iterable[Article], digest_date: date, now: datetime) -> None:
    rows = [
        {
            "source": a.source,
            "url": a.url,
            "title": a.title,
            "author": a.author,
            "published_at": a.published_at.astimezone(UTC).isoformat(),
            "score": a.score,
            "tags": json.dumps(a.tags, ensure_ascii=False),
            "digest_date": digest_date.isoformat(),
            "updated_at": now.astimezone(UTC).isoformat(),
        }
        for a in articles
    ]
    if not rows:
        return
    try:
        db.executemany(UPSERT, rows)
        db.commit()
    except Exception:
        db.rollback()
        raise


def load(db: Database, digest_date: date) -> list[Article]:
    rows = db.execute(SELECT_BY_DIGEST_DATE, {"digest_date": digest_date.isoformat()})
    return [
        Article(
            source=row["source"],
            url=row["url"],
            title=row["title"],
            published_at=datetime.fromisoformat(row["published_at"]),
            author=row["author"],
            score=row["score"],
            tags=tuple(json.loads(row["tags"])),
        )
        for row in rows
    ]
