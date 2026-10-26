import functools

import pytest

import handler
from tools import build_tools


@pytest.fixture
def tools(table):
    backend = functools.partial(handler.handle, table)
    built = build_tools(backend, "alice")
    return {t.tool_name: t for t in built}


def test_four_tools_are_exposed(tools):
    assert set(tools) == {"list_orders", "get_order", "cancel_order", "create_ticket"}


def test_model_never_sees_a_customer_id_parameter(tools):
    for tool_obj in tools.values():
        properties = tool_obj.tool_spec["inputSchema"]["json"]["properties"]
        assert "customer_id" not in properties


def test_list_orders_is_bound_to_the_signed_in_customer(tools):
    orders = tools["list_orders"](limit=10)["orders"]
    assert {o["customer_id"] for o in orders} == {"alice"}
    assert len(orders) == 3


def test_get_order_of_another_customer_is_not_found(tools):
    assert tools["get_order"](order_id="2001")["error"] == "NOT_FOUND"


def test_cancel_order_success_and_refusal(tools):
    assert tools["cancel_order"](order_id="1001")["status"] == "CANCELLED"
    assert tools["cancel_order"](order_id="1002")["error"] == "NOT_CANCELLABLE"


def test_create_ticket_with_and_without_order(tools):
    assert tools["create_ticket"](subject="Hi", description="Question")["status"] == "OPEN"
    assert tools["create_ticket"](subject="Late", description="Where?", order_id="1002")["order_id"] == "1002"
    assert tools["create_ticket"](subject="Mine?", description="x", order_id="2001")["error"] == "NOT_FOUND"


def test_build_tools_rejects_empty_customer(table):
    with pytest.raises(ValueError):
        build_tools(functools.partial(handler.handle, table), "  ")
