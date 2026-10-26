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
- `agentcore` CLI 1.0.0 (upgraded from 0.31.1 in Phase 0), Node 24, npm 11, uv 0.12, Python 3.14, Docker 29, AWS CLI 2.36. `cdk` is not installed globally (use npx).
- AWS: account <ACCOUNT_ID>, region us-east-1, CDK already bootstrapped (CDKToolkit stack exists).
- An unrelated Cognito pool `CustomerSupportGatewayPool` already exists in the account. Do not modify it. Create a new pool.
- The sibling folders `C:\Users\AI_Dev\projects\undercover` and `dice-roll-api` are unrelated to this project.

## State
- DONE: empty AgentCore project shell created with `agentcore create --name supportdesk --no-agent` (config files + CDK folder, git repo).
- DONE: the throwaway `starteragent` hello-world scaffold was deleted.
- DONE (Phase 0): CLI upgraded to 1.0.0, project migrated to v1 format, `agentcore build` works. See "Phase 0 findings" below.
- NOTHING is deployed to AWS. `agentcore/aws-targets.json` has no targets yet.
- The Phase 0 migration changes are COMMITTED (commit 08245f6).
- DONE (Phase 1, step 1 of 2): DynamoDB single-table design and tool logic, local only, 13 passing tests (`uv run pytest -q`). See "Phase 1 progress" below.
- Phase 1 step 1 is COMMITTED (commit d37e591).
- DONE (Phase 1, step 2 of 2): Strands agent under `app/supportdesk/`, 26 passing tests total. COMMITTED (commit 6f77697, committed by the user). See "Phase 1 step 2 progress" below.
- DONE (Phase 2, local only): runtime, memory, gateway + Lambda target, Cedar policy, evaluators and online eval are written into agentcore.json; `main.py` now reads the customer from the JWT and calls the gateway.
  User ran `uv run pytest -q`: 41 passed. User ran `agentcore build`: OK (schema accepted, including the REPLACE_* placeholders and `requestHeaderAllowlist`). See "Phase 2 progress" below.
  Phase 2 is NOT yet committed (ask the user to commit). `agentcore build` only checks the schema locally: the Cedar policy, evaluators and everything else are still unvalidated by AWS until a deploy.
- Phase 2 files were already committed before the Phase 3 commit (git status showed no Phase 2 changes pending).
- DONE (Phase 3, local only): `infra/` Python CDK app (auth stack + app stack), chat Lambda, `scripts/configure_agentcore.py`, `scripts/seed.py`, tests.
  User ran `uv run pytest -q`: 85 passed. User ran `npx cdk synth supportdesk-auth --quiet` in `infra/`: OK (app stack correctly skipped, inputs missing). COMMITTED by the user (commit 13bc3b9, 22 files). See "Phase 3 progress" at the end of this file.
- DONE (Phase 4, local only): React + TypeScript + Vite front end in `web/` with Cognito login and a chat screen; `scripts/write_web_config.py`. NOT yet committed. See "Phase 4 progress" at the end of this file.
- DONE (Phase 5, local only; nothing deployed): lint, mypy, audits, `cdk synth supportdesk-app`, cost estimate. NOT yet committed. See "Phase 5 progress" near the end of this file and docs/PHASE5-EXPLAINED.md.
- NEXT: Phase 6 (commit, user approves cost estimate, deploy, test, destroy, redeploy).

## Schema facts (confirmed against the 0.31.1 .llm-context; RE-CHECK against 1.0.0 before relying on them)
- Project name: letters and digits only, max 23 characters. Renaming a resource destroys and recreates it.
- Runtime authorizer: AWS_IAM or CUSTOM_JWT. Gateway authorizer: NONE, AWS_IAM or CUSTOM_JWT.
- Gateway Lambda targets use `compute` with host Lambda and an `implementation` binding, plus `toolDefinitions`.
- Gateway can attach a policy engine with mode LOG_ONLY or ENFORCE. Policies are Cedar.
- Memory strategies: SEMANTIC, SUMMARIZATION, USER_PREFERENCE, EPISODIC. Event expiry is 3 to 365 days.
- `agentcore validate` does NOT exist in 1.0.0. Run `agentcore build` after every edit to the JSON files instead.

## Phase 0 findings (2026-10-26, read-only; nothing deployed)
Plain-language version of this section: docs/PHASE0-EXPLAINED.md

