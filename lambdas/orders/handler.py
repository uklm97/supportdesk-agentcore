"""Lambda entry point for the AgentCore Gateway "orders" target.

ASSUMPTION (verify in Phase 2): the gateway invokes the Lambda with the tool's
arguments as the event, and puts the tool name in
context.client_context.custom["bedrockAgentCoreToolName"], usually prefixed with
"<target name>___". Both forms are handled below.
"""

from __future__ import annotations

import os
from typing import Any

import boto3

import orders_core
from orders_core import OrderError

TOOL_NAME_KEY = "bedrockAgentCoreToolName"
TARGET_SEPARATOR = "___"

_table: Any = None


def _get_table() -> Any:
    global _table
    if _table is None:
        _table = boto3.resource("dynamodb").Table(os.environ["ORDERS_TABLE"])
    return _table


def handle(table: Any, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Run one tool. Always returns a dict; business errors become {"error", "message"}."""
    try:
        if tool_name == "get_order":
            return orders_core.get_order(table, args.get("customer_id"), args.get("order_id"))
        if tool_name == "list_orders":
            orders = orders_core.list_orders(table, args.get("customer_id"), args.get("limit", 10))
            return {"orders": orders}
        if tool_name == "cancel_order":
            return orders_core.cancel_order(table, args.get("customer_id"), args.get("order_id"))
        if tool_name == "create_ticket":
            return orders_core.create_ticket(
                table,
                args.get("customer_id"),
                args.get("subject"),
                args.get("description"),
                args.get("order_id"),
            )
        return {"error": "UNKNOWN_TOOL", "message": f"Unknown tool: {tool_name}"}
    except OrderError as error:
        return {"error": error.code, "message": error.message}


def _tool_name(context: Any) -> str:
    custom = getattr(getattr(context, "client_context", None), "custom", None) or {}
    name = custom.get(TOOL_NAME_KEY, "")
    return name.split(TARGET_SEPARATOR, 1)[-1]


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return handle(_get_table(), _tool_name(context), event or {})
