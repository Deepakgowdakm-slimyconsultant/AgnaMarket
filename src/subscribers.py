"""
subscribers.py

AgnaMarket has no server and no database — it runs entirely on GitHub
Actions cron jobs. So "the database" is just data/subscribers.json,
committed back to the repo by the poll_commands workflow whenever it
changes. This keeps hosting cost at zero, at the tradeoff of being
eventually-consistent (fine, since it only needs to be right once a day).

Structure of data/subscribers.json:
{
  "+919xxxxxxxxx": {
    "language": "en",              // "en" or "kn"
    "subscriptions": [
      {"crop": "Ragi (Finger Millet)/Nachni", "mandis": ["Tumkur", "Chitradurga"]}
    ],
    "last_seen": "2026-07-30T09:00:00"
  }
}
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "subscribers.json"


def load(path: Path = DEFAULT_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save(data: dict[str, Any], path: Path = DEFAULT_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)
    os.replace(tmp_path, path)  # atomic write — never leaves a half-written file


def get_subscriber(data: dict[str, Any], phone: str) -> dict[str, Any]:
    return data.get(phone, {"language": "en", "subscriptions": [], "last_seen": None})


def touch(data: dict[str, Any], phone: str) -> dict[str, Any]:
    sub = get_subscriber(data, phone)
    sub["last_seen"] = datetime.now().isoformat()
    data[phone] = sub
    return data


def add_tracking(data: dict[str, Any], phone: str, crop: str, mandis: list[str]) -> dict[str, Any]:
    sub = get_subscriber(data, phone)
    existing = next((s for s in sub["subscriptions"] if s["crop"] == crop), None)
    if existing:
        merged = sorted(set(existing["mandis"]) | set(mandis))
        existing["mandis"] = merged
    else:
        sub["subscriptions"].append({"crop": crop, "mandis": sorted(set(mandis))})
    data[phone] = sub
    return data


def remove_tracking(data: dict[str, Any], phone: str, crop: str, mandis: list[str] | None = None) -> dict[str, Any]:
    sub = get_subscriber(data, phone)
    if mandis is None:
        sub["subscriptions"] = [s for s in sub["subscriptions"] if s["crop"] != crop]
    else:
        for s in sub["subscriptions"]:
            if s["crop"] == crop:
                s["mandis"] = [m for m in s["mandis"] if m not in mandis]
        sub["subscriptions"] = [s for s in sub["subscriptions"] if s["mandis"]]
    data[phone] = sub
    return data


def unsubscribe_all(data: dict[str, Any], phone: str) -> dict[str, Any]:
    if phone in data:
        data[phone]["subscriptions"] = []
    return data


def set_language(data: dict[str, Any], phone: str, language: str) -> dict[str, Any]:
    sub = get_subscriber(data, phone)
    sub["language"] = language
    data[phone] = sub
    return data