### User decisions made in Phase 0
- Use the latest AgentCore CLI (now 1.0.0). All code we write is Python: Strands agent, tool Lambdas, tests, scripts, and `infra/` (Python CDK).
- The CLI-generated `agentcore/cdk/` is TypeScript. Leave it TypeScript and do not hand-edit it. It is generated plumbing, not our code.
- The user may have leftover resources from earlier projects in the AWS account. Do not reuse or touch them. Create new ones with new names.
- Before running ANY command, tell the user in plain words what it does and why. Explain, do not just chain commands.
- The user wants everything documented so they can read it later. Keep docs/PHASE0-EXPLAINED.md style notes for each phase.

### What was done (nothing deployed, no AWS resources created or changed)
- Upgraded the global CLI 0.31.1 -> 1.0.0 (`npm install -g @aws/agentcore@latest`).
- Ran `agentcore migrate --yes`: the project is now v1 format (agentcore.json `version: 2`, `migratedFrom: "v1"`). Nothing was deployed, so no names had to be kept.
  The 11 changed files are listed in agentcore/.cli/migrate/result-*.md. Migration removed jest/prettier from the generated CDK app and its sample test.
- Ran `agentcore build` on the empty project: it works and synthesizes an empty `cdk.out`. This is not a real test of outputs.

### CLI 1.0.0 facts (verified from `--help` and from the library source in agentcore/cdk/node_modules)
- There is no `validate` command in 1.0.0. The old "run `agentcore validate`" rule is dead. Use `agentcore build` to check the project.
- `agentcore deploy [--target <name>] [--yes]`. No `--dry-run` or `--diff` anymore. Preview with `agentcore build`, then `npx cdk diff` inside agentcore/cdk.
  The stack is named `AgentCore-<project>-<target>`. The `default` target is created automatically on first deploy from your account and region.
- There is no `destroy` command. Teardown path: `agentcore remove all --yes`, then `agentcore deploy --yes`.
  On deploy, `--yes` confirms removing the stack when the project declares nothing. This is NOT yet tested against real AWS.
  Evidence it works: a stack from an older project, `AgentCore-IncidentInvestigator-default`, shows DELETE_COMPLETE.
- Other commands now: build, status, logs, traces, invoke, export, migrate, remove, plus resource groups (harness, runtime, gateway, identity, memory, eval, payment).
  `agentcore add` can add: harness, runtime, runtime-endpoint, gateway, gateway-target, gateway-connector, policy-engine, policy, credentials, memory, evaluator, online-eval, config-bundle, payment-manager, payment-connector.
  `agentcore create --template` has `agent-python-strands` and `empty` (the one we used). 1.0.0 also adds "harness" (config-defined agents, no code).
- The generated CDK app is now two small files (bin/cdk.ts, lib/cdk-stack.ts). `lib/cdk-stack.ts` is meant to be extended with our own resources.
  That is another way to add DynamoDB etc. We chose a separate `infra/` instead. Keep that choice unless a problem shows up.

### Stack outputs (read from @aws/agentcore-cdk 1.0.0 source; not yet seen in a real deployed stack)
- Every output is also a CloudFormation EXPORT named `<StackName>-<...>`. Runtime: RuntimeId, RuntimeArn, RoleArn (plus Endpoint Id/Arn).
  Gateway: Id, Arn, Url, and target Ids. Memory: Id, Arn, MemoryIds, MemoryNames. Also evaluators, online evals, policy engines, policies, tool Lambda Arn/Name.
- Consequence: `infra/` can read these. But if `infra/` uses CloudFormation Fn::ImportValue on an export, CloudFormation blocks deleting or changing that export
  while `infra/` still uses it. Decision: `infra/` must NOT use ImportValue. A Python script reads the outputs with
  `aws cloudformation describe-stacks` and passes them to the `infra/` CDK app as CDK context or SSM parameters.
- Open question for the real deploy: output logical IDs end in "Output" and may include the runtime name. Confirm exact names after the first deploy.

### Still unverified (needs a real deploy, so needs your approval and a cost estimate)
- That teardown (`remove all` then `deploy --yes`) deletes everything cleanly, and that redeploy then works.
- The exact output names in a deployed stack.
- Whether `.llm-context/*.ts` (written by the 0.31.1 CLI) still matches the 1.0.0 schema. Re-read it, and check `agentcore build` errors, when adding resources.

