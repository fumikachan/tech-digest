"""記事を SQLite に保存する。

digest_date は「その記事が初めて載ったダイジェストの日付」。
同じ記事を後日また取得しても digest_date は変えないので、
トレンドに何日も残る記事が毎日重複して載らない。
"""

import json
import sqlite3
from collections.abc import Iterable
from datetime import UTC, date, datetime
from pathlib import Path

from tech_digest.models import Article

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


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def save(
    conn: sqlite3.Connection, articles: Iterable[Article], digest_date: date, now: datetime
) -> None:
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
    with conn:
        conn.executemany(UPSERT, rows)


def load(conn: sqlite3.Connection, digest_date: date) -> list[Article]:
    rows = conn.execute(
        """
        SELECT * FROM articles
        WHERE digest_date = ?
        ORDER BY score DESC NULLS LAST, published_at DESC
        """,
        (digest_date.isoformat(),),
    )
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
