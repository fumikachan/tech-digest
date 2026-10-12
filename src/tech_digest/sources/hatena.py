"""はてなブックマークのテクノロジー人気エントリーを RSS から取得する。"""

from dataclasses import replace
from datetime import date

import httpx

from tech_digest.config import Settings
from tech_digest.models import Article
from tech_digest.sources._feed import fetch_feed, parse_feed

FEED_URL = "https://b.hatena.ne.jp/hotentry/it.rss"
# カテゴリ名と「あとで読む」はほぼ全記事に付いていて、内容を表さないので除く
IGNORED_TAGS = {"テクノロジー", "あとで読む"}


def fetch(client: httpx.Client, digest_date: date, settings: Settings) -> list[Article]:
    # フィードは「今の人気エントリー」なので日付は使わない
    return parse(fetch_feed(client, FEED_URL))


def parse(content: bytes) -> list[Article]:
    return [
        replace(a, tags=tuple(t for t in a.tags if t not in IGNORED_TAGS))
        for a in parse_feed(content, "hatena", score_key="hatena_bookmarkcount")
    ]
