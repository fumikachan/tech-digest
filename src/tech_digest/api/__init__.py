"""読み取り専用の API（API Gateway の HTTP API + Lambda）。設計は docs/API_DESIGN.md を参照。

- routes.py         各エンドポイントの処理（API Gateway のイベントの形は知らない）
- lambda_handler.py Lambda の入口。API Gateway のイベントを routes に渡し、レスポンスの形に直す
- devserver.py      ローカル開発用。API Gateway の代わりに HTTP を受けて lambda_handler を呼ぶ
"""
