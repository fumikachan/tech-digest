from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Article:
    source: str
    url: str
    title: str
    published_at: datetime
    author: str | None = None
    score: int | None = None  # いいね数・ブックマーク数など。取得元が提供しない場合は None
    tags: tuple[str, ...] = ()
