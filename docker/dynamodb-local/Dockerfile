# ローカル開発用の DynamoDB Local（compose の dynamodb サービス）。
# 元のイメージにはデータを置くディレクトリがないので、名前付きボリュームをマウントすると
# root の持ち物として作られ、uid 1000（dynamodblocal）で動く DynamoDB Local から書き込めない。
# イメージ側に dynamodblocal の持ち物として作っておくと、空のボリュームは持ち主と権限を引き継ぐ。
FROM amazon/dynamodb-local:3.3.2

RUN mkdir /home/dynamodblocal/data
