"""AgentCore Runtime entrypoint for SupportDesk.

Request payload: {"prompt": "<text>", "customer_id": "<id>"}

ASSUMPTION / TODO (Phase 2): customer_id is read from the payload only so the
agent can be exercised locally. In the deployed system the customer id must come
from the verified JWT of the logged-in user, never from the payload, and the
backend below must call the AgentCore Gateway instead of raising.
"""

from __future__ import annotations

from typing import Any

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from agent import build_agent

app = BedrockAgentCoreApp()


def gateway_backend(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    raise NotImplementedError("Gateway wiring is Phase 2")


def run(payload: dict[str, Any], backend: Any = gateway_backend, model: Any = None) -> dict[str, Any]:
    """Validate the payload, run the agent once, return {"response": text}."""
    prompt = payload.get("prompt") if isinstance(payload, dict) else None
    customer_id = payload.get("customer_id") if isinstance(payload, dict) else None
    if not isinstance(prompt, str) or not prompt.strip():
        return {"error": "INVALID_INPUT", "message": "prompt must be a non-empty string"}
    if not isinstance(customer_id, str) or not customer_id.strip():
        return {"error": "INVALID_INPUT", "message": "customer_id must be a non-empty string"}
    agent = build_agent(backend, customer_id, model=model)
    result = agent(prompt)
    return {"response": str(result)}


@app.entrypoint
def invoke(payload: dict[str, Any], context: Any = None) -> dict[str, Any]:
    return run(payload)


if __name__ == "__main__":
    app.run()
