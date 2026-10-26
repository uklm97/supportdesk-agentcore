"""A scripted fake model for Strands agent tests. It never calls AWS.

Each scripted turn is one model reply:
    text("hello")                        -> the model answers with text and stops
    tool_call("get_order", {"order_id": "1001"})  -> the model asks Strands to run a tool
Strands runs the tool, feeds the result back, and asks the model again, which plays the next turn.
"""

from __future__ import annotations

import json
from typing import Any

from strands.models import Model


def text(content: str) -> dict[str, Any]:
    return {"kind": "text", "text": content}


def tool_call(name: str, arguments: dict[str, Any], tool_use_id: str = "tool-1") -> dict[str, Any]:
    return {"kind": "tool", "name": name, "input": arguments, "id": tool_use_id}


class FakeModel(Model):
    def __init__(self, turns: list[dict[str, Any]]) -> None:
        self._turns = list(turns)
        self.calls: list[dict[str, Any]] = []  # what the agent sent to the model, for assertions
        self._config: dict[str, Any] = {}

    def update_config(self, **model_config: Any) -> None:
        self._config.update(model_config)

    def get_config(self) -> Any:
        return self._config

    def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):
        raise NotImplementedError("not used in these tests")

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
        self.calls.append(
            {
                "messages": list(messages),
                "tool_names": [spec["name"] for spec in (tool_specs or [])],
                "system_prompt": system_prompt,
            }
        )
        if not self._turns:
            raise AssertionError("FakeModel was asked for more turns than were scripted")
        turn = self._turns.pop(0)
        yield {"messageStart": {"role": "assistant"}}
        if turn["kind"] == "text":
            yield {"contentBlockStart": {"start": {}}}
            yield {"contentBlockDelta": {"delta": {"text": turn["text"]}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "end_turn"}}
        else:
            yield {"contentBlockStart": {"start": {"toolUse": {"toolUseId": turn["id"], "name": turn["name"]}}}}
            yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(turn["input"])}}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}
