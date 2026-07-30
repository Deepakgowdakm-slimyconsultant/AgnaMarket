"""
whatsapp_client.py

Thin wrapper around Twilio's WhatsApp API.

Two things this project needs that a simple outbound-alert bot (like the
KCET bot) didn't:
  1. Sending outbound alerts (same as before).
  2. Reading INCOMING messages, so farmers can self-serve their own
     TRACK/ADD/REMOVE commands.

Because AgnaMarket has no always-on server, incoming messages aren't
received via a webhook — instead, poll_commands.py (run on a schedule by
GitHub Actions) polls Twilio's Messages API for anything new since the last
run. This trades a little latency (up to the poll interval, e.g. 15-20 min)
for zero hosting cost and zero server maintenance.

Required environment variables / GitHub Actions secrets:
  TWILIO_ACCOUNT_SID
  TWILIO_AUTH_TOKEN
  TWILIO_WHATSAPP_FROM     e.g. "whatsapp:+14155238886" (sandbox) or your
                           approved WhatsApp Business number
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

try:
    from twilio.rest import Client
except ImportError:  # pragma: no cover
    Client = None  # allows the module to be imported for tests without the package installed


def _client():
    if Client is None:
        raise RuntimeError("twilio package not installed — run: pip install twilio")
    sid = os.environ["TWILIO_ACCOUNT_SID"]
    token = os.environ["TWILIO_AUTH_TOKEN"]
    return Client(sid, token)


def send_whatsapp(to_phone: str, body: str) -> str:
    """Send a WhatsApp message. `to_phone` should be in E.164 format, e.g.
    '+919876543210' (the 'whatsapp:' prefix is added here).
    Returns the Twilio message SID on success.
    """
    from_number = os.environ["TWILIO_WHATSAPP_FROM"]
    client = _client()
    msg = client.messages.create(
        from_=from_number if from_number.startswith("whatsapp:") else f"whatsapp:{from_number}",
        to=f"whatsapp:{to_phone}",
        body=body,
    )
    return msg.sid


def fetch_new_incoming_messages(since: Optional[datetime]) -> list[dict]:
    """Poll Twilio for inbound WhatsApp messages received after `since`.

    Returns a list of {"from": "+91...", "body": "...", "date_sent": datetime}
    ordered oldest-first, so commands get applied in the order farmers sent
    them.
    """
    client = _client()
    from_number = os.environ["TWILIO_WHATSAPP_FROM"]
    from_number = from_number if from_number.startswith("whatsapp:") else f"whatsapp:{from_number}"

    messages = client.messages.list(to=from_number, date_sent_after=since)

    out = []
    for m in messages:
        if m.direction != "inbound":
            continue
        out.append(
            {
                "from": m.from_.replace("whatsapp:", ""),
                "body": m.body or "",
                "date_sent": m.date_sent,
            }
        )
    out.sort(key=lambda x: x["date_sent"] or datetime.min)
    return out
