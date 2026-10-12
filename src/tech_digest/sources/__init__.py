"""記事の取得元。新しい取得元は fetch 関数を持つモジュールを作り、SOURCES に追加する。"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

import httpx

from tech_digest.config import Settings
from tech_digest.models import Article
from tech_digest.sources import hatena, qiita, zenn

FetchFn = Callable[[httpx.Client, date, Settings], list[Article]]


@dataclass(frozen=True)
class Source:
    name: str
    title: str
    description: str
    score_unit: str | None
    fetch: FetchFn


# ダイジェストにはこの順で並ぶ
SOURCES = [
    Source("qiita", "Qiita", "前日の新着", "いいね", qiita.fetch),
    Source("zenn", "Zenn", "トレンド", None, zenn.fetch),
    Source("hatena", "はてなブックマーク", "テクノロジー人気エントリー", "users", hatena.fetch),
]
