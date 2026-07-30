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

# A small set of common crop nicknames -> the exact commodity string used by
# the Agmarknet dataset. Extend this over time — it's the single place that
# needs updating when a new crop is added.
CROP_ALIASES = {
    "ragi": "Ragi (Finger Millet)/Nachni",
    "nachni": "Ragi (Finger Millet)/Nachni",
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
    """Return the canonical commodity name for a casual crop name, or None
    if we're not confident. Exact alias match only — deliberately NOT fuzzy,
    because guessing the wrong crop is worse than asking the farmer to
    retype it using HELP/CROPS.
    """
    key = user_text.strip().lower()
    return CROP_ALIASES.get(key)


def resolve_mandi(user_text: str, cutoff: float = 0.6) -> tuple[Optional[str], list[str]]:
    """Try to resolve a farmer-typed mandi name to a canonical one.

    Returns (best_match_or_None, list_of_close_alternatives).

    If the input is an exact (case-insensitive) match, returns it immediately
    with high confidence. Otherwise, uses fuzzy matching but NEVER silently
    picks a mandi the farmer didn't clearly mean — if the top match isn't
    a strong one, best_match is None and the alternatives are returned so
    the calling code can ask the farmer to confirm.
    """
    names = _load_market_names()
    lowered = {n.lower(): n for n in names}

    key = user_text.strip().lower()
    if key in lowered:
        return lowered[key], []

    close = difflib.get_close_matches(key, lowered.keys(), n=3, cutoff=cutoff)
    if close and close[0] != key:
        # Only auto-accept if the match is unambiguous (clearly closer than
        # the second-best option). Otherwise surface all candidates.
        scores = [
            difflib.SequenceMatcher(None, key, c).ratio() for c in close
        ]
        if len(scores) == 1 or (scores[0] - scores[1] > 0.15):
            return lowered[close[0]], [lowered[c] for c in close[1:]]
        return None, [lowered[c] for c in close]

    return None, []


def list_known_crops() -> list[str]:
    return sorted(set(CROP_ALIASES.keys()))


def list_known_mandis() -> list[str]:
    return _load_market_names()
