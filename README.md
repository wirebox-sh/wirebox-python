# Wirebox Python SDK

Official Python SDK for [Wirebox](https://wirebox.sh) — The real-world identity, communication, and context execution layer for AI agents.

Equips autonomous agents with dedicated email inboxes, network tunnels, and webhooks with first-class synchronous and asynchronous support.

[![PyPI](https://img.shields.io/pypi/v/wirebox.svg)](https://pypi.org/project/wirebox/)
[![Python Version](https://img.shields.io/pypi/pyversions/wirebox.svg)](https://pypi.org/project/wirebox/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

---

## Key Features

- **Dual Engine**: High-performance synchronous `Wirebox` and native asynchronous `AsyncWirebox` clients.
- **Identity & Mailbox Hub**: Provision autonomous agent personas with atomic dedicated email inboxes (`@wireboxmail.com`).
- **Zero-Config Network Tunnels**: Expose local agent servers or containers to the public internet (`https://<handle>.tunnel.wirebox.sh`) over secure WebSockets — **no ngrok required**.
- **Cryptographic Webhook Verification**: Constant-time HMAC-SHA256 signature verification (`verify_webhook`) with anti-replay timestamp validation.
- **Zero Heavy C Dependencies**: Built cleanly on `httpx` and `websockets` — installs instantly across Linux, macOS, and Windows.
- **Modern Pythonic Design**: Full Python 3.11+ type hints (PEP 561 `py.typed`), immutable dataclasses, and rich exception hierarchy.

---

## Installation

```bash
pip install wirebox
```

Or using modern package managers:

```bash
# With uv
uv add wirebox

# With poetry
poetry add wirebox
```

---

## Quickstart

### 1. Asynchronous Client (Recommended for AI Agents & FastAPI)

```python
import asyncio
from wirebox import AsyncWirebox


async def main():
    async with AsyncWirebox(api_key="wb_live_xxxxxxxx") as client:
        # 1. Provision an autonomous agent identity
        agent = await client.create_identity("sales-bot", display_name="Sales Assistant")
        print(f"Created agent @{agent.agent_handle} with inbox {agent.mailbox.email_address}")

        # 2. Dispatch an outbound email
        result = await agent.send_email(
            to="client@example.com",
            subject="Welcome to Wirebox",
            text="Hello! This message was dispatched autonomously by an AI agent.",
        )
        print(f"Email sent with status: {result.status}")

        # 3. Retrieve and iterate over inbox messages
        async for msg in agent.iter_messages():
            print(f"[{msg.direction}] {msg.from_address}: {msg.subject}")


asyncio.run(main())
```

### 2. Synchronous Client (For Scripts, REPL & CLI tools)

```python
from wirebox import Wirebox

client = Wirebox(api_key="wb_live_xxxxxxxx")

# Provision or fetch existing identity
agent = client.get_identity("sales-bot")

# Send email
agent.send_email(
    to="support@example.com",
    subject="Agent status update",
    text="All background jobs running normally.",
)

# Whoami identity check
me = client.whoami()
print(f"Authenticated as org: {me.organization.slug} ({me.api_key.role})")
```

---

## Webhooks & Cryptographic Signature Verification

Wirebox signs every webhook payload with an HMAC-SHA256 signature to guarantee authenticity and prevent tampering or replay attacks.

Use `verify_webhook` directly in any web framework:

### FastAPI / Starlette Example:

```python
from fastapi import FastAPI, Request, HTTPException
from wirebox import verify_webhook

app = FastAPI()
WEBHOOK_SECRET = "whsec_your_signing_secret"


@app.post("/webhook")
async def webhook_endpoint(request: Request):
    raw_body = await request.body()

    # Validates signature and checks timestamp within 300-second window
    if not verify_webhook(payload=raw_body, headers=request.headers, secret=WEBHOOK_SECRET):
        raise HTTPException(status_code=403, detail="Invalid signature")

    payload = await request.json()
    event_type = payload.get("event_type")
    print(f"Received verified event: {event_type}")

    return {"status": "ok"}
```

---

## Network Tunnels (Local Port Forwarding)

Connect local ports or container services to your agent's public tunnel URL without opening firewall ports or buying static IPs:

```python
import asyncio
from wirebox import AsyncWirebox


async def main():
    async with AsyncWirebox(api_key="wb_live_...") as client:
        agent = await client.get_identity("sales-bot")

        # Reverse-proxy inbound HTTPS traffic from tunnel to local port 3456
        tunnel = await agent.connect_tunnel(forward_to=3456)
        print(f"Public tunnel URL: {tunnel.public_url}")

        # Keep proxying until closed
        await tunnel.wait_closed()


asyncio.run(main())
```

---

## Exception Hierarchy

All SDK exceptions inherit from `WireboxError`:

```text
WireboxError
├── WireboxConnectionError         # Network, connection drop, or timeout failures
├── ValidationError                # Client-side parameter validation failure
└── WireboxAPIError                # Non-2xx responses from Wirebox API
    ├── AuthenticationError        # HTTP 401 / 403 (invalid API key or lack of permissions)
    ├── NotFoundError              # HTTP 404 (identity, mailbox, message, or webhook not found)
    ├── RateLimitError             # HTTP 429 (rate limits exceeded)
    ├── HandleAlreadyTakenError    # HTTP 409 (agent_handle already registered)
    └── FreeTierLimitExceededError # HTTP 403/429 (free tier quota limit reached)
```

Example handling:

```python
from wirebox import Wirebox, HandleAlreadyTakenError, WireboxAPIError

client = Wirebox(api_key="wb_live_...")

try:
    agent = client.create_identity("sales-bot")
except HandleAlreadyTakenError:
    print("Handle is already claimed. Fetching existing identity instead...")
    agent = client.get_identity("sales-bot")
except WireboxAPIError as e:
    print(f"API failed with [{e.status} {e.code}]: {e.message} (request_id: {e.request_id})")
```

---

## License

MIT © [Wirebox](https://wirebox.sh)
