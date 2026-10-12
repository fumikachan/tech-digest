import json
from datetime import UTC, date, datetime, timedelta

from tech_digest import site
from tech_digest.archive import DailyDigest, export_day, load_days
from tech_digest.models import Article

DAY = date(2026, 10, 12)


def article(url: str, source: str = "qiita", score: int | None = 1, **kw) -> Article:
    return Article(
        source=source,
        url=url,
        title=kw.get("title", url),
        published_at=datetime(2026, 10, 11, 6, 13, tzinfo=UTC),
        author=kw.get("author"),
        score=score,
        tags=kw.get("tags", ()),
    )


def test_export_and_load_round_trip(tmp_path):
    digest = DailyDigest(DAY, [article("https://a", tags=("Python",), author="bob")])
    export_day(digest, tmp_path)
    export_day(DailyDigest(DAY - timedelta(days=1), []), tmp_path)

    days = load_days(tmp_path)
    assert [d.date for d in days] == [DAY, DAY - timedelta(days=1)]  # 新しい順
    assert days[0].articles == digest.articles


def test_build_site_writes_pages(tmp_path):
    days = [
        DailyDigest(DAY, [article("https://new", title="新しい記事")]),
        DailyDigest(DAY - timedelta(days=1), [article("https://old", source="hatena")]),
    ]
    site.build_site(days, tmp_path)

    index = (tmp_path / "index.html").read_text()
    assert "新しい記事" in index  # トップは最新の日
    assert (tmp_path / "days" / "2026-10-12.html").exists()
    assert (tmp_path / "days" / "2026-10-11.html").exists()
    assert 'href="days/2026-10-11.html"' in index  # 前の日へのリンク
    assert (tmp_path / "assets" / "app.js").exists()
    assert (tmp_path / ".nojekyll").exists()
    assert "Content-Security-Policy" in index

    archive = (tmp_path / "archive.html").read_text()
    assert 'href="days/2026-10-12.html"' in archive


def test_build_site_escapes_untrusted_data(tmp_path):
    evil = article(
        "javascript:alert(1)",
        title='<script>alert("x")</script>',
        author="<b>bob</b>",
        tags=('"><img src=x>',),
    )
    site.build_site([DailyDigest(DAY, [evil, article("https://ok")])], tmp_path)
    html = (tmp_path / "index.html").read_text()

    assert "<script>alert" not in html
    assert "&lt;script&gt;alert(&#34;x&#34;)&lt;/script&gt;" in html
    assert "<b>bob</b>" not in html
    assert "<img src=x>" not in html
    assert "javascript:" not in html  # 危険な URL はリンクにしない

    index = json.loads((tmp_path / "search.json").read_text())
    assert [a["u"] for a in index] == ["https://ok"]  # 検索の索引にも入れない


def test_search_index_covers_recent_days_only(tmp_path):
    days = [
        DailyDigest(DAY - timedelta(days=i), [article(f"https://example.com/{i}")])
        for i in range(site.SEARCH_DAYS + 5)
    ]
    site.build_site(days, tmp_path)
    index = json.loads((tmp_path / "search.json").read_text())
    assert len(index) == site.SEARCH_DAYS
    assert index[0] == {
        "d": "2026-10-12",
        "s": "qiita",
        "t": "https://example.com/0",
        "u": "https://example.com/0",
        "c": 1,
        "g": [],
    }


def test_build_site_without_days(tmp_path):
    site.build_site([], tmp_path)
    assert "まだダイジェストがありません" in (tmp_path / "index.html").read_text()
