from collections.abc import Sequence
from datetime import date

from tech_digest.models import Article
from tech_digest.sources import Source

MAX_TAGS = 3


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


def _link(article: Article) -> str:
    title = article.title.replace("[", r"\[").replace("]", r"\]")
    return f"[{title}]({article.url})"


def _meta(article: Article, score_unit: str | None) -> str:
    parts = []
    if article.score is not None and score_unit:
        parts.append(f"{article.score} {score_unit}")
    if article.author:
        parts.append(article.author)
    if article.tags:
        parts.append(", ".join(article.tags[:MAX_TAGS]))
    return f" — {' · '.join(parts)}" if parts else ""
