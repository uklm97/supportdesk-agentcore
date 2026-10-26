# Phase 3 in plain words: login, the web back end, and demo data

Status: files are written and checked locally (85 tests pass, the login stack synthesizes). Nothing has been deployed.

## The problem this phase solves
The agent must know WHO is asking. That means a real login service (Cognito), and the agent's runtime and gateway
must be told which login service to trust. Cognito does not exist until it is created, so the order matters:
login first, then the agent, then everything else. Teardown is the reverse.

## What each piece is
- **`supportdesk-auth` stack (infra/):** a Cognito user pool. Nobody can sign themselves up; an admin creates users.
  Two groups, `customers` and `staff`. One app client for the web page. Its ids are published as plain stack outputs.
- **`supportdesk-app` stack (infra/):**
  - the DynamoDB table `supportdesk-orders` (you pay per request, nothing when idle);
  - a private S3 bucket behind CloudFront for the web page (Phase 4);
  - an HTTP API with one route, `POST /chat`, that rejects any request without a valid Cognito token,
    and a small Lambda that passes the question and the SAME token on to the agent;
  - two alarms and a monthly budget that email you. A firewall (WAF) exists only if you switch it on, because it costs money even idle.
- **chat Lambda (lambdas/chat):** a bridge. It never decides who the customer is. The agent reads that from the token itself.
- **`scripts/configure_agentcore.py`:** reads the pool id and client id from the auth stack and writes them into the two
  places in `agentcore.json` that hold `REPLACE_*` placeholders (runtime and gateway). It keeps the file's layout.
  It also writes `infra/inputs.json`, which the app stack reads. `--reset` puts the placeholders back.
- **`scripts/seed.py`:** creates alice, bob and a staff user, then loads orders under each customer's Cognito `sub`
  (the random id Cognito gives each user). That is why seeding has to happen after the users exist.

## Why not pass values between stacks with CloudFormation exports
An export that is in use blocks deleting the stack that owns it. We want to destroy and redeploy freely, so values are copied by a script instead.

## What is still unproven
Only a real deploy can show that the runtime accepts the chat Lambda's call and that API Gateway accepts the Cognito access token.
The tests only prove the templates are well formed and the scripts behave.
