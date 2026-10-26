"""Login: a Cognito user pool, one app client and two groups.

Deployed FIRST, because the AgentCore runtime and gateway must be told which login
service to trust. Everything here is safe to destroy (RemovalPolicy.DESTROY).

Design choices:
- No self sign-up: users are created by an admin (scripts/seed.py for the demo users).
- No hosted UI and no callback URLs: the web app signs in with the Cognito API (SRP), so
  this stack does not need to know the CloudFront address.
- The runtime and gateway check the ACCESS token (its `client_id` claim must match the
  app client). The web app must therefore send the access token, not the id token.
- The USER_PASSWORD flow is on only so a test script can sign in without the web app.
"""

from __future__ import annotations

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_cognito as cognito
from constructs import Construct


class AuthStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        pool = cognito.UserPool(
            self,
            "Pool",
            user_pool_name="supportdesk-users",
            self_sign_up_enabled=False,
            sign_in_aliases=cognito.SignInAliases(email=True, username=False),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True)
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=12,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True,
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.DESTROY,
        )

        cognito.CfnUserPoolGroup(
            self,
            "CustomersGroup",
            user_pool_id=pool.user_pool_id,
            group_name="customers",
            description="Shoppers who ask about their own orders",
        )
        cognito.CfnUserPoolGroup(
            self,
            "StaffGroup",
            user_pool_id=pool.user_pool_id,
            group_name="staff",
            description="Support staff (separate from customers)",
        )

        client = pool.add_client(
            "WebClient",
            user_pool_client_name="supportdesk-web",
            generate_secret=False,
            disable_o_auth=True,
            auth_flows=cognito.AuthFlow(user_srp=True, user_password=True),
            prevent_user_existence_errors=True,
            enable_token_revocation=True,
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(7),
        )

        # Plain outputs only: no export_name, so nothing can block a later delete.
        CfnOutput(self, "UserPoolId", value=pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=client.user_pool_client_id)
        CfnOutput(
            self,
            "DiscoveryUrl",
            value=f"https://cognito-idp.{self.region}.amazonaws.com/{pool.user_pool_id}/.well-known/openid-configuration",
        )
