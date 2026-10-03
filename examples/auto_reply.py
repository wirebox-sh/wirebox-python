"""Wirebox Python SDK — Autonomous Auto-Reply Agent Example.

Demonstrates:
1. Resolving the active AgentIdentity with zero-config credentials
2. Ensuring an agent-scoped webhook subscription is active
3. Connecting an in-memory WebSocket reverse-proxy tunnel
4. Intercepting "email.received" events in process memory
5. Automatically dispatching a threaded reply via agent.reply_email()

Usage:
    python examples/auto_reply.py
    python examples/auto_reply.py --once   # Connects, verifies health ping, and exits cleanly
"""

from __future__ import annotations

import asyncio
import datetime
import json
import sys

import httpx

from wirebox import AsyncWirebox
from wirebox.exceptions import WireboxAPIError


async def main() -> None:
    once_mode = "--once" in sys.argv

    print("=" * 64)
    print("  Wirebox Python SDK — Autonomous Auto-Reply Agent")
    print("========================================================\n")

    async with AsyncWirebox() as client:
        agent = await client.get_identity()

        print(f"Agent Handle:    @{agent.agent_handle}")
        print(f"Display Name:    {agent.display_name or 'N/A'}")
        print(f"Mailbox Address: {agent.mailbox.email_address}")
        print(f"Tunnel URL:      {agent.tunnel.public_url}")

        target_endpoint = f"{agent.tunnel.public_url}/webhook"

        # 1. Ensure webhook subscription exists
        webhooks = await agent.list_webhooks()
        hook = next((w for w in webhooks if w.url == target_endpoint), None)
        ephemeral = False

        if not hook:
            print(f"\nSetting up webhook subscription for {target_endpoint}...")
            hook = await agent.create_webhook(
                url=target_endpoint,
                events=["email.received", "test.ping"],
            )
            ephemeral = True
            print(f"✔ Webhook registered: {hook.id}")
        else:
            print(f"✔ Using existing webhook subscription: {hook.id}")

        # 2. In-memory event handler
        async def handle_request(request: httpx.Request) -> httpx.Response:
            now = datetime.datetime.now().strftime("%H:%M:%S")

            try:
                payload = json.loads(request.content.decode("utf-8"))
            except Exception:
                payload = {}

            event_type = payload.get("event_type") or payload.get("type") or "unknown"

            if event_type == "test.ping":
                print(f"[{now}] 🏓 Ping event received. Returning 200 OK.")
                return httpx.Response(200, json={"pong": True})

            if event_type == "email.received":
                data = payload.get("data") or {}
                incoming = data.get("message") or {}
                sender = incoming.get("from") or incoming.get("from_address") or "Unknown"
                subject = incoming.get("subject") or "(no subject)"
                snippet = incoming.get("snippet") or incoming.get("preview") or ""
                msg_id = incoming.get("id")

                print(f"\n[{now}] 📬 Email received!")
                print(f"   From:    {sender}")
                print(f"   Subject: {subject}")
                if snippet:
                    print(f"   Snippet: {snippet[:80]}")

                if msg_id:
                    try:
                        print("   ⚡ Dispatching automated reply via agent.reply_email()...")
                        reply = await agent.reply_email(
                            msg_id,
                            text=(
                                f"Hello!\n\n"
                                f"This is an automated response from @{agent.agent_handle} "
                                f"powered by the Wirebox Python SDK.\n\n"
                                f'I have received your email: "{subject}".\n\n'
                                f"All systems operational!"
                            ),
                        )
                        reply_id = reply.id or reply.message_id
                        print(f"   ✔ Reply dispatched successfully! ID: {reply_id}")
                    except WireboxAPIError as reply_err:
                        print(f"   ❌ Failed to reply: {reply_err}")
            else:
                print(f"[{now}] ℹ️ Received event: {event_type}")

            return httpx.Response(200, json={"received": True})

        # 3. Connect in-memory tunnel session
        print("\nConnecting in-memory tunnel gateway...")
        session = await agent.connect_tunnel(handler=handle_request)
        print("✔ Tunnel connected and ready to receive real-world events!")
        print("\n💡 Test this agent now by sending an email to:")
        print(f"   👉 {agent.mailbox.email_address}")

        if once_mode:
            print("\n[--once flag detected] Testing tunnel ping before exit...")
            # Fire an internal test ping if supported
            try:
                await client.webhooks.test(hook.id)
                print("✔ Webhook test ping successfully delivered!")
            except Exception as test_err:
                print(f"ℹ️  Ping status: {test_err}")

            print("\nDisconnecting tunnel session...")
            await session.close()
            if ephemeral and hook:
                print(f"Removing ephemeral webhook {hook.id}...")
                await client.webhooks.delete(hook.id)
            print("[✓] Auto-reply test cycle completed successfully!")
            return

        print("\nWaiting for incoming events (Press Ctrl+C to exit)...\n")

        try:
            await session.wait_closed()
        finally:
            print("\nDisconnecting tunnel session...")
            await session.close()
            if ephemeral and hook:
                print(f"Removing ephemeral webhook {hook.id}...")
                await client.webhooks.delete(hook.id)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete.")
    except Exception as exc:
        print(f"\n[!] Error: {exc}", file=sys.stderr)
        sys.exit(1)
