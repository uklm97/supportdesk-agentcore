import pytest

import handler
import orders_core
from orders_core import OrderError


def test_get_order_returns_plain_json_types(table):
    order = orders_core.get_order(table, "alice", "1001")
    assert order["order_id"] == "1001"
    assert order["customer_id"] == "alice"
    assert order["total_cents"] == 2599
    assert isinstance(order["total_cents"], int)
    assert "PK" not in order and "SK" not in order


def test_get_order_of_another_customer_is_not_found(table):
    with pytest.raises(OrderError) as excinfo:
        orders_core.get_order(table, "alice", "2001")
    assert excinfo.value.code == "NOT_FOUND"


def test_list_orders_only_own_orders_newest_first(table):
    orders = orders_core.list_orders(table, "alice")
    assert [o["order_id"] for o in orders] == ["1003", "1002", "1001"]
    assert orders_core.list_orders(table, "alice", limit=2)[0]["order_id"] == "1003"
    assert [o["order_id"] for o in orders_core.list_orders(table, "bob")] == ["2001"]


def test_list_orders_rejects_bad_limit(table):
    with pytest.raises(OrderError):
        orders_core.list_orders(table, "alice", limit=0)


def test_cancel_placed_order(table):
    order = orders_core.cancel_order(table, "alice", "1001")
    assert order["status"] == "CANCELLED"
    assert "cancelled_at" in order
    assert orders_core.get_order(table, "alice", "1001")["status"] == "CANCELLED"


def test_cancel_shipped_order_is_refused_and_unchanged(table):
    with pytest.raises(OrderError) as excinfo:
        orders_core.cancel_order(table, "alice", "1002")
    assert excinfo.value.code == "NOT_CANCELLABLE"
    assert orders_core.get_order(table, "alice", "1002")["status"] == "SHIPPED"


def test_cancel_twice_second_time_refused(table):
    orders_core.cancel_order(table, "alice", "1001")
    with pytest.raises(OrderError) as excinfo:
        orders_core.cancel_order(table, "alice", "1001")
    assert excinfo.value.code == "NOT_CANCELLABLE"


def test_cancel_missing_or_foreign_order_is_not_found(table):
    for customer, order_id in (("alice", "9999"), ("alice", "2001")):
        with pytest.raises(OrderError) as excinfo:
            orders_core.cancel_order(table, customer, order_id)
        assert excinfo.value.code == "NOT_FOUND"
    assert orders_core.get_order(table, "bob", "2001")["status"] == "PLACED"


def test_create_ticket_with_and_without_order(table):
    plain = orders_core.create_ticket(table, "alice", "Hello", "Question about billing")
    assert plain["status"] == "OPEN" and plain["order_id"] is None
    linked = orders_core.create_ticket(table, "alice", "Late", "Where is it?", order_id="1002")
    assert linked["order_id"] == "1002"
    stored = table.get_item(Key={"PK": "CUSTOMER#alice", "SK": f"TICKET#{linked['ticket_id']}"})
    assert stored["Item"]["subject"] == "Late"


def test_create_ticket_for_foreign_order_is_refused(table):
    with pytest.raises(OrderError) as excinfo:
        orders_core.create_ticket(table, "alice", "Mine?", "Not mine", order_id="2001")
    assert excinfo.value.code == "NOT_FOUND"


def test_create_ticket_validates_input(table):
    with pytest.raises(OrderError):
        orders_core.create_ticket(table, "alice", "  ", "body")
    with pytest.raises(OrderError):
        orders_core.create_ticket(table, "alice", "s", "x" * 4001)


def test_handler_routes_tools_and_returns_errors_as_data(table):
    assert handler.handle(table, "get_order", {"customer_id": "alice", "order_id": "1001"})["status"] == "PLACED"
    assert len(handler.handle(table, "list_orders", {"customer_id": "alice"})["orders"]) == 3
    assert handler.handle(table, "cancel_order", {"customer_id": "alice", "order_id": "1002"})["error"] == "NOT_CANCELLABLE"
    assert handler.handle(table, "get_order", {"customer_id": "alice"})["error"] == "INVALID_INPUT"
    assert handler.handle(table, "nope", {})["error"] == "UNKNOWN_TOOL"


def test_tool_name_strips_gateway_target_prefix():
    class Ctx:
        class client_context:
            custom = {"bedrockAgentCoreToolName": "orders___cancel_order"}

    assert handler._tool_name(Ctx()) == "cancel_order"
    assert handler._tool_name(object()) == ""
