"""Wirebox Python SDK — Quickstart Example.

Demonstrates zero-config initialization with Wirebox(), caller introspection,
identity discovery, sending an outbound email, and inspecting inbox messages.

Usage:
    python -m examples.quickstart
    # or
    python examples/quickstart.py
"""

from __future__ import annotations

import os
import sys

from wirebox import Wirebox


def main() -> None:
    print("=" * 60)
    print("Wirebox Python SDK - Quickstart")
    print("=" * 60)

    # 1. Zero-config client initialization
    # Automatically resolves API key from ~/.wirebox/credentials or ~/.wirebox/config
    client = Wirebox()

    # 2. Caller introspection via /v1/me
    who = client.whoami()
    print(f"\n[1] Authenticated Organization: {who.organization.name} ({who.organization.id})")
    print(f"    Billing Plan: {who.organization.billing_plan}")
    print(f"    Active Actor: {who.auth.actor_id} (Type: {who.auth.type})")
    print(f"    Usage: {who.usage.agents_count}/{who.usage.agents_limit} agents provisioned")

    # 3. Retrieve or discover active agent identity
    agents = client.list_identities(limit=10)
    if not agents:
        print("\n[!] No active agent identities found. Creating a starter identity...")
        agent = client.create_identity("assistant-bot", display_name="AI Assistant")
    else:
        agent = agents[0]

    print(f"\n[2] Active Agent Identity: @{agent.agent_handle}")
    print(f"    Display Name:    {agent.display_name or 'N/A'}")
    print(f"    Primary Mailbox: {agent.mailbox.email_address}")
    print(f"    Network Tunnel:  {agent.tunnel.public_url}")

    # 4. Dispatch a verified outbound email
    recipient = os.environ.get("AGENT_RECIPIENT") or agent.mailbox.email_address
    print(f"\n[3] Dispatching verified outbound message to: {recipient}...")

    dispatch_result = agent.send_email(
        to=recipient,
        subject="[Wirebox Quickstart] Autonomous Agent Online",
        text=(
            f"Hello!\n\n"
            f"Your personal agent @{agent.agent_handle} is fully provisioned with real-world infrastructure:\n"
            f"- Email Inbox: {agent.mailbox.email_address}\n"
            f"- Edge Tunnel: {agent.tunnel.public_url}\n\n"
            f"Sent autonomously via the Wirebox Edge Core API."
        ),
    )

    print(f"    Message Dispatched! ID: {dispatch_result.id}")
    if dispatch_result.thread_id:
        print(f"    Thread ID: {dispatch_result.thread_id}")

    # 5. Inspect mailbox messages
    print(f"\n[4] Querying recent messages for {agent.mailbox.email_address}...")
    messages = agent.list_messages(limit=5)
    print(f"    Found {len(messages)} recent message(s):")
    for msg in messages:
        snippet_text = (msg.snippet or msg.preview)[:60]
        print(f"     - [{msg.direction.upper()}] from={msg.from_address}")
        print(f"       subject: {msg.subject}")
        print(f"       snippet: {snippet_text}...")

    print("\n[✓] Wirebox Python Quickstart completed successfully!\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n[!] Error: {exc}", file=sys.stderr)
        sys.exit(1)
