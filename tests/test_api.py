"""API のテスト。API Gateway のイベント（ペイロード形式 2.0）を作り、Lambda のハンドラーに渡す。"""

import json
from datetime import UTC, date, datetime

import pytest

from tech_digest.api import lambda_handler, routes
from tech_digest.api.devserver import to_event
from tech_digest.models import Article

NOW = datetime(2026, 10, 13, tzinfo=UTC)
DAY1 = date(2026, 10, 12)
DAY2 = date(2026, 10, 13)


def article(url: str, source: str = "qiita", **kw) -> Article:
    return Article(
        source=source,
        url=url,
        title=kw.get("title", url),
        published_at=datetime(2026, 10, 11, tzinfo=UTC),
        score=kw.get("score"),
        tags=kw.get("tags", ()),
    )


@pytest.fixture
def store(dynamo_store, monkeypatch):
    """moto の DynamoDB に 2 日分の記事を入れ、ハンドラーがそれを使うようにする。"""
    dynamo_store.save(
        [
            article("https://q1", title="Docker 入門", score=10, tags=("Docker",)),
            article("https://q2", title="AWS Lambda の基本", score=30, tags=("AWS", "Python")),
            article("javascript:alert(1)", title="危険な URL", score=1),
            article("https://h1", source="hatena", title="aws の話", score=200),
        ],
        DAY1,
        NOW,
    )
    dynamo_store.save([article("https://q3", title="Terraform と AWS", score=5)], DAY2, NOW)
    monkeypatch.setattr(lambda_handler, "_store", dynamo_store)
    return dynamo_store


def call(target: str) -> tuple[int, dict]:
    event = to_event("GET", target)
    assert event is not None, f"ルートがありません: {target}"
    response = lambda_handler.handler(event, None)
    return response["statusCode"], json.loads(response["body"])


def test_sources_are_listed_in_order(store):
    status, body = call("/sources")
    assert status == 200
    assert [s["name"] for s in body["sources"]] == ["qiita", "zenn", "hatena"]
    assert body["sources"][2]["score_unit"] == "users"


def test_days_are_newest_first_with_zero_counts(store):
    status, body = call("/days")
    assert status == 200
    assert body["days"] == [
        {"date": "2026-10-13", "counts": {"qiita": 1, "zenn": 0, "hatena": 0}},
        {"date": "2026-10-12", "counts": {"qiita": 3, "zenn": 0, "hatena": 1}},
    ]


def test_day_returns_articles_by_score_with_safe_urls(store):
    status, body = call("/days/2026-10-12")
    assert status == 200
    assert body["date"] == "2026-10-12"
    assert [a["title"] for a in body["articles"]] == [
        "aws の話",
        "AWS Lambda の基本",
        "Docker 入門",
        "危険な URL",
    ]
    assert body["articles"][1]["tags"] == ["AWS", "Python"]
    assert body["articles"][3]["url"] is None  # javascript: はリンクにさせない


@pytest.mark.parametrize(
    ("target", "status"),
    [
        ("/days/2026-01-01", 404),  # ダイジェストのない日
        ("/days/20261012", 400),  # date.fromisoformat は通すが、形が違う
        ("/days/2026-13-01", 400),  # 存在しない日付
    ],
)
def test_day_errors(store, target, status):
    assert call(target)[0] == status


def test_search_matches_all_terms_in_title_and_tags(store):
    status, body = call("/search?q=aws")
    assert status == 200
    assert body["total"] == 3
    # 大文字小文字を区別しない。スコアの高い順
    assert [a["title"] for a in body["articles"]] == [
        "aws の話",
        "AWS Lambda の基本",
        "Terraform と AWS",
    ]
    assert body["articles"][0]["date"] == "2026-10-12"

    # 空白区切りの語はすべて含むものだけ（Python はタグにある）
    assert [a["title"] for a in call("/search?q=AWS+python")[1]["articles"]] == [
        "AWS Lambda の基本"
    ]


def test_search_filters_and_sorts(store):
    body = call("/search?q=aws&source=qiita&sort=date")[1]
    assert [a["title"] for a in body["articles"]] == ["Terraform と AWS", "AWS Lambda の基本"]


def test_search_covers_only_recent_days(store, monkeypatch):
    monkeypatch.setattr(routes, "SEARCH_DAYS", 1)
    assert [a["title"] for a in call("/search?q=aws")[1]["articles"]] == ["Terraform と AWS"]


@pytest.mark.parametrize(
    "target",
    [
        "/search",
        "/search?q=+",
        "/search?q=" + "a" * 101,
        "/search?q=a&source=x",
        "/search?q=a&sort=x",
    ],
)
def test_search_rejects_bad_parameters(store, target):
    status, body = call(target)
    assert status == 400
    assert body["message"]


def test_unknown_route_is_404():
    assert to_event("GET", "/wp-admin") is None  # API Gateway なら Lambda まで届かない
    response = lambda_handler.handler({"routeKey": "GET /wp-admin"}, None)
    assert response["statusCode"] == 404


def test_internal_error_hides_details(store, monkeypatch):
    def broken():
        raise RuntimeError("接続先の秘密の情報")

    monkeypatch.setattr(store, "list_days", broken)
    event = to_event("GET", "/days")
    assert event is not None
    response = lambda_handler.handler(event, None)
    assert response["statusCode"] == 500
    assert "秘密" not in response["body"]
    assert response["headers"]["cache-control"] == "no-store"


def test_to_event_matches_api_gateway_shape():
    event = to_event("GET", "/days/2026-10-12?x=1&x=2")
    assert event is not None
    assert event["routeKey"] == "GET /days/{date}"
    assert event["pathParameters"] == {"date": "2026-10-12"}
    assert event["queryStringParameters"] == {"x": "1,2"}  # 同じ名前はカンマでつなぐ
    assert to_event("POST", "/days") is None
