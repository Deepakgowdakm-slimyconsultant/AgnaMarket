"""
data_validator.py

This is the most important file in the whole project.

AgnaMarket's one non-negotiable rule: a farmer should never receive a price
that we are not reasonably confident is real and current. This module is
where that promise actually gets enforced — everything else just fetches
and formats.

Three checks, applied in order:
  1. Internal consistency  -> is this even a sane record on its own?
  2. Freshness              -> how old is this data, actually?
  3. Historical plausibility -> does it look like a typo/outlier vs recent
     prices at the same mandi for the same crop?

Nothing here silently drops a farmer's requested mandi. Every outcome is
one of: OK, STALE (with the real date attached), or FLAGGED (shown, with a
visible warning) — never a silent guess.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median
from typing import Optional

from src.agmarknet_client import MandiPriceRecord

# If a record's arrival_date is more than this many days before "today",
# we treat it as stale rather than current.
STALE_AFTER_DAYS = 2

# If today's modal price differs from the recent median by more than this
# fraction, flag it for the farmer to see with a warning rather than hide it.
OUTLIER_THRESHOLD = 0.40  # 40%

# Need at least this many historical points before we trust a median enough
# to flag outliers against it. Below this, we just show the price plainly.
MIN_HISTORY_FOR_OUTLIER_CHECK = 3


@dataclass
class ValidatedPrice:
    record: Optional[MandiPriceRecord]
    status: str  # "ok" | "stale" | "flagged" | "rejected" | "no_data"
    reason: str  # human-readable, farmer-facing-safe explanation
    days_old: Optional[int] = None


def _days_old(record: MandiPriceRecord, as_of: datetime) -> Optional[int]:
    d = record.arrival_date_obj
    if d is None:
        return None
    return (as_of.date() - d.date()).days


def validate_record(
    record: Optional[MandiPriceRecord],
    history_modal_prices: list[float],
    as_of: Optional[datetime] = None,
) -> ValidatedPrice:
    """Validate a single fetched price record against our accuracy rules.

    `history_modal_prices` should be recent (e.g. last 7-14 days) modal
    prices for the SAME mandi + SAME commodity, oldest-to-newest, not
    including today's record.
    """
    as_of = as_of or datetime.now()

    if record is None:
        return ValidatedPrice(
            record=None,
            status="no_data",
            reason="No price has ever been reported for this mandi/crop combination. "
            "Double-check the mandi name and crop spelling.",
        )

    if not record.is_internally_consistent:
        return ValidatedPrice(
            record=record,
            status="rejected",
            reason="The government data for this entry looks internally inconsistent "
            "(e.g. min/max/modal don't line up, or a price is zero). "
            "We're withholding this number rather than risk showing you something wrong.",
        )

    days_old = _days_old(record, as_of)

    if days_old is not None and days_old > STALE_AFTER_DAYS:
        return ValidatedPrice(
            record=record,
            status="stale",
            reason=f"This is the most recent price we have, but it's from "
            f"{record.arrival_date}, not today. This mandi may not have reported since.",
            days_old=days_old,
        )

    if len(history_modal_prices) >= MIN_HISTORY_FOR_OUTLIER_CHECK:
        recent_median = median(history_modal_prices)
        if recent_median > 0:
            deviation = abs(record.modal_price - recent_median) / recent_median
            if deviation > OUTLIER_THRESHOLD:
                return ValidatedPrice(
                    record=record,
                    status="flagged",
                    reason=(
                        f"This price (₹{record.modal_price:.0f}) is "
                        f"{deviation*100:.0f}% away from the recent typical price "
                        f"(₹{recent_median:.0f}). Could be a genuine market swing "
                        f"(festival demand, sudden shortage) or a data entry error at "
                        f"the mandi — worth confirming locally before acting on it."
                    ),
                    days_old=days_old,
                )

    return ValidatedPrice(record=record, status="ok", reason="", days_old=days_old)
