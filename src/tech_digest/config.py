import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# 日本はサマータイムがないので固定オフセットで十分。
# zoneinfo と違い、tzdata のないコンテナイメージでも動く。
JST = timezone(timedelta(hours=9), "JST")


def today_jst() -> date:
    return datetime.now(JST).date()


@dataclass(frozen=True)
class Settings:
    """設定はすべて環境変数から読む（ローカル・Docker・クラウドで同じコードが動くように）。"""

    db_path: Path  # DATABASE_URL がないときに使う SQLite のファイル
    output_dir: Path
    qiita_token: str | None
    database_url: str | None = None  # postgresql://... があれば PostgreSQL を使う
    dynamodb_table: str | None = None  # あれば DynamoDB を使う（DATABASE_URL より優先）
    dynamodb_endpoint_url: str | None = None  # DynamoDB Local の URL。AWS では設定しない

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.environ.get("DATABASE_URL") or None,
            dynamodb_table=os.environ.get("DYNAMODB_TABLE") or None,
            dynamodb_endpoint_url=os.environ.get("DYNAMODB_ENDPOINT_URL") or None,
            db_path=Path(os.environ.get("TECH_DIGEST_DB_PATH", "data/tech-digest.db")),
            output_dir=Path(os.environ.get("TECH_DIGEST_OUTPUT_DIR", "digests")),
            qiita_token=os.environ.get("QIITA_TOKEN") or None,
        )
