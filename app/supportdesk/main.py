"""AgentCore Runtime entrypoint for SupportDesk.

Request payload: {"prompt": "<text>"}

Who is the customer? The runtime's CUSTOM_JWT authorizer verifies the caller's Cognito
token before this code runs. We read the `sub` claim from the forwarded Authorization
header and use it as the customer id. The payload is NEVER trusted for identity.

Tool calls go through the AgentCore Gateway with the same token, and the gateway's
Cedar policy refuses any call whose customer_id differs from the token's `sub`.

UNTESTED against a real runtime, gateway or memory (see docs/PROGRESS.md, Phase 6).
"""

from __future__ import annotations

import os
from typing import Any

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from agent import build_agent
from gateway import make_gateway_backend
from identity import bearer_token, customer_id_from_token

app = BedrockAgentCoreApp()


# Injected by the AgentCore CDK construct at deploy time. The names follow the CLI
# docs: MEMORY_<NAME>_ID and AGENTCORE_GATEWAY_<NAME>_URL. CONFIRM after the first deploy.
MEMORY_ID_ENV = "MEMORY_SUPPORTDESKMEMORY_ID"
GATEWAY_URL_ENVS = ("AGENTCORE_GATEWAY_SUPPORTDESKGW_URL", "GATEWAY_URL")


def _gateway_url() -> str:
    for name in GATEWAY_URL_ENVS:
        value = os.environ.get(name, "")
        if value:
            # The gateway's MCP endpoint is at /mcp.
            return value if value.rstrip("/").endswith("/mcp") else value.rstrip("/") + "/mcp"
    return ""


def _session_manager(customer_id: str, session_id: str | None) -> Any:
    """Short-term memory per customer and session. None when memory is not configured."""
    memory_id = os.environ.get(MEMORY_ID_ENV, "")
    if not memory_id or not session_id:
        return None
    from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
    from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager

    config = AgentCoreMemoryConfig(memory_id=memory_id, session_id=session_id, actor_id=customer_id)
    return AgentCoreMemorySessionManager(config, region_name=os.environ.get("AWS_REGION", "us-east-1"))


def run(
    payload: dict[str, Any],
    customer_id: str | None,
    backend: Any,
    model: Any = None,
    session_manager: Any = None,
) -> dict[str, Any]:
    """Validate the request, run the agent once, return {"response": text}."""
    if not isinstance(customer_id, str) or not customer_id.strip():
        return {"error": "UNAUTHENTICATED", "message": "No signed-in customer could be determined"}
    prompt = payload.get("prompt") if isinstance(payload, dict) else None
    if not isinstance(prompt, str) or not prompt.strip():
        return {"error": "INVALID_INPUT", "message": "prompt must be a non-empty string"}
    agent = build_agent(backend, customer_id, model=model, session_manager=session_manager)
    result = agent(prompt)
    return {"response": str(result)}


@app.entrypoint
def invoke(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
    token = bearer_token(context)
    customer_id = customer_id_from_token(token)
    if token is None or customer_id is None:
        return {"error": "UNAUTHENTICATED", "message": "No signed-in customer could be determined"}
    backend = make_gateway_backend(_gateway_url(), token)
    session_manager = _session_manager(customer_id, getattr(context, "session_id", None))
    return run(payload, customer_id, backend, session_manager=session_manager)


if __name__ == "__main__":
    app.run()
