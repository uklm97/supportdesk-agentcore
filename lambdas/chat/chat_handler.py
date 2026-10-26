"""Chat Lambda: the bridge between the web app and the AgentCore runtime.

Flow: browser -> API Gateway HTTP API (verifies the Cognito JWT) -> this Lambda ->
AgentCore runtime (verifies the SAME JWT again, then reads `sub` as the customer id).

This Lambda only forwards the caller's Authorization header. It never decides who the
customer is and has no AWS permissions of its own to reach customer data. Standard
library only, so the zip needs no dependencies.

Request body (JSON): {"prompt": "<text>", "session_id": "<optional, 33-100 chars>"}
Response (JSON):     {"response": "<text>", "session_id": "<id to send next time>"}

ASSUMPTION, UNVERIFIED until Phase 6: a runtime with a CUSTOM_JWT authorizer is called over
HTTPS at /runtimes/<url-encoded ARN>/invocations with a Bearer token and a session id header.
"""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any

SESSION_HEADER = "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id"
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{33,100}$")
MAX_PROMPT_CHARS = 2000
RUNTIME_TIMEOUT_SECONDS = 25


class RuntimeCallError(Exception):
    """The runtime could not be reached or refused the call. Carries no internals for the client."""


def _reply(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }


def runtime_url(runtime_arn: str, region: str) -> str:
    quoted = urllib.parse.quote(runtime_arn, safe="")
    return f"https://bedrock-agentcore.{region}.amazonaws.com/runtimes/{quoted}/invocations?qualifier=DEFAULT"


def call_runtime(url: str, authorization: str, session_id: str, prompt: str) -> dict[str, Any]:
    """POST the prompt to the runtime and return its JSON answer."""
    request = urllib.request.Request(
        url,
        data=json.dumps({"prompt": prompt}).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": authorization,
            "Content-Type": "application/json",
            SESSION_HEADER: session_id,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=RUNTIME_TIMEOUT_SECONDS) as response:  # noqa: S310 (https only)
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        # Log the status only: the body may contain details we do not want in the browser.
        print(f"runtime returned HTTP {error.code}")
        raise RuntimeCallError("runtime refused the call") from error
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        print(f"runtime call failed: {type(error).__name__}")
        raise RuntimeCallError("runtime unreachable or invalid answer") from error


def _parse_body(event: dict[str, Any]) -> dict[str, Any] | None:
    raw = event.get("body")
    if not isinstance(raw, str):
        return None
    if event.get("isBase64Encoded"):
        try:
            raw = base64.b64decode(raw).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return None
    try:
        parsed = json.loads(raw)
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def lambda_handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    runtime_arn = os.environ.get("RUNTIME_ARN", "")
    if not runtime_arn:
        print("RUNTIME_ARN is not configured")
        return _reply(500, {"error": "SERVER_ERROR", "message": "The service is not configured"})

    headers = {str(k).lower(): v for k, v in (event.get("headers") or {}).items()}
    authorization = headers.get("authorization", "")
    if not authorization.lower().startswith("bearer "):
        return _reply(401, {"error": "UNAUTHENTICATED", "message": "Sign in first"})

    body = _parse_body(event)
    prompt = body.get("prompt") if body else None
    if not isinstance(prompt, str) or not prompt.strip():
        return _reply(400, {"error": "INVALID_INPUT", "message": "prompt must be a non-empty string"})
    if len(prompt) > MAX_PROMPT_CHARS:
        return _reply(400, {"error": "INVALID_INPUT", "message": f"prompt is longer than {MAX_PROMPT_CHARS} characters"})

    session_id = body.get("session_id") if body else None
    if session_id is None:
        session_id = f"session-{uuid.uuid4().hex}"
    elif not isinstance(session_id, str) or not SESSION_ID_PATTERN.match(session_id):
        return _reply(400, {"error": "INVALID_INPUT", "message": "session_id must be 33 to 100 letters, digits, - or _"})

    region = os.environ.get("AWS_REGION", "us-east-1")
    try:
        answer = call_runtime(runtime_url(runtime_arn, region), authorization, session_id, prompt)
    except RuntimeCallError:
        return _reply(502, {"error": "UPSTREAM_ERROR", "message": "The assistant is not available right now"})

    text = answer.get("response") if isinstance(answer, dict) else None
    if not isinstance(text, str):
        # The runtime answered with an error object (for example UNAUTHENTICATED) or something unexpected.
        print(f"unexpected runtime answer keys: {sorted(answer) if isinstance(answer, dict) else type(answer).__name__}")
        return _reply(502, {"error": "UPSTREAM_ERROR", "message": "The assistant is not available right now"})
    return _reply(200, {"response": text, "session_id": session_id})
