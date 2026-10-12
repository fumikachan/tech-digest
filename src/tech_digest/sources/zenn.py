"""Zenn のトレンド記事を RSS から取得する。"""

from datetime import date

import httpx

from tech_digest.config import Settings
from tech_digest.models import Article
from tech_digest.sources._feed import fetch_feed, parse_feed

FEED_URL = "https://zenn.dev/feed"


def fetch(client: httpx.Client, digest_date: date, settings: Settings) -> list[Article]:
    # フィードは「今のトレンド」なので日付は使わない
    return parse(fetch_feed(client, FEED_URL))


def parse(content: bytes) -> list[Article]:
    return parse_feed(content, "zenn")
