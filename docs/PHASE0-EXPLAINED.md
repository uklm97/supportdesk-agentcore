# Phase 0 explained (plain language)

Written for you to read later. The technical version is in `PROGRESS.md`.

## What was Phase 0 for?
We planned two separate pieces and had to check they can live side by side:

1. **The AgentCore piece (`agentcore/`)**: the agent itself, its memory, its tool gateway, its safety rules and its quality checks.
   You describe it in JSON files. The `agentcore` command turns that JSON into AWS resources.
2. **Our own piece (`infra/`, not created yet)**: login (Cognito), the web API, the database, the website hosting, alarms and a budget.

Phase 0 asks: can the command deploy and delete the first piece cleanly, and can the second piece use what the first one creates?

## What I did (and what I did NOT do)
- I did NOT deploy anything. No AWS resources were created, changed or deleted. Your account is untouched.
- I upgraded the `agentcore` command on your laptop from 0.31.1 to 1.0.0, because you asked for the latest.
- I converted the project files to the 1.0.0 format with `agentcore migrate --yes`. Nothing was deployed, so this was safe.
- I ran `agentcore build` on the empty project. It runs fine, but an empty project proves very little.

## What I found
**Deploying.** One command: `agentcore deploy`. It creates one CloudFormation stack named `AgentCore-supportdesk-default`.
CloudFormation is AWS's "list of things that should exist", and deleting the stack deletes the things.

**Deleting.** There is no `destroy` command. You first remove everything from the project (`agentcore remove all --yes`),
then run `agentcore deploy --yes`, which tells AWS to delete the stack. It looks right on paper, but I have not run it. We test it in Phase 6.
An old stack from one of your earlier projects (`AgentCore-IncidentInvestigator-default`) shows as already deleted, so this route has worked before.

**Does `infra/` work alongside it?** Yes, in principle. The agent stack publishes values (agent id, gateway address, memory id) as stack "outputs".
Our second piece can read them.
One warning: the outputs are also "exports". If another stack hard-links to an export, AWS refuses to delete or change it. That would break our
deploy, destroy and redeploy cycle. So `infra/` will not hard-link. A small Python script will read the values and hand them over instead.

## Decisions you made
- Latest `agentcore` CLI.
- All our code in Python (the agent, the Lambdas, the tests, the scripts, and `infra/` too).
  The `agentcore/cdk/` folder is TypeScript, but the CLI generates and owns it. We do not edit it.
- Old resources in your AWS account are ignored. New project, new names.
- I explain every command before I run it.

## What is still not proven
- That delete-then-redeploy really works end to end.
- The exact names of the outputs.
These need a real deploy. I will do that only in Phase 6, after your approval and a cost estimate, so we pay for one test, not two.

## What comes next: Phase 1
The agent's building blocks, all in Python: the DynamoDB table layout, the tool Lambdas (look up an order, cancel an order and so on),
the Strands agent, and unit tests that use a fake model so they cost nothing. It runs on your laptop and deploys nothing.

## When to start a new chat
Start a new chat **now**. This one has a lot of command output in it, and every message resends all of it, which costs money.
Everything a new chat needs is in `PROGRESS.md`. Paste this as your first message:

> Read C:\Users\AI_Dev\projects\agentcore-projects\supportdesk\docs\PROGRESS.md and continue with the next unfinished phase.
> Use Git Bash for commands, explain what each command does before running it, pause after the phase to explain, and do not deploy without my approval.

Do the same after every phase.
