"""S012-T001 spike — trades → 1m OHLCV aggregation boundary validation.

Not production API; not collected by pytest.

Validates Wave 0 binding decisions before derived OHLCV contracts:

- UTC left-labeled 1m bucket assignment from trade event_at
- open/high/low/close/volume aggregation rules
- observed_at / available_at bar interval semantics

Run:

    uv run python tests/spike/run_trades_to_bars_spike.py
    uv run python tests/spike/run_trades_to_bars_spike.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path

_SPIKE_DIR = Path(__file__).resolve().parent
if str(_SPIKE_DIR) not in sys.path:
    sys.path.insert(0, str(_SPIKE_DIR))

from _trades_to_bars_spike import (
    DERIVATION_VERSION,
    aggregate_trades_to_bars,
    iter_synthetic_bars,
    synthetic_trades_across_minutes,
    validate_bucket_alignment,
)

from trading_framework.time.models.timeframe import Timeframe


@dataclass(frozen=True, slots=True)
class SpikeCheck:
    name: str
    passed: bool
    detail: str = ""


def _run_checks() -> list[SpikeCheck]:
    checks: list[SpikeCheck] = []
    trades = synthetic_trades_across_minutes()
    bars = aggregate_trades_to_bars(trades, target_timeframe=Timeframe("1m"))

    checks.append(
        SpikeCheck(
            name="two_minute_buckets",
            passed=len(bars) == 2,
            detail=str(len(bars)),
        )
    )
    if bars:
        first = bars[0]
        checks.append(
            SpikeCheck(
                name="first_bar_ohlcv",
                passed=(
                    first.open == Decimal("100.00")
                    and first.high == Decimal("101.50")
                    and first.low == Decimal("99.25")
                    and first.close == Decimal("100.75")
                    and first.volume == 26
                ),
                detail=(
                    f"o={first.open} h={first.high} l={first.low} c={first.close} v={first.volume}"
                ),
            )
        )
        checks.append(
            SpikeCheck(
                name="bucket_interval_alignment",
                passed=all(validate_bucket_alignment(bar) for bar in bars),
                detail=DERIVATION_VERSION,
            )
        )
        checks.append(
            SpikeCheck(
                name="empty_buckets_omitted",
                passed=len(list(iter_synthetic_bars())) == 2,
                detail="no zero-volume filler bars",
            )
        )
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Trades→1m bars spike (S012-T001)")
    parser.add_argument("--json", action="store_true", help="Print JSON report")
    args = parser.parse_args(argv)

    checks = _run_checks()
    passed = all(check.passed for check in checks)

    if args.json:
        payload = {"passed": passed, "checks": [asdict(check) for check in checks]}
        print(json.dumps(payload, indent=2))
    else:
        for check in checks:
            status = "PASS" if check.passed else "FAIL"
            print(f"[{status}] {check.name}: {check.detail}")
        print(f"overall: {'PASS' if passed else 'FAIL'}")

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