## Next steps
1. Phase 0: DONE except the real-deploy checks above. Those will be folded into Phase 6 (deploy, test, destroy, redeploy) so we do not pay for a throwaway deploy.
2. Phase 1: DONE (both steps). The text below is the old plan, kept for reference. Next is Phase 2.
   Old plan: step 1 (DynamoDB design, tool logic, Lambda handler, tests) is done.
   Remaining: the Strands agent under `app/` (system prompt, tools that call the order functions, unit tests with a mocked model),
   then update this file and write docs/PHASE1-EXPLAINED.md. All Python. Local only, no deploy.
   Agent code location: `agentcore add runtime` has no template option, and the Strands template exists only in `agentcore create --template agent-python-strands`.
   Either write the agent files by hand (preferred, no exploration needed) or scaffold a scratch project outside this repo and copy the pattern.
   `agentcore add runtime --help` was already read (1.0.0): flags include --name, --language, --protocol, --authorizer-type, --authorizer-configuration, --environment-variables, --additional-policies.
   Also create docs/PHASE1-EXPLAINED.md in plain language when the phase ends.
3. Phase 2: DONE locally (tests and `agentcore build` pass). Real validation happens at deploy time (Phase 6).
4. Phase 3 (NEXT): Python CDK. (a) `auth` stack: Cognito user pool + app client + test users, deployed first. (b) `infra/` app stack: DynamoDB table named exactly `supportdesk-orders`
   (pay-per-request), API Gateway HTTP API + Lambda that calls the runtime with the user's JWT, S3 + CloudFront, alarms, budget, WAF behind an off-by-default flag.
   (c) A Python script that reads the auth stack outputs and writes the discovery URL and client id into agentcore.json (runtime AND gateway), and a seed script that loads orders under `CUSTOMER#<sub>`.
   No ImportValue (see "Stack outputs"). Local only: `cdk synth` and tests, no deploy.
   Phase 4: React front end with Cognito login.
5. Phase 5: lint, type checks, tests, `cdk synth`, cost estimate, user approval. Phase 6: deploy, test, destroy, redeploy.

## Phase 1 progress (step 1 done)
- Files: `pyproject.toml` (Python 3.12 via uv, boto3; dev: pytest, moto), `.python-version`, `.gitignore`,
  `lambdas/orders/orders_core.py` (get_order, list_orders, cancel_order, create_ticket), `lambdas/orders/handler.py`, `tests/test_orders.py`.
- DynamoDB: one pay-per-request table. `PK = CUSTOMER#<id>`, `SK = ORDER#<id>` or `TICKET#<id>`. Order fields: status, created_at, total_cents, items.
  Statuses used: PLACED, PROCESSING, SHIPPED, CANCELLED. Tickets start OPEN.
- Cancel is allowed only from PLACED or PROCESSING, enforced by a DynamoDB ConditionExpression (race-safe).
- Business errors are returned as data: `{"error": CODE, "message": ...}` with codes NOT_FOUND, NOT_CANCELLABLE, INVALID_INPUT, UNKNOWN_TOOL.
- The Lambda reads the table name from env var `ORDERS_TABLE`.
- Tests run in about 8 seconds with moto, no AWS calls: `cd supportdesk; uv run pytest -q`.
- ASSUMPTION to verify in Phase 2: the gateway passes tool args as the Lambda event and the tool name in
  `context.client_context.custom["bedrockAgentCoreToolName"]`, prefixed `<target>___`. `handler.py` handles both prefixed and bare names.
- ASSUMPTION: the code trusts the `customer_id` argument. Phase 2 must add a Cedar policy comparing it to the logged-in user (JWT claim).
- Known stale doc: `AGENTS.md` still mentions `agentcore validate` (does not exist in 1.0.0). Use `agentcore build`.

## Phase 1 step 2 progress (done, plain-language version: docs/PHASE1-EXPLAINED.md)
- Files in `app/supportdesk/`: `prompts.py` (system prompt), `tools.py` (`build_tools(backend, customer_id)`), `agent.py` (`build_agent`, `default_model`),
  `main.py` (`BedrockAgentCoreApp` entrypoint plus testable `run()`). Tests: `tests/conftest.py` (shared `table` fixture, moved out of test_orders.py),
  `tests/fake_model.py` (scripted fake Strands model), `tests/test_tools.py`, `tests/test_agent.py`.
- Installed (uv.lock): strands-agents 1.62.0, bedrock-agentcore 1.25.0. `pyproject.toml` pytest `pythonpath` now includes `app/supportdesk`.
- Design: the tools do NOT expose `customer_id` to the model. It is bound in a closure when the agent is built (one agent per request).
  A test proves that a model passing `customer_id=bob` still acts as the signed-in customer.
