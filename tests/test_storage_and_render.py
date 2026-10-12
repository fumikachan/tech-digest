from datetime import UTC, date, datetime

from tech_digest import storage
from tech_digest.models import Article
from tech_digest.render import render_markdown
from tech_digest.sources import SOURCES

NOW = datetime(2026, 10, 12, tzinfo=UTC)
DAY1 = date(2026, 10, 12)
DAY2 = date(2026, 10, 13)


def article(url: str, score: int | None = None, source: str = "qiita", **kw) -> Article:
    return Article(
        source=source,
        url=url,
        title=kw.get("title", url),
        published_at=datetime(2026, 10, 11, tzinfo=UTC),
        score=score,
        tags=kw.get("tags", ()),
    )


def test_save_is_idempotent_and_keeps_first_digest_date(tmp_path):
    conn = storage.connect(tmp_path / "test.db")
    storage.save(conn, [article("https://a", score=1)], DAY1, NOW)
    # 翌日も同じ記事がトレンドに残っていた（スコアは増えた）
    storage.save(conn, [article("https://a", score=9), article("https://b", score=2)], DAY2, NOW)

    day1 = storage.load(conn, DAY1)
    day2 = storage.load(conn, DAY2)
    assert [a.url for a in day1] == ["https://a"]
    assert day1[0].score == 9  # スコアは最新に更新される
    assert [a.url for a in day2] == ["https://b"]  # 前日に載った記事は重複しない


def test_load_orders_by_score_with_nulls_last(tmp_path):
    conn = storage.connect(tmp_path / "test.db")
    articles = [article("https://low", 1), article("https://none"), article("https://high", 50)]
    storage.save(conn, articles, DAY1, NOW)
    assert [a.url for a in storage.load(conn, DAY1)] == [
        "https://high",
        "https://low",
        "https://none",
    ]


def test_render_markdown_groups_by_source_and_limits():
    articles = [
        article("https://q1", 30, title="Docker [入門]", tags=("Docker", "Linux", "WSL", "x")),
        article("https://q2", 10),
        article("https://q3", 5),
        article("https://h1", 200, source="hatena"),
    ]
    md = render_markdown(DAY1, articles, SOURCES, limit=2)

    assert md.startswith("# 技術ブログダイジェスト 2026-10-12")
    assert r"1. [Docker \[入門\]](https://q1) — 30 いいね · Docker, Linux, WSL" in md
    assert "https://q3" not in md
    assert "ほか 1 件" in md
    assert "## Zenn（トレンド）\n\n新しい記事はありませんでした。" in md
    assert "1. [https://h1](https://h1) — 200 users" in md
