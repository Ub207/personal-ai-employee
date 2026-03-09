#!/usr/bin/env python3
"""
a2a_agent.py — Platinum Tier Agent-to-Agent Communication
===========================================================
Phase 1: File-based A2A via /Updates/ (vault as audit record).
Phase 2 (optional): HTTP-based direct messaging while keeping vault as log.

Agents communicate by writing structured JSON message files:
  /Updates/A2A_<timestamp>_<from>_to_<to>_<type>.json

Message format:
  {
    "from": "cloud",
    "to":   "local",
    "type": "request" | "response" | "signal" | "delegate",
    "action": "process_email" | "send_approval" | ...,
    "payload": {...},
    "timestamp": "2026-03-09T10:00:00Z",
    "message_id": "uuid",
    "reply_to": null
  }

Usage:
  # Send a message (from cloud to local):
  python watchers/a2a_agent.py send \
      --from cloud --to local \
      --type delegate --action process_approval \
      --payload '{"file": "EMAIL_DRAFT_2026-03-09.md"}'

  # Listen for messages (local agent picks up what cloud sent):
  python watchers/a2a_agent.py listen --agent local --watch

  # Show message history:
  python watchers/a2a_agent.py history
"""

import os
import sys
import json
import time
import uuid
import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("A2AAgent")

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_VAULT = Path(os.environ.get("VAULT_PATH", "D:/bronze_tier")).resolve()
AGENT_ID = os.environ.get("AGENT_ID", "local")

VALID_AGENTS = {"cloud", "local", "broadcast"}
VALID_TYPES  = {"request", "response", "signal", "delegate", "ack", "error"}


class A2AMessage:
    """Represents a single agent-to-agent message."""

    def __init__(
        self,
        from_agent: str,
        to_agent: str,
        msg_type: str,
        action: str,
        payload: dict | None = None,
        reply_to: str | None = None,
    ):
        self.message_id = str(uuid.uuid4())[:12]
        self.from_agent = from_agent
        self.to_agent   = to_agent
        self.msg_type   = msg_type
        self.action     = action
        self.payload    = payload or {}
        self.reply_to   = reply_to
        self.timestamp  = datetime.now(timezone.utc).isoformat()
        self.read_by: list[str] = []

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "from": self.from_agent,
            "to": self.to_agent,
            "type": self.msg_type,
            "action": self.action,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "reply_to": self.reply_to,
            "read_by": self.read_by,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "A2AMessage":
        msg = cls(
            from_agent=d.get("from", "unknown"),
            to_agent=d.get("to", "broadcast"),
            msg_type=d.get("type", "signal"),
            action=d.get("action", ""),
            payload=d.get("payload", {}),
            reply_to=d.get("reply_to"),
        )
        msg.message_id = d.get("message_id", msg.message_id)
        msg.timestamp  = d.get("timestamp", msg.timestamp)
        msg.read_by    = d.get("read_by", [])
        return msg

    def filename(self) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
        return f"A2A_{ts}_{self.from_agent}_to_{self.to_agent}_{self.action[:20]}.json"

    def __repr__(self) -> str:
        return (
            f"[{self.timestamp[:19]}] {self.from_agent} -> {self.to_agent} "
            f"({self.msg_type}/{self.action}) id={self.message_id}"
        )


