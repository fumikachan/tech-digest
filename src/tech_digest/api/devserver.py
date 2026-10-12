"""ローカル開発用の API サーバー。API Gateway の代わりに HTTP を受け、Lambda のハンドラーを呼ぶ。

    DYNAMODB_TABLE=tech-digest DYNAMODB_ENDPOINT_URL=http://localhost:8000 \\
        uv run python -m tech_digest.api.devserver

本番では使わない（http.server は本番向けではない）。AWS では API Gateway がこの役をする。
"""

import argparse
import logging
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qsl, urlsplit

from tech_digest.api.lambda_handler import handler
from tech_digest.api.routes import ROUTES

logger = logging.getLogger("tech_digest.api.devserver")


def _compile(route_key: str) -> tuple[str, re.Pattern[str]]:
    """ルートキーをメソッドとパスの正規表現に分ける。

    例: "GET /days/{date}" → ("GET", ^/days/(?P<date>[^/]+)$)
    """
    method, path = route_key.split(" ", 1)
    return method, re.compile("^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", path) + "$")


_PATTERNS = {key: _compile(key) for key in ROUTES}


def to_event(method: str, target: str) -> dict[str, Any] | None:
    """リクエストを API Gateway のイベント（ペイロード形式 2.0）の形にする。

    ルートがなければ None。
    """
    url = urlsplit(target)
    for route_key, (route_method, pattern) in _PATTERNS.items():
        match = pattern.match(url.path)
        if match and method == route_method:
            # API Gateway と同じく、同じ名前のパラメータが複数あればカンマでつなぐ
            query: dict[str, str] = {}
            for name, value in parse_qsl(url.query):
                query[name] = f"{query[name]},{value}" if name in query else value
            return {
                "version": "2.0",
                "routeKey": route_key,
                "rawPath": url.path,
                "rawQueryString": url.query,
                "pathParameters": match.groupdict() or None,
                "queryStringParameters": query or None,
                "requestContext": {"http": {"method": method, "path": url.path}},
            }
    return None


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # 名前は http.server が決めている
        event = to_event("GET", self.path)
        if event is None:
            # API Gateway も、ルートのないパスには Lambda を呼ばずに 404 を返す
            self._send(404, {"content-type": "application/json"}, '{"message":"Not Found"}')
            return
        response = handler(event, None)
        self._send(response["statusCode"], response["headers"], response["body"])

    def _send(self, status: int, headers: dict[str, str], body: str) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    parser = argparse.ArgumentParser(description="ローカル開発用の API サーバー")
    # 既定は 127.0.0.1（この PC からだけ）。compose のコンテナで動かすときは 0.0.0.0 にする
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    server = ThreadingHTTPServer((args.host, args.port), _Handler)
    logger.info("API を起動しました: http://%s:%d （Ctrl+C で止める）", args.host, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
