"""Synthesizes the CDK stacks to CloudFormation templates in memory. No AWS calls, nothing deployed."""

import json

import aws_cdk as cdk
from aws_cdk.assertions import Match, Template

from supportdesk_infra.app_stack import AppStack
from supportdesk_infra.auth_stack import AuthStack
from supportdesk_infra.settings import Settings, load_settings

ENV = cdk.Environment(account="123456789012", region="us-east-1")
FULL = Settings(
    user_pool_id="us-east-1_AbC123xyz",
    client_id="3abcdefghijklmnop1234",
    runtime_arn="arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/supportdesk_supportdesk-AbC",
    alert_email="me@example.com",
)


def synth_auth() -> Template:
    return Template.from_stack(AuthStack(cdk.App(), "supportdesk-auth", env=ENV))


def synth_app(settings: Settings = FULL) -> Template:
    return Template.from_stack(AppStack(cdk.App(), "supportdesk-app", settings=settings, env=ENV))


def test_auth_stack_has_a_pool_without_self_signup_and_two_groups():
    t = synth_auth()
    t.has_resource_properties(
        "AWS::Cognito::UserPool",
        {"AdminCreateUserConfig": {"AllowAdminCreateUserOnly": True}},
    )
    t.resource_count_is("AWS::Cognito::UserPoolGroup", 2)
    t.has_resource_properties("AWS::Cognito::UserPoolGroup", {"GroupName": "customers"})
    t.has_resource_properties("AWS::Cognito::UserPoolGroup", {"GroupName": "staff"})


def test_auth_client_has_no_secret_and_exposes_the_ids_as_plain_outputs():
    t = synth_auth()
    t.has_resource_properties("AWS::Cognito::UserPoolClient", {"GenerateSecret": False})
    outputs = t.to_json()["Outputs"]
    assert {"UserPoolId", "UserPoolClientId", "DiscoveryUrl"} <= set(outputs)
    assert all("Export" not in out for out in outputs.values())  # no ImportValue trap


def test_auth_resources_are_destroyed_with_the_stack():
    t = synth_auth()
    for resource in t.find_resources("AWS::Cognito::UserPool").values():
        assert resource["DeletionPolicy"] == "Delete"


def test_chat_api_stage_is_throttled_to_cap_cost():
    synth_app().has_resource_properties(
        "AWS::ApiGatewayV2::Stage",
        {"DefaultRouteSettings": {"ThrottlingRateLimit": 5, "ThrottlingBurstLimit": 10}},
    )


def test_table_is_pay_per_request_with_the_name_the_gateway_expects():
    synth_app().has_resource_properties(
        "AWS::DynamoDB::Table",
        {"TableName": "supportdesk-orders", "BillingMode": "PAY_PER_REQUEST"},
    )


def test_chat_route_is_protected_by_the_jwt_authorizer():
    t = synth_app()
    t.has_resource_properties(
        "AWS::ApiGatewayV2::Authorizer",
        {
            "AuthorizerType": "JWT",
            "JwtConfiguration": {
                "Audience": [FULL.client_id],
                "Issuer": f"https://cognito-idp.us-east-1.amazonaws.com/{FULL.user_pool_id}",
            },
        },
    )
    t.has_resource_properties("AWS::ApiGatewayV2::Route", {"RouteKey": "POST /chat", "AuthorizationType": "JWT"})


def test_chat_lambda_gets_the_runtime_arn_but_no_dynamodb_access():
    t = synth_app()
    t.has_resource_properties(
        "AWS::Lambda::Function",
        {"Handler": "chat_handler.lambda_handler", "Environment": {"Variables": {"RUNTIME_ARN": FULL.runtime_arn}}},
    )
    assert "dynamodb:" not in json.dumps(t.find_resources("AWS::IAM::Policy"))


def test_no_always_on_or_provisioned_resources():
    t = synth_app()
    for forbidden in ("AWS::EC2::NatGateway", "AWS::EC2::VPC", "AWS::RDS::DBInstance"):
        t.resource_count_is(forbidden, 0)


def test_waf_is_off_by_default_and_on_when_asked():
    synth_app().resource_count_is("AWS::WAFv2::WebACL", 0)
    on = Settings(**{**FULL.__dict__, "enable_waf": True})
    synth_app(on).resource_count_is("AWS::WAFv2::WebACL", 1)


def test_budget_and_alarms_exist():
    t = synth_app()
    t.has_resource_properties("AWS::Budgets::Budget", {"Budget": Match.object_like({"BudgetLimit": {"Amount": 20, "Unit": "USD"}})})
    t.resource_count_is("AWS::CloudWatch::Alarm", 2)
    t.has_resource_properties("AWS::SNS::Subscription", {"Protocol": "email", "Endpoint": "me@example.com"})


def test_bucket_is_private_and_site_uses_the_cheapest_price_class():
    t = synth_app()
    t.has_resource_properties(
        "AWS::S3::Bucket",
        {"PublicAccessBlockConfiguration": Match.object_like({"BlockPublicAcls": True, "RestrictPublicBuckets": True})},
    )
    t.has_resource_properties("AWS::CloudFront::Distribution", {"DistributionConfig": Match.object_like({"PriceClass": "PriceClass_100"})})


def test_settings_reports_missing_inputs():
    assert Settings().missing_for_app() == ["user_pool_id", "client_id", "runtime_arn", "alert_email"]
    assert FULL.missing_for_app() == []


def test_settings_prefer_context_over_the_file(tmp_path):
    path = tmp_path / "inputs.json"
    path.write_text(json.dumps({"user_pool_id": "from-file", "client_id": "file-client", "enable_waf": True}))
    context = {"user_pool_id": "from-context"}
    settings = load_settings(context.get, inputs_path=path)
    assert settings.user_pool_id == "from-context"
    assert settings.client_id == "file-client"
    assert settings.enable_waf is True
    assert load_settings({}.get, inputs_path=tmp_path / "missing.json").enable_waf is False
