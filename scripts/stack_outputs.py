"""Small helper shared by the scripts: read a CloudFormation stack's outputs."""

from __future__ import annotations

from typing import Any


def read_stack_outputs(cloudformation: Any, stack_name: str) -> dict[str, str]:
    """Return {OutputKey: OutputValue}. Raises RuntimeError with a plain message if the stack is missing."""
    try:
        stacks = cloudformation.describe_stacks(StackName=stack_name)["Stacks"]
    except Exception as error:  # botocore ClientError when the stack does not exist
        raise RuntimeError(f"Could not read stack '{stack_name}': {error}") from error
    if not stacks:
        raise RuntimeError(f"Stack '{stack_name}' was not found")
    return {o["OutputKey"]: o["OutputValue"] for o in stacks[0].get("Outputs", [])}


def require_outputs(outputs: dict[str, str], stack_name: str, *keys: str) -> list[str]:
    missing = [key for key in keys if key not in outputs]
    if missing:
        raise RuntimeError(f"Stack '{stack_name}' has no output(s) {', '.join(missing)}. Found: {sorted(outputs)}")
    return [outputs[key] for key in keys]
