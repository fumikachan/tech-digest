"""Qiita API v2 から前日の新着記事を取得する。https://qiita.com/api/v2/docs"""

import logging
from datetime import date, datetime, timedelta

import httpx

from tech_digest.config import Settings
from tech_digest.models import Article

logger = logging.getLogger(__name__)

API_URL = "https://qiita.com/api/v2/items"
PER_PAGE = 100  # API の上限
MAX_PAGES = 10  # トークンなしのレート制限は 60 回/時なので、1 回の実行で使いすぎない


def fetch(client: httpx.Client, digest_date: date, settings: Settings) -> list[Article]:
    target = digest_date - timedelta(days=1)
    query = f"created:>={target.isoformat()} created:<{digest_date.isoformat()}"
    headers = {"Authorization": f"Bearer {settings.qiita_token}"} if settings.qiita_token else {}

    articles: list[Article] = []
    for page in range(1, MAX_PAGES + 1):
        res = client.get(
            API_URL,
            params={"query": query, "page": page, "per_page": PER_PAGE},
            headers=headers,
        )
        res.raise_for_status()
        items = res.json()
        articles.extend(parse(items))
        if len(items) < PER_PAGE:
            break
    else:
        logger.warning("Qiita: %d ページで打ち切りました（記事が多すぎます）", MAX_PAGES)
    return articles


def parse(items: list[dict]) -> list[Article]:
    return [
        Article(
            source="qiita",
            url=item["url"],
            title=item["title"],
            published_at=datetime.fromisoformat(item["created_at"]),
            author=item["user"]["id"],
            score=item["likes_count"],
            tags=tuple(tag["name"] for tag in item["tags"]),
        )
        for item in items
    ]
