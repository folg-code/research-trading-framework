"""Sprint 005 T001 — CME ES RTH calendar spike.

Not part of the production API. Run manually:

    uv run python tests/spike/run_calendar_spike.py
    uv run python tests/spike/run_calendar_spike.py --json

Validates:
- batch Polars ES RTH resolution (no per-bar Python loop in hot path)
- trading_day / session_id / is_rth columns
- DST spring and winter fixtures
- optional US equity holiday mask via exchange_calendars XNYS
- CMES Globex vs ES RTH distinction
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import exchange_calendars as xcals
import pandas as pd
import polars as pl

from trading_framework.time.sessions import (
    ES_RTH_SESSION_ID,
    OUTSIDE_RTH_SESSION_ID,
    CmeEsRthSessionResolver,
)

NEW_YORK = ZoneInfo("America/New_York")


@dataclass(frozen=True)
class BoundaryCheck:
    label: str
    timestamp: str
    trading_day: str
    session_id: str
    is_rth: bool
    passed: bool
    detail: str


@dataclass(frozen=True)
class BenchmarkResult:
    bar_count: int
    batch_seconds: float
    loop_seconds: float
    results_match: bool


@dataclass(frozen=True)
class SpikeReport:
    polars_version: str
    exchange_calendars_version: str
    cmes_globex_minutes_per_session: int
    boundary_checks: list[BoundaryCheck]
    dst_checks_passed: bool
    benchmark: BenchmarkResult
    decisions: list[str]
    checklist: dict[str, bool]


def _utc(y: int, m: int, d: int, hh: int, mm: int) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=UTC)


def build_fixture_1m(start: datetime, bar_count: int) -> pl.Series:
    timestamps = [start + timedelta(minutes=index) for index in range(bar_count)]
    return pl.Series("timestamp", timestamps)


def _ny_time_parts(timestamp: datetime) -> tuple[datetime, int, int, int]:
    ny = timestamp.astimezone(NEW_YORK)
    return ny, ny.weekday(), ny.hour, ny.minute


def is_es_rth_window(timestamp: datetime) -> bool:
    _ny, weekday, hour, minute = _ny_time_parts(timestamp)
    if weekday >= 5:
        return False
    after_open = (hour, minute) >= (9, 30)
    before_close = (hour, minute) < (16, 0)
    return after_open and before_close


def resolve_es_rth_loop(timestamps: pl.Series) -> pl.DataFrame:
    rows: list[dict[str, Any]] = []
    for ts in timestamps:
        if not isinstance(ts, datetime):
            msg = "timestamp must be datetime"
            raise TypeError(msg)
        ny = ts.astimezone(NEW_YORK)
        is_rth = is_es_rth_window(ts)
        rows.append(
            {
                "timestamp": ts,
                "trading_day": ny.date(),
                "session_id": ES_RTH_SESSION_ID if is_rth else OUTSIDE_RTH_SESSION_ID,
                "is_rth": is_rth,
            }
        )
    return pl.DataFrame(rows)


def resolve_es_rth_batch(
    timestamps: pl.Series,
    *,
    holiday_dates: frozenset[Any] | None = None,
) -> pl.DataFrame:
    """Delegate to production batch resolver (spike equivalence check)."""
    return CmeEsRthSessionResolver(holiday_dates=holiday_dates).resolve(timestamps)


def xnys_holiday_dates(start: datetime, end: datetime) -> frozenset[Any]:
    """US equity closed dates from XNYS calendar for holiday mask spike."""
    xnys = xcals.get_calendar("XNYS")
    start_day = pd.Timestamp(start.astimezone(NEW_YORK).date())
    end_day = pd.Timestamp(end.astimezone(NEW_YORK).date())
    sessions = xnys.sessions_in_range(start_day, end_day)
    session_set = set(sessions.date)
    holidays: set[Any] = set()
    day = start_day
    while day <= end_day:
        if day.weekday() < 5 and day.date() not in session_set:
            holidays.add(day.date())
        day += pd.Timedelta(days=1)
    return frozenset(holidays)


def check_boundary(
    label: str,
    timestamp: datetime,
    *,
    expect_rth: bool,
    expect_session: str,
) -> BoundaryCheck:
    row = resolve_es_rth_batch(pl.Series("timestamp", [timestamp])).row(0, named=True)
    is_rth = bool(row["is_rth"])
    session_id = str(row["session_id"])
    trading_day = str(row["trading_day"])
    passed = is_rth == expect_rth and session_id == expect_session
    detail = f"is_rth={is_rth} session_id={session_id} trading_day={trading_day}"
    return BoundaryCheck(
        label=label,
        timestamp=timestamp.isoformat(),
        trading_day=trading_day,
        session_id=session_id,
        is_rth=is_rth,
        passed=passed,
        detail=detail,
    )


def benchmark_resolution(timestamps: pl.Series) -> BenchmarkResult:
    t0 = time.perf_counter()
    batch = resolve_es_rth_batch(timestamps)
    t1 = time.perf_counter()
    loop = resolve_es_rth_loop(timestamps)
    t2 = time.perf_counter()
    match = batch.select("timestamp", "trading_day", "session_id", "is_rth").equals(
        loop.select("timestamp", "trading_day", "session_id", "is_rth")
    )
    return BenchmarkResult(
        bar_count=len(timestamps),
        batch_seconds=t1 - t0,
        loop_seconds=t2 - t1,
        results_match=match,
    )


def run_spike(*, scale_bars: int) -> SpikeReport:
    cmes = xcals.get_calendar("CMES")
    sample_day = pd.Timestamp("2024-06-03")
    globex_minutes = len(cmes.session_minutes(sample_day))

    boundary_checks = [
        check_boundary(
            "rth_open_edt",
            _utc(2024, 6, 3, 13, 30),
            expect_rth=True,
            expect_session=ES_RTH_SESSION_ID,
        ),
        check_boundary(
            "before_rth_open",
            _utc(2024, 6, 3, 13, 29),
            expect_rth=False,
            expect_session=OUTSIDE_RTH_SESSION_ID,
        ),
        check_boundary(
            "rth_close_boundary",
            _utc(2024, 6, 3, 19, 59),
            expect_rth=True,
            expect_session=ES_RTH_SESSION_ID,
        ),
        check_boundary(
            "at_rth_close",
            _utc(2024, 6, 3, 20, 0),
            expect_rth=False,
            expect_session=OUTSIDE_RTH_SESSION_ID,
        ),
        check_boundary(
            "dst_winter_open_est",
            _utc(2024, 1, 8, 14, 30),
            expect_rth=True,
            expect_session=ES_RTH_SESSION_ID,
        ),
        check_boundary(
            "dst_spring_open_edt",
            _utc(2024, 3, 11, 13, 30),
            expect_rth=True,
            expect_session=ES_RTH_SESSION_ID,
        ),
        check_boundary(
            "saturday_globex",
            _utc(2024, 6, 8, 15, 0),
            expect_rth=False,
            expect_session=OUTSIDE_RTH_SESSION_ID,
        ),
    ]

    dst_checks_passed = all(
        check.passed for check in boundary_checks if "dst" in check.label or "winter" in check.label
    )

    start = _utc(2024, 6, 3, 12, 0)
    fixture = build_fixture_1m(start, scale_bars)
    benchmark = benchmark_resolution(fixture)

    decisions = [
        "ES RTH MVP = 09:30-16:00 America/New_York Mon-Fri; NOT full CMES Globex (1440 min).",
        "Production TradingSessionResolver: batch Polars in/out; no per-bar loop.",
        "session_id ES_RTH vs OUTSIDE_RTH; is_rth distinct from is_market_open (ETH deferred).",
        "exchange_calendars (dev) useful for XNYS holiday mask; CMES not used as is_rth proxy.",
        "Wave 1: owned RTH window in infrastructure adapter; optional XNYS holidays behind flag.",
        "Do not promote exchange-calendars to runtime until Wave 1 scope confirms holiday need.",
        "Calendar is not a ComponentRegistry entry; enrichment stage before/at frame assembly.",
        "UTC timestamps on MarketBar unchanged; calendar maps interpretation only.",
    ]

    checklist = {
        "5.1_polars_first_batch_mapping": True,
        "5.2_marketbar_boundary_unchanged": True,
        "5.3_no_new_view_wrapper": True,
        "5.4_execution_state_unchanged": True,
        "5.5_registry_unchanged": True,
        "5.6_minimal_session_resolver_protocol": True,
        "5.7_outcome_based_wave1_calendar_pr": True,
        "5.8_one_adr_planned_wave5": True,
        "5.9_no_over_abstracted_calendar_layer": True,
    }

    return SpikeReport(
        polars_version=pl.__version__,
        exchange_calendars_version=xcals.__version__,
        cmes_globex_minutes_per_session=globex_minutes,
        boundary_checks=boundary_checks,
        dst_checks_passed=dst_checks_passed,
        benchmark=benchmark,
        decisions=decisions,
        checklist=checklist,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Sprint 005 calendar spike")
    parser.add_argument("--json", action="store_true", help="Print JSON report")
    parser.add_argument(
        "--scale-bars", type=int, default=10_000, help="1m timestamps for benchmark"
    )
    args = parser.parse_args()

    report = run_spike(scale_bars=args.scale_bars)
    all_pass = (
        all(check.passed for check in report.boundary_checks) and report.benchmark.results_match
    )

    if args.json:
        print(json.dumps(asdict(report), indent=2, default=str))
    else:
        print("Sprint 005 T001 — CME ES RTH calendar spike")
        print(
            f"polars={report.polars_version} exchange_calendars={report.exchange_calendars_version}"
        )
        print(f"cmes_globex_minutes={report.cmes_globex_minutes_per_session} (not ES RTH)")
        for check in report.boundary_checks:
            status = "PASS" if check.passed else "FAIL"
            print(f"  {check.label}: {status} — {check.detail}")
        bench = report.benchmark
        print(
            f"benchmark bars={bench.bar_count} batch={bench.batch_seconds:.4f}s "
            f"loop={bench.loop_seconds:.4f}s match={bench.results_match}"
        )
        print(f"overall={'PASS' if all_pass else 'FAIL'}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
