"""
agmarknet_client.py

Talks to the government's open data API for daily mandi prices.

Source dataset: "Current Daily Price of Various Commodities from Various
Markets (Mandi)" — published by the Ministry of Agriculture and Farmers
Welfare, sourced from the AGMARKNET portal, hosted on data.gov.in.

Resource ID: 9ef84268-d588-465a-a308-a864a43d0070
Docs page:   https://www.data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi

IMPORTANT — API key:
The sample key baked into data.gov.in's own docs
("579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b") is public and
capped at ~10 records per call. That's fine for testing this script, but for
real use you MUST register your own free key at https://data.gov.in
(Login -> My Account -> Generate API Key) and set it as the DATA_GOV_IN_API_KEY
secret in the GitHub repo. Never commit a real key to the repo.
"""

from __future__ import annotations

import os
import json
import time
import urllib.request
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
BASE_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"

# Public sample key. Rate-limited to ~10 records/call. Used only as a
# last-resort fallback so the script never hard-crashes with no key set.
FALLBACK_SAMPLE_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"

# data.gov.in is a government server that's occasionally slow, not always
# a hard failure. We give it more time and a couple of retries before
# genuinely giving up, rather than failing the whole run on one slow response.
REQUEST_TIMEOUT_SECONDS = 45
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 8


def _fetch_url(url: str) -> str:
    """GET a URL with retries. Raises RuntimeError only after every
    attempt has failed."""
    last_error: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
                return resp.read().decode("utf-8")
        except Exception as exc:  # noqa: BLE001 — deliberately broad, we retry regardless of cause
            last_error = exc
            if attempt < MAX_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_SECONDS)
    raise RuntimeError(
        f"Agmarknet API request failed after {MAX_ATTEMPTS} attempts: {last_error}"
    ) from last_error


@dataclass
class MandiPriceRecord:
    state: str
    district: str
    market: str
    commodity: str
    variety: str
    grade: str
    arrival_date: str  # as given by the API, format DD/MM/YYYY
    min_price: float
    max_price: float
    modal_price: float

    @property
    def arrival_date_obj(self) -> Optional[datetime]:
        try:
            return datetime.strptime(self.arrival_date, "%d/%m/%Y")
        except (ValueError, TypeError):
            return None

    @property
    def is_internally_consistent(self) -> bool:
        """Basic sanity check on the record itself, independent of history.

        Government data entry does sometimes produce nonsense (min > max,
        zero prices, etc). We never forward a record like this to a farmer
        as if it were a normal price.
        """
        try:
            if self.min_price <= 0 or self.max_price <= 0 or self.modal_price <= 0:
                return False
            if not (self.min_price <= self.modal_price <= self.max_price):
                return False
            return True
        except TypeError:
            return False


def _get_api_key() -> str:
    key = os.environ.get("DATA_GOV_IN_API_KEY", "").strip()
    if key:
        return key
    return FALLBACK_SAMPLE_KEY


def fetch_prices(
    commodity: str,
    market: Optional[str] = None,
    state: str = "Karnataka",
    limit: int = 200,
) -> list[MandiPriceRecord]:
    """Fetch current mandi price records for a commodity in Karnataka.

    If `market` is given, results are additionally filtered to that market
    name (exact match against the API's own market naming — use
    refresh_reference_lists.py output to get the correct spelling).

    Raises RuntimeError on network/API failure — callers must handle this
    explicitly rather than silently treating a failed fetch as "no data",
    since those are very different situations for a farmer.
    """
    params = {
        "api-key": _get_api_key(),
        "format": "json",
        "limit": str(limit),
        "filters[state]": state,
        "filters[commodity]": commodity,
    }
    if market:
        params["filters[market]"] = market

    url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"

    try:
        raw = _fetch_url(url)
    except RuntimeError:
        raise

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Agmarknet API returned unparseable response: {exc}") from exc

    records_raw = payload.get("records", [])
    records: list[MandiPriceRecord] = []
    for r in records_raw:
        try:
            records.append(
                MandiPriceRecord(
                    state=r.get("state", ""),
                    district=r.get("district", ""),
                    market=r.get("market", ""),
                    commodity=r.get("commodity", ""),
                    variety=r.get("variety", ""),
                    grade=r.get("grade", ""),
                    arrival_date=r.get("arrival_date", ""),
                    min_price=float(r.get("min_price", 0) or 0),
                    max_price=float(r.get("max_price", 0) or 0),
                    modal_price=float(r.get("modal_price", 0) or 0),
                )
            )
        except (TypeError, ValueError):
            # A single malformed row should never crash the whole fetch.
            # It just gets skipped — and will show up as "no data" for that
            # market rather than a wrong number.
            continue

    return records


def fetch_distinct_markets(state: str = "Karnataka", limit: int = 500) -> list[dict]:
    """Pull a broad sample of records for the state and derive the distinct
    (district, market) pairs actually present in the live data. Used by
    refresh_reference_lists.py to keep config/mandis_karnataka.json honest.
    """
    params = {
        "api-key": _get_api_key(),
        "format": "json",
        "limit": str(limit),
        "filters[state]": state,
    }
    url = f"{BASE_URL}?{urllib.parse.urlencode(params)}"

    raw = _fetch_url(url)
    payload = json.loads(raw)

    seen = set()
    out = []
    for r in payload.get("records", []):
        key = (r.get("district", ""), r.get("market", ""))
        if key not in seen and key != ("", ""):
            seen.add(key)
            out.append({"district": key[0], "market": key[1]})
    return out
