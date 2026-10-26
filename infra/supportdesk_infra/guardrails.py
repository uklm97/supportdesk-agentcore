"""Cost and safety extras of the app stack: optional WAF, alarms, monthly budget.

Kept apart from app_stack.py so that file stays readable.
"""

from __future__ import annotations

from aws_cdk import Duration
from aws_cdk import aws_apigatewayv2 as apigwv2
from aws_cdk import aws_budgets as budgets
from aws_cdk import aws_cloudwatch as cloudwatch
from aws_cdk import aws_cloudwatch_actions as cw_actions
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as subscriptions
from aws_cdk import aws_wafv2 as wafv2
from constructs import Construct


def _visibility(name: str) -> wafv2.CfnWebACL.VisibilityConfigProperty:
    return wafv2.CfnWebACL.VisibilityConfigProperty(
        cloud_watch_metrics_enabled=True, metric_name=name, sampled_requests_enabled=True
    )


def create_web_acl(scope: Construct) -> wafv2.CfnWebACL:
    """WAF for CloudFront (scope CLOUDFRONT must live in us-east-1). Costs money even when idle."""
    return wafv2.CfnWebACL(
        scope,
        "WebAcl",
        scope="CLOUDFRONT",
        default_action=wafv2.CfnWebACL.DefaultActionProperty(allow={}),
        visibility_config=_visibility("supportdesk-waf"),
        rules=[
            wafv2.CfnWebACL.RuleProperty(
                name="AwsCommonRules",
                priority=1,
                override_action=wafv2.CfnWebACL.OverrideActionProperty(none={}),
                statement=wafv2.CfnWebACL.StatementProperty(
                    managed_rule_group_statement=wafv2.CfnWebACL.ManagedRuleGroupStatementProperty(
                        vendor_name="AWS", name="AWSManagedRulesCommonRuleSet"
                    )
                ),
                visibility_config=_visibility("supportdesk-waf-common"),
            ),
            wafv2.CfnWebACL.RuleProperty(
                name="RateLimitPerIp",
                priority=2,
                action=wafv2.CfnWebACL.RuleActionProperty(block={}),
                statement=wafv2.CfnWebACL.StatementProperty(
                    rate_based_statement=wafv2.CfnWebACL.RateBasedStatementProperty(
                        limit=500, aggregate_key_type="IP"
                    )
                ),
                visibility_config=_visibility("supportdesk-waf-rate"),
            ),
        ],
    )


def add_alarms(
    scope: Construct, chat_function: _lambda.IFunction, api: apigwv2.HttpApi, email: str
) -> sns.Topic:
    """Email me when the chat Lambda errors or the chat API returns a 5xx."""
    topic = sns.Topic(scope, "AlertsTopic", display_name="SupportDesk alerts")
    topic.add_subscription(subscriptions.EmailSubscription(email))
    action = cw_actions.SnsAction(topic)
    five_minutes = Duration.minutes(5)

    for alarm_id, metric, text in (
        ("ChatFunctionErrors", chat_function.metric_errors(period=five_minutes, statistic="Sum"), "The chat Lambda raised an error"),
        ("ChatApiServerErrors", api.metric_server_error(period=five_minutes, statistic="Sum"), "The chat API returned a 5xx"),
    ):
        cloudwatch.Alarm(
            scope,
            alarm_id,
            metric=metric,
            threshold=1,
            evaluation_periods=1,
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
            alarm_description=text,
        ).add_alarm_action(action)
    return topic


def _notification(kind: str, percent: float, email: str) -> budgets.CfnBudget.NotificationWithSubscribersProperty:
    return budgets.CfnBudget.NotificationWithSubscribersProperty(
        notification=budgets.CfnBudget.NotificationProperty(
            notification_type=kind,
            comparison_operator="GREATER_THAN",
            threshold=percent,
            threshold_type="PERCENTAGE",
        ),
        subscribers=[budgets.CfnBudget.SubscriberProperty(subscription_type="EMAIL", address=email)],
    )


def add_budget(scope: Construct, amount_usd: float, email: str) -> budgets.CfnBudget:
    """Monthly cost budget for the WHOLE account (not only this project), with two email alerts."""
    return budgets.CfnBudget(
        scope,
        "MonthlyBudget",
        budget=budgets.CfnBudget.BudgetDataProperty(
            budget_name="supportdesk-monthly",
            budget_type="COST",
            time_unit="MONTHLY",
            budget_limit=budgets.CfnBudget.SpendProperty(amount=amount_usd, unit="USD"),
        ),
        notifications_with_subscribers=[
            _notification("ACTUAL", 80, email),
            _notification("FORECASTED", 100, email),
        ],
    )
