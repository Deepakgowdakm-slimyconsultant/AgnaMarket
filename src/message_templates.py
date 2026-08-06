"""
message_templates.py

Every message a farmer sees, in both English and Kannada. Plain words,
short sentences, no jargon — same design principle you set for SeatSense.
Nothing here uses a "modal price" or "outlier deviation" type of term
without immediately explaining it in one plain clause.
"""

from __future__ import annotations

from typing import Optional

from src.data_validator import ValidatedPrice


HELP_TEXT = {
    "en": (
        "AgnaMarket commands:\n"
        "TRACK <crop> <mandi1>, <mandi2> - start tracking a crop at mandis\n"
        "  e.g. TRACK ragi Tumkur, Chitradurga\n"
        "ADD <crop> <mandi> - add one more mandi to a crop you track\n"
        "REMOVE <crop> <mandi> - stop tracking one mandi for a crop\n"
        "REMOVE <crop> - stop tracking a crop completely\n"
        "LIST - show what you're currently tracking\n"
        "CROPS - show supported crop names\n"
        "MANDIS - show known mandi names\n"
        "LANG KN - switch to Kannada / LANG EN - switch to English\n"
        "STOP - stop all alerts"
    ),
    "kn": (
        "AgnaMarket ಆದೇಶಗಳು:\n"
        "TRACK <ಬೆಳೆ> <ಮಂಡಿ1>, <ಮಂಡಿ2> - ಬೆಳೆ ಬೆಲೆ ಟ್ರ್ಯಾಕ್ ಮಾಡಲು ಪ್ರಾರಂಭಿಸಿ\n"
        "  ಉದಾ: TRACK ragi Tumkur, Chitradurga\n"
        "ADD <ಬೆಳೆ> <ಮಂಡಿ> - ಇನ್ನೊಂದು ಮಂಡಿ ಸೇರಿಸಿ\n"
        "REMOVE <ಬೆಳೆ> <ಮಂಡಿ> - ಒಂದು ಮಂಡಿ ತೆಗೆದುಹಾಕಿ\n"
        "LIST - ನೀವು ಟ್ರ್ಯಾಕ್ ಮಾಡುತ್ತಿರುವುದನ್ನು ತೋರಿಸಿ\n"
        "STOP - ಎಲ್ಲಾ ಎಚ್ಚರಿಕೆಗಳನ್ನು ನಿಲ್ಲಿಸಿ"
    ),
}

WELCOME_TEXT = {
    "en": (
        "Welcome to AgnaMarket! This bot sends you daily mandi prices for the "
        "crops and mandis you choose - straight to WhatsApp, no app needed.\n\n"
        + HELP_TEXT["en"]
    ),
    "kn": (
        "AgnaMarket ಗೆ ಸ್ವಾಗತ! ಈ ಬಾಟ್ ನೀವು ಆಯ್ಕೆ ಮಾಡಿದ ಬೆಳೆ ಮತ್ತು ಮಂಡಿಗಳ "
        "ದೈನಂದಿನ ಬೆಲೆಗಳನ್ನು ನೇರವಾಗಿ WhatsApp ಗೆ ಕಳುಹಿಸುತ್ತದೆ.\n\n" + HELP_TEXT["kn"]
    ),
}


def unknown_command(lang: str = "en") -> str:
    if lang == "kn":
        return "ಕ್ಷಮಿಸಿ, ಅರ್ಥವಾಗಲಿಲ್ಲ. HELP ಎಂದು ಟೈಪ್ ಮಾಡಿ ಸಹಾಯ ಪಡೆಯಿರಿ."
    return "Sorry, I didn't understand that. Type HELP to see the exact commands."


def crop_not_recognized(crop_text: str, known_crops: list[str], lang: str = "en") -> str:
    sample = ", ".join(known_crops[:10])
    if lang == "kn":
        return f"'{crop_text}' ಬೆಳೆ ಗುರುತಿಸಲಾಗಿಲ್ಲ. ಬೆಂಬಲಿತ ಬೆಳೆಗಳು: {sample} ..."
    return (
        f"I don't recognize the crop '{crop_text}'. Supported crops include: "
        f"{sample} ... Type CROPS to see the full list."
    )


def mandi_ambiguous(mandi_text: str, alternatives: list[str], lang: str = "en") -> str:
    alt_str = ", ".join(alternatives) if alternatives else "none found"
    if lang == "kn":
        return f"'{mandi_text}' ಮಂಡಿ ಖಚಿತವಾಗಿ ಗುರುತಿಸಲಾಗಿಲ್ಲ. ಇವುಗಳಲ್ಲಿ ಒಂದಿರಬಹುದೇ?: {alt_str}"
    return (
        f"I'm not confident '{mandi_text}' matches a real mandi. "
        f"Did you mean one of: {alt_str}? Please resend with the exact name, "
        f"or type MANDIS to see the full list."
    )


