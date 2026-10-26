"""Demo users and demo orders used by scripts/seed.py."""

from __future__ import annotations

from typing import Any

DEFAULT_TABLE = "supportdesk-orders"  # must match infra/supportdesk_infra/app_stack.py

# (email, group). Users are created silently by an admin: Cognito sends no email.
USERS = [
    ("alice@example.com", "customers"),
    ("bob@example.com", "customers"),
    ("staff@example.com", "staff"),
]

# order id, status, created_at, total_cents, items. Two customers, so that cross-customer
# access can be tried on purpose in Phase 6. The staff user has no orders.
ORDERS: dict[str, list[tuple[str, str, str, int, list[dict[str, Any]]]]] = {
    "alice@example.com": [
        ("1001", "PLACED", "2026-10-01T10:00:00+00:00", 2599, [{"sku": "MUG-BLUE", "qty": 1}]),
        ("1002", "SHIPPED", "2026-10-05T10:00:00+00:00", 1000, [{"sku": "STICKER-PACK", "qty": 2}]),
        ("1003", "PROCESSING", "2026-10-09T10:00:00+00:00", 4500, [{"sku": "HOODIE-M", "qty": 1}]),
        ("1004", "CANCELLED", "2026-09-20T10:00:00+00:00", 1999, [{"sku": "CAP-BLACK", "qty": 1}]),
    ],
    "bob@example.com": [
        ("2001", "PLACED", "2026-10-02T10:00:00+00:00", 999, [{"sku": "NOTEBOOK-A5", "qty": 1}]),
        ("2002", "SHIPPED", "2026-10-06T10:00:00+00:00", 7250, [{"sku": "BACKPACK", "qty": 1}]),
    ],
}
