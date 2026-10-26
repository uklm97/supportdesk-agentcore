import pytest

import write_web_config as wwc


class FakeCloudFormation:
    def __init__(self, stacks):
        self.stacks = stacks

    def describe_stacks(self, StackName):
        if StackName not in self.stacks:
            raise Exception(f"Stack {StackName} does not exist")
        return {"Stacks": [{"Outputs": [{"OutputKey": k, "OutputValue": v} for k, v in self.stacks[StackName].items()]}]}


AUTH = {"UserPoolId": "us-east-1_abc", "UserPoolClientId": "client1"}
APP = {"ApiUrl": "https://x.execute-api.us-east-1.amazonaws.com/"}


def test_reads_both_stacks_and_trims_the_trailing_slash():
    cf = FakeCloudFormation({"supportdesk-auth": AUTH, "supportdesk-app": APP})
    config = wwc.collect(cf, "us-east-1", "supportdesk-auth", "supportdesk-app", None)
    assert config == {
        "region": "us-east-1",
        "userPoolId": "us-east-1_abc",
        "userPoolClientId": "client1",
        "apiUrl": "https://x.execute-api.us-east-1.amazonaws.com",
    }


def test_api_url_override_skips_the_app_stack():
    cf = FakeCloudFormation({"supportdesk-auth": AUTH})
    config = wwc.collect(cf, "us-east-1", "supportdesk-auth", "supportdesk-app", "https://override.test/")
    assert config["apiUrl"] == "https://override.test"


def test_missing_stack_gives_a_plain_error():
    cf = FakeCloudFormation({"supportdesk-auth": AUTH})
    with pytest.raises(RuntimeError, match="supportdesk-app"):
        wwc.collect(cf, "us-east-1", "supportdesk-auth", "supportdesk-app", None)
