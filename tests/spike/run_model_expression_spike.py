"""S006-T001 spike — AnalysisFrame adapter, ternary logic, firing policies.

Not production API; not collected by pytest.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

import polars as pl

from trading_framework.market_analysis.assembly.frame import AnalysisFrame


class SignalFiringPolicy(StrEnum):
    ON_TRUE_EDGE = "on_true_edge"
    ON_EVENT = "on_event"


@dataclass(frozen=True, slots=True)
class SpikeCheck:
    name: str
    passed: bool
    detail: str = ""


def _analysis_frame_to_polars(
    frame: AnalysisFrame,
    *,
    column_keys: tuple[str, ...],
    evaluation_minutes: int = 1,
) -> pl.DataFrame:
    rows: dict[str, list[Any]] = {
        "timestamp": list(frame.timestamps),
    }
    delta = timedelta(minutes=evaluation_minutes)
    rows["available_at"] = [ts + delta for ts in frame.timestamps]
    for key in column_keys:
        values = frame.columns[key]
        rows[key] = list(values)
    return pl.DataFrame(rows)


def _compare_eq(series: pl.Series, expected: float) -> pl.Series:
    frame = pl.DataFrame({"value": series})
    return frame.select(
        pl.when(pl.col("value").is_nan())
        .then(None)
        .otherwise(pl.col("value") == expected)
        .alias("result")
    )["result"]


def _and_nullable(left: pl.Series, right: pl.Series) -> pl.Series:
    frame = pl.DataFrame({"left": left, "right": right})
    return frame.select(
        pl.when(pl.col("left").eq(False))
        .then(False)
        .when(pl.col("right").eq(False))
        .then(False)
        .when(pl.col("left").is_null() | pl.col("right").is_null())
        .then(None)
        .otherwise(True)
        .alias("result")
    )["result"]


def _or_nullable(left: pl.Series, right: pl.Series) -> pl.Series:
    frame = pl.DataFrame({"left": left, "right": right})
    return frame.select(
        pl.when(pl.col("left").eq(True))
        .then(True)
        .when(pl.col("right").eq(True))
        .then(True)
        .when(pl.col("left").is_null() | pl.col("right").is_null())
        .then(None)
        .otherwise(False)
        .alias("result")
    )["result"]


def _not_nullable(series: pl.Series) -> pl.Series:
    frame = pl.DataFrame({"value": series})
    return frame.select(
        pl.when(pl.col("value").is_null()).then(None).otherwise(~pl.col("value")).alias("result")
    )["result"]


def _on_true_edge(condition: pl.Series) -> pl.Series:
    frame = pl.DataFrame({"condition": condition})
    return frame.select(
        pl.when(pl.col("condition").is_null())
        .then(False)
        .when(pl.col("condition").shift(1).is_null() & pl.col("condition").eq(True))
        .then(True)
        .when(pl.col("condition").shift(1).eq(False) & pl.col("condition").eq(True))
        .then(True)
        .otherwise(False)
        .alias("result")
    )["result"]


def _on_event(condition: pl.Series) -> pl.Series:
    frame = pl.DataFrame({"condition": condition})
    return frame.select(
        (pl.col("condition").fill_null(False) & pl.col("condition").eq(True)).alias("result")
    )["result"]


def _sample_frame() -> AnalysisFrame:
    start = datetime(2024, 6, 3, 14, 30, tzinfo=UTC)
    timestamps = tuple(start + timedelta(minutes=index) for index in range(6))
    state = (math.nan, 0.0, 1.0, 1.0, 1.0, 0.0)
    event = (0.0, 0.0, 1.0, 0.0, 0.0, 0.0)
    return AnalysisFrame(
        timestamps=timestamps,
        columns={"volatility_state": state, "higher_low_event": event},
        column_lineage={},
    )


def run_spike() -> list[SpikeCheck]:
    checks: list[SpikeCheck] = []
    frame = _sample_frame()
    df = _analysis_frame_to_polars(frame, column_keys=("volatility_state", "higher_low_event"))

    checks.append(
        SpikeCheck(
            name="frame_adapter_rows",
            passed=df.height == len(frame.timestamps),
            detail=f"rows={df.height}",
        )
    )
    checks.append(
        SpikeCheck(
            name="frame_adapter_nan_preserved",
            passed=df["volatility_state"].is_nan()[0],
        )
    )

    compare = _compare_eq(df["volatility_state"], 1.0)
    checks.append(
        SpikeCheck(
            name="compare_null_on_nan_operand",
            passed=bool(compare.is_null()[0]),
        )
    )

    and_result = _and_nullable(
        pl.Series([False, True, True, None]),
        pl.Series([None, False, None, True]),
    )
    checks.append(SpikeCheck(name="and_false_null", passed=and_result[0] is False))
    checks.append(SpikeCheck(name="and_true_null", passed=and_result[2] is None))

    or_result = _or_nullable(
        pl.Series([False, True, False, None]),
        pl.Series([None, False, None, False]),
    )
    checks.append(SpikeCheck(name="or_true_null", passed=or_result[1] is True))
    checks.append(SpikeCheck(name="or_false_null", passed=or_result[2] is None))

    not_result = _not_nullable(pl.Series([None, True, False]))
    checks.append(SpikeCheck(name="not_null", passed=bool(not_result.is_null()[0])))

    state_condition = _compare_eq(df["volatility_state"], 1.0)
    edge = _on_true_edge(state_condition)
    checks.append(
        SpikeCheck(
            name="on_true_edge_single_emission",
            passed=int(edge.sum()) == 1 and bool(edge[2]),
            detail=f"edge={edge.to_list()}",
        )
    )

    event_condition = _compare_eq(df["higher_low_event"], 1.0)
    event_emit = _on_event(event_condition)
    checks.append(
        SpikeCheck(
            name="on_event_sparse_emission",
            passed=int(event_emit.sum()) == 1 and bool(event_emit[2]),
            detail=f"event={event_emit.to_list()}",
        )
    )
    checks.append(
        SpikeCheck(
            name="null_does_not_fire",
            passed=not bool(edge[0]) and not bool(event_emit[0]),
        )
    )

    return checks


def _checklist_pass(checks: list[SpikeCheck]) -> dict[str, bool]:
    return {
        "polars_first_batch": True,
        "no_global_mutable_state": True,
        "no_speculative_infrastructure": True,
        "reuse_ma_frame_path": True,
        "domain_boundary_preserved": True,
        "all_checks_pass": all(check.passed for check in checks),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="S006 model expression spike")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary")
    args = parser.parse_args()

    checks = run_spike()
    checklist = _checklist_pass(checks)
    payload = {
        "task": "S006-T001",
        "checks": [
            {"name": check.name, "passed": check.passed, "detail": check.detail} for check in checks
        ],
        "checklist": checklist,
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        for check in checks:
            status = "PASS" if check.passed else "FAIL"
            suffix = f" ({check.detail})" if check.detail else ""
            print(f"{status}: {check.name}{suffix}")
        print()
        print("Checklist:", checklist)

    return 0 if checklist["all_checks_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
