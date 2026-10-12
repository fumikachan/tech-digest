from datetime import UTC, date, datetime

import httpx

from tech_digest.config import Settings
from tech_digest.sources import hatena, qiita, zenn

ZENN_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0"><channel><title>Zenn</title>
<item>
  <title><![CDATA[Docker \xe5\x85\xa5\xe9\x96\x80]]></title>
  <link>https://zenn.dev/alice/articles/docker</link>
  <pubDate>Sun, 11 Oct 2026 14:28:19 GMT</pubDate>
  <dc:creator>Alice</dc:creator>
</item>
</channel></rss>"""

HATENA_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" xmlns="http://purl.org/rss/1.0/"
 xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:hatena="http://www.hatena.ne.jp/info/xmlns#">
<channel rdf:about="https://b.hatena.ne.jp/hotentry/it"><title>hotentry</title></channel>
<item rdf:about="https://example.com/terraform">
  <title>Terraform Tips</title>
  <link>https://example.com/terraform</link>
  <dc:date>2026-10-11T12:13:54Z</dc:date>
  <dc:subject>\xe3\x83\x86\xe3\x82\xaf\xe3\x83\x8e\xe3\x83\xad\xe3\x82\xb8\xe3\x83\xbc</dc:subject>
  <dc:subject>infra</dc:subject>
  <dc:subject>aws</dc:subject>
  <hatena:bookmarkcount>223</hatena:bookmarkcount>
</item>
</rdf:RDF>"""


def qiita_item(n: int, likes: int = 0) -> dict:
    return {
        "url": f"https://qiita.com/bob/items/{n}",
        "title": f"記事 {n}",
        "created_at": "2026-10-11T15:13:37+09:00",
        "user": {"id": "bob"},
        "likes_count": likes,
        "tags": [{"name": "Python"}, {"name": "uv"}],
    }


def test_qiita_parse():
    [article] = qiita.parse([qiita_item(1, likes=25)])
    assert article.source == "qiita"
    assert article.url == "https://qiita.com/bob/items/1"
    assert article.author == "bob"
    assert article.score == 25
    assert article.tags == ("Python", "uv")
    assert article.published_at == datetime(2026, 10, 11, 6, 13, 37, tzinfo=UTC)


def test_qiita_fetch_queries_previous_day_and_paginates():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        page = int(request.url.params["page"])
        count = qiita.PER_PAGE if page == 1 else 5
        return httpx.Response(200, json=[qiita_item(page * 1000 + i) for i in range(count)])

    settings = Settings(db_path=None, output_dir=None, qiita_token="secret")  # type: ignore[arg-type]
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        articles = qiita.fetch(client, date(2026, 10, 12), settings)

    assert len(articles) == qiita.PER_PAGE + 5
    assert len(requests) == 2  # 2 ページ目が 100 件未満なので終了
    assert requests[0].url.params["query"] == "created:>=2026-10-11 created:<2026-10-12"
    assert requests[0].headers["Authorization"] == "Bearer secret"


def test_zenn_parse():
    [article] = zenn.parse(ZENN_FEED)
    assert article.source == "zenn"
    assert article.title == "Docker 入門"
    assert article.author == "Alice"
    assert article.score is None
    assert article.published_at == datetime(2026, 10, 11, 14, 28, 19, tzinfo=UTC)


def test_hatena_parse():
    [article] = hatena.parse(HATENA_FEED)
    assert article.source == "hatena"
    assert article.url == "https://example.com/terraform"
    assert article.score == 223
    assert article.tags == ("infra", "aws")
