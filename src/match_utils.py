"""
match_utils.py

Farmers will not type "Ragi (Finger Millet)/Nachni" — they'll type "ragi".
This module bridges that gap safely: it matches loose, casual input against
the canonical names the government API actually uses, WITHOUT ever silently
guessing wrong. If we're not confident, we say so and offer the closest
real options instead of picking one for the farmer.
"""

from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Optional

MANDI_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "mandis_karnataka.json"

CROP_ALIASES = {
    "ragi": "Ragi(Finger Millet)",
    "nachni": "Ragi(Finger Millet)",
    "arecanut": "Arecanut(Betelnut/Supari)",
    "areca": "Arecanut(Betelnut/Supari)",
    "supari": "Arecanut(Betelnut/Supari)",
    "tomato": "Tomato",
    "onion": "Onion",
    "maize": "Maize",
    "jowar": "Jowar(Sorghum)",
    "paddy": "Paddy(Dhan)(Common)",
    "rice": "Rice",
    "groundnut": "Groundnut",
    "cotton": "Cotton",
    "coconut": "Coconut",
    "coffee": "Coffee",
    "pepper": "Pepper ungarbled",
    "sugarcane": "Sugarcane",
    "turmeric": "Turmeric",
    "banana": "Banana",
    "potato": "Potato",
    "chilli": "Dry Chillies",
    "chili": "Dry Chillies",
}


def _load_market_names() -> list[str]:
    with open(MANDI_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return sorted({m["market"] for m in cfg["markets"]})


def resolve_crop(user_text: str) -> Optional[str]:
    key = user_text.strip().lower()
    return CROP_ALIASES.get(key)


def _strip_apmc(name: str) -> str:
    n = name.strip()
    if n.lower().endswith(" apmc"):
        return n[: -len(" apmc")].strip()
    return n


def resolve_mandi(user_text: str, cutoff: float = 0.6) -> tuple[Optional[str], list[str]]:
    names = _load_market_names()
    full_lowered = {n.lower(): n for n in names}

    short_to_full: dict[str, str] = {}
    for n in names:
        short_to_full.setdefault(_strip_apmc(n).lower(), n)

    key = user_text.strip().lower()

    if key in short_to_full:
        return short_to_full[key], []
    if key in full_lowered:
        return full_lowered[key], []

    close = difflib.get_close_matches(key, short_to_full.keys(), n=3, cutoff=cutoff)
    if close:
        scores = [difflib.SequenceMatcher(None, key, c).ratio() for c in close]
        if len(scores) == 1 or (scores[0] - scores[1] > 0.15):
            return short_to_full[close[0]], [short_to_full[c] for c in close[1:]]
        return None, [short_to_full[c] for c in close]

    return None, []


def list_known_crops() -> list[str]:
    return sorted(set(CROP_ALIASES.keys()))


def list_known_mandis() -> list[str]:
    return _load_market_names()
