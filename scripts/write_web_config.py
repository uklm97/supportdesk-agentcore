"""Write web/public/config.json (what the React app reads at run time) from deployed stack outputs.

READ-ONLY toward AWS: it only calls cloudformation:DescribeStacks. Run it after `supportdesk-auth`
and `supportdesk-app` are deployed. The file is git-ignored because it holds this deployment's ids.

Usage (from the supportdesk folder):
    uv run python scripts/write_web_config.py
    uv run python scripts/write_web_config.py --api-url https://abc.execute-api.us-east-1.amazonaws.com
    uv run python scripts/write_web_config.py --dry-run     # print, write nothing
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from stack_outputs import read_stack_outputs, require_outputs

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "web" / "public" / "config.json"


def build_config(region: str, user_pool_id: str, client_id: str, api_url: str) -> dict[str, str]:
    return {
        "region": region,
        "userPoolId": user_pool_id,
        "userPoolClientId": client_id,
        "apiUrl": api_url.rstrip("/"),
    }


def collect(cloudformation: Any, region: str, auth_stack: str, app_stack: str, api_url: str | None) -> dict[str, str]:
    auth = read_stack_outputs(cloudformation, auth_stack)
    pool_id, client_id = require_outputs(auth, auth_stack, "UserPoolId", "UserPoolClientId")
    if not api_url:
        app = read_stack_outputs(cloudformation, app_stack)
        api_url = require_outputs(app, app_stack, "ApiUrl")[0]
    return build_config(region, pool_id, client_id, api_url)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write web/public/config.json from stack outputs")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--auth-stack", default="supportdesk-auth")
    parser.add_argument("--app-stack", default="supportdesk-app")
    parser.add_argument("--api-url", help="skip reading the app stack and use this API base URL")
    parser.add_argument("--dry-run", action="store_true", help="print the config and write nothing")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    import boto3

    try:
        config = collect(
            boto3.client("cloudformation", region_name=args.region),
            args.region,
            args.auth_stack,
            args.app_stack,
            args.api_url,
        )
    except RuntimeError as error:
        print(f"ERROR: {error}")
        return 1
    text = json.dumps(config, indent=2) + "\n"
    if args.dry_run:
        print(text)
        return 0
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(text, encoding="utf-8")
    print(f"Wrote {CONFIG_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