class A2AChannel:
    """
    File-based A2A channel.
    Messages are JSON files in /Updates/. The vault Git sync carries them between agents.
    """

    def __init__(self, vault_path: Path, agent_id: str):
        self.vault    = vault_path
        self.agent_id = agent_id
        self.updates  = vault_path / "Updates"
        self.updates.mkdir(parents=True, exist_ok=True)
        self._read_ids: set[str] = set()

    # ── Send ──────────────────────────────────────────────────────────────────

    def send(self, message: A2AMessage) -> Path:
        """Write a message file to /Updates/."""
        file_path = self.updates / message.filename()
        file_path.write_text(
            json.dumps(message.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        log.info(f"Sent: {message}")
        return file_path

    def send_message(
        self,
        to_agent: str,
        msg_type: str,
        action: str,
        payload: dict | None = None,
        reply_to: str | None = None,
    ) -> A2AMessage:
        """Convenience: create and send a message."""
        msg = A2AMessage(
            from_agent=self.agent_id,
            to_agent=to_agent,
            msg_type=msg_type,
            action=action,
            payload=payload,
            reply_to=reply_to,
        )
        self.send(msg)
        return msg

    def reply(self, original: A2AMessage, action: str, payload: dict | None = None) -> A2AMessage:
        """Send a reply to a received message."""
        return self.send_message(
            to_agent=original.from_agent,
            msg_type="response",
            action=action,
            payload=payload,
            reply_to=original.message_id,
        )

    # ── Receive ───────────────────────────────────────────────────────────────

    def get_unread(self) -> list[A2AMessage]:
        """
        Return messages addressed to this agent (or broadcast) that haven't been read.
        Marks them as read by updating the file.
        """
        messages = []
        for f in sorted(self.updates.glob("A2A_*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                msg = A2AMessage.from_dict(data)

                # Skip if not addressed to us
                if msg.to_agent not in (self.agent_id, "broadcast"):
                    continue

                # Skip if already read by us
                if self.agent_id in msg.read_by:
                    continue

                # Mark as read
                msg.read_by.append(self.agent_id)
                data["read_by"] = msg.read_by
                f.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

                messages.append(msg)
                log.info(f"Received: {msg}")

            except (json.JSONDecodeError, OSError):
                continue

        return messages

    def get_history(self, limit: int = 50) -> list[A2AMessage]:
        """Return last N messages (all agents, not filtered)."""
        messages = []
        for f in sorted(self.updates.glob("A2A_*.json"), reverse=True)[:limit]:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                messages.append(A2AMessage.from_dict(data))
            except (json.JSONDecodeError, OSError):
                continue
        return messages

    # ── Listen loop ───────────────────────────────────────────────────────────

    def listen(self, handler=None, interval: int = 30) -> None:
        """
        Poll for messages. If handler is provided, call it for each message.
        handler signature: handler(message: A2AMessage, channel: A2AChannel) -> None
        """
        log.info(f"A2A listener started for agent={self.agent_id} (polling every {interval}s)")
        while True:
            try:
                messages = self.get_unread()
                for msg in messages:
                    if handler:
                        try:
                            handler(msg, self)
                        except Exception as exc:
                            log.error(f"Handler error for {msg}: {exc}")
            except KeyboardInterrupt:
                log.info("A2A listener stopping.")
                break
            except Exception as exc:
                log.error(f"Listen error: {exc}")
            time.sleep(interval)


# ── Default message handlers ──────────────────────────────────────────────────

def default_local_handler(msg: A2AMessage, channel: A2AChannel) -> None:
    """
    Default Local agent handler for incoming A2A messages.
    Local handles: approval requests, send actions, payment confirmations.
    """
    log.info(f"Handling {msg.action} from {msg.from_agent}")

    if msg.action == "request_approval":
        file_name = msg.payload.get("file", "")
        log.info(f"Approval request received for: {file_name}")
        channel.reply(msg, "ack_approval_request", {"status": "queued", "file": file_name})

    elif msg.action == "send_email":
        # Local executes via MCP — cloud asked, local acts
        to = msg.payload.get("to", "")
        subject = msg.payload.get("subject", "")
        log.info(f"Email send request: to={to} subject={subject}")
        # In production, this would call the email MCP server
        channel.reply(msg, "email_queued", {"to": to, "status": "queued_for_mcp"})

    elif msg.action == "heartbeat":
        log.debug("Cloud heartbeat received.")

    else:
        log.warning(f"Unknown action: {msg.action}")
        channel.reply(msg, "error", {"error": f"Unknown action: {msg.action}"})


def default_cloud_handler(msg: A2AMessage, channel: A2AChannel) -> None:
    """
    Default Cloud agent handler.
    Cloud handles: draft requests, social scheduling, signal acks.
    """
    log.info(f"Cloud handling {msg.action} from {msg.from_agent}")

    if msg.action == "draft_email":
        # Local delegates drafting to cloud
        subject = msg.payload.get("subject", "")
        sender  = msg.payload.get("from", "")
        log.info(f"Drafting email response: subject={subject} from={sender}")
        channel.reply(msg, "email_draft_created", {
            "status": "draft_written_to_pending_approval",
            "subject": subject,
        })

    elif msg.action == "schedule_post":
        platform = msg.payload.get("platform", "")
        channel.reply(msg, "post_scheduled", {"platform": platform, "status": "queued"})

    elif msg.action == "ack_approval_request":
        log.info(f"Local acknowledged approval request: {msg.payload}")

    else:
        log.warning(f"Unknown action: {msg.action}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="A2A Agent — file-based inter-agent messaging")
    sub = parser.add_subparsers(dest="command", required=True)

    # send
    send_p = sub.add_parser("send", help="Send an A2A message")
    send_p.add_argument("--from", dest="from_agent", default=AGENT_ID)
    send_p.add_argument("--to", dest="to_agent", required=True)
    send_p.add_argument("--type", dest="msg_type", default="request", choices=list(VALID_TYPES))
    send_p.add_argument("--action", required=True)
    send_p.add_argument("--payload", default="{}", help="JSON payload string")
    send_p.add_argument("--reply-to", default=None)
    send_p.add_argument("--vault-path", default=str(DEFAULT_VAULT))

    # listen
    listen_p = sub.add_parser("listen", help="Listen for incoming messages")
    listen_p.add_argument("--agent", default=AGENT_ID)
    listen_p.add_argument("--interval", type=int, default=30)
    listen_p.add_argument("--vault-path", default=str(DEFAULT_VAULT))

    # history
    hist_p = sub.add_parser("history", help="Show message history")
    hist_p.add_argument("--limit", type=int, default=20)
    hist_p.add_argument("--vault-path", default=str(DEFAULT_VAULT))

    args = parser.parse_args()
    vault = Path(getattr(args, "vault_path", str(DEFAULT_VAULT))).resolve()

    if args.command == "send":
        channel = A2AChannel(vault, args.from_agent)
        try:
            payload = json.loads(args.payload)
        except json.JSONDecodeError:
            log.error("Invalid JSON payload")
            sys.exit(1)
        msg = channel.send_message(
            to_agent=args.to_agent,
            msg_type=args.msg_type,
            action=args.action,
            payload=payload,
            reply_to=args.reply_to,
        )
        print(f"Message sent: {msg.message_id}")

    elif args.command == "listen":
        channel = A2AChannel(vault, args.agent)
        handler = default_local_handler if args.agent == "local" else default_cloud_handler
        channel.listen(handler=handler, interval=args.interval)

    elif args.command == "history":
        channel = A2AChannel(vault, AGENT_ID)
        msgs = channel.get_history(limit=args.limit)
        print(f"Last {len(msgs)} messages:")
        for m in msgs:
            print(f"  {m}")


if __name__ == "__main__":
    main()
