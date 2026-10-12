"""JSON の記録から静的サイトを作る（GitHub Pages に置く）。

出力:
  index.html               最新の日のダイジェスト
  days/YYYY-MM-DD.html     日付ごとのダイジェスト
  archive.html             過去の一覧
  search.html + search.json  直近 SEARCH_DAYS 日分のキーワード検索（ブラウザ内で検索）
  assets/                  CSS と JavaScript

HTML は Jinja2 の自動エスケープで出力する。記事のタイトルなどは外部サイトから来る値なので、
手で文字列を組み立てず、必ずテンプレート経由で埋め込む。
"""

import json
import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from tech_digest.archive import DailyDigest
from tech_digest.config import JST
from tech_digest.models import Article
from tech_digest.render import safe_url
from tech_digest.sources import SOURCES, Source

SEARCH_DAYS = 30  # 検索の対象にする日数（増やすと search.json が大きくなる）
PREVIEW_ITEMS = 30  # 1 つの取得元で最初に表示する件数（JavaScript で残りを開く）
MAX_TAGS = 3


@dataclass(frozen=True)
class Item:
    title: str
    url: str | None  # http(s) 以外の URL は None にしてリンクにしない
    source: str
    author: str | None
    score: int | None
    tags: tuple[str, ...]
    published_at: str  # ISO 8601（並べ替え用）
    published_label: str  # 表示用（JST）


@dataclass(frozen=True)
class Section:
    source: Source
    items: list[Item]


def build_site(days: Sequence[DailyDigest], out_dir: Path) -> None:
    """days（新しい順）からサイトを out_dir に作る。out_dir の中身は作り直す。"""
    if out_dir.exists():
        shutil.rmtree(out_dir)
    (out_dir / "days").mkdir(parents=True)

    env = Environment(
        loader=PackageLoader("tech_digest", "templates"),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    dates = [d.date for d in days]

    for i, day in enumerate(days):
        context = {
            "day": day.date,
            "sections": _sections(day.articles),
            "total": len(day.articles),
            "newer": dates[i - 1] if i > 0 else None,
            "older": dates[i + 1] if i + 1 < len(dates) else None,
            "preview_items": PREVIEW_ITEMS,
        }
        page = env.get_template("day.html")
        _write(out_dir / "days" / f"{day.date}.html", page.render(root="../", **context))
        if i == 0:
            _write(out_dir / "index.html", page.render(root="", is_index=True, **context))

    if not days:
        _write(out_dir / "index.html", env.get_template("empty.html").render(root=""))

    archive = [
        {
            "date": d.date,
            "counts": {s.name: sum(a.source == s.name for a in d.articles) for s in SOURCES},
        }
        for d in days
    ]
    _write(
        out_dir / "archive.html",
        env.get_template("archive.html").render(root="", days=archive, sources=SOURCES),
    )
    _write(
        out_dir / "search.html",
        env.get_template("search.html").render(root="", search_days=SEARCH_DAYS, sources=SOURCES),
    )
    _write(out_dir / "search.json", json.dumps(_search_index(days), ensure_ascii=False))

    assets = out_dir / "assets"
    assets.mkdir()
    for name in ("style.css", "app.js"):
        (assets / name).write_bytes(files("tech_digest").joinpath("static", name).read_bytes())
    # GitHub Pages で Jekyll の処理をさせない（_ で始まるファイルなどを消されないように）
    (out_dir / ".nojekyll").touch()


def _sections(articles: Sequence[Article]) -> list[Section]:
    return [
        Section(source=s, items=[_item(a) for a in articles if a.source == s.name]) for s in SOURCES
    ]


def _item(a: Article) -> Item:
    published = a.published_at.astimezone(JST)
    return Item(
        title=a.title,
        url=safe_url(a.url),
        source=a.source,
        author=a.author,
        score=a.score,
        tags=a.tags[:MAX_TAGS],
        published_at=published.isoformat(),
        published_label=published.strftime("%m/%d %H:%M"),
    )


def _search_index(days: Sequence[DailyDigest]) -> list[dict]:
    """検索用の索引。ファイルを小さくするため、キーは 1 文字にして必要な項目だけ入れる。"""
    index = []
    for day in days[:SEARCH_DAYS]:
        for a in day.articles:
            url = safe_url(a.url)
            if not url:
                continue
            index.append(
                {
                    "d": day.date.isoformat(),
                    "s": a.source,
                    "t": a.title,
                    "u": url,
                    "c": a.score,
                    "g": list(a.tags[:MAX_TAGS]),
                }
            )
    return index


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