- Tools talk to a `backend(tool_name, args) -> dict`. In tests that is `handler.handle` over moto. In `main.py` the default `gateway_backend` raises NotImplementedError (Phase 2 wires the gateway).
- The agent prompt makes the model ask for confirmation before cancelling. This is only a prompt rule, not enforced in code. Consider a code or policy guard later.
- Model: Bedrock model id default `us.anthropic.claude-haiku-4-5-20251001-v1:0`, overridable with env var `MODEL_ID`. UNVERIFIED that it is available in this account. Check before Phase 6.
- The fake model streams events by hand (messageStart, contentBlock*, messageStop). It works with strands 1.62.0.
- Harmless warning in pytest: a Pydantic deprecation inside the bedrock_agentcore library. Ignore.
- NOT TESTED against a real model or a real AgentCore runtime. `main.py` was only imported and its `run()` tested, never started with `app.run()`.

### Phase 2 TODOs created by this step
- Register the runtime: `agentcore add runtime` (flags: --name, --language, --protocol, --authorizer-type, ...). Set `entrypoint` to `main.py` and `codeLocation` to `app/supportdesk`.
  The CodeZip build probably needs a requirements file or pyproject INSIDE `app/supportdesk` (strands-agents, bedrock-agentcore). Check what `agentcore build` expects.
  The modules use flat imports (`from agent import ...`), which works only when `app/supportdesk` is the code root. Keep it that way.
- Replace `payload["customer_id"]` in `main.py` with the verified JWT claim (runtime authorizer CUSTOM_JWT with the new Cognito pool). Never trust the payload in production.
- Implement `gateway_backend` to call the AgentCore Gateway (MCP tools) and add the Cedar policy that compares the customer id with the token.
- Decide whether to add session memory, and a guard that blocks `cancel_order` unless the customer confirmed.

## Phase 2 progress (edits written; plain-language version: docs/PHASE2-EXPLAINED.md)
### Decision made in Phase 2 (user accepted the recommendation)
- Cognito goes in its OWN small CDK stack (`auth`), deployed FIRST, so the runtime and gateway can verify the real user JWT (CUSTOM_JWT).
  Deploy order: auth stack -> `agentcore/` -> rest of `infra/`. Teardown in reverse. This replaces the single-`infra/` idea in "Decisions".
  A Phase 3 Python script must write the pool's discovery URL and app client id into agentcore.json (runtime AND gateway authorizers).
  Until then the JSON holds the placeholders `REPLACE_USER_POOL_ID` and `REPLACE_APP_CLIENT_ID`. Deploying with them will fail or be useless.

### What was written
- `agentcore.json`: runtime `supportdesk` (CodeZip, `app/supportdesk`, `main.py`, PYTHON_3_12, CUSTOM_JWT, idle timeout 600 s);
  memory `supportdeskmemory` (7-day expiry, NO long-term strategies = short-term only, cheapest);
  gateway `supportdeskgw` (MCP, CUSTOM_JWT, semantic search off, policy engine `supportdeskpolicies` in ENFORCE) with Lambda target `orders`
  (path `lambdas/orders`, handler `handler.lambda_handler`, 4 tool definitions, IAM limited to the table `supportdesk-orders`);
  policy engine `supportdeskpolicies` with one Cedar policy `customer_owns_the_call`;
  evaluators `CancelConfirmation` (SESSION) and `ReplyAccuracy` (TRACE); online eval `supportdeskonlineeval` at samplingRate 1 (percent), `enableOnCreate: false`.
- `app/supportdesk/identity.py` (reads `sub` from the Authorization header), `gateway.py` (MCP client, prefixes tool names with `orders___`),
  `requirements.txt`; `main.py` rewritten (identity from JWT, gateway backend, optional memory session manager); `agent.py` takes `session_manager`.
- `lambdas/orders/handler.py`: table name now defaults to `supportdesk-orders` (agentcore.json has no env var field for gateway Lambdas).
- Tests: `tests/test_agent.py` updated for the new `run(payload, customer_id, backend, ...)` signature; new `tests/test_identity_gateway.py`.

