import json

import pytest

import chat_handler

ARN = "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/supportdesk_supportdesk-AbC"
SESSION = "s" * 40


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("RUNTIME_ARN", ARN)
    monkeypatch.setenv("AWS_REGION", "us-east-1")


def event(body=None, token="Bearer abc.def.ghi", raw=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = token
    return {"headers": headers, "body": raw if raw is not None else json.dumps(body)}


def body_of(result):
    return json.loads(result["body"])


def test_forwards_the_token_and_returns_the_answer(monkeypatch):
    seen = {}

    def fake_call(url, authorization, session_id, prompt):
        seen.update(url=url, authorization=authorization, session_id=session_id, prompt=prompt)
        return {"response": "Order 1001 is placed."}

    monkeypatch.setattr(chat_handler, "call_runtime", fake_call)
    result = chat_handler.lambda_handler(event({"prompt": "Where is 1001?", "session_id": SESSION}))
    assert result["statusCode"] == 200
    assert body_of(result) == {"response": "Order 1001 is placed.", "session_id": SESSION}
    assert seen["authorization"] == "Bearer abc.def.ghi"
    assert seen["prompt"] == "Where is 1001?"
    assert seen["url"].startswith("https://bedrock-agentcore.us-east-1.amazonaws.com/runtimes/arn%3Aaws")
    assert seen["url"].endswith("/invocations?qualifier=DEFAULT")


def test_makes_a_valid_session_id_when_none_is_sent(monkeypatch):
    monkeypatch.setattr(chat_handler, "call_runtime", lambda *a: {"response": "hi"})
    result = chat_handler.lambda_handler(event({"prompt": "hello"}))
    assert chat_handler.SESSION_ID_PATTERN.match(body_of(result)["session_id"])


def test_never_puts_a_customer_id_from_the_body_into_the_call(monkeypatch):
    seen = {}
    monkeypatch.setattr(chat_handler, "call_runtime", lambda url, auth, sid, prompt: seen.update(prompt=prompt) or {"response": "x"})
    chat_handler.lambda_handler(event({"prompt": "hi", "customer_id": "bob"}))
    assert "bob" not in json.dumps(seen)


@pytest.mark.parametrize("token", [None, "", "Basic abc", "Bearer"])
def test_rejects_a_missing_or_wrong_authorization_header(token):
    assert chat_handler.lambda_handler(event({"prompt": "hi"}, token=token))["statusCode"] == 401


@pytest.mark.parametrize(
    "body",
    [{}, {"prompt": ""}, {"prompt": "   "}, {"prompt": 5}, {"prompt": "x" * 2001}, {"prompt": "hi", "session_id": "short"}],
)
def test_rejects_bad_input(body):
    assert chat_handler.lambda_handler(event(body))["statusCode"] == 400


def test_rejects_a_body_that_is_not_json():
    assert chat_handler.lambda_handler(event(raw="not json"))["statusCode"] == 400


def test_runtime_failure_becomes_a_safe_502(monkeypatch):
    def boom(*args):
        raise chat_handler.RuntimeCallError("details that must not leak")

    monkeypatch.setattr(chat_handler, "call_runtime", boom)
    result = chat_handler.lambda_handler(event({"prompt": "hi"}))
    assert result["statusCode"] == 502
    assert "leak" not in result["body"]


def test_runtime_error_object_becomes_a_502(monkeypatch):
    monkeypatch.setattr(chat_handler, "call_runtime", lambda *a: {"error": "UNAUTHENTICATED", "message": "x"})
    assert chat_handler.lambda_handler(event({"prompt": "hi"}))["statusCode"] == 502


def test_missing_runtime_arn_is_a_500(monkeypatch):
    monkeypatch.delenv("RUNTIME_ARN")
    assert chat_handler.lambda_handler(event({"prompt": "hi"}))["statusCode"] == 500
