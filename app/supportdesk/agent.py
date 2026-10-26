"""Builds the SupportDesk Strands agent.

The model is injectable so tests can pass a fake one and cost nothing.
"""

from __future__ import annotations

import os
from typing import Any

from strands import Agent
from strands.models import BedrockModel

from prompts import SYSTEM_PROMPT
from tools import Backend, build_tools

# ASSUMPTION (verify before Phase 6): this cheaper Bedrock model id is available in
# us-east-1 for this account. Override with the MODEL_ID environment variable.
DEFAULT_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"


def default_model() -> BedrockModel:
    return BedrockModel(
        model_id=os.environ.get("MODEL_ID", DEFAULT_MODEL_ID),
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
        temperature=0.2,
    )


def build_agent(backend: Backend, customer_id: str, model: Any = None) -> Agent:
    """One agent per request, bound to one signed-in customer."""
    return Agent(
        model=model if model is not None else default_model(),
        system_prompt=SYSTEM_PROMPT,
        tools=build_tools(backend, customer_id),
        callback_handler=None,
    )