### Verified in Phase 2 from AWS docs (Cedar and evaluators)
- Principal `AgentCore::OAuthUser`; JWT claims are tags (`principal.hasTag("sub")`, `principal.getTag("sub")`); tool arguments are `context.input.<name>`;
  action ids are `<Target>___<tool>`; a policy that names specific actions needs the gateway ARN, a policy over ANY action uses `resource is AgentCore::Gateway`.
  Because the gateway ARN is unknown before the first deploy, the policy covers any action on any gateway and relies on all four tools having `customer_id`.
- Custom judge placeholders: SESSION `{context}`, `{available_tools}`; TRACE `{context}`, `{assistant_turn}`. `Builtin.Faithfulness` exists. `Builtin.GoalSuccessRate` is NOT used.
- Memory env var format `MEMORY_<NAME>_ID` (uppercase). Local-dev gateway env vars are `AGENTCORE_GATEWAY_<NAME>_URL`.

### UNVERIFIED / likely to need fixes at `agentcore build` or the first deploy
- Cedar: `context has input` and `FAIL_ON_ANY_FINDINGS` may be rejected by the policy validator. If so, try without the `context has input` line or set `IGNORE_ALL_FINDINGS` temporarily.
- Whether the deployed runtime receives `AGENTCORE_GATEWAY_SUPPORTDESKGW_URL` and `MEMORY_SUPPORTDESKMEMORY_ID` (docs only say so for local dev / "CDK-injected"). `main.py` also accepts `GATEWAY_URL`. Confirm after first deploy.
- `requestHeaderAllowlist: ["Authorization"]` on the runtime: not confirmed that it is needed or accepted. If `agentcore build` rejects it, remove it and check how the runtime exposes the token.
- `requirements.txt` vs pyproject for the CodeZip build, and whether `aws-opentelemetry-distro` belongs there (copied from memory of the starter template).
- Judge model `us.anthropic.claude-haiku-4-5-20251001-v1:0` for the evaluators (docs example uses a Sonnet id). Model availability in this account is still unchecked.
- Gateway passes tool args as the Lambda event and the tool name in client context (the Phase 1 assumption) is still unverified.
- `gateway.py` uses Strands `MCPClient.call_tool_sync`; the import name of the streamable HTTP client differs between `mcp` versions (handled with a fallback). Untested against a real gateway.
- Gateway Lambda target DynamoDB table `supportdesk-orders` does not exist until `infra/` creates it with exactly that name.
- Customer ids are now Cognito `sub` values, not "alice". The seed script in Phase 3 must create order rows under `CUSTOMER#<sub>`.
- The cancel-confirmation guard in code was NOT added (still only a prompt rule); the `CancelConfirmation` evaluator only measures it after the fact.

## Phase 3 progress (DONE locally: tests and auth synth pass; nothing deployed; plain-language version: docs/PHASE3-EXPLAINED.md)
### Files
- `pyproject.toml`: new dependency group `infra` (aws-cdk-lib, constructs), `[tool.uv] default-groups = ["dev","infra"]`, pytest `pythonpath` now also has `lambdas/chat`, `infra`, `scripts`.
  `.gitignore`: `infra/cdk.out/`, `infra/inputs.json`.
- `infra/app.py`, `infra/cdk.json` (`uv run python app.py`), `infra/inputs.example.json`, `infra/supportdesk_infra/{settings,auth_stack,app_stack,guardrails}.py`.
  - Stack `supportdesk-auth`: user pool `supportdesk-users` (admin-created users only, no hosted UI), groups `customers` and `staff`, app client `supportdesk-web` (no secret, SRP and USER_PASSWORD flows),
    plain outputs `UserPoolId`, `UserPoolClientId`, `DiscoveryUrl` (no export names). All resources DESTROY.
  - Stack `supportdesk-app` (skipped by `app.py` while inputs are missing): table `supportdesk-orders`, private S3 bucket + CloudFront (price class 100), chat Lambda + HTTP API `POST /chat` with a JWT authorizer
    (audience = app client id), alarms and a monthly budget by email, WAF only when `enable_waf` is true. Outputs: ApiUrl, SiteUrl, SiteBucketName, DistributionId, OrdersTableName.
  - Inputs reach the app stack through CDK context or `infra/inputs.json` (written by the configure script). No ImportValue anywhere.
- `lambdas/chat/chat_handler.py`: stdlib only. Forwards the caller's Bearer token to the runtime (`/runtimes/<encoded ARN>/invocations?qualifier=DEFAULT`, session id header); never sends a customer id.
- `scripts/configure_agentcore.py` (fills the 2 authorizers in agentcore.json, byte-exact so CRLF is kept; `--reset` restores placeholders; writes `infra/inputs.json`), `scripts/stack_outputs.py`,
  `scripts/seed.py` + `scripts/seed_data.py` (3 users: alice, bob, staff@example.com; orders under `CUSTOMER#<sub>`; `--dry-run`).
