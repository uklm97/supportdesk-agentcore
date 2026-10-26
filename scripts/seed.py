"""Create the demo users in Cognito and load demo orders into DynamoDB.

Why this is needed: the agent treats the token's `sub` claim as the customer id, so orders
must be stored under `CUSTOMER#<sub>`. A `sub` is a random id that Cognito makes when the
user is created, so the data can only be loaded AFTER the users exist.

What it does (safe to run again):
  1. For each demo user: create the Cognito user if missing, set a permanent password,
     add the user to its group (customers or staff), read the user's `sub`.
  2. For each customer: write demo orders under CUSTOMER#<sub>. Running it again resets
     those orders to their starting status (handy to repeat a cancel demo).

Usage (from the supportdesk folder, after the auth stack and the app stack are deployed):
    uv run python scripts/seed.py
    uv run python scripts/seed.py --password "Your-Own-Passw0rd!"
    uv run python scripts/seed.py --dry-run          # prints the plan, touches nothing

Without --password a random one is generated and printed once.
"""

from __future__ import annotations

import argparse
import json
import secrets
import string
import sys
from pathlib import Path
from typing import Any

from seed_data import DEFAULT_TABLE, ORDERS, USERS
from stack_outputs import read_stack_outputs, require_outputs

ROOT = Path(__file__).resolve().parent.parent
INPUTS_JSON = ROOT / "infra" / "inputs.json"


def generate_password() -> str:
    """Random password that satisfies the pool policy (12+, upper, lower, digit, symbol)."""
    pools = [string.ascii_lowercase, string.ascii_uppercase, string.digits, "!@#$%^*-_="]
    chars = [secrets.choice(pool) for pool in pools]
    everything = "".join(pools)
    chars += [secrets.choice(everything) for _ in range(12)]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def ensure_user(cognito: Any, pool_id: str, email: str, group: str, password: str) -> str:
    """Create the user if missing, set the password, add to the group. Returns the `sub`."""
    try:
        cognito.admin_create_user(
            UserPoolId=pool_id,
            Username=email,
            UserAttributes=[
                {"Name": "email", "Value": email},
                {"Name": "email_verified", "Value": "true"},
            ],
            MessageAction="SUPPRESS",
        )
    except cognito.exceptions.UsernameExistsException:
        pass
    cognito.admin_set_user_password(UserPoolId=pool_id, Username=email, Password=password, Permanent=True)
    cognito.admin_add_user_to_group(UserPoolId=pool_id, Username=email, GroupName=group)
    user = cognito.admin_get_user(UserPoolId=pool_id, Username=email)
    attributes = {a["Name"]: a["Value"] for a in user["UserAttributes"]}
    return attributes["sub"]


def order_items_for(sub: str, email: str) -> list[dict[str, Any]]:
    """DynamoDB items for one customer, with the same keys as lambdas/orders/orders_core.py."""
    return [
        {
            "PK": f"CUSTOMER#{sub}",
            "SK": f"ORDER#{order_id}",
            "status": status,
            "created_at": created,
            "total_cents": total,
            "items": items,
        }
        for order_id, status, created, total, items in ORDERS.get(email, [])
    ]


def seed_orders(table: Any, sub: str, email: str) -> int:
    items = order_items_for(sub, email)
    for item in items:
        table.put_item(Item=item)
    return len(items)


def _resolve_pool_id(args: argparse.Namespace) -> str:
    if args.user_pool_id:
        return args.user_pool_id
    if INPUTS_JSON.exists():
        saved = json.loads(INPUTS_JSON.read_text(encoding="utf-8")).get("user_pool_id")
        if saved:
            return saved
    import boto3

    outputs = read_stack_outputs(boto3.client("cloudformation", region_name=args.region), args.auth_stack)
    return require_outputs(outputs, args.auth_stack, "UserPoolId")[0]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create demo users and demo orders")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--auth-stack", default="supportdesk-auth")
    parser.add_argument("--user-pool-id", help="default: infra/inputs.json, then the auth stack outputs")
    parser.add_argument("--table", default=DEFAULT_TABLE)
    parser.add_argument("--password", help="password for all demo users (default: random, printed once)")
    parser.add_argument("--dry-run", action="store_true", help="print the plan and change nothing")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.dry_run:
        print(f"Would use table {args.table} in {args.region} and create these users:")
        for email, group in USERS:
            print(f"  {email:22} group={group:10} orders={len(ORDERS.get(email, []))}")
        return 0

    import boto3

    pool_id = _resolve_pool_id(args)
    password = args.password or generate_password()
    cognito = boto3.client("cognito-idp", region_name=args.region)
    table = boto3.resource("dynamodb", region_name=args.region).Table(args.table)

    for email, group in USERS:
        sub = ensure_user(cognito, pool_id, email, group, password)
        count = seed_orders(table, sub, email)
        print(f"{email:22} group={group:10} sub={sub}  orders written: {count}")

    print()
    print("Password for all demo users:", "(the one you passed)" if args.password else password)
    return 0


if __name__ == "__main__":
    sys.exit(main())
