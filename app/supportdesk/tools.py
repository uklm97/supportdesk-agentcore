"""Strands tools for the SupportDesk agent.

The tools never take a customer_id from the model. The id of the signed-in
customer is bound when the tools are built, so the model cannot ask for
somebody else's data.

`backend` is any function (tool_name, args) -> dict. In local tests it is
lambdas/orders/handler.handle over a mocked DynamoDB table. In Phase 2 it will
call the AgentCore Gateway.
"""

from __future__ import annotations

from typing import Any, Callable

from strands import tool

Backend = Callable[[str, dict[str, Any]], dict[str, Any]]


def build_tools(backend: Backend, customer_id: str) -> list[Any]:
    if not isinstance(customer_id, str) or not customer_id.strip():
        raise ValueError("customer_id must be a non-empty string")
    customer_id = customer_id.strip()

    @tool
    def list_orders(limit: int = 10) -> dict[str, Any]:
        """List the signed-in customer's most recent orders, newest first.

        Args:
            limit: How many orders to return, from 1 to 50.
        """
        return backend("list_orders", {"customer_id": customer_id, "limit": limit})

    @tool
    def get_order(order_id: str) -> dict[str, Any]:
        """Get the details of one order of the signed-in customer.

        Args:
            order_id: The order number, for example 1001.
        """
        return backend("get_order", {"customer_id": customer_id, "order_id": order_id})

    @tool
    def cancel_order(order_id: str) -> dict[str, Any]:
        """Cancel one order. Only call this after the customer has confirmed.

        Only orders with status PLACED or PROCESSING can be cancelled.

        Args:
            order_id: The order number to cancel.
        """
        return backend("cancel_order", {"customer_id": customer_id, "order_id": order_id})

    @tool
    def create_ticket(subject: str, description: str, order_id: str | None = None) -> dict[str, Any]:
        """Open a support ticket for a human agent.

        Args:
            subject: A short title, at most 200 characters.
            description: What the customer needs, at most 4000 characters.
            order_id: The related order number, if there is one.
        """
        args: dict[str, Any] = {
            "customer_id": customer_id,
            "subject": subject,
            "description": description,
        }
        if order_id:
            args["order_id"] = order_id
        return backend("create_ticket", args)

    return [list_orders, get_order, cancel_order, create_ticket]