def confirm_tracking(crop: str, mandis: list[str], lang: str = "en") -> str:
    mandi_str = ", ".join(mandis)
    if lang == "kn":
        return f"ಸರಿ! ಈಗ {crop} ಬೆಲೆಯನ್ನು ಈ ಮಂಡಿಗಳಲ್ಲಿ ಟ್ರ್ಯಾಕ್ ಮಾಡಲಾಗುತ್ತಿದೆ: {mandi_str}"
    return f"Done! Now tracking {crop} prices at: {mandi_str}. You'll get a daily update."


def confirm_removed(crop: str, mandis: list[str] | None, lang: str = "en") -> str:
    if mandis:
        target = ", ".join(mandis)
        if lang == "kn":
            return f"{crop} ಗಾಗಿ {target} ಅನ್ನು ತೆಗೆದುಹಾಕಲಾಗಿದೆ."
        return f"Removed {target} from your {crop} tracking."
    if lang == "kn":
        return f"{crop} ಟ್ರ್ಯಾಕಿಂಗ್ ಸಂಪೂರ್ಣವಾಗಿ ನಿಲ್ಲಿಸಲಾಗಿದೆ."
    return f"Stopped tracking {crop} completely."


def subscription_list(subscriptions: list[dict], lang: str = "en") -> str:
    if not subscriptions:
        if lang == "kn":
            return "ನೀವು ಪ್ರಸ್ತುತ ಯಾವುದನ್ನೂ ಟ್ರ್ಯಾಕ್ ಮಾಡುತ್ತಿಲ್ಲ. TRACK ಬಳಸಿ ಪ್ರಾರಂಭಿಸಿ."
        return "You're not tracking anything yet. Use TRACK <crop> <mandi> to start."
    lines = []
    for s in subscriptions:
        lines.append(f"- {s['crop']}: {', '.join(s['mandis'])}")
    header = "ನೀವು ಟ್ರ್ಯಾಕ್ ಮಾಡುತ್ತಿರುವುದು:" if lang == "kn" else "You're currently tracking:"
    return header + "\n" + "\n".join(lines)


def stopped_all(lang: str = "en") -> str:
    if lang == "kn":
        return "ಎಲ್ಲಾ ಟ್ರ್ಯಾಕಿಂಗ್ ನಿಲ್ಲಿಸಲಾಗಿದೆ. ಮತ್ತೆ ಪ್ರಾರಂಭಿಸಲು TRACK ಬಳಸಿ."
    return "All alerts stopped. Send TRACK <crop> <mandi> anytime to start again."


def format_price_line(mandi: str, vp: ValidatedPrice, lang: str = "en") -> str:
    """One line of a daily alert message for a single mandi."""
    if vp.status == "fetch_error":
        return f"- {mandi}: " + (
            "ಬೆಲೆ ಪರಿಶೀಲಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ (ಸಂಪರ್ಕ ಸಮಸ್ಯೆ), ಮುಂದಿನ ಬಾರಿ ಪ್ರಯತ್ನಿಸುತ್ತೇವೆ" if lang == "kn"
            else "couldn't check the price just now (connection issue) — will retry next update"
        )

    if vp.status == "no_data":
        return f"- {mandi}: " + ("ಬೆಲೆ ಲಭ್ಯವಿಲ್ಲ" if lang == "kn" else "no price data available")

    if vp.status == "rejected":
        return f"- {mandi}: " + (
            "ಈ ಬೆಲೆ ಪರಿಶೀಲನೆಗಾಗಿ ತಡೆಹಿಡಿಯಲಾಗಿದೆ" if lang == "kn"
            else "price withheld (data looked wrong, being rechecked)"
        )

    r = vp.record
    price_str = f"₹{r.modal_price:.0f}/quintal"

    if vp.status == "stale":
        date_note = f" (as of {r.arrival_date}, not today)"
        return f"- {mandi}: {price_str}{date_note}"

    if vp.status == "flagged":
        return f"- {mandi}: {price_str} ⚠️ unusual vs recent prices - {vp.reason}"

    return f"- {mandi}: {price_str} (as of {r.arrival_date})"


def daily_alert_header(crop: str, lang: str = "en") -> str:
    if lang == "kn":
        return f"{crop} - ಇಂದಿನ ಮಂಡಿ ಬೆಲೆಗಳು:"
    return f"{crop} - today's mandi prices:"


def daily_alert_footer(best_mandi: Optional[str], lang: str = "en") -> str:
    if not best_mandi:
        return ""
    if lang == "kn":
        return f"\nಇಂದು ಉತ್ತಮ ಬೆಲೆ: {best_mandi}"
    return f"\nBest price today: {best_mandi}"
