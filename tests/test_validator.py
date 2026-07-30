import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agmarknet_client import MandiPriceRecord
from src.data_validator import validate_record
from src.command_parser import parse
from src.match_utils import resolve_mandi, resolve_crop


def make_record(modal=3000.0, min_p=2800.0, max_p=3200.0, days_ago=0):
    date = (datetime.now() - timedelta(days=days_ago)).strftime("%d/%m/%Y")
    return MandiPriceRecord(
        state="Karnataka", district="Tumakuru", market="Tumkur",
        commodity="Ragi (Finger Millet)/Nachni", variety="Local", grade="FAQ",
        arrival_date=date, min_price=min_p, max_price=max_p, modal_price=modal,
    )


def test_ok_record_passes():
    r = make_record()
    result = validate_record(r, history_modal_prices=[2950, 3000, 3050])
    assert result.status == "ok"


def test_rejects_inconsistent_min_max():
    r = make_record(modal=3000, min_p=3500, max_p=3200)  # min > max: nonsense
    result = validate_record(r, history_modal_prices=[])
    assert result.status == "rejected"


def test_rejects_zero_price():
    r = make_record(modal=0)
    result = validate_record(r, history_modal_prices=[])
    assert result.status == "rejected"


def test_flags_stale_data():
    r = make_record(days_ago=5)
    result = validate_record(r, history_modal_prices=[2950, 3000, 3050])
    assert result.status == "stale"
    assert result.days_old == 5


def test_flags_outlier_price():
    # Internally consistent (min <= modal <= max) but far from recent history
    r = make_record(modal=6000, min_p=5800, max_p=6200)
    result = validate_record(r, history_modal_prices=[2900, 3000, 3100, 2950])
    assert result.status == "flagged"


def test_no_data_when_record_missing():
    result = validate_record(None, history_modal_prices=[])
    assert result.status == "no_data"


def test_no_outlier_flag_with_insufficient_history():
    r = make_record(modal=6000, min_p=5800, max_p=6200)
    result = validate_record(r, history_modal_prices=[3000])  # only 1 point
    assert result.status == "ok"


def test_command_parser_track():
    cmd = parse("TRACK ragi Tumkur, Chitradurga")
    assert cmd.action == "track"
    assert cmd.crop_text == "ragi"
    assert cmd.mandi_texts == ["Tumkur", "Chitradurga"]


def test_command_parser_stop():
    assert parse("STOP").action == "stop"


def test_command_parser_unknown():
    assert parse("blah blah").action == "unknown"


def test_resolve_crop_alias():
    assert resolve_crop("ragi") == "Ragi (Finger Millet)/Nachni"
    assert resolve_crop("nonsense_crop_xyz") is None


def test_resolve_mandi_exact():
    match, alts = resolve_mandi("Tumkur")
    assert match == "Tumkur"


def test_resolve_mandi_typo():
    match, alts = resolve_mandi("Tumkor")  # common typo
    assert match == "Tumkur"


if __name__ == "__main__":
    import traceback
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed, failed = 0, 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
            passed += 1
        except Exception:
            print(f"FAIL  {t.__name__}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
