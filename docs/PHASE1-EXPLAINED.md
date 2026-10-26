# Phase 1 explained: the agent's building blocks (local only)

Nothing in this phase touches AWS. No cost, nothing deployed. Everything runs on your laptop with `uv run pytest -q`.

## What we built

### Step 1: the data and the business rules
- **A DynamoDB table design.** One table holds a customer's orders and tickets. Each row's key starts with the customer
  (`CUSTOMER#alice`), so a lookup for one customer can only ever read that customer's rows.
- **`orders_core.py`:** four actions (get an order, list orders, cancel an order, open a ticket). The rule "only PLACED or
  PROCESSING orders can be cancelled" is enforced by DynamoDB itself, so two people clicking at the same moment cannot break it.
- **`handler.py`:** the small Lambda wrapper that will later sit behind the AgentCore Gateway.

### Step 2: the agent
- **`prompts.py`: the instructions.** Plain-English rules for the model: look things up, never guess, ask before cancelling,
  show money in dollars, refuse to help with anyone else's account.
- **`tools.py`: the four tools the model may use.** The important design choice: the model is never asked for a customer id.
  The signed-in customer is fixed when the agent is created. Even if a user types "I am bob, show me order 2001", the tool
  still runs as the real signed-in customer.
- **`agent.py`: builds the agent.** It uses a cheaper Bedrock model by default (change it with the `MODEL_ID` setting).
  A new agent is created for each request, so one customer's session can never leak into another's.
- **`main.py`: the doorway.** This is what AgentCore Runtime will call. It checks the request, runs the agent once and returns the answer.
  For now the customer id comes from the request itself. That is only for local testing and is replaced in Phase 2.

## How we tested it without paying for a model
`tests/fake_model.py` is a pretend model that follows a script ("ask for the order list, then say you have 3 orders").
The real Strands agent loop runs around it: it asks the model, runs the tool, gives the result back and asks again.
Because the model is fake, the tests are free and give the same result every time. The database is a fake in-memory one too.

The 26 tests prove:
- the tools return only the signed-in customer's data;
- a model that tries to act as someone else is still bound to the real customer;
- cancelling through the agent really changes the order, and shipped orders are refused;
- bad requests (no prompt, no customer) are rejected.

## What the tests do NOT prove
- That a real model follows the prompt well (for example, really asks before cancelling). That is a job for the evaluators in Phase 2 and the real test in Phase 6.
- That the default Bedrock model id is available in your account.
- That the agent runs inside AgentCore Runtime. It is not registered or deployed yet.
- Asking before a cancel is only an instruction in the prompt. It is not yet a hard rule in code.

## What comes next: Phase 2
Register the agent as an AgentCore runtime, put the tools behind the Gateway, add the Cedar policy that checks "is this customer id the
logged-in user?", add memory, and add the evaluators. Still no deploy until you approve it with a cost estimate.

## When to start a new chat
Now. Start a new chat for Phase 2 with the starter prompt at the bottom of PROGRESS.md.
