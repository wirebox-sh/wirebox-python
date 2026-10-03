"""Wirebox Python SDK — Personal Agent Identity Layer.

Demonstrates how an AI platform or agent developer uses Wirebox as the
foundational IDENTITY and REAL-WORLD COMMUNICATION layer for autonomous agents.

Key Architectural Principle:
- Wirebox does NOT implement agent reasoning, LLM orchestration, or task planning.
- Wirebox provides the physical IDENTITY INFRASTRUCTURE that equips agents with:
  1. Identity Presence: Unique global agent handle (@handle) and tenant isolation
  2. Mailbox Infrastructure: Dedicated email address ({handle}@wireboxmail.com)
  3. Telecom & Messaging: Dedicated carrier phone numbers, SMS, and Apple iMessage
  4. Edge Gateway (Tunnel): Reverse-proxy WebSocket tunnel streaming real-world
     inbound events directly into the agent's runtime process

Usage:
    python examples/personal_agent_identity.py
    python examples/personal_agent_identity.py --once   # Self-test cycle and exit
"""

from __future__ import annotations

import asyncio
import os
import sys
import time

from wirebox import AsyncWirebox
from wirebox.exceptions import WireboxAPIError


async def main() -> None:
    once_mode = "--once" in sys.argv

    print("=" * 64)
    print("  Wirebox Python SDK — Personal Agent Identity Layer")
    print("  Identity & Communication Infrastructure for AI Agents")
    print("=" * 64 + "\n")

    async with AsyncWirebox() as client:
        # ----------------------------------------------------------------------
        # Phase 1: Identity Provisioning & Resolution
        # ----------------------------------------------------------------------
        print("[Phase 1: Identity Provisioning & Resolution]")
        whoami = await client.whoami()
        is_identity_scoped = bool(whoami.scoped_identity_id)

        if is_identity_scoped:
            print("✔ Operating in Identity-Scoped Mode (Strict Tenant Isolation)")
            identity = await client.get_identity()
            print(
                f"✔ Loaded active agent identity: @{identity.agent_handle} "
                f"({identity.display_name or 'N/A'})\n"
            )
        else:
            print("✔ Operating in Platform Admin Mode")
            # Reuse existing identity if available to conserve tenant quotas
            existing_agents = await client.list_identities(limit=1)
            if existing_agents:
                identity = existing_agents[0]
                print(
                    f"✔ Reusing active agent identity: @{identity.agent_handle} "
                    f"({identity.display_name or 'N/A'})\n"
                )
            else:
                agent_handle = f"assistant-{int(time.time()) % 10000}"
                print(f"Provisioning new agent identity container: @{agent_handle}...")
                identity = await client.create_identity(
                    agent_handle,
                    display_name="Personal Travel Coordinator",
                    description="Dedicated real-world identity for autonomous travel coordination",
                )
                print(f"✔ Identity container provisioned! ID: {identity.id}\n")

        # ----------------------------------------------------------------------
        # Phase 2: Inspect Communication Assets Bound to this Identity
        # ----------------------------------------------------------------------
        print("-" * 64)
        print(f"  Identity Assets Bound to @{identity.agent_handle}")
        print("-" * 64)
        print(f"  📧 Mailbox:     {identity.mailbox.email_address}")
        print(f"  🌐 Edge Tunnel: {identity.tunnel.public_url}")
        print("  📱 Messaging:   Configured for Carrier SMS & Phone Numbers")
        print("-" * 64 + "\n")

        # ----------------------------------------------------------------------
        # Phase 3: Phone & Telecom Infrastructure
        # ----------------------------------------------------------------------
        print("[Phase 2: Phone & Telecom Infrastructure]")
        try:
            phone_num = await identity.get_phone_number()
            print(
                f"✔ Bound carrier phone number: {phone_num.phone_number} "
                f"(Status: {phone_num.status})\n"
            )
        except Exception:
            print(f"Requesting carrier phone number allocation for @{identity.agent_handle}...")
            try:
                new_phone = await client.phone.numbers.provision(
                    identity.agent_handle,
                    country_code="US",
                    type="local",
                )
                print(
                    f"✔ Carrier phone number provisioned: {new_phone.phone_number} "
                    f"({new_phone.type})\n"
                )
            except WireboxAPIError as err:
                if err.status_code == 403 and "phone_provisioning_restricted" in str(err):
                    print(
                        "ℹ️  [Telecom Gate] Phone number provisioning is currently in Private Beta."
                    )
                    print(
                        "    (Once organization is whitelisted, dedicated US/CA cellular numbers activate instantly)\n"
                    )
                elif err.status_code == 409:
                    print("✔ Agent already possesses an active phone number.\n")
                else:
                    print(f"ℹ️  [Telecom Notice] {err}\n")

        # ----------------------------------------------------------------------
        # Phase 4: Outbound Real-World Communication (Using Identity Mailbox)
        # ----------------------------------------------------------------------
        print("[Phase 3: Outbound Communication via Identity Mailbox]")
        print("Dispatching travel reservation confirmation from agent's dedicated identity...")

        recipient = os.environ.get("AGENT_RECIPIENT") or identity.mailbox.email_address
        try:
            email_result = await identity.send_email(
                to=recipient,
                subject="[Confirmed] Flight SFO -> HND Reservation for Alex",
                text="\n".join(
                    [
                        "Hello Alex,",
                        "",
                        "Your autonomous travel assistant has finalized your booking:",
                        "  - Flight: NH 107 (San Francisco -> Tokyo Haneda)",
                        "  - Status: Confirmed & Ticketed",
                        "  - Booking Ref: WB-9921B",
                        "",
                        "This notification was dispatched using the agent's dedicated Wirebox identity mailbox.",
                        "You can reply directly to this thread anytime to request adjustments.",
                        "",
                        f"— {identity.display_name or 'Agent'} (@{identity.agent_handle})",
                    ]
                ),
            )

            print("✔ Outbound email dispatched!")
            print(f"  Message ID: {email_result.id or email_result.message_id}")
            print(f"  Recipient:  {recipient}\n")
        except WireboxAPIError as err:
            if "not a verified address" in str(err):
                print(
                    f"ℹ️ [Sandbox Notice] Recipient '{recipient}' is not verified in sandbox mode."
                )
                print("   (Set AGENT_RECIPIENT=<your-verified-email> to test external delivery)\n")
            else:
                raise

        # ----------------------------------------------------------------------
        # Phase 5: Inbound Edge Gateway (Ingesting Real-World Signals into Agent)
        # ----------------------------------------------------------------------
        print("[Phase 4: Inbound Edge Gateway (Mail & Phone Events)]")
        target_endpoint = f"{identity.tunnel.public_url}/webhook"

        hook = await identity.create_webhook(
            url=target_endpoint,
            events=["email.received", "test.ping", "sms.received"],
        )
        print(f"✔ Webhook route bound: {hook.id} -> {target_endpoint}\n")

        print("----------------------------------------------------------------")
        print("  Personal Agent Identity Container Ready")
        print(f"  Agent Handle:    @{identity.agent_handle}")
        print(f"  Email Address:   {identity.mailbox.email_address}")
        print(f"  Gateway Tunnel:  {identity.tunnel.public_url}")
        print("----------------------------------------------------------------")

        if once_mode:
            print("\n[--once flag detected] Test cycle complete. Exiting cleanly.")
            return

        print("\nAgent identity infrastructure is operational. Press Ctrl+C to stop.\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown requested by user.")
    except Exception as exc:
        print(f"\n[!] Error: {exc}", file=sys.stderr)
        sys.exit(1)
