"""Order and ticket logic for SupportDesk, written against a boto3 DynamoDB Table.

Table design (single table, pay-per-request):
    PK = "CUSTOMER#<customer_id>"
    SK = "ORDER#<order_id>"   or   "TICKET#<ticket_id>"

Every operation takes a customer_id and only ever touches items under that
customer's partition key. Checking that the caller really is that customer is
NOT done here: the gateway policy (Cedar, Phase 2) compares customer_id with the
logged-in user's token.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

CANCELLABLE_STATUSES = ("PLACED", "PROCESSING")


class OrderError(Exception):
    """A business error that is safe to show to the agent (no internals)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _pk(customer_id: str) -> str:
    return f"CUSTOMER#{customer_id}"


def _require(name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OrderError("INVALID_INPUT", f"{name} must be a non-empty string")
    return value.strip()


def _plain(value: Any) -> Any:
    """Convert DynamoDB Decimals to int/float so the result is JSON friendly."""
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


def _order_view(item: dict[str, Any]) -> dict[str, Any]:
    view = _plain(item)
    view["customer_id"] = view.pop("PK").removeprefix("CUSTOMER#")
    view["order_id"] = view.pop("SK").removeprefix("ORDER#")
    return view


def _now() -> str:
    return datetime.now(UTC).isoformat()


def get_order(table: Any, customer_id: str, order_id: str) -> dict[str, Any]:
    customer_id = _require("customer_id", customer_id)
    order_id = _require("order_id", order_id)
    response = table.get_item(Key={"PK": _pk(customer_id), "SK": f"ORDER#{order_id}"})
    item = response.get("Item")
    if item is None:
        raise OrderError("NOT_FOUND", f"Order {order_id} was not found for this customer")
    return _order_view(item)


def list_orders(table: Any, customer_id: str, limit: int = 10) -> list[dict[str, Any]]:
    customer_id = _require("customer_id", customer_id)
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 50:
        raise OrderError("INVALID_INPUT", "limit must be an integer between 1 and 50")
    response = table.query(
        KeyConditionExpression=Key("PK").eq(_pk(customer_id)) & Key("SK").begins_with("ORDER#")
    )
    orders = [_order_view(item) for item in response.get("Items", [])]
    orders.sort(key=lambda o: o.get("created_at", ""), reverse=True)
    return orders[:limit]


def cancel_order(table: Any, customer_id: str, order_id: str) -> dict[str, Any]:
    customer_id = _require("customer_id", customer_id)
    order_id = _require("order_id", order_id)
    key = {"PK": _pk(customer_id), "SK": f"ORDER#{order_id}"}
    try:
        response = table.update_item(
            Key=key,
            UpdateExpression="SET #s = :cancelled, cancelled_at = :now",
            ConditionExpression="attribute_exists(PK) AND #s IN (:placed, :processing)",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":cancelled": "CANCELLED",
                ":now": _now(),
                ":placed": CANCELLABLE_STATUSES[0],
                ":processing": CANCELLABLE_STATUSES[1],
            },
            ReturnValues="ALL_NEW",
        )
    except ClientError as error:
        if error.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
        existing = table.get_item(Key=key).get("Item")
        if existing is None:
            raise OrderError("NOT_FOUND", f"Order {order_id} was not found for this customer") from error
        raise OrderError(
            "NOT_CANCELLABLE",
            f"Order {order_id} has status {existing['status']} and can no longer be cancelled",
        ) from error
    return _order_view(response["Attributes"])


def create_ticket(
    table: Any,
    customer_id: str,
    subject: str,
    description: str,
    order_id: str | None = None,
) -> dict[str, Any]:
    customer_id = _require("customer_id", customer_id)
    subject = _require("subject", subject)
    description = _require("description", description)
    if len(subject) > 200 or len(description) > 4000:
        raise OrderError("INVALID_INPUT", "subject max 200 and description max 4000 characters")
    if order_id is not None:
        order_id = _require("order_id", order_id)
        get_order(table, customer_id, order_id)  # raises NOT_FOUND for someone else's order

    ticket_id = uuid.uuid4().hex[:12]
    item: dict[str, Any] = {
        "PK": _pk(customer_id),
        "SK": f"TICKET#{ticket_id}",
        "status": "OPEN",
        "subject": subject,
        "description": description,
        "created_at": _now(),
    }
    if order_id is not None:
        item["order_id"] = order_id
    table.put_item(Item=item)
    return {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "status": "OPEN",
        "subject": subject,
        "order_id": order_id,
    }
