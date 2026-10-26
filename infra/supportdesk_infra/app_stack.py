"""Table, chat API and web hosting. Alarms, budget and WAF are in guardrails.py.

Deployed LAST (after supportdesk-auth and the agentcore/ project). All pay-per-use:
DynamoDB on demand, one small Lambda, an HTTP API, S3 + CloudFront (cheapest price
class). No NAT gateway, no provisioned capacity. WAF exists only when settings.enable_waf
is true, because a WAF web ACL costs money even with no traffic.

UNVERIFIED until the Phase 6 deploy (docs/PROGRESS.md): that API Gateway accepts the
Cognito access token through the JWT authorizer, and that the runtime accepts the chat
Lambda's call. `cdk synth` only proves the template is well formed.
"""

from __future__ import annotations

from pathlib import Path

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack, Tags
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_apigatewayv2_authorizers as authorizers
from aws_cdk import aws_apigatewayv2_integrations as integrations
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from constructs import Construct

from supportdesk_infra import guardrails
from supportdesk_infra.settings import Settings

CHAT_CODE_DIR = Path(__file__).resolve().parents[2] / "lambdas" / "chat"

# The gateway's Lambda permissions in agentcore.json and the orders Lambda use exactly this name.
ORDERS_TABLE_NAME = "supportdesk-orders"

LOCAL_DEV_ORIGIN = "http://localhost:5173"  # Vite dev server (Phase 4)

# Requests per second allowed on the whole chat API (a demo needs far less than this).
CHAT_RATE_LIMIT = 5
CHAT_BURST_LIMIT = 10


class AppStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, settings: Settings, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        Tags.of(self).add("project", "supportdesk")

        table = dynamodb.Table(
            self,
            "OrdersTable",
            table_name=ORDERS_TABLE_NAME,
            partition_key=dynamodb.Attribute(name="PK", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="SK", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
        )

        bucket = s3.Bucket(
            self,
            "SiteBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )
        web_acl = guardrails.create_web_acl(self) if settings.enable_waf else None
        distribution = cloudfront.Distribution(
            self,
            "SiteDistribution",
            default_root_object="index.html",
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
            web_acl_id=web_acl.attr_arn if web_acl else None,
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            ),
            # Single-page app: unknown paths load index.html and the browser router takes over.
            error_responses=[
                cloudfront.ErrorResponse(http_status=403, response_http_status=200, response_page_path="/index.html"),
                cloudfront.ErrorResponse(http_status=404, response_http_status=200, response_page_path="/index.html"),
            ],
        )
        site_origin = f"https://{distribution.distribution_domain_name}"

        # Chat path: browser -> HTTP API (checks the JWT) -> Lambda -> AgentCore runtime.
        chat_function = _lambda.Function(
            self,
            "ChatFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="chat_handler.lambda_handler",
            code=_lambda.Code.from_asset(str(CHAT_CODE_DIR)),
            timeout=Duration.seconds(29),  # the HTTP API cuts the connection after 30 seconds
            memory_size=256,
            log_group=logs.LogGroup(
                self,
                "ChatFunctionLogs",
                retention=logs.RetentionDays.ONE_WEEK,
                removal_policy=RemovalPolicy.DESTROY,
            ),
            environment={"RUNTIME_ARN": settings.runtime_arn},
        )
        issuer = f"https://cognito-idp.{settings.region}.amazonaws.com/{settings.user_pool_id}"
        api = apigwv2.HttpApi(
            self,
            "ChatApi",
            api_name="supportdesk-chat",
            cors_preflight=apigwv2.CorsPreflightOptions(
                allow_origins=[site_origin, LOCAL_DEV_ORIGIN],
                allow_methods=[apigwv2.CorsHttpMethod.POST],
                allow_headers=["authorization", "content-type"],
                max_age=Duration.hours(1),
            ),
        )
        api.add_routes(
            path="/chat",
            methods=[apigwv2.HttpMethod.POST],
            integration=integrations.HttpLambdaIntegration("ChatIntegration", chat_function),
            # An access token carries a `client_id` claim; API Gateway compares it with this list.
            authorizer=authorizers.HttpJwtAuthorizer("CognitoJwt", issuer, jwt_audience=[settings.client_id]),
        )

        # Cost guard: every chat call can trigger a Bedrock model call, so cap the request rate.
        default_stage = api.default_stage
        assert default_stage is not None  # created by default
        stage_resource = default_stage.node.default_child
        assert isinstance(stage_resource, apigwv2.CfnStage)
        stage_resource.default_route_settings = apigwv2.CfnStage.RouteSettingsProperty(
            throttling_rate_limit=CHAT_RATE_LIMIT,
            throttling_burst_limit=CHAT_BURST_LIMIT,
        )

        guardrails.add_alarms(self, chat_function, api, settings.alert_email)
        guardrails.add_budget(self, settings.budget_usd, settings.alert_email)

        # Plain outputs, no export names (see settings.py).
        CfnOutput(self, "ApiUrl", value=api.api_endpoint)
        CfnOutput(self, "SiteUrl", value=site_origin)
        CfnOutput(self, "SiteBucketName", value=bucket.bucket_name)
        CfnOutput(self, "DistributionId", value=distribution.distribution_id)
        CfnOutput(self, "OrdersTableName", value=table.table_name)
