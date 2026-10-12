import os
import re
from datetime import UTC, date, datetime

import pytest

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


@pytest.fixture(params=["sqlite", "postgres"])
def db(request, tmp_path):
    """同じテストを SQLite と PostgreSQL の両方で実行する。

    PostgreSQL は TEST_DATABASE_URL があるときだけ（なければ skip）。中のデータは毎回消す。
    CI（GitHub Actions は CI=true を設定する）では skip せず失敗させる。
    設定漏れで PostgreSQL のテストが黙って省略され、「成功」に見えるのを防ぐため。
    """
    if request.param == "sqlite":
        database = storage.connect_sqlite(tmp_path / "test.db")
    else:
        url = os.environ.get("TEST_DATABASE_URL")
        if not url:
            if os.environ.get("CI"):
                pytest.fail("CI では TEST_DATABASE_URL が必要です")
            pytest.skip("TEST_DATABASE_URL が未設定のため PostgreSQL のテストを省略")
        database = storage.connect_postgres(url)
        database.execute("TRUNCATE articles")
        database.commit()
    yield database
    database.close()


def test_save_is_idempotent_and_keeps_first_digest_date(db):
    storage.save(db, [article("https://a", score=1)], DAY1, NOW)
    # 翌日も同じ記事がトレンドに残っていた（スコアは増えた）
    storage.save(db, [article("https://a", score=9), article("https://b", score=2)], DAY2, NOW)

    day1 = storage.load(db, DAY1)
    day2 = storage.load(db, DAY2)
    assert [a.url for a in day1] == ["https://a"]
    assert day1[0].score == 9  # スコアは最新に更新される
    assert [a.url for a in day2] == ["https://b"]  # 前日に載った記事は重複しない


def test_load_orders_by_score_with_nulls_last(db):
    articles = [article("https://low", 1), article("https://none"), article("https://high", 50)]
    storage.save(db, articles, DAY1, NOW)
    assert [a.url for a in storage.load(db, DAY1)] == [
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


def test_render_escapes_untrusted_text_and_urls():
    articles = [
        Article(
            source="hatena",
            url="https://evil.example/x) [偽](https://phish.example",
            title="<img src=x onerror=alert(1)>\n# 見出し *強調*",
            published_at=datetime(2026, 10, 11, tzinfo=UTC),
            author="<b>bob</b>",
            score=1,
            tags=("<script>",),
        ),
        Article(
            source="hatena",
            url="javascript:alert(1)",
            title="スクリプト URL",
            published_at=datetime(2026, 10, 11, tzinfo=UTC),
            score=0,
        ),
    ]
    md = render_markdown(DAY1, articles, SOURCES, limit=10)

    assert not re.search(r"(?<!\\)<", md)  # エスケープされていない < がない（HTML タグにならない）
    assert r"\<img src=x onerror=alert(1)\> # 見出し \*強調\*" in md  # 改行もつぶれる
    assert r"\<b\>bob\</b\> · \<script\>" in md
    # ) や空白がエンコードされ、リンクを途中で閉じて別のリンクを差し込めない
    assert "(https://evil.example/x%29%20[%E5%81%BD]%28https://phish.example)" in md
    assert "javascript:" not in md
    assert "2. スクリプト URL — 0 users" in md  # 危険な URL はリンクにしない
