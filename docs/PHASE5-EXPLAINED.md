# Phase 5 - Quality checks and pre-deploy review (plain language)

Nothing was deployed. No AWS resource was created, changed or deleted. The only AWS call was one read-only
check that the Bedrock model profile `us.anthropic.claude-haiku-4-5-20251001-v1:0` is ACTIVE in us-east-1.

## What was checked, and the result
| Check | Result |
|---|---|
| Python tests (`uv run pytest -q`) | 92 passed |
| Python lint (`ruff`, rules E F I UP B) | clean (12 auto-fixes: import order, `datetime.UTC`, `collections.abc`) |
| Python type check (`mypy`) | clean, 21 files |
| Python dependency audit (`pip-audit`) | clean after the fix below |
| Front end type check, tests, build | clean, 8 tests passed, build OK |
| Front end `npm audit` (`web/`) | 0 vulnerabilities |
| `agentcore build` | OK |
| `cdk synth supportdesk-app` (with example inputs, written to a temp folder) | OK |
| `npm audit --omit=dev` in `agentcore/cdk/` | 1 high: `brace-expansion` inside `aws-cdk-lib` (see "Left alone") |

## Problems found and fixed
1. **Vulnerable `mcp` package.** `pip-audit` flagged `mcp` 2.1.1 (CVE-2026-59951, fixed in 1.30.0 and 2.2.0).
   `strands-agents` 1.62.0 requires `mcp<2.2`, so 2.2.0 is not allowed. Fix: `pyproject.toml` now pins `mcp>=1.30,<2`.
   The lock file moved to `mcp` 1.30.0. 88 tests still passed.
2. **Real bug caught by mypy.** `app/supportdesk/gateway.py` guessed the name of the MCP connect function.
   The 2.x name does not accept the `headers` argument we need to forward the user's token. With `mcp` 1.30 the old
   `streamablehttp_client` does accept it, so `gateway.py` now imports that one directly. Still UNTESTED against a real gateway.
3. **No cost cap on the chat API.** Every chat call can cause paid model calls. The HTTP API stage now throttles to
   5 requests per second (burst 10). A test (`test_chat_api_stage_is_throttled_to_cap_cost`) guards it.
4. **Config added:** `[tool.ruff]` in `pyproject.toml` so lint is repeatable.

## Open item from Phase 4: how the site gets into S3 (decided)
Decision: **`aws s3 sync` through `scripts/deploy_web.py`, not a CDK BucketDeployment.**
Reasons: no extra helper Lambda in the stack, the build and the `config.json` can be rewritten without a CDK redeploy,
and `--dry-run` shows what would change first. The script uploads hashed files under `assets/` with a long cache,
everything else (`index.html`, `config.json`) with no cache, then invalidates CloudFront. 3 tests cover the commands.
It changes AWS, so it runs only in Phase 6 after your approval.

## Left alone on purpose
- `brace-expansion` high-severity finding in `agentcore/cdk/node_modules`: it is build-time tooling in the generated CDK app,
  which we must not hand-edit. It never ships to AWS. A `npm audit fix` there is possible but is a change to generated files:
  your call.
- The generated agentcore stack template contains a CloudWatch log group with 731 days retention. I did not find out which
  group it is or whether the CLI lets us change it. Check after the first deploy and delete the logs at teardown.

## Cost estimate (ROUGH, from memory of public list prices, NOT checked against the AWS price pages today)
Assumptions: one day of testing, about 100 chat turns, each turn about 3 model calls (tool use) of about 3,000 input
and 300 output tokens, Claude Haiku 4.5 at about 1 USD per million input tokens and 5 USD per million output tokens.

| Service | Estimate for the test day |
|---|---|
| Bedrock model calls | about 1.5 to 2 USD (about 0.015 per chat turn). This is the main cost and it grows with usage |
| AgentCore Runtime (billed per second of active CPU and memory) | well under 1 USD |
| AgentCore Gateway and policy checks (billed per call) | cents |
| AgentCore Memory | about 0 (no strategies configured, events expire after 7 days) |
| Online evaluation | 0 (created paused; resuming it starts judge-model costs) |
| API Gateway, chat Lambda, DynamoDB on demand | cents (free tier covers most of it) |
| CloudFront, S3, Cognito | about 0 (free tiers, 5 demo users) |
| CloudWatch logs (7 days on our Lambda) | cents |
| AWS Budgets (first 2 budgets are free) and SNS email | 0 |
| WAF (flag off) | 0 (it would be about 5 to 8 USD per month if turned on) |

**Expected total: about 2 to 5 USD for one deploy-test-destroy day**, with a hard ceiling set by the API throttle
and your 20 USD budget alert (an alert only, it does not stop spending). The real risks are: leaving things running,
resuming the online evaluation, and a model-calling loop. Destroy right after testing.

## Before Phase 6 (needs your decisions)
1. Commit the Phase 4 and Phase 5 work (the user commits).
2. Provide the alert email address for `infra/inputs.json`. Confirm the SNS and Budgets emails by clicking the links.
3. Approve the deploy and the cost estimate above. Check model access for the Haiku 4.5 profile in this account first.
4. Run `scripts/configure_agentcore.py --reset` before any commit that follows a real configure run.
