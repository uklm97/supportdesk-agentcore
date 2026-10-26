"""Fill the login placeholders in agentcore/agentcore.json (and write infra/inputs.json).

The AgentCore runtime and gateway must know which Cognito pool to trust, but that pool only
exists once the `supportdesk-auth` stack is deployed. This script reads the pool id and app
client id from that stack's outputs and writes them into BOTH authorizers (runtime and
gateway) of agentcore.json.

It edits the text with regular expressions instead of re-saving the JSON, so the hand-formatted
file keeps its layout. It is safe to run again (it replaces whatever is there, so it also works
after a destroy and redeploy that made a new pool). --reset puts the placeholders back.

Usage (from the supportdesk folder):
    uv run python scripts/configure_agentcore.py
    uv run python scripts/configure_agentcore.py --reset
    uv run python scripts/configure_agentcore.py --runtime-arn <arn> --alert-email <email>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from stack_outputs import read_stack_outputs, require_outputs

ROOT = Path(__file__).resolve().parent.parent
AGENTCORE_JSON = ROOT / "agentcore" / "agentcore.json"
INPUTS_JSON = ROOT / "infra" / "inputs.json"

PLACEHOLDER_POOL = "REPLACE_USER_POOL_ID"
PLACEHOLDER_CLIENT = "REPLACE_APP_CLIENT_ID"

POOL_ID_PATTERN = re.compile(r"^[a-z]{2}-[a-z]+-\d_[A-Za-z0-9]+$")
CLIENT_ID_PATTERN = re.compile(r"^[a-z0-9]{10,}$")

_AUTHORIZER_RE = re.compile(r'"customJwtAuthorizer"')
_DISCOVERY_RE = re.compile(r'("discoveryUrl"\s*:\s*")[^"]*(")')
_CLIENTS_RE = re.compile(r'("allowedClients"\s*:\s*)\[[^\]]*\]')


def discovery_url(region: str, pool_id: str) -> str:
    return f"https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/openid-configuration"


def apply_to_text(text: str, region: str, pool_id: str, client_id: str) -> tuple[str, int]:
    """Return (new_text, number_of_authorizers_updated). Raises ValueError on any surprise."""
    expected = len(_AUTHORIZER_RE.findall(text))
    if expected == 0:
        raise ValueError("agentcore.json has no customJwtAuthorizer block, nothing to fill in")
    url = discovery_url(region, pool_id)
    text, url_count = _DISCOVERY_RE.subn(lambda m: m.group(1) + url + m.group(2), text)
    text, client_count = _CLIENTS_RE.subn(lambda m: m.group(1) + json.dumps([client_id]), text)
    if url_count != expected or client_count != expected:
        raise ValueError(
            f"Expected {expected} discoveryUrl and allowedClients entries, found {url_count} and {client_count}"
        )
    json.loads(text)  # must still be valid JSON, otherwise nothing is written
    return text, expected


def read_text_exact(path: Path) -> str:
    """Read without translating line endings (Windows would turn CRLF into LF)."""
    return path.read_bytes().decode("utf-8")


def write_text_exact(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


def update_inputs(path: Path, values: dict[str, Any]) -> dict[str, Any]:
    """Merge values into infra/inputs.json (keeps keys that are already there)."""
    current: dict[str, Any] = {}
    if path.exists():
        current = json.loads(path.read_text(encoding="utf-8"))
    current.update({k: v for k, v in values.items() if v not in (None, "")})
    path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    return current


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fill the Cognito placeholders in agentcore.json")
    parser.add_argument("--auth-stack", default="supportdesk-auth", help="stack that holds the Cognito pool")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--user-pool-id", help="skip AWS and use this pool id")
    parser.add_argument("--client-id", help="skip AWS and use this app client id")
    parser.add_argument("--runtime-arn", help="stored in infra/inputs.json for the app stack")
    parser.add_argument("--alert-email", help="stored in infra/inputs.json for alarms and the budget")
    parser.add_argument("--reset", action="store_true", help="put the REPLACE_* placeholders back")
    parser.add_argument("--agentcore-json", type=Path, default=AGENTCORE_JSON)
    parser.add_argument("--inputs", type=Path, default=INPUTS_JSON)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    text = read_text_exact(args.agentcore_json)

    if args.reset:
        new_text, count = apply_to_text(text, args.region, PLACEHOLDER_POOL, PLACEHOLDER_CLIENT)
        write_text_exact(args.agentcore_json, new_text)
        print(f"Put the placeholders back in {count} authorizer(s) of {args.agentcore_json}")
        return 0

    pool_id, client_id = args.user_pool_id, args.client_id
    if not pool_id or not client_id:
        import boto3

        outputs = read_stack_outputs(boto3.client("cloudformation", region_name=args.region), args.auth_stack)
        pool_id, client_id = require_outputs(outputs, args.auth_stack, "UserPoolId", "UserPoolClientId")

    if not POOL_ID_PATTERN.match(pool_id) or not CLIENT_ID_PATTERN.match(client_id):
        print(f"These do not look like a Cognito pool id and app client id: {pool_id!r}, {client_id!r}", file=sys.stderr)
        return 1

    new_text, count = apply_to_text(text, args.region, pool_id, client_id)
    write_text_exact(args.agentcore_json, new_text)
    print(f"Updated {count} authorizer(s) in {args.agentcore_json}")
    print(f"  discoveryUrl   {discovery_url(args.region, pool_id)}")
    print(f"  allowedClients [{client_id}]")

    stored = update_inputs(
        args.inputs,
        {
            "region": args.region,
            "user_pool_id": pool_id,
            "client_id": client_id,
            "runtime_arn": args.runtime_arn,
            "alert_email": args.alert_email,
        },
    )
    print(f"Wrote {args.inputs} with keys: {', '.join(sorted(stored))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
