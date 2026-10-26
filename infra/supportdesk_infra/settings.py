"""Inputs of the app stack.

Values come from CDK context (`-c key=value`) first, then from infra/inputs.json
(written by scripts/configure_agentcore.py), then from the defaults below.
Values are passed this way, and NOT through CloudFormation exports, so that stacks can
be deleted and redeployed in any order without "export is in use" errors.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

INPUTS_FILE = Path(__file__).resolve().parent.parent / "inputs.json"


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    region: str = "us-east-1"
    user_pool_id: str = ""
    client_id: str = ""
    runtime_arn: str = ""
    alert_email: str = ""
    budget_usd: float = 20.0
    enable_waf: bool = False  # WAF costs money even when idle, so it is off unless asked for.

    def missing_for_app(self) -> list[str]:
        required = {
            "user_pool_id": self.user_pool_id,
            "client_id": self.client_id,
            "runtime_arn": self.runtime_arn,
            "alert_email": self.alert_email,
        }
        return [name for name, value in required.items() if not value]


def load_settings(
    get_context: Callable[[str], Any],
    inputs_path: Path = INPUTS_FILE,
) -> Settings:
    file_values: dict[str, Any] = {}
    if inputs_path.exists():
        file_values = json.loads(inputs_path.read_text(encoding="utf-8"))

    def pick(key: str, default: Any) -> Any:
        value = get_context(key)
        if value is None or value == "":
            value = file_values.get(key, default)
        return value

    return Settings(
        region=str(pick("region", "us-east-1")),
        user_pool_id=str(pick("user_pool_id", "")),
        client_id=str(pick("client_id", "")),
        runtime_arn=str(pick("runtime_arn", "")),
        alert_email=str(pick("alert_email", "")),
        budget_usd=float(pick("budget_usd", 20.0)),
        enable_waf=_as_bool(pick("enable_waf", False)),
    )
