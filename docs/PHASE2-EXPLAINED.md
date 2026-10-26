# Phase 2 explained: wiring the agent to AgentCore (still nothing deployed)

No AWS resources exist and nothing costs money yet. This phase only wrote configuration and code.
Result of the local checks: all 41 tests pass and `agentcore build` succeeds. That only proves the files are well formed.
AWS has not seen any of it yet, so policy and runtime problems can still show up at the first deploy.

## The big picture
A customer logs in (Cognito) and talks to the agent. The agent never touches the database directly. It calls tools through
a **gateway**, and the gateway checks a **policy** before the tool runs.

## The decision we made
Cognito (the login service) gets its own tiny stack, deployed first. The runtime and the gateway both need to know "which
login service do I trust?", and that answer only exists after Cognito is created. The deploy order is now:
login stack -> AgentCore -> the rest. Teardown is the reverse. Until the login stack exists, agentcore.json holds
`REPLACE_USER_POOL_ID` and `REPLACE_APP_CLIENT_ID`. A Phase 3 script fills them in.

## What each piece is
- **Runtime** (`supportdesk`): where the agent code runs. It only accepts requests with a valid login token.
- **Identity from the token:** `identity.py` reads the user's id (`sub`) from the token. The request body can no longer say who you are.
- **Gateway** (`supportdeskgw`) + **orders target:** a doorway in front of the Lambda holding the 4 order tools. `gateway.py` calls it using the user's own token.
- **Cedar policy:** one rule: "a tool call is allowed only if its `customer_id` equals the `sub` of the caller's token". Anything else is denied.
  This is the real protection: even if the agent were tricked, the gateway would refuse a call for someone else's orders.
- **Memory:** short-term only (the conversation), kept 7 days. No long-term strategies, because they cost extra and we do not need them.
- **Evaluators:** two LLM judges. `CancelConfirmation` checks the agent asked "are you sure?" before cancelling. `ReplyAccuracy` checks answers match the tool data.
  The online eval samples 1 percent of sessions and is created **paused**, so no judge costs until you resume it.

## What is NOT proven
Everything above is untested against real AWS. The list of things most likely to need a fix is in PROGRESS.md under
"UNVERIFIED". The biggest ones: whether the Cedar validator accepts the policy, whether the runtime receives the token
header and the gateway/memory environment variables, and whether the order Lambda receives arguments the way we assume.

## Side effect to remember
Customer ids are now the Cognito `sub` (a long random id), not "alice". The test data we load later must use those ids.

## Cost note
Nothing is deployed, so nothing is billed. A cost estimate comes before any deploy.
