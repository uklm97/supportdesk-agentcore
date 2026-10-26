# SupportDesk - Progress and Handoff

Read this file first in any new chat. Keep it updated at the end of every phase.

## Goal
A production-grade, end-to-end customer support agent on AWS. Real user login, a web front end, several AWS services.
It must be deployable, so we can deploy, test, destroy, and redeploy cleanly. It is not a hello-world project.

## Decisions (agreed with the user)
- Domain: customer support agent ("SupportDesk"). Customers act on their own orders. Staff are in a separate group.
- Agent framework: Strands (project 1). LangGraph is for the NEXT project, not this one.
- Two layers, deployed in this order and destroyed in reverse:
  1. `agentcore/` - AgentCore project managed by the `agentcore` CLI: runtime, memory, gateway, Cedar policies, evaluators.
     Do not hand-edit the generated CDK under `agentcore/cdk/`. The JSON files are the source of truth.
  2. `infra/` - separate CDK app (not created yet): Cognito, API Gateway HTTP API, Lambda, DynamoDB, S3, CloudFront, alarms, budget.
  This split is an assumption. It must be verified in Phase 0 (does the CLI deploy and destroy cleanly alongside it?).
- Cost rules: pay-per-use services only (no NAT gateway, no provisioned capacity, no always-on servers), cheaper Bedrock model
  in dev (switchable by config), low online-eval sampling rate, short log retention and memory expiry, WAF behind an off-by-default flag,
  an AWS Budget alarm, and everything destroyed after testing.
- Pause after every phase and explain what was built and why. Never deploy without the user's explicit approval and a cost estimate.

## Environment (verified 2026-10-26)
- Windows laptop, VS Code with Cline. User wants commands run through Git Bash: `& 'C:\Program Files\Git\bin\bash.exe' -c '<cmd>'`.
  Keep bash commands simple: nested quotes and `for` loops break when passed through PowerShell.
- `agentcore` CLI 0.31.1, Node 24, npm 11, uv 0.12, Python 3.14, Docker 29, AWS CLI 2.36. `cdk` is not installed globally (use npx).
- AWS: account <ACCOUNT_ID>, region us-east-1, CDK already bootstrapped (CDKToolkit stack exists).
- An unrelated Cognito pool `CustomerSupportGatewayPool` already exists in the account. Do not modify it. Create a new pool.
- The sibling folders `C:\Users\AI_Dev\projects\undercover` and `dice-roll-api` are unrelated to this project.

## State
- DONE: empty AgentCore project shell created with `agentcore create --name supportdesk --no-agent` (config files + CDK folder, git repo).
- DONE: the throwaway `starteragent` hello-world scaffold was deleted.
- NOTHING is deployed to AWS. `agentcore/aws-targets.json` has no targets yet.
- NOT STARTED: agent code, tools, policies, memory, evaluators, `infra/`, front end, tests, scripts.

## Schema facts already confirmed (from agentcore/.llm-context/agentcore.ts)
- Project name: letters and digits only, max 23 characters. Renaming a resource destroys and recreates it.
- Runtime authorizer: AWS_IAM or CUSTOM_JWT. Gateway authorizer: NONE, AWS_IAM or CUSTOM_JWT.
- Gateway Lambda targets use `compute` with host Lambda and an `implementation` binding, plus `toolDefinitions`.
- Gateway can attach a policy engine with mode LOG_ONLY or ENFORCE. Policies are Cedar.
- Memory strategies: SEMANTIC, SUMMARIZATION, USER_PREFERENCE, EPISODIC. Event expiry is 3 to 365 days.
- Run `agentcore validate` after every edit to the JSON files.

## Next steps
1. Phase 0 (remaining): verify how `agentcore deploy` and the destroy path work and whether `infra/` can read the agent's outputs.
2. Phase 1: tool Lambdas, DynamoDB table design, Strands agent, unit tests with a mocked model.
3. Phase 2: Cedar policies, memory, gateway wiring, evaluators.
4. Phase 3: `infra/` CDK app. Phase 4: React front end with Cognito login.
5. Phase 5: lint, type checks, tests, `cdk synth`, cost estimate, user approval. Phase 6: deploy, test, destroy, redeploy.

## New-chat starter prompt
"Read C:\Users\AI_Dev\projects\agentcore-projects\supportdesk\docs\PROGRESS.md and continue with the next unfinished phase.
Use Git Bash for commands, pause after the phase to explain, and do not deploy without my approval."
