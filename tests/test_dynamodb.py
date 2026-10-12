"""DynamoDB だけにある動き（日付ごとの件数、属性の削除、接続先の切り替え、テーブル作成）のテスト。

SQL 版と共通の動き（重複排除・並び順）は test_storage_and_render.py で 3 つの DB に対して確かめる。
"""

from datetime import UTC, date, datetime
from pathlib import Path

from tech_digest import cli, storage
from tech_digest.config import Settings
from tech_digest.models import Article
from tech_digest.storage.dynamodb import DaySummary, DynamoStore, create_table

NOW = datetime(2026, 10, 12, tzinfo=UTC)
DAY1 = date(2026, 10, 12)
DAY2 = date(2026, 10, 13)


def article(url: str, source: str = "qiita", **kw) -> Article:
    return Article(
        source=source,
        url=url,
        title=kw.get("title", url),
        published_at=kw.get("published_at", datetime(2026, 10, 11, tzinfo=UTC)),
        author=kw.get("author"),
        score=kw.get("score"),
        tags=kw.get("tags", ()),
    )


def test_day_counts_include_earlier_runs_and_are_idempotent(dynamo_store):
    dynamo_store.save([article("https://a"), article("https://b")], DAY1, NOW)
    dynamo_store.save([article("https://h", source="hatena")], DAY1, NOW)
    # 同じ日にもう一度実行した（a は既にある。c は新しい）
    dynamo_store.save([article("https://a"), article("https://c")], DAY1, NOW)
    # 翌日も a がトレンドに残っていた
    dynamo_store.save([article("https://a"), article("https://d")], DAY2, NOW)

    assert dynamo_store.list_days() == [
        DaySummary(date=DAY2, counts={"qiita": 1}),
        DaySummary(date=DAY1, counts={"qiita": 3, "hatena": 1}),
    ]


def test_update_keeps_first_published_at_and_removes_missing_values(dynamo_store):
    first = article(
        "https://a",
        author="alice",
        score=5,
        tags=("Python", "AWS"),
        published_at=datetime(2026, 10, 11, 9, tzinfo=UTC),
    )
    dynamo_store.save([first], DAY1, NOW)
    # 後日の取得では著者とスコアが取れず、公開日時も違って返ってきた
    later = article(
        "https://a", title="新しいタイトル", published_at=datetime(2026, 10, 12, tzinfo=UTC)
    )
    dynamo_store.save([later], DAY2, NOW)

    [saved] = dynamo_store.load(DAY1)
    assert saved == Article(
        source="qiita",
        url="https://a",
        title="新しいタイトル",
        published_at=first.published_at,  # SQL 版と同じく、公開日時は最初の値のまま
        author=None,
        score=None,
        tags=(),
    )
    assert dynamo_store.load(DAY2) == []


def test_load_returns_empty_for_unknown_day(dynamo_store):
    assert dynamo_store.load(DAY1) == []
    assert dynamo_store.list_days() == []


def test_connect_prefers_dynamodb_when_table_is_set(dynamo_store):
    settings = Settings(
        db_path=Path("unused.db"),
        output_dir=Path("unused"),
        qiita_token=None,
        database_url="postgresql://unused",
        dynamodb_table=dynamo_store.table,
    )
    store = storage.connect(settings)
    assert isinstance(store, DynamoStore)
    store.save([article("https://a")], DAY1, NOW)
    assert [a.url for a in dynamo_store.load(DAY1)] == ["https://a"]
    store.close()


def test_create_table_does_nothing_when_table_exists(dynamo_store):
    assert create_table(dynamo_store.client, dynamo_store.table) is False  # fixture で作成済み
    assert create_table(dynamo_store.client, "another") is True


def test_create_table_command_is_only_for_dynamodb_local(monkeypatch):
    # AWS のテーブルは Terraform で作るので、DYNAMODB_ENDPOINT_URL がなければ断る
    # （AWS には接続しない）
    monkeypatch.setenv("DYNAMODB_TABLE", "tech-digest")
    monkeypatch.delenv("DYNAMODB_ENDPOINT_URL", raising=False)
    assert cli.main(["create-table"]) == 1
