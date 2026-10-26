# SupportDesk: a customer-support AI agent on Amazon Bedrock AgentCore

SupportDesk is a complete customer-support agent built on
[Amazon Bedrock AgentCore](https://aws.amazon.com/bedrock/agentcore/). A signed-in customer chats with the agent
to look at their orders, cancel an order that has not shipped, or open a support ticket.

The focus is the surrounding platform, not just the model: identity, authorization, memory, tools, evaluation,
cost control and clean teardown.

## What it does

- **Chat web app**: React + TypeScript + Vite, served from S3 behind CloudFront, with Cognito login.
- **Agent**: a [Strands Agents](https://strandsagents.com/) agent running on AgentCore Runtime, using Claude Haiku 4.5 on Bedrock.
- **Tools through a Gateway**: order lookup, order cancel and ticket creation are exposed over MCP by an AgentCore Gateway
  and run in a Lambda function backed by a single DynamoDB table.
- **Safety by design**:
  - The customer id comes from the signed JWT, never from the chat text.
  - A **Cedar policy** on the Gateway allows a tool call only when it is for the caller's own orders.
  - The agent must ask for confirmation before it cancels anything.
- **Memory**: AgentCore Memory keeps the conversation context across turns.
- **Evaluation**: custom evaluators (reply accuracy, cancel confirmation) and an online evaluation config, created paused to avoid judge-call cost.
- **Cost guard rails**: pay-per-request DynamoDB, CloudFront price class 100, API throttling, 7-day log retention, a monthly budget alert, WAF off by default.

## Architecture

```
Browser (React) --login--> Cognito
   |  Bearer token
   v
CloudFront + S3 (site)      API Gateway (HTTP API, JWT authorizer)
                                  |  POST /chat
                                  v
                            Chat Lambda ---> AgentCore Runtime (Strands agent, Claude Haiku 4.5)
                                                    |  \
                                                    |   AgentCore Memory
                                                    v
                                            AgentCore Gateway (MCP + Cedar policy)
                                                    |
                                                    v
                                           Orders Lambda --> DynamoDB
```

## Repository layout

| Path | What is in it |
|---|---|
| `app/supportdesk/` | The agent: prompt, tools, gateway client, identity helpers, entry point |
| `agentcore/` | AgentCore project config (`agentcore.json`) and the generated CDK app |
| `lambdas/orders/`, `lambdas/chat/` | Tool Lambda and the chat proxy Lambda |
| `infra/` | Python CDK: `supportdesk-auth` (Cognito) and `supportdesk-app` (API, site, table, alarms, budget) |
| `web/` | The front end |
| `scripts/` | `configure_agentcore.py`, `seed.py`, `write_web_config.py`, `deploy_web.py`, `stack_outputs.py` |
| `tests/` | About 90 pytest tests (agent logic, tools, infra templates, scripts) |
| `docs/` | `PROGRESS.md` (full build log) and a plain-language `PHASEn-EXPLAINED.md` per phase |

## Run the tests (no AWS needed)

```bash
uv sync
uv run pytest -q
```

## Deploy (costs money; read first)

Prerequisites: AWS credentials, CDK bootstrapped, [uv](https://docs.astral.sh/uv/), Node.js 20+, the AgentCore CLI and Bedrock model access.
One deploy-test-destroy day cost roughly 2 to 5 USD in the estimate, mostly model calls. Deploy one stack at a time, in this order:

1. `cd infra && npx cdk deploy supportdesk-auth`
2. `uv run python scripts/configure_agentcore.py --user-pool-id <id> --client-id <id> --alert-email <you@example.com>`
3. `agentcore deploy`
4. Re-run the configure script with `--runtime-arn <arn>`
5. `cd infra && npx cdk deploy supportdesk-app`
6. `uv run python scripts/seed.py` (demo users and orders; the password is printed once)
7. `uv run python scripts/write_web_config.py`, then `cd web && npm run build`, then `uv run python scripts/deploy_web.py`

Destroy in reverse order. Run `configure_agentcore.py --reset` before committing so no account-specific ids land in git.

## License

No license has been chosen yet.
