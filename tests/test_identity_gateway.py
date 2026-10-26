import base64
import json
from types import SimpleNamespace

import pytest

from gateway import make_gateway_backend, parse_tool_result
from identity import bearer_token, customer_id_from_token


def make_jwt(claims):
    def enc(obj):
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")

    return f"{enc({'alg': 'none'})}.{enc(claims)}.signature"


def test_customer_id_is_the_sub_claim():
    assert customer_id_from_token(make_jwt({"sub": "abc-123"})) == "abc-123"


@pytest.mark.parametrize("bad", [None, "", "x", "a.b", "a.!!!.c", make_jwt({"nosub": 1}), make_jwt({"sub": 5}), make_jwt({"sub": " "})])
def test_unreadable_tokens_give_no_customer(bad):
    assert customer_id_from_token(bad) is None


def test_bearer_token_is_read_case_insensitively():
    ctx = SimpleNamespace(request_headers={"authorization": "Bearer tok123"})
    assert bearer_token(ctx) == "tok123"
    assert bearer_token(SimpleNamespace(request_headers={"Authorization": "Basic x"})) is None
    assert bearer_token(SimpleNamespace(request_headers=None)) is None
    assert bearer_token(None) is None


def test_parse_tool_result_variants():
    assert parse_tool_result({"status": "success", "content": [{"text": '{"a": 1}'}]}) == {"a": 1}
    assert parse_tool_result({"status": "success", "content": [], "structuredContent": {"b": 2}}) == {"b": 2}
    assert parse_tool_result({"status": "error", "content": [{"text": "denied"}]})["error"] == "GATEWAY_ERROR"
    assert parse_tool_result({"status": "success", "content": [{"text": "not json"}]})["error"] == "GATEWAY_ERROR"


class FakeClient:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def call_tool_sync(self, tool_use_id, name, arguments):
        self.calls.append((name, arguments))
        return self.reply


def test_gateway_backend_prefixes_the_target_name():
    client = FakeClient({"status": "success", "content": [{"text": '{"orders": []}'}]})
    backend = make_gateway_backend("https://gw/mcp", "tok", client_factory=lambda: client)
    assert backend("list_orders", {"customer_id": "alice"}) == {"orders": []}
    assert client.calls == [("orders___list_orders", {"customer_id": "alice"})]


def test_gateway_backend_needs_a_url():
    with pytest.raises(ValueError):
        make_gateway_backend("", "tok")
