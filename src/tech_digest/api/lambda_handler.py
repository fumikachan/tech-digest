"""Lambda の入口。API Gateway（HTTP API、ペイロード形式 2.0）のイベントを受け取る。

イベントの例（必要なところだけ）:
    {"routeKey": "GET /days/{date}", "pathParameters": {"date": "2026-10-12"},
     "queryStringParameters": {"q": "aws"}, ...}

返す dict（statusCode・headers・body）を API Gateway が HTTP のレスポンスにする。
"""

import json
import logging
from typing import Any

from tech_digest.api.routes import ROUTES, ApiError, Request
from tech_digest.config import Settings
from tech_digest.storage import dynamodb

logger = logging.getLogger(__name__)

# 成功したレスポンスをブラウザや CDN（Phase 5 の CloudFront）にキャッシュさせる秒数。
# 過去の日付でもスコアは後日の取得で更新されるので、長くはしない
CACHE_SECONDS = 300

# Lambda は同じ実行環境を次の呼び出しでも使い回す（ウォームスタート）。
# クライアントをハンドラーの外に置き、接続の準備を毎回やり直さないようにする
_store: dynamodb.DynamoStore | None = None


def handler(event: dict[str, Any], context: object) -> dict[str, Any]:
    route = ROUTES.get(event.get("routeKey", ""))
    if route is None:
        return _response(404, {"message": "Not Found"})
    request = Request(
        path_params=event.get("pathParameters") or {},
        query=event.get("queryStringParameters") or {},
    )
    try:
        return _response(200, route(_get_store(), request))
    except ApiError as e:
        return _response(e.status, {"message": e.message})
    except Exception:
        # 中身（DB のエラーなど）はログにだけ出し、利用者には見せない
        logger.exception("API の処理に失敗しました: %s", event.get("routeKey"))
        return _response(500, {"message": "Internal Server Error"})


def _get_store() -> dynamodb.DynamoStore:
    global _store
    if _store is None:
        settings = Settings.from_env()
        if not settings.dynamodb_table:
            raise RuntimeError("DYNAMODB_TABLE が設定されていません")
        _store = dynamodb.connect(settings.dynamodb_table, settings.dynamodb_endpoint_url)
    return _store


def _response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    cache = f"public, max-age={CACHE_SECONDS}" if status == 200 else "no-store"
    return {
        "statusCode": status,
        "headers": {
            "content-type": "application/json; charset=utf-8",
            "cache-control": cache,
        },
        "body": json.dumps(body, ensure_ascii=False),
    }
