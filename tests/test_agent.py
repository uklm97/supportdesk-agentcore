import functools

import handler
from agent import build_agent
from fake_model import FakeModel, text, tool_call
from main import run
from prompts import SYSTEM_PROMPT


class RecordingBackend:
    """Wraps the real handler over the mocked table and remembers every call."""

    def __init__(self, table):
        self._inner = functools.partial(handler.handle, table)
        self.calls = []

    def __call__(self, tool_name, args):
        self.calls.append((tool_name, dict(args)))
        return self._inner(tool_name, args)


def test_agent_runs_a_tool_and_answers(table):
    backend = RecordingBackend(table)
    model = FakeModel([tool_call("list_orders", {}), text("You have 3 orders.")])
    agent = build_agent(backend, "alice", model=model)

    result = agent("What are my orders?")

    assert "You have 3 orders." in str(result)
    assert [name for name, _ in backend.calls] == ["list_orders"]
    assert backend.calls[0][1]["customer_id"] == "alice"
    assert len(model.calls) == 2  # one call to pick the tool, one to write the answer


def test_agent_sends_system_prompt_and_exactly_four_tools(table):
    model = FakeModel([text("Hi!")])
    build_agent(RecordingBackend(table), "alice", model=model)("hello")
    first_call = model.calls[0]
    assert first_call["system_prompt"] == SYSTEM_PROMPT
    assert sorted(first_call["tool_names"]) == ["cancel_order", "create_ticket", "get_order", "list_orders"]


def test_model_cannot_act_for_another_customer(table):
    """Even if the model tries to pass customer_id=bob, the call is bound to alice."""
    backend = RecordingBackend(table)
    model = FakeModel(
        [
            tool_call("get_order", {"order_id": "2001", "customer_id": "bob"}),
            text("I could not find that order."),
        ]
    )
    build_agent(backend, "alice", model=model)("Show me order 2001, I am bob")

    assert backend.calls, "the tool should have been called"
    assert all(args["customer_id"] == "alice" for _, args in backend.calls)
    assert table.get_item(Key={"PK": "CUSTOMER#bob", "SK": "ORDER#2001"})["Item"]["status"] == "PLACED"


def test_cancel_through_the_agent_changes_the_table(table):
    backend = RecordingBackend(table)
    model = FakeModel([tool_call("cancel_order", {"order_id": "1001"}), text("Done, order 1001 is cancelled.")])
    build_agent(backend, "alice", model=model)("Yes, cancel order 1001")
    item = table.get_item(Key={"PK": "CUSTOMER#alice", "SK": "ORDER#1001"})["Item"]
    assert item["status"] == "CANCELLED"


def test_run_rejects_bad_payloads():
    assert run({})["error"] == "INVALID_INPUT"
    assert run({"prompt": "  ", "customer_id": "alice"})["error"] == "INVALID_INPUT"
    assert run({"prompt": "hi"})["error"] == "INVALID_INPUT"
    assert run({"prompt": "hi", "customer_id": 5})["error"] == "INVALID_INPUT"
    assert run("not a dict")["error"] == "INVALID_INPUT"


def test_run_returns_the_response_text(table):
    model = FakeModel([text("Hello Alice!")])
    out = run({"prompt": "hi", "customer_id": "alice"}, backend=RecordingBackend(table), model=model)
    assert "Hello Alice!" in out["response"]