- Tests: `tests/test_infra.py`, `test_chat_handler.py`, `test_seed.py`, `test_configure_agentcore.py`.
### Open items / UNVERIFIED
- Verified locally: 85 tests pass (the app stack is synthesized in memory by `tests/test_infra.py`), and `npx cdk synth supportdesk-auth` works from `infra/` (cdk CLI 2.1146.1 via npx).
  The `cdk synth` of the APP stack from the command line has not been run (needs `infra/inputs.json`); the in-memory synth in the tests covers the template.
  Harmless notice: "85 feature flags are not configured". Ignore for now.
- Needs a real deploy to confirm: that the runtime accepts the chat Lambda's HTTPS call with a Bearer token (URL format and session header are from memory); that API Gateway's JWT authorizer accepts the Cognito ACCESS token
  (it compares the `client_id` claim with the audience); the exact runtime ARN output name (the `runtime_arn` input comes from the agentcore stack after its deploy).
- `test_reset_puts_the_placeholders_back` expects the committed agentcore.json to hold the REPLACE_* placeholders. After running the configure script for real, run it with `--reset` before committing/testing.
- The AppStack budget covers the whole account, not only this project. The alert email must be confirmed by clicking the SNS and Budgets emails.
- Deploy order when the time comes: `supportdesk-auth` -> configure script -> `agentcore deploy` -> configure script with `--runtime-arn` -> `supportdesk-app` -> seed script. Teardown in reverse.
- Note: in this chat the assistant ran one read-only directory listing against the then-current rule; the user has since changed the rule so the assistant runs commands (see LATEST WORKFLOW).

## Phase 4 progress (DONE locally; nothing deployed; plain-language version: docs/PHASE4-EXPLAINED.md)
### Files (all under `web/` unless noted)
- `package.json`, `tsconfig.json` (strict), `vite.config.ts` (port 5173 strict = the origin the API CORS rule allows; `global` defined for the Cognito library; vitest config), `index.html`.
- `src/config.ts` (reads `/config.json` at run time, `parseConfig` validates), `src/auth.ts` (amazon-cognito-identity-js: SRP sign-in, restore/refresh session, sign out; handles NEW_PASSWORD_REQUIRED with a plain error),
  `src/api.ts` (`sendChat`: POST `<apiUrl>/chat` with `Authorization: Bearer <ACCESS token>`, body `{prompt, session_id?}`, never a customer id; 401 -> "sign in again"),
  `src/App.tsx`, `src/Login.tsx`, `src/Chat.tsx`, `src/main.tsx`, `src/styles.css`.
- Tests: `src/config.test.ts`, `src/api.test.ts` (8 vitest tests). `tests/test_write_web_config.py` (3 pytest tests).
- `scripts/write_web_config.py`: reads `supportdesk-auth` (UserPoolId, UserPoolClientId) and `supportdesk-app` (ApiUrl) outputs, writes `web/public/config.json` (git-ignored). Read-only toward AWS. `--api-url` and `--dry-run` flags.
- `.gitignore`: `web/node_modules/`, `web/dist/`, `web/public/config.json`.
- Installed: react 19, react-dom 19, amazon-cognito-identity-js 6, vite 8, vitest 5, typescript 7, @vitejs/plugin-react 6.
### Verified locally
- `npm run typecheck` clean, `npm test` 8 passed, `npm run build` OK (JS 313 kB, 96 kB gzip), `uv run pytest -q` 88 passed.
### Open items / UNVERIFIED
- Nothing renders in a browser yet and there are no component tests (login/chat screens were only type-checked and built). Needs a manual check against the real deployment.
- The front end uses the ACCESS token. Whether API Gateway's JWT authorizer accepts it is still unverified (see Phase 3 open items).
- GAP: `infra/` does NOT upload `web/dist` to the site bucket (no BucketDeployment). Phase 6 plan: `npm run build`, write config, then `aws s3 sync web/dist s3://<SiteBucketName>` and a CloudFront invalidation (both change AWS: need approval). Or add a BucketDeployment to app_stack (adds a helper Lambda; decide in Phase 5).
- `config.json` must be uploaded with the site too (it lives in `web/public/`, so `vite build` copies it into `dist/`). Write it BEFORE building.
- Demo users are created with a permanent password by `scripts/seed.py`, so no new-password challenge is needed. Sign-in uses the email address.
- Local run (after deploy): write config, then `cd web; npm run dev` and open http://localhost:5173 (allowed by the API CORS rule).
- The npm install printed no audit; `--no-audit` was used, so dependency vulnerabilities have not been checked. Consider `npm audit` in Phase 5.

