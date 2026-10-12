"""DynamoDB の保存先。設計は docs/API_DESIGN.md を参照。

1 つのテーブルに 2 種類のアイテムを入れる（シングルテーブル設計）。
- 記事: PK = ARTICLE#<source>#<url>, SK = ARTICLE。GSI1（GSI1PK = DAY#<digest_date>）で日付から引く
- 日付: PK = DAYS, SK = <digest_date>。取得元ごとの件数（アーカイブ用）。
  GSI1PK を持たないので GSI1 には入らない

boto3 は低レベルの client を使う。値は {"S": "文字列"} や {"N": "数値の文字列"} の形で書く
（DynamoDB の API がやり取りする形そのもの）。読むときは TypeDeserializer で Python の値に戻す。
"""

from collections import Counter
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any

import boto3
from boto3.dynamodb.types import TypeDeserializer

from tech_digest.models import Article

if TYPE_CHECKING:
    # boto3-stubs（開発用の依存）。実行時には読み込まない
    from mypy_boto3_dynamodb import DynamoDBClient

ARTICLE_SK = "ARTICLE"
DAYS_PK = "DAYS"
GSI1 = "GSI1"
# DynamoDB Local につなぐときのリージョン（-sharedDb なので使われないが、boto3 が指定を求める）
LOCAL_REGION = "ap-northeast-1"

_deserializer = TypeDeserializer()


@dataclass(frozen=True)
class DaySummary:
    date: date
    counts: dict[str, int]  # 取得元ごとの件数


def connect(table: str, endpoint_url: str | None = None) -> "DynamoStore":
    if endpoint_url:
        # DynamoDB Local は認証情報を確かめない（-sharedDb ならリージョンも関係ない）。
        # ダミーの値を使い、手元にある本物の AWS の認証情報をローカルのサーバーへ送らない
        client = boto3.client(
            "dynamodb",
            endpoint_url=endpoint_url,
            region_name=LOCAL_REGION,
            aws_access_key_id="local",
            aws_secret_access_key="local",
        )
    else:
        # リージョンと認証情報は boto3 の標準の方法で読む（AWS_REGION などの環境変数や IAM ロール）
        client = boto3.client("dynamodb")
    return DynamoStore(client, table)


def create_table(client: "DynamoDBClient", table: str) -> bool:
    """テーブルを作る（ローカルの DynamoDB Local とテスト用）。既にあれば何もせず False を返す。

    AWS では Terraform（Phase 3 では手作業）で作り、アプリにはテーブルを作る権限を渡さない。
    """
    try:
        _create_table(client, table)
    except client.exceptions.ResourceInUseException:
        return False
    client.get_waiter("table_exists").wait(TableName=table)
    return True


