"""記事の保存先。環境変数で次のどれかを使う（上にあるものが優先）。

- DYNAMODB_TABLE があれば DynamoDB（storage/dynamodb.py。AWS とローカルの DynamoDB Local）
- DATABASE_URL があれば PostgreSQL（storage/sql.py）
- どちらもなければ SQLite（storage/sql.py）

どの保存先も、記事は (source, url) で 1 件にし、digest_date は「初めて載った日」で更新しない。
"""

from collections.abc import Iterable
from datetime import date, datetime
from typing import Protocol

from tech_digest.config import Settings
from tech_digest.models import Article


class Store(Protocol):
    def save(self, articles: Iterable[Article], digest_date: date, now: datetime) -> None: ...

    def load(self, digest_date: date) -> list[Article]:
        """digest_date に初めて載った記事を、スコアの高い順（同じなら新しい順）に返す。"""
        ...

    def close(self) -> None: ...


def connect(settings: Settings) -> Store:
    # 使う保存先のドライバーだけを読み込む（Lambda で使わない psycopg を読み込まないように）
    if settings.dynamodb_table:
        from tech_digest.storage import dynamodb

        return dynamodb.connect(settings.dynamodb_table, settings.dynamodb_endpoint_url)

    from tech_digest.storage import sql

    if settings.database_url:
        return sql.connect_postgres(settings.database_url)
    return sql.connect_sqlite(settings.db_path)
