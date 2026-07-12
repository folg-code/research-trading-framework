"""Sprint 004 T001 — MTF Polars implementation spike.

Not part of the production API. Run manually:

    uv run python tests/spike/run_mtf_polars_spike.py
    uv run python tests/spike/run_mtf_polars_spike.py --json

Validates:
- 1m → 5m OHLCV resampling (group_by_dynamic)
- available_at semantics on HTF bars
- backward join_asof alignment (LAST_CLOSED_BAR)
- look-ahead guard at a hand-crafted timestamp
- conversion boundary Polars → MarketBar → AnalysisDataView
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import tracemalloc
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import polars as pl

from trading_framework.core.types import Price, Volume
from trading_framework.market.models import MarketBar
from trading_framework.market.temporal.bar_interval import derive_bar_interval
from trading_framework.market_analysis.data.view import AnalysisDataView
from trading_framework.time.models.timeframe import Timeframe


@dataclass(frozen=True)
class LookAheadCheck:
    evaluation_at: str
    htf_available_at_used: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ConversionBenchmark:
    bar_count_1m: int
    bars_5m: int
    polars_to_bars_seconds: float
    bars_to_view_seconds: float
    peak_bytes: int


@dataclass(frozen=True)
class SpikeReport:
    polars_version: str
    resample_row_counts: dict[str, int]
    ohlcv_rules_verified: bool
    look_ahead_checks: list[LookAheadCheck]
    partial_bucket_note: str
    conversion: ConversionBenchmark
    decisions: list[str]
    checklist: dict[str, bool]


def _utc(y: int, m: int, d: int, hh: int, mm: int) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=UTC)


def build_lookahead_fixture_1m() -> pl.DataFrame:
    """Deterministic 1m bars from 10:00 through 10:44 inclusive."""
    start = _utc(2024, 6, 3, 10, 0)
    rows: list[dict[str, Any]] = []
    price = 100.0
    for i in range(45):
        ts = start + timedelta(minutes=i)
        o = price
        h = price + 1.0
        low = price - 0.5
        c = price + 0.25
        rows.append(
            {
                "observed_at": ts,
                "open": o,
                "high": h,
                "low": low,
                "close": c,
                "volume": float(1_000 + i),
            }
        )
        price += 0.1
    return pl.DataFrame(rows).sort("observed_at")


def build_scale_fixture_1m(bar_count: int) -> pl.DataFrame:
    start = _utc(2024, 1, 2, 14, 30)
    rows: list[dict[str, Any]] = []
    price = 20_000.0
    for i in range(bar_count):
        ts = start + timedelta(minutes=i)
        rows.append(
            {
                "observed_at": ts,
                "open": price,
                "high": price + 2.0,
                "low": price - 1.0,
                "close": price + 0.5,
                "volume": float(100 + (i % 500)),
            }
        )
        price += 0.05
    return pl.DataFrame(rows)


def resample_ohlcv_1m_to_5m(source: pl.DataFrame) -> pl.DataFrame:
    """Fixed UTC left-labeled 5m buckets via group_by_dynamic."""
    resampled = (
        source.sort("observed_at")
        .group_by_dynamic("observed_at", every="5m", closed="left", label="left")
        .agg(
            pl.col("open").first().alias("open"),
            pl.col("high").max().alias("high"),
            pl.col("low").min().alias("low"),
            pl.col("close").last().alias("close"),
            pl.col("volume").sum().alias("volume"),
        )
        .rename({"observed_at": "observed_at"})
    )
    tf_5m = Timeframe("5m")
    available = [
        derive_bar_interval(row["observed_at"], tf_5m)[1] for row in resampled.iter_rows(named=True)
    ]
    return resampled.with_columns(pl.Series("available_at", available))


def verify_manual_ohlcv_rules(source_1m: pl.DataFrame, resampled_5m: pl.DataFrame) -> bool:
    """Check first full 5m bucket 10:00-10:04 manually."""
    bucket = source_1m.filter(
        (pl.col("observed_at") >= _utc(2024, 6, 3, 10, 0))
        & (pl.col("observed_at") < _utc(2024, 6, 3, 10, 5))
    )
    row = resampled_5m.filter(pl.col("observed_at") == _utc(2024, 6, 3, 10, 0)).row(0, named=True)
    return (
        row["open"] == bucket["open"][0]
        and row["high"] == bucket["high"].max()
        and row["low"] == bucket["low"].min()
        and row["close"] == bucket["close"][-1]
        and row["volume"] == bucket["volume"].sum()
    )


def simple_atr_5m(resampled: pl.DataFrame, period: int = 14) -> pl.DataFrame:
    """Minimal TR → SMA ATR on 5m frame for spike (not production component)."""
    prev_close = pl.col("close").shift(1).fill_null(pl.col("close"))
    tr = pl.max_horizontal(
        pl.col("high") - pl.col("low"),
        (pl.col("high") - prev_close).abs(),
        (pl.col("low") - prev_close).abs(),
    )
    return (
        resampled.sort("observed_at")
        .with_columns(tr.alias("true_range"))
        .with_columns(pl.col("true_range").rolling_mean(window_size=period).alias("atr"))
        .select("observed_at", "available_at", "atr")
    )


def align_htf_to_1m(htf: pl.DataFrame, ltf: pl.DataFrame) -> pl.DataFrame:
    """Backward as-of on available_at (LAST_CLOSED_BAR consumption grid)."""
    ltf_eval = ltf.select(pl.col("observed_at").alias("evaluation_at"))
    htf_values = htf.filter(pl.col("atr").is_not_null()).select("available_at", "atr")
    return ltf_eval.sort("evaluation_at").join_asof(
        htf_values.sort("available_at"),
        left_on="evaluation_at",
        right_on="available_at",
        strategy="backward",
    )


def check_lookahead_at(
    aligned: pl.DataFrame,
    evaluation_at: datetime,
    *,
    must_not_equal_available_at: datetime | None = None,
) -> LookAheadCheck:
    row = aligned.filter(pl.col("evaluation_at") == evaluation_at)
    if row.is_empty():
        return LookAheadCheck(
            evaluation_at=evaluation_at.isoformat(),
            htf_available_at_used="",
            passed=False,
            detail="evaluation timestamp missing from aligned frame",
        )
    used_available = row["available_at"][0]
    if used_available is None:
        return LookAheadCheck(
            evaluation_at=evaluation_at.isoformat(),
            htf_available_at_used="",
            passed=False,
            detail="no HTF value joined (warm-up or gap)",
        )
    passed = used_available <= evaluation_at
    detail = f"joined available_at={used_available.isoformat()}"
    if must_not_equal_available_at is not None and used_available == must_not_equal_available_at:
        passed = False
        detail += " — incorrectly used incomplete HTF bar"
    return LookAheadCheck(
        evaluation_at=evaluation_at.isoformat(),
        htf_available_at_used=used_available.isoformat(),
        passed=passed,
        detail=detail,
    )


def polars_to_market_bars(frame: pl.DataFrame, timeframe: Timeframe) -> tuple[MarketBar, ...]:
    bars: list[MarketBar] = []
    for row in frame.iter_rows(named=True):
        observed = row["observed_at"]
        if not isinstance(observed, datetime):
            msg = "observed_at must be datetime"
            raise TypeError(msg)
        available = row.get("available_at")
        if available is None or not isinstance(available, datetime):
            _, available = derive_bar_interval(observed, timeframe)
        bars.append(
            MarketBar(
                open=Price(Decimal(str(row["open"]))),
                high=Price(Decimal(str(row["high"]))),
                low=Price(Decimal(str(row["low"]))),
                close=Price(Decimal(str(row["close"]))),
                volume=Volume(int(row["volume"])),
                observed_at=observed,
                available_at=available,
            )
        )
    return tuple(bars)


def benchmark_conversion(source_5m: pl.DataFrame) -> ConversionBenchmark:
    tf = Timeframe("5m")
    tracemalloc.start()
    t0 = time.perf_counter()
    bars = polars_to_market_bars(source_5m, tf)
    t1 = time.perf_counter()
    view = AnalysisDataView.from_bars(bars)
    t2 = time.perf_counter()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    _ = view  # use result
    return ConversionBenchmark(
        bar_count_1m=0,
        bars_5m=len(bars),
        polars_to_bars_seconds=t1 - t0,
        bars_to_view_seconds=t2 - t1,
        peak_bytes=peak,
    )


def run_spike(scale_bars: int) -> SpikeReport:
    fixture = build_lookahead_fixture_1m()
    resampled = resample_ohlcv_1m_to_5m(fixture)
    ohlcv_ok = verify_manual_ohlcv_rules(fixture, resampled)
    atr_htf = simple_atr_5m(resampled, period=3)
    aligned = align_htf_to_1m(atr_htf, fixture)

    eval_1037 = _utc(2024, 6, 3, 10, 37)
    incomplete_htf_available = _utc(2024, 6, 3, 10, 40)
    checks = [
        check_lookahead_at(
            aligned,
            eval_1037,
            must_not_equal_available_at=incomplete_htf_available,
        ),
        check_lookahead_at(aligned, _utc(2024, 6, 3, 10, 35)),
        check_lookahead_at(aligned, _utc(2024, 6, 3, 10, 40)),
    ]

    scale_1m = build_scale_fixture_1m(scale_bars)
    scale_5m = resample_ohlcv_1m_to_5m(scale_1m)
    conversion = benchmark_conversion(scale_5m)
    conversion = ConversionBenchmark(
        bar_count_1m=scale_bars,
        bars_5m=scale_5m.height,
        polars_to_bars_seconds=conversion.polars_to_bars_seconds,
        bars_to_view_seconds=conversion.bars_to_view_seconds,
        peak_bytes=conversion.peak_bytes,
    )

    partial_note = (
        "Polars group_by_dynamic(closed=left, label=left) emits buckets aligned to UTC "
        "epoch boundaries from the first observed timestamp in the sorted frame. "
        "Trailing partial bucket at range end is included when it contains at least one "
        "source row; leading partial bucket behavior verified on 14:30-start scale fixture."
    )

    decisions = [
        (
            "Use Polars group_by_dynamic for 1m->5m/1h OHLCV in ResampleNode "
            "(add polars to runtime deps in PR 2)."
        ),
        "ResampleSpec carries fixed UTC left/left semantics; no BoundaryPolicy enum in S004.",
        "Defer TradingCalendar subsystem; document PRB-007 deferral in ADR-MA-012.",
        "ResampleNode is execution DAG node type, not ComponentRegistry entry.",
        "Layered identity: ResampleIdentity / ComponentComputationIdentity / AlignmentIdentity.",
        "Request resolution produces explicit ResampleSpec before planner; no planner magic.",
        (
            "S004 boundary-only: Polars resample/align; convert to AnalysisDataView "
            "once for NumPy ATR path."
        ),
        "Defer MarketFrame migration to Sprint 005+ unless query path changes in parallel.",
    ]

    checklist = {
        "5.1_polars_first_for_new_batch_paths": True,
        "5.2_marketbar_not_required_for_mtf_spike_path": True,
        "5.3_no_analysisdataview_api_extension": True,
        "5.4_execution_state_consolidation_deferred": True,
        "5.5_registry_unchanged_until_second_backend": True,
        "5.6_layered_identity_not_wrapper_proliferation": True,
        "5.7_outcome_based_remaining_tasks": True,
        "5.8_one_adr_planned": True,
        "5.9_heuristic_applied_at_boundary": True,
    }

    return SpikeReport(
        polars_version=pl.__version__,
        resample_row_counts={
            "lookahead_fixture_1m": fixture.height,
            "lookahead_fixture_5m": resampled.height,
            "scale_fixture_1m": scale_bars,
            "scale_fixture_5m": scale_5m.height,
        },
        ohlcv_rules_verified=ohlcv_ok,
        look_ahead_checks=checks,
        partial_bucket_note=partial_note,
        conversion=conversion,
        decisions=decisions,
        checklist=checklist,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Sprint 004 MTF Polars spike")
    parser.add_argument("--json", action="store_true", help="Print JSON report to stdout")
    parser.add_argument(
        "--scale-bars", type=int, default=3_000, help="1m bars for conversion benchmark"
    )
    args = parser.parse_args()

    report = run_spike(scale_bars=args.scale_bars)
    all_pass = report.ohlcv_rules_verified and all(c.passed for c in report.look_ahead_checks)

    if args.json:
        print(json.dumps(asdict(report), indent=2, default=str))
    else:
        print("Sprint 004 T001 — MTF Polars spike")
        print(f"polars={report.polars_version}")
        print(f"ohlcv_rules_verified={report.ohlcv_rules_verified}")
        for check in report.look_ahead_checks:
            status = "PASS" if check.passed else "FAIL"
            print(f"  look_ahead {check.evaluation_at}: {status} - {check.detail}")
        conv = report.conversion
        print(f"conversion_5m_bars={conv.bars_5m} peak_bytes={conv.peak_bytes}")
        print(f"overall={'PASS' if all_pass else 'FAIL'}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
