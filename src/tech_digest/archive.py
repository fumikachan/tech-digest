"""1 日分のダイジェストを JSON ファイルとして書き出し・読み込みする。

DB（GitHub Actions ではキャッシュに置いた SQLite）は消えることがあるので、
サイトに載せる過去の記録は JSON にして data ブランチに残し、サイトはそこから作る。
"""

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from tech_digest.models import Article

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class DailyDigest:
    date: date
    articles: list[Article]


def export_day(digest: DailyDigest, out_dir: Path) -> Path:
    """digest を out_dir/YYYY-MM-DD.json に書き出す。同じ日を書き出すと上書きする。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{digest.date.isoformat()}.json"
    data = {
        "version": SCHEMA_VERSION,
        "date": digest.date.isoformat(),
        "articles": [
            {
                "source": a.source,
                "url": a.url,
                "title": a.title,
                "author": a.author,
                "score": a.score,
                "tags": list(a.tags),
                "published_at": a.published_at.isoformat(),
            }
            for a in digest.articles
        ],
    }
    # 差分が読みやすいよう、キーの順序を固定して 1 記事 1 行に近い形で書く
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


def load_days(data_dir: Path) -> list[DailyDigest]:
    """data_dir の YYYY-MM-DD.json をすべて読み、日付の新しい順に返す。"""
    days = []
    for path in sorted(data_dir.glob("????-??-??.json"), reverse=True):
        data = json.loads(path.read_text(encoding="utf-8"))
        days.append(
            DailyDigest(
                date=date.fromisoformat(data["date"]),
                articles=[
                    Article(
                        source=a["source"],
                        url=a["url"],
                        title=a["title"],
                        author=a.get("author"),
                        score=a.get("score"),
                        tags=tuple(a.get("tags", [])),
                        published_at=datetime.fromisoformat(a["published_at"]),
                    )
                    for a in data["articles"]
                ],
            )
        )
    return days
