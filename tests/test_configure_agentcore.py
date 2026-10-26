import json
from pathlib import Path

import pytest

import configure_agentcore as cfg

REAL_FILE = Path(__file__).resolve().parent.parent / "agentcore" / "agentcore.json"
POOL = "us-east-1_AbC123xyz"
CLIENT = "3abcdefghijklmnop1234"


def test_fills_both_authorizers_and_keeps_json_valid():
    text = REAL_FILE.read_text(encoding="utf-8")
    new_text, count = cfg.apply_to_text(text, "us-east-1", POOL, CLIENT)
    assert count == 2  # runtime and gateway
    assert new_text.count(POOL) == 2
    assert new_text.count(CLIENT) == 2
    assert "REPLACE_" not in new_text
    data = json.loads(new_text)
    runtime = data["runtimes"][0]["authorizerConfiguration"]["customJwtAuthorizer"]
    gateway = data["agentCoreGateways"][0]["authorizerConfiguration"]["customJwtAuthorizer"]
    for block in (runtime, gateway):
        assert block["discoveryUrl"] == cfg.discovery_url("us-east-1", POOL)
        assert block["allowedClients"] == [CLIENT]


def test_only_the_authorizer_lines_change():
    text = REAL_FILE.read_text(encoding="utf-8")
    new_text, _ = cfg.apply_to_text(text, "us-east-1", POOL, CLIENT)
    before, after = text.splitlines(), new_text.splitlines()
    assert len(before) == len(after)
    assert sum(1 for a, b in zip(before, after, strict=True) if a != b) <= 4


def test_running_twice_with_a_new_pool_replaces_the_old_values():
    text = REAL_FILE.read_text(encoding="utf-8")
    once, _ = cfg.apply_to_text(text, "us-east-1", POOL, CLIENT)
    twice, _ = cfg.apply_to_text(once, "us-east-1", "us-east-1_Other999", "newclient1234567")
    assert POOL not in twice and CLIENT not in twice
    assert twice.count("us-east-1_Other999") == 2


def test_reset_puts_the_placeholders_back():
    text = REAL_FILE.read_text(encoding="utf-8")
    filled, _ = cfg.apply_to_text(text, "us-east-1", POOL, CLIENT)
    reset, _ = cfg.apply_to_text(filled, "us-east-1", cfg.PLACEHOLDER_POOL, cfg.PLACEHOLDER_CLIENT)
    assert reset == text  # the committed file holds the placeholders


def test_refuses_a_file_without_authorizers():
    with pytest.raises(ValueError):
        cfg.apply_to_text('{"name": "x"}', "us-east-1", POOL, CLIENT)


def test_line_endings_are_preserved_byte_for_byte(tmp_path):
    target = tmp_path / "agentcore.json"
    crlf = REAL_FILE.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    target.write_bytes(crlf)
    code = cfg.main(
        ["--user-pool-id", POOL, "--client-id", CLIENT, "--agentcore-json", str(target), "--inputs", str(tmp_path / "i.json")]
    )
    assert code == 0
    written = target.read_bytes()
    assert b"\r\n" in written
    assert written.count(b"\n") == written.count(b"\r\n")  # no bare LF was introduced


def test_main_writes_both_files(tmp_path):
    target = tmp_path / "agentcore.json"
    target.write_text(REAL_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    inputs = tmp_path / "inputs.json"
    code = cfg.main(
        [
            "--user-pool-id", POOL, "--client-id", CLIENT,
            "--runtime-arn", "arn:aws:bedrock-agentcore:us-east-1:1:runtime/x",
            "--alert-email", "me@example.com",
            "--agentcore-json", str(target), "--inputs", str(inputs),
        ]
    )
    assert code == 0
    assert POOL in target.read_text(encoding="utf-8")
    saved = json.loads(inputs.read_text(encoding="utf-8"))
    assert saved["user_pool_id"] == POOL
    assert saved["client_id"] == CLIENT
    assert saved["alert_email"] == "me@example.com"


def test_main_rejects_values_that_do_not_look_like_cognito_ids(tmp_path):
    target = tmp_path / "agentcore.json"
    original = REAL_FILE.read_text(encoding="utf-8")
    target.write_text(original, encoding="utf-8")
    code = cfg.main(
        ["--user-pool-id", "nope", "--client-id", "x", "--agentcore-json", str(target), "--inputs", str(tmp_path / "i.json")]
    )
    assert code == 1
    assert target.read_text(encoding="utf-8") == original


def test_read_stack_outputs_helpers():
    from stack_outputs import read_stack_outputs, require_outputs

    class Cf:
        def describe_stacks(self, StackName):
            return {"Stacks": [{"Outputs": [{"OutputKey": "UserPoolId", "OutputValue": POOL}]}]}

    outputs = read_stack_outputs(Cf(), "s")
    assert require_outputs(outputs, "s", "UserPoolId") == [POOL]
    with pytest.raises(RuntimeError):
        require_outputs(outputs, "s", "UserPoolClientId")
