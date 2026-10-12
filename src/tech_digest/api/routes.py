"""API の各エンドポイントの処理。

ROUTES のキーは API Gateway のルートキー（"メソッド パス"）と同じ形にする。
AWS ではこのキーと同じルートを API Gateway に作るので、ここにないパスは Lambda まで届かない。
"""

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from tech_digest.models import Article
from tech_digest.render import safe_url
from tech_digest.sources import SOURCES
from tech_digest.storage.dynamodb import DynamoStore

SEARCH_DAYS = (
    30  # 検索の対象にする日数（増やすと 1 回の検索で読む量が増える。API_DESIGN.md の見積もり）
)
MAX_RESULTS = 100
MAX_QUERY_LENGTH = 100
SORTS = ("score", "date")

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True)
class Request:
    path_params: Mapping[str, str] = field(default_factory=dict)
    query: Mapping[str, str] = field(default_factory=dict)


class ApiError(Exception):
    """利用者に見せてよいエラー（400 や 404）。メッセージはそのままレスポンスに入る。"""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def get_sources(store: DynamoStore, request: Request) -> dict[str, Any]:
    return {
        "sources": [
            {
                "name": s.name,
                "title": s.title,
                "description": s.description,
                "score_unit": s.score_unit,
            }
            for s in SOURCES
        ]
    }


def get_days(store: DynamoStore, request: Request) -> dict[str, Any]:
    return {
        "days": [
            # 記事のなかった取得元も 0 として返す（画面で表を作りやすいように）
            {
                "date": d.date.isoformat(),
                "counts": {s.name: d.counts.get(s.name, 0) for s in SOURCES},
            }
            for d in store.list_days()
        ]
    }


def get_day(store: DynamoStore, request: Request) -> dict[str, Any]:
    digest_date = _parse_date(request.path_params.get("date", ""))
    if store.get_day(digest_date) is None:
        raise ApiError(404, f"{digest_date} のダイジェストはありません")
    return {
        "date": digest_date.isoformat(),
        "articles": [_article(a) for a in store.load(digest_date)],
    }


def search(store: DynamoStore, request: Request) -> dict[str, Any]:
    """直近 SEARCH_DAYS 日の記事から、タイトルとタグにすべての語を含むものを返す。"""
    q = request.query.get("q", "").strip()
    if not q:
        raise ApiError(400, "q（検索語）を指定してください")
    if len(q) > MAX_QUERY_LENGTH:
        raise ApiError(400, f"q は {MAX_QUERY_LENGTH} 文字以内にしてください")
    source = request.query.get("source") or None
    if source is not None and source not in {s.name for s in SOURCES}:
        raise ApiError(400, f"source が不正です: {source}")
    sort = request.query.get("sort") or "score"
    if sort not in SORTS:
        raise ApiError(400, f"sort は {' / '.join(SORTS)} のどれかにしてください")

    terms = q.lower().split()
    hits: list[tuple[date, Article]] = []
    for day in store.list_days()[:SEARCH_DAYS]:
        for a in store.load(day.date):
            if source and a.source != source:
                continue
            text = " ".join((a.title, *a.tags)).lower()
            if all(term in text for term in terms):
                hits.append((day.date, a))

    def by_score(hit: tuple[date, Article]) -> tuple[bool, int, date]:
        d, a = hit
        return (a.score is not None, a.score or 0, d)

    def by_date(hit: tuple[date, Article]) -> tuple[date, bool, int]:
        d, a = hit
        return (d, a.score is not None, a.score or 0)

    hits.sort(key=by_score if sort == "score" else by_date, reverse=True)
    return {
        "total": len(hits),
        "articles": [{"date": d.isoformat(), **_article(a)} for d, a in hits[:MAX_RESULTS]],
    }


Handler = Callable[[DynamoStore, Request], dict[str, Any]]

ROUTES: dict[str, Handler] = {
    "GET /sources": get_sources,
    "GET /days": get_days,
    "GET /days/{date}": get_day,
    "GET /search": search,
}


def _parse_date(value: str) -> date:
    # date.fromisoformat は 20261012 なども受け付けるので、形を先に確かめる
    if _DATE.fullmatch(value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise ApiError(400, "日付は YYYY-MM-DD の形で指定してください")


def _article(a: Article) -> dict[str, Any]:
    return {
        "source": a.source,
        "url": safe_url(a.url),  # http(s) 以外は None（画面ではリンクにしない）
        "title": a.title,
        "author": a.author,
        "score": a.score,
        "tags": list(a.tags),
        "published_at": a.published_at.isoformat(),
    }
