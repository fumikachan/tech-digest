import boto3
import pytest
from moto import mock_aws

from tech_digest.storage.dynamodb import DynamoStore, create_table

TEST_TABLE = "tech-digest-test"


@pytest.fixture
def dynamo_store(monkeypatch):
    """moto の偽の DynamoDB にテーブルを作る（ネットワークに出ない）。"""
    # 手元の本物の AWS の設定や認証情報を誤って使わないよう、ダミーの値で上書きする
    for name in ("AWS_PROFILE", "AWS_ENDPOINT_URL", "AWS_ENDPOINT_URL_DYNAMODB"):
        monkeypatch.delenv(name, raising=False)
    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        monkeypatch.setenv(name, "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-northeast-1")

    with mock_aws():
        client = boto3.client("dynamodb")
        create_table(client, TEST_TABLE)
        store = DynamoStore(client, TEST_TABLE)
        yield store
        store.close()
