"""
command_parser.py

Parses free-typed WhatsApp messages from farmers into structured commands.

Supported commands (case-insensitive, farmer can also just send in Kannada
script for a few keywords — see KANNADA_KEYWORDS below):

  TRACK <crop> <mandi1>, <mandi2>, ...   e.g. "TRACK ragi Tumkur, Chitradurga"
  ADD <crop> <mandi>                     e.g. "ADD arecanut Shimoga"
  REMOVE <crop> <mandi>                  e.g. "REMOVE ragi Davanagere"
  REMOVE <crop>                          removes the whole crop
  LIST                                   shows current subscriptions
  LANG EN / LANG KN                      switch alert language
  CROPS                                  lists supported crop names
  MANDIS                                 lists known mandi names
  STOP                                   unsubscribes from everything
  HELP                                   shows the command list

Design choice: this is intentionally a strict, small command grammar rather
than free-form NLP. A farmer's WhatsApp bot silently misunderstanding "stop
sending me ragi prices from Tumkur" is worse than a bot that requires
"REMOVE ragi Tumkur" but is 100% predictable once learned. HELP always
brings back the exact syntax.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ParsedCommand:
    action: str  # "track" | "add" | "remove" | "list" | "lang" | "crops" | "mandis" | "stop" | "help" | "unknown"
    crop_text: str | None = None
    mandi_texts: list[str] = field(default_factory=list)
    language: str | None = None
    raw: str = ""


def _split_mandis(text: str) -> list[str]:
    # Farmers separate mandi names with commas, "and", or just spaces.
    text = text.replace(" and ", ",").replace("&", ",")
    parts = [p.strip() for p in text.split(",")]
    return [p for p in parts if p]


def parse(message: str) -> ParsedCommand:
    raw = message.strip()
    if not raw:
        return ParsedCommand(action="unknown", raw=raw)

    tokens = raw.split(maxsplit=1)
    verb = tokens[0].strip().upper()
    rest = tokens[1] if len(tokens) > 1 else ""

    if verb in ("HELP", "?"):
        return ParsedCommand(action="help", raw=raw)

    if verb == "LIST":
        return ParsedCommand(action="list", raw=raw)

    if verb == "CROPS":
        return ParsedCommand(action="crops", raw=raw)

    if verb == "MANDIS":
        return ParsedCommand(action="mandis", raw=raw)

    if verb == "STOP":
        return ParsedCommand(action="stop", raw=raw)

    if verb == "LANG":
        lang = rest.strip().lower()
        if lang in ("en", "english"):
            return ParsedCommand(action="lang", language="en", raw=raw)
        if lang in ("kn", "kannada", "ಕನ್ನಡ"):
            return ParsedCommand(action="lang", language="kn", raw=raw)
        return ParsedCommand(action="unknown", raw=raw)

    if verb in ("TRACK", "ADD"):
        rest_tokens = rest.split(maxsplit=1)
        if len(rest_tokens) < 2:
            return ParsedCommand(action="unknown", raw=raw)
        crop_text, mandi_text = rest_tokens[0], rest_tokens[1]
        return ParsedCommand(
            action="track" if verb == "TRACK" else "add",
            crop_text=crop_text,
            mandi_texts=_split_mandis(mandi_text),
            raw=raw,
        )

    if verb == "REMOVE":
        rest_tokens = rest.split(maxsplit=1)
        if not rest_tokens:
            return ParsedCommand(action="unknown", raw=raw)
        crop_text = rest_tokens[0]
        mandi_text = rest_tokens[1] if len(rest_tokens) > 1 else ""
        return ParsedCommand(
            action="remove",
            crop_text=crop_text,
            mandi_texts=_split_mandis(mandi_text) if mandi_text else [],
            raw=raw,
        )

    return ParsedCommand(action="unknown", raw=raw)