def _create_table(client: "DynamoDBClient", table: str) -> None:
    client.create_table(
        TableName=table,
        # 定義するのはキーに使う属性だけ（ほかの属性はアイテムごとに自由に持てる）
        AttributeDefinitions=[
            {"AttributeName": name, "AttributeType": "S"}
            for name in ("PK", "SK", "GSI1PK", "GSI1SK")
        ],
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": GSI1,
                "KeySchema": [
                    {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )


class DynamoStore:
    """storage.Store を満たす。"""

    def __init__(self, client: "DynamoDBClient", table: str) -> None:
        self.client = client
        self.table = table

    def save(self, articles: Iterable[Article], digest_date: date, now: datetime) -> None:
        day = digest_date.isoformat()
        today: dict[
            str, str
        ] = {}  # この呼び出しで書いた記事のうち、digest_date が今日のもの（PK → source）
        for a in articles:
            item = self._upsert(a, day, now)
            if item["digest_date"] == day:
                today[item["PK"]] = a.source
        self._put_day(day, today, now)

    def load(self, digest_date: date) -> list[Article]:
        articles = [_to_article(item) for item in self._query_day(digest_date.isoformat())]
        # SQL 版の ORDER BY score DESC NULLS LAST, published_at DESC と同じ並び
        # （sort は安定なので、後の基準から順に 2 回並べる）
        articles.sort(key=lambda a: a.published_at, reverse=True)
        articles.sort(key=lambda a: (a.score is not None, a.score or 0), reverse=True)
        return articles

    def list_days(self) -> list[DaySummary]:
        """ダイジェストのある日付を新しい順に返す。"""
        pages = self.client.get_paginator("query").paginate(
            TableName=self.table,
            KeyConditionExpression="PK = :pk",
            ExpressionAttributeValues={":pk": {"S": DAYS_PK}},
            ScanIndexForward=False,  # SK（日付）の降順
        )
        return [_to_day(_to_python(item)) for page in pages for item in page["Items"]]

    def get_day(self, digest_date: date) -> DaySummary | None:
        """digest_date のダイジェストがなければ None。"""
        response = self.client.get_item(
            TableName=self.table,
            Key={"PK": {"S": DAYS_PK}, "SK": {"S": digest_date.isoformat()}},
        )
        item = response.get("Item")
        return _to_day(_to_python(item)) if item else None

    def close(self) -> None:
        self.client.close()

    def _upsert(self, a: Article, day: str, now: datetime) -> dict[str, Any]:
        """記事を書き、書いた後のアイテムを返す。

        digest_date と GSI1 のキーは if_not_exists() で「まだないときだけ」入れる。
        後日また取得しても初めて載った日は変わらず、タイトルやスコアだけが新しくなる
        （SQL 版の ON CONFLICT DO UPDATE と同じ動き）。
        """
        published_at = a.published_at.astimezone(UTC).isoformat()
        sets = [
            "#source = :source",
            "#url = :url",
            "#title = :title",
            "#tags = :tags",
            "#updated_at = :updated_at",
            "#published_at = if_not_exists(#published_at, :published_at)",
            "#digest_date = if_not_exists(#digest_date, :digest_date)",
            "GSI1PK = if_not_exists(GSI1PK, :gsi1pk)",
            "GSI1SK = if_not_exists(GSI1SK, :gsi1sk)",
        ]
        removes = []
        values: dict[str, Any] = {
            ":source": {"S": a.source},
            ":url": {"S": a.url},
            ":title": {"S": a.title},
            ":tags": {"L": [{"S": tag} for tag in a.tags]},
            ":updated_at": {"S": now.astimezone(UTC).isoformat()},
            ":published_at": {"S": published_at},
            ":digest_date": {"S": day},
            ":gsi1pk": {"S": f"DAY#{day}"},
            ":gsi1sk": {"S": f"{a.source}#{published_at}"},
        }
        # 値がない属性は持たない（前は値があって今回なくなったときは消す）
        if a.author is None:
            removes.append("#author")
        else:
            sets.append("#author = :author")
            values[":author"] = {"S": a.author}
        if a.score is None:
            removes.append("#score")
        else:
            sets.append("#score = :score")
            values[":score"] = {"N": str(a.score)}

        expression = "SET " + ", ".join(sets)
        if removes:
            expression += " REMOVE " + ", ".join(removes)
        names = ("source", "url", "title", "tags", "updated_at", "published_at", "digest_date")
        response = self.client.update_item(
            TableName=self.table,
            Key={"PK": {"S": f"ARTICLE#{a.source}#{a.url}"}, "SK": {"S": ARTICLE_SK}},
            UpdateExpression=expression,
            # 属性名は #name の形で書く（DynamoDB の予約語と重なっても動くように）
            ExpressionAttributeNames={f"#{n}": n for n in (*names, "author", "score")},
            ExpressionAttributeValues=values,
            ReturnValues="ALL_NEW",
        )
        return _to_python(response["Attributes"])

    def _put_day(self, day: str, today: Mapping[str, str], now: datetime) -> None:
        """その日の取得元ごとの件数を書く。

        件数は GSI1 を数えて毎回作り直す。何度実行しても同じ結果になり、
        途中で失敗しても次の実行で直る。
        ただし GSI は書き込みから少し遅れて反映される（結果整合性）ので、
        この呼び出しで書いたばかりの記事は GSI1 に頼らず today（UpdateItem の戻り値）から数える。
        """
        sources = dict(today)
        for item in self._query_day(day):
            sources.setdefault(item["PK"], item["source"])
        counts = Counter(sources.values())
        self.client.put_item(
            TableName=self.table,
            Item={
                "PK": {"S": DAYS_PK},
                "SK": {"S": day},
                "counts": {"M": {s: {"N": str(n)} for s, n in counts.items()}},
                "updated_at": {"S": now.astimezone(UTC).isoformat()},
            },
        )

    def _query_day(self, day: str) -> Iterator[dict[str, Any]]:
        """GSI1 から digest_date が day の記事をすべて返す。"""
        # Query は 1 回で最大 1 MB までしか返さないので、paginator で続きも取る
        pages = self.client.get_paginator("query").paginate(
            TableName=self.table,
            IndexName=GSI1,
            KeyConditionExpression="GSI1PK = :pk",
            ExpressionAttributeValues={":pk": {"S": f"DAY#{day}"}},
        )
        for page in pages:
            for item in page["Items"]:
                yield _to_python(item)


def _to_python(item: Mapping[str, Any]) -> dict[str, Any]:
    """{"S": "..."} などの形を Python の値に戻す（数値は Decimal になる）。"""
    return {key: _deserializer.deserialize(value) for key, value in item.items()}


def _to_article(item: Mapping[str, Any]) -> Article:
    score = item.get("score")
    return Article(
        source=item["source"],
        url=item["url"],
        title=item["title"],
        published_at=datetime.fromisoformat(item["published_at"]),
        author=item.get("author"),
        score=None if score is None else int(score),
        tags=tuple(item["tags"]),
    )


def _to_day(item: Mapping[str, Any]) -> DaySummary:
    counts = {source: int(n) for source, n in item["counts"].items()}
    return DaySummary(date=date.fromisoformat(item["SK"]), counts=counts)
