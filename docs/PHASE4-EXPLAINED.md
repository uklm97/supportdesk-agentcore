# Phase 4 explained: the web front end

Nothing was deployed and nothing in AWS changed in this phase.

## What was built
A small website in the `web/` folder. It has two screens:
1. **Login**: email and password. The browser talks to Cognito (the login service from Phase 3) and gets back tokens.
2. **Chat**: a text box and a conversation. Each message goes to the chat API from Phase 3.

## How a message travels
Browser -> API Gateway (checks the login token) -> chat Lambda -> AgentCore runtime (checks the same token again,
then reads who you are from it) -> tools -> your orders in DynamoDB.
The browser never says "I am customer X". The server works that out from the token, so one customer cannot see another's orders.

## Why these choices
- **Access token, not ID token**: the runtime checks which app client the token belongs to, and that claim is in the access token.
- **Settings in `/config.json`, not baked into the build**: the pool id, client id and API address only exist after a deploy.
  A small script (`scripts/write_web_config.py`) reads them from CloudFormation and writes the file. One build works everywhere.
- **No sign-up screen**: admins create users (the seed script makes the demo users).
- **Tokens stay in the browser's local storage** (Cognito library default). That is simple, but a script injected into the page could read them,
  so the page loads no third-party scripts. A stricter design would use cookies set by a server.
- **Vite + React + TypeScript**: small, fast, and the type checker catches mistakes before running.

## What was checked
- Type check: clean. Front-end tests: 8 passed. Production build: OK. Python tests: 88 passed.
- NOT checked: the screens in a real browser, and the real login and chat flow. That needs the deployed stacks (Phase 6).

## What is still missing
- Putting the built site into the S3 bucket. `infra/` creates the bucket and CloudFront but does not upload files yet.
  This will be a separate step in Phase 6, and it needs your approval.
