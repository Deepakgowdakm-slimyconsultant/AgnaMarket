"""
poll_commands.py

Run on a schedule (every 15-20 min) by .github/workflows/poll_commands.yml.

1. Checks Twilio for any new inbound WhatsApp messages since the last run.
2. Parses each as a command (TRACK/ADD/REMOVE/LIST/...).
3. Updates data/subscribers.json accordingly.
4. Replies to the farmer confirming what happened (or explaining why not).

State for "since when did we last check" is kept in data/.last_poll.txt so
each run only processes genuinely new messages.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import subscribers as subs
from src import message_templates as tmpl
from src.command_parser import parse
from src.match_utils import resolve_crop, resolve_mandi, list_known_crops
from src.whatsapp_client import send_whatsapp, fetch_new_incoming_messages

LAST_POLL_PATH = Path(__file__).resolve().parent.parent / "data" / ".last_poll.txt"


def _read_last_poll() -> datetime | None:
    if not LAST_POLL_PATH.exists():
        return None
    try:
        return datetime.fromisoformat(LAST_POLL_PATH.read_text().strip())
    except ValueError:
        return None


def _write_last_poll(when: datetime) -> None:
    LAST_POLL_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAST_POLL_PATH.write_text(when.isoformat())


def handle_message(data: dict, phone: str, body: str) -> str:
    """Process one inbound message, mutate `data` in place, return the reply text."""
    sub = subs.get_subscriber(data, phone)
    lang = sub.get("language", "en")
    subs.touch(data, phone)

    cmd = parse(body)

    if cmd.action == "help":
        return tmpl.HELP_TEXT[lang]

    if cmd.action == "list":
        return tmpl.subscription_list(sub["subscriptions"], lang)

    if cmd.action == "crops":
        return ", ".join(list_known_crops())

    if cmd.action == "mandis":
        from src.match_utils import list_known_mandis
        return ", ".join(list_known_mandis())

    if cmd.action == "stop":
        subs.unsubscribe_all(data, phone)
        return tmpl.stopped_all(lang)

    if cmd.action == "lang":
        subs.set_language(data, phone, cmd.language)
        return tmpl.WELCOME_TEXT[cmd.language]

    if cmd.action in ("track", "add"):
        crop = resolve_crop(cmd.crop_text)
        if not crop:
            return tmpl.crop_not_recognized(cmd.crop_text, list_known_crops(), lang)

        resolved_mandis = []
        for m in cmd.mandi_texts:
            match, alternatives = resolve_mandi(m)
            if not match:
                return tmpl.mandi_ambiguous(m, alternatives, lang)
            resolved_mandis.append(match)

        if not resolved_mandis:
            return tmpl.unknown_command(lang)

        subs.add_tracking(data, phone, crop, resolved_mandis)
        return tmpl.confirm_tracking(crop, resolved_mandis, lang)

    if cmd.action == "remove":
        crop = resolve_crop(cmd.crop_text)
        if not crop:
            return tmpl.crop_not_recognized(cmd.crop_text, list_known_crops(), lang)

        if cmd.mandi_texts:
            resolved_mandis = []
            for m in cmd.mandi_texts:
                match, _ = resolve_mandi(m)
                resolved_mandis.append(match or m)
            subs.remove_tracking(data, phone, crop, resolved_mandis)
            return tmpl.confirm_removed(crop, resolved_mandis, lang)
        else:
            subs.remove_tracking(data, phone, crop, None)
            return tmpl.confirm_removed(crop, None, lang)

    return tmpl.unknown_command(lang)


def main() -> None:
    since = _read_last_poll()
    now = datetime.now()

    messages = fetch_new_incoming_messages(since)
    if not messages:
        _write_last_poll(now)
        print("No new messages.")
        return

    data = subs.load()

    for m in messages:
        phone, body = m["from"], m["body"]
        is_new_subscriber = phone not in data
        reply = handle_message(data, phone, body)
        if is_new_subscriber:
            lang = subs.get_subscriber(data, phone).get("language", "en")
            reply = tmpl.WELCOME_TEXT[lang] + "\n\n" + reply
        send_whatsapp(phone, reply)
        print(f"Processed message from {phone}: {body!r} -> replied.")

    subs.save(data)
    _write_last_poll(now)


if __name__ == "__main__":
    main()
