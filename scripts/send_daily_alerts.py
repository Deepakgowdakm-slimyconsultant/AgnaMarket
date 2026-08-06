"""
send_daily_alerts.py

Run once a day (e.g. 7:30 AM IST) by .github/workflows/daily_alerts.yml.

For every subscriber, for every (crop, mandis) they track:
  1. Fetch today's price at each mandi.
  2. Validate each price against data_validator's accuracy rules.
  3. Build one WhatsApp message per crop, showing all tracked mandis and
     which one is currently best (only among prices we actually trust —
     "ok" or "stale" status; never among "rejected" ones).
  4. Update the local price history cache used for tomorrow's outlier checks.

Nothing here is invented. If a mandi has no trustworthy price today, the
message says so plainly instead of omitting it or guessing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import subscribers as subs
from src import message_templates as tmpl
from src.agmarknet_client import fetch_prices
from src.data_validator import validate_record

HISTORY_DIR = Path(__file__).resolve().parent.parent / "data" / "price_history"
HISTORY_WINDOW_DAYS = 14


def _history_path(crop: str, mandi: str) -> Path:
    safe = f"{crop}__{mandi}".replace("/", "_").replace(" ", "_")
    return HISTORY_DIR / f"{safe}.json"


def _load_history(crop: str, mandi: str) -> list[float]:
    p = _history_path(crop, mandi)
    if not p.exists():
        return []
    return json.loads(p.read_text()).get("modal_prices", [])


def _append_history(crop: str, mandi: str, modal_price: float) -> None:
    p = _history_path(crop, mandi)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    history = _load_history(crop, mandi)
    history.append(modal_price)
    history = history[-HISTORY_WINDOW_DAYS:]
    p.write_text(json.dumps({"modal_prices": history}, indent=2))


# Cache of API results within a single run, so we don't refetch the same
# crop+mandi combination twice if multiple farmers track the same thing.
_fetch_cache: dict[tuple[str, str], object] = {}


def _get_validated_price(crop: str, mandi: str):
    from src.data_validator import ValidatedPrice

    cache_key = (crop, mandi)
    if cache_key not in _fetch_cache:
        try:
            records = fetch_prices(commodity=crop, market=mandi)
        except RuntimeError as exc:
            print(f"WARNING: fetch failed for {crop} @ {mandi}: {exc}")
            # A network/API failure is NOT the same thing as "this mandi
            # genuinely has no price today" — a farmer deserves to know
            # which one happened, so we don't route this through
            # validate_record(None, ...), which would say "never reported."
            self_status = ValidatedPrice(
                record=None,
                status="fetch_error",
                reason=(
                    "Couldn't reach the price server just now (temporary "
                    "connection issue). This isn't the same as the mandi "
                    "having no price — we'll try again on the next update."
                ),
            )
            _fetch_cache[cache_key] = self_status
            return _fetch_cache[cache_key]

        record = records[0] if records else None
        history = _load_history(crop, mandi)
        validated = validate_record(record, history)
        _fetch_cache[cache_key] = validated
        if record and validated.status in ("ok", "flagged"):
            _append_history(crop, mandi, record.modal_price)
    return _fetch_cache[cache_key]


def build_alert_message(crop: str, mandis: list[str], lang: str) -> str:
    lines = [tmpl.daily_alert_header(crop, lang)]
    best_mandi = None
    best_price = None

    for mandi in mandis:
        vp = _get_validated_price(crop, mandi)
        lines.append(tmpl.format_price_line(mandi, vp, lang))
        if vp.status in ("ok", "stale") and vp.record:
            if best_price is None or vp.record.modal_price > best_price:
                best_price = vp.record.modal_price
                best_mandi = mandi

    lines.append(tmpl.daily_alert_footer(best_mandi, lang))
    return "\n".join(lines)


def main() -> None:
    from src.whatsapp_client import send_whatsapp

    data = subs.load()
    if not data:
        print("No subscribers yet.")
        return

    for phone, sub in data.items():
        if not sub.get("subscriptions"):
            continue
        lang = sub.get("language", "en")
        for entry in sub["subscriptions"]:
            message = build_alert_message(entry["crop"], entry["mandis"], lang)
            try:
                send_whatsapp(phone, message)
                print(f"Sent alert to {phone} for {entry['crop']}.")
            except Exception as exc:  # noqa: BLE001
                print(f"ERROR sending to {phone}: {exc}")


if __name__ == "__main__":
    main()
