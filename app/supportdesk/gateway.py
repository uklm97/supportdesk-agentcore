"""Calls the AgentCore Gateway (MCP over HTTP) on behalf of the signed-in customer.

The caller's own JWT is forwarded as the Bearer token, so the gateway's Cedar policy
sees the real user (principal tag `sub`) and can compare it with the `customer_id`
argument of each tool call.

UNTESTED against a real gateway: the MCP client call below follows the public Strands
MCPClient API. Confirm in Phase 6.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, cast

from strands.tools.mcp import MCPClient

TARGET_NAME = "orders"
TARGET_SEPARATOR = "___"


def _transport_factory(url: str, token: str) -> Callable[[], Any]:
    # pyproject.toml pins mcp<2. In 1.x this function accepts `headers`; the newer
    # `streamable_http_client` does not, and mcp 2.x removed this one.
    from mcp.client.streamable_http import streamablehttp_client as connect

    return lambda: connect(url, headers={"Authorization": f"Bearer {token}"})


def parse_tool_result(result: dict[str, Any]) -> dict[str, Any]:
    """Turn an MCP tool result into the plain dict the Lambda returned."""
    structured = result.get("structuredContent")
    text = "".join(part.get("text", "") for part in result.get("content", []) if isinstance(part, dict))
    if result.get("status") == "error":
        return {"error": "GATEWAY_ERROR", "message": text or "The gateway refused or failed the call"}
    if isinstance(structured, dict) and structured:
        return structured
    try:
        parsed = json.loads(text)
    except ValueError:
        return {"error": "GATEWAY_ERROR", "message": "The gateway returned a reply that is not JSON"}
    return parsed if isinstance(parsed, dict) else {"result": parsed}


def make_gateway_backend(
    url: str,
    token: str,
    client_factory: Callable[[], Any] | None = None,
) -> Callable[[str, dict[str, Any]], dict[str, Any]]:
    """Return backend(tool_name, args) -> dict. `client_factory` is for tests."""
    if not url:
        raise ValueError("GATEWAY_URL is not set")
    factory = client_factory or (lambda: MCPClient(_transport_factory(url, token)))

    def backend(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        qualified = f"{TARGET_NAME}{TARGET_SEPARATOR}{tool_name}"
        with factory() as client:
            result = client.call_tool_sync(tool_use_id=f"{tool_name}-call", name=qualified, arguments=args)
        return parse_tool_result(cast(dict[str, Any], result))

    return backend
