import boto3
import pytest
from moto import mock_aws

import orders_core
import seed


class FakeCognito:
    """Just enough of the Cognito admin API to test seed.ensure_user without AWS."""

    class exceptions:
        class UsernameExistsException(Exception):
            pass

    def __init__(self):
        self.users = {}
        self.groups = {}
        self.passwords = {}

    def admin_create_user(self, UserPoolId, Username, UserAttributes, MessageAction):
        assert MessageAction == "SUPPRESS"
        if Username in self.users:
            raise self.exceptions.UsernameExistsException()
        self.users[Username] = f"sub-of-{Username}"

    def admin_set_user_password(self, UserPoolId, Username, Password, Permanent):
        assert Permanent is True
        self.passwords[Username] = Password

    def admin_add_user_to_group(self, UserPoolId, Username, GroupName):
        self.groups.setdefault(Username, set()).add(GroupName)

    def admin_get_user(self, UserPoolId, Username):
        return {"UserAttributes": [{"Name": "sub", "Value": self.users[Username]}]}


@pytest.fixture
def empty_table(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    with mock_aws():
        yield boto3.resource("dynamodb").create_table(
            TableName="orders",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )


def test_generated_password_meets_the_pool_policy():
    for _ in range(50):
        password = seed.generate_password()
        assert len(password) >= 12
        assert any(c.islower() for c in password)
        assert any(c.isupper() for c in password)
        assert any(c.isdigit() for c in password)
        assert any(not c.isalnum() for c in password)


def test_ensure_user_returns_sub_and_is_repeatable():
    cognito = FakeCognito()
    first = seed.ensure_user(cognito, "pool", "alice@example.com", "customers", "Pw-1")
    second = seed.ensure_user(cognito, "pool", "alice@example.com", "customers", "Pw-2")
    assert first == second == "sub-of-alice@example.com"
    assert cognito.passwords["alice@example.com"] == "Pw-2"
    assert cognito.groups["alice@example.com"] == {"customers"}


def test_orders_are_stored_under_the_cognito_sub_and_the_tools_can_read_them(empty_table):
    assert seed.seed_orders(empty_table, "sub-abc", "alice@example.com") == 4
    seed.seed_orders(empty_table, "sub-def", "bob@example.com")

    listed = orders_core.list_orders(empty_table, "sub-abc")
    assert {o["order_id"] for o in listed} == {"1001", "1002", "1003", "1004"}
    assert all(o["customer_id"] == "sub-abc" for o in listed)
    assert orders_core.get_order(empty_table, "sub-def", "2001")["status"] == "PLACED"
    with pytest.raises(orders_core.OrderError):
        orders_core.get_order(empty_table, "sub-def", "1001")  # alice's order is invisible to bob


def test_seeding_again_resets_a_cancelled_order(empty_table):
    seed.seed_orders(empty_table, "sub-abc", "alice@example.com")
    orders_core.cancel_order(empty_table, "sub-abc", "1001")
    seed.seed_orders(empty_table, "sub-abc", "alice@example.com")
    assert orders_core.get_order(empty_table, "sub-abc", "1001")["status"] == "PLACED"


def test_staff_user_has_no_orders(empty_table):
    assert seed.seed_orders(empty_table, "sub-staff", "staff@example.com") == 0


def test_dry_run_touches_nothing(capsys):
    assert seed.main(["--dry-run"]) == 0
    assert "alice@example.com" in capsys.readouterr().out
