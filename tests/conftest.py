import boto3
import pytest
from moto import mock_aws


@pytest.fixture
def table(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    with mock_aws():
        resource = boto3.resource("dynamodb")
        tbl = resource.create_table(
            TableName="orders",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        seed = [
            ("alice", "1001", "PLACED", "2026-10-01T10:00:00+00:00", 2599),
            ("alice", "1002", "SHIPPED", "2026-10-05T10:00:00+00:00", 1000),
            ("alice", "1003", "PROCESSING", "2026-10-09T10:00:00+00:00", 4500),
            ("bob", "2001", "PLACED", "2026-10-02T10:00:00+00:00", 999),
        ]
        for customer, order_id, status, created, total in seed:
            tbl.put_item(
                Item={
                    "PK": f"CUSTOMER#{customer}",
                    "SK": f"ORDER#{order_id}",
                    "status": status,
                    "created_at": created,
                    "total_cents": total,
                    "items": [{"sku": "SKU-1", "qty": 1}],
                }
            )
        yield tbl
