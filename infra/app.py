"""Entry point of the infra CDK app (Python).

Two stacks, deployed in this order (see docs/PROGRESS.md):
  1. supportdesk-auth  - Cognito. Needs no inputs.
  2. (agentcore/ project, deployed by the agentcore CLI)
  3. supportdesk-app   - table, chat API, web hosting, alarms, budget.
                         Needs infra/inputs.json (written by scripts/configure_agentcore.py).

The app stack is skipped while its inputs are missing, so `cdk deploy supportdesk-auth`
works before anything else exists. No stack uses Fn::ImportValue.
"""

import os
import sys

import aws_cdk as cdk

from supportdesk_infra.app_stack import AppStack
from supportdesk_infra.auth_stack import AuthStack
from supportdesk_infra.settings import load_settings

app = cdk.App()
settings = load_settings(app.node.try_get_context)
env = cdk.Environment(account=os.environ.get("CDK_DEFAULT_ACCOUNT"), region=settings.region)

AuthStack(app, "supportdesk-auth", env=env)

missing = settings.missing_for_app()
if missing:
    print(f"supportdesk-app skipped, missing inputs: {', '.join(missing)}", file=sys.stderr)
else:
    AppStack(app, "supportdesk-app", settings=settings, env=env)

app.synth()
