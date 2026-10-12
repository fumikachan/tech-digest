"""RSS / Atom フィードを使う取得元の共通処理。"""

import calendar
from datetime import UTC, datetime

import feedparser
import httpx

from tech_digest.models import Article


def fetch_feed(client: httpx.Client, url: str) -> bytes:
    res = client.get(url)
    res.raise_for_status()
    return res.content


def parse_feed(content: bytes, source: str, score_key: str | None = None) -> list[Article]:
    feed = feedparser.parse(content)
    if feed.bozo and not feed.entries:
        raise ValueError(f"{source}: フィードを解析できませんでした: {feed.bozo_exception}")

    articles = []
    for entry in feed.entries:
        published = entry.get("published_parsed") or entry.get("updated_parsed")
        if not published:
            continue
        score = entry.get(score_key) if score_key else None
        articles.append(
            Article(
                source=source,
                url=entry.link,
                title=entry.title,
                published_at=datetime.fromtimestamp(calendar.timegm(published), UTC),
                author=entry.get("author"),
                score=int(score) if score is not None else None,
                tags=tuple(tag.term for tag in entry.get("tags", [])),
            )
        )
    return articles
