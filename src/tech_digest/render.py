"""ダイジェストを Markdown にする。

タイトル・著者・タグ・URL は外部サイトから来る信頼できない値なので、必ずエスケープしてから埋め込む。
Markdown は後で HTML に変換して公開するため、ここで漏れると XSS やリンクの差し替えにつながる。
"""

import re
from collections.abc import Sequence
from datetime import date
from urllib.parse import quote, urlsplit

from tech_digest.models import Article
from tech_digest.sources import Source

MAX_TAGS = 3
# HTML タグ（< >）、リンク構文（[ ]）、強調・コード（* _ `）、エスケープ自体（\）
_MARKDOWN_SPECIAL = re.compile(r"([\\`*_\[\]<>])")
# URL として残す文字。( ) < > " と空白はリンク構文を壊すので %エンコードする
_URL_SAFE = ":/?#@!$&'*+,;=%~[]"


def render_markdown(
    digest_date: date, articles: Sequence[Article], sources: Sequence[Source], limit: int
) -> str:
    """取得元ごとに、並び順を保ったまま上位 limit 件を Markdown にする。"""
    lines = [f"# 技術ブログダイジェスト {digest_date.isoformat()}", ""]
    for source in sources:
        items = [a for a in articles if a.source == source.name]
        lines += [f"## {source.title}（{source.description}）", ""]
        if not items:
            lines += ["新しい記事はありませんでした。", ""]
            continue
        for i, article in enumerate(items[:limit], start=1):
            lines.append(f"{i}. {_link(article)}{_meta(article, source.score_unit)}")
        if len(items) > limit:
            lines += ["", f"ほか {len(items) - limit} 件"]
        lines.append("")
    return "\n".join(lines)


def escape_text(text: str) -> str:
    """改行をつぶし、Markdown / HTML として解釈される記号をバックスラッシュでエスケープする。"""
    return _MARKDOWN_SPECIAL.sub(r"\\\1", " ".join(text.split()))


def safe_url(url: str) -> str | None:
    """http(s) 以外（javascript: など）は None。リンク構文を壊す文字は %エンコードする。"""
    url = url.strip()
    if urlsplit(url).scheme.lower() not in ("http", "https"):
        return None
    return quote(url, safe=_URL_SAFE)


def _link(article: Article) -> str:
    title = escape_text(article.title)
    url = safe_url(article.url)
    return f"[{title}]({url})" if url else title


def _meta(article: Article, score_unit: str | None) -> str:
    parts = []
    if article.score is not None and score_unit:
        parts.append(f"{article.score} {score_unit}")
    if article.author:
        parts.append(escape_text(article.author))
    if article.tags:
        parts.append(", ".join(escape_text(t) for t in article.tags[:MAX_TAGS]))
    return f" — {' · '.join(parts)}" if parts else ""