## Phase 5 progress (DONE locally; nothing deployed; details and cost table: docs/PHASE5-EXPLAINED.md)
- Checks now passing: `uv run pytest -q` 92 passed; `uvx ruff check app lambdas infra/app.py infra/supportdesk_infra scripts tests` clean (config in pyproject `[tool.ruff]`);
  mypy clean (`MYPYPATH=lambdas/orders:lambdas/chat:app/supportdesk:infra:scripts uv run --with mypy mypy --ignore-missing-imports --explicit-package-bases lambdas app infra/app.py infra/supportdesk_infra scripts`);
  `pip-audit` clean; `web/` typecheck, 8 tests, build and `npm audit` clean; `agentcore build` OK; `npx cdk synth supportdesk-app` OK with example inputs passed as `-c` flags and `-o` to a temp folder.
- Fixes: `mcp` pinned `>=1.30,<2` (CVE in 2.1.1; strands caps mcp below 2.2); `gateway.py` uses `streamablehttp_client` (accepts `headers`); API stage throttle 5 rps / burst 10 in `app_stack.py` (+ test).
- Synth summary of the app stack: table PAY_PER_REQUEST (DESTROY), private S3 + CloudFront PriceClass_100, chat Lambda python3.12 256 MB 29 s with 7-day log group, JWT-protected `POST /chat`, monthly budget 20 USD.
- DECIDED: the site is uploaded with `scripts/deploy_web.py` (`aws s3 sync` + CloudFront invalidation, `--dry-run` available), not a BucketDeployment. It changes AWS: run only in Phase 6 with approval. 3 tests.
- Verified read-only: Bedrock inference profile `us.anthropic.claude-haiku-4-5-20251001-v1:0` is ACTIVE in us-east-1. Invocation permission for this account is still UNVERIFIED.
- Left alone: `npm audit` high finding (`brace-expansion`) in generated `agentcore/cdk` (build-time only); a 731-day log group in the generated agentcore template (find out after deploy).
- Cost estimate: about 2 to 5 USD for one deploy-test-destroy day, mostly Bedrock. Prices are from memory, not checked today. User has NOT yet approved a deploy.
- Phase 6 prerequisites: user commits; alert email for `infra/inputs.json`; model access check; approval. Run `configure_agentcore.py --reset` before committing after a real configure run.

## Working rules learned
- Do not re-verify facts already written in this file. Do not scaffold scratch projects to explore. Batch work, write files, then test.
- LATEST WORKFLOW (user, end of Phase 3, overrides everything below about who runs commands): THE ASSISTANT RUNS THE COMMANDS ITSELF (through Git Bash) and shows the user the result. Still explain in one plain sentence what each command does before running it. The assistant must still NEVER deploy or run anything that creates, changes or deletes AWS resources without the user's explicit approval and a cost estimate first. The 4 lines below describe the OLDER "user runs commands" workflow and are SUPERSEDED:
- OLD WORKFLOW (superseded): the assistant does NOT run shell commands.
  For each step: (1) explain in plain words what the command does and why, (2) give the exact command in a fenced code block
  so the user can copy and run it in Git Bash, (3) wait for the user to paste the output, then continue.
  File edits by the assistant are still fine. The user wants to learn what is happening. This stays in force until the user says otherwise.
- Keep chats short: start a new chat after each phase or step.
- COST LESSONS from Phase 3:
  - NEVER search or read inside `agentcore/cdk/cdk.out/`, `agentcore/cdk/node_modules/`, `.venv/`, `infra/cdk.out/` or `uv.lock`. They hold huge single-line files. Search only inside `app/`, `lambdas/`, `infra/supportdesk_infra/`, `scripts/`, `tests/`, `docs/`.
  - Read PROGRESS.md ONCE (use start_line/end_line if it is truncated). Do not re-read it. Do not run wide regex searches like `PK|SK`.
  - Keep each editor call under 6000 characters. Split big files up front (the editor rejects larger ones and the text then has to be sent twice).
  - SUPERSEDED: the user now WANTS the assistant to run commands (see LATEST WORKFLOW). Keep command output small (pipe through `tail -n 30` or `head -n 40`, use `-q` flags) because every output line is re-billed on every later turn.
  - Phase 4 should be small: write the front end files, then run `npm install` and the build yourself (quiet flags, short output).
  - The cost the user is talking about is the CLAUDE API cost of the chats (not AWS). Biggest levers: one phase per chat, no searches in generated folders, no repeated file reads, short command output.

