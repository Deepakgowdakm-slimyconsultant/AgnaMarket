"""
refresh_reference_lists.py

The seed list in config/mandis_karnataka.json is a starting point, not the
truth. This script pulls the actual, current list of Karnataka markets
straight from the live API and overwrites that config file — so mandi-name
matching (match_utils.py) never drifts from what the government dataset
actually contains.

Run this periodically (weekly is plenty — mandi lists don't change often)
via .github/workflows/ — a separate lightweight workflow, since it needs a
bigger API quota than the daily alert job.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agmarknet_client import fetch_distinct_markets

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "mandis_karnataka.json"


def main() -> None:
    markets = fetch_distinct_markets(state="Karnataka")
    if not markets:
        print("WARNING: got zero markets back — NOT overwriting existing config, "
              "to avoid wiping a good list because of a bad API response.")
        return

    payload = {
        "_meta": {
            "note": "Auto-refreshed from the live data.gov.in Agmarknet API. "
            "Do not hand-edit — edit the refresh script instead if needed.",
            "last_refreshed": datetime.now().isoformat(),
            "source": "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070",
            "market_count": len(markets),
        },
        "markets": markets,
    }

    CONFIG_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Refreshed {len(markets)} Karnataka markets.")


if __name__ == "__main__":
    main()