## USER DECISIONS after Phase 5 (2026-10-27)
- WAF stays OFF (enable_waf false) to keep costs down.
- The "100 chat turns" in the cost estimate was only a sizing assumption. Test with about 10 to 20 turns (about 0.15 to 0.30 USD of model calls).
- Keep Phase 6 chats short: no re-reading files, tiny command output, deploy one stack at a time.

## New-chat starter prompt (PHASE 6 version, use this one)
"Read C:\Users\AI_Dev\projects\agentcore-projects\supportdesk\docs\PROGRESS.md once (it is long: read the State section and the Phase 5 progress section first, then only what you need) and continue with Phase 6 (deploy, test, destroy).
YOU run the commands yourself in Git Bash. Before each one, say in one plain sentence what it does. Keep command output short.
Before EACH command that creates, changes or deletes AWS resources, tell me the cost and wait for my yes. WAF stays off. Deploy one stack at a time in the order from PROGRESS.md.
Do not search inside cdk.out, node_modules, .venv or uv.lock. Keep every file edit under 6000 characters. Pause after the phase to explain.
My alert email is: <PUT YOUR EMAIL HERE>"

## Phase 5 starter prompt (superseded)
"Read C:\Users\AI_Dev\projects\agentcore-projects\supportdesk\docs\PROGRESS.md once and continue with Phase 5 (quality checks and pre-deploy review: lint, type checks, npm audit, `cdk synth` of the app stack, cost estimate).
YOU run the commands yourself in Git Bash (not me). Before each one, say in one plain sentence what it does. Keep command output short. Never run anything that changes AWS (deploy, create, delete) without my approval and a cost estimate.
You may edit files directly. Do not search inside cdk.out, node_modules, .venv or uv.lock. Do not re-verify facts already in PROGRESS.md. Keep every file edit under 6000 characters.
Pause after the phase to explain. Do not deploy anything without my approval and a cost estimate."
Phase 5 should also settle the open item from Phase 4: how the built site gets into the S3 bucket (`aws s3 sync` vs a BucketDeployment).

## Phase 4 starter prompt (superseded)
"Read C:\Users\AI_Dev\projects\agentcore-projects\supportdesk\docs\PROGRESS.md once and continue with Phase 4 (React front end with Cognito login).
YOU run the commands yourself in Git Bash (not me). Before each one, say in one plain sentence what it does. Keep command output short. Never run anything that changes AWS (deploy, create, delete) without my approval and a cost estimate.
You may edit files directly. Do not search inside cdk.out, node_modules, .venv or uv.lock. Do not re-verify facts already in PROGRESS.md. Keep every file edit under 6000 characters.
Pause after the phase to explain. Do not deploy anything without my approval and a cost estimate."

## Older starter prompt
"Read C:\Users\AI_Dev\projects\agentcore-projects\supportdesk\docs\PROGRESS.md and continue with the next unfinished phase.
Use Git Bash for commands, explain what each command does before running it, pause after the phase to explain,
and do not deploy without my approval."

## Phase 6 progress (2026-10-27, in progress)
- Deployed in order and OK: `supportdesk-auth`, `agentcore deploy` (stack AgentCore-supportdesk-default), `supportdesk-app`, seed script, web upload (`write_web_config.py`, `npm run build`, `deploy_web.py`).
- Site: <SITE_URL> . Demo users alice, bob, staff (@example.com). The password was printed once by seed.py.
- Fix for local scripts: `uv add "botocore[crt]"` (the `aws login` credentials need it). This changed pyproject.toml and uv.lock.
- `uv run pytest -q`: 91 passed, 1 failed (`test_reset_puts_the_placeholders_back`). Expected while real ids are in agentcore.json. Run `configure_agentcore.py --reset` before committing.
- Live test with alice: all 4 orders, statuses, dates and totals matched seed_data.py.
- Rules 8 and 9 (order dates, no shipping promises) were added to app/supportdesk/prompts.py and deployed. Further notes are kept locally.

