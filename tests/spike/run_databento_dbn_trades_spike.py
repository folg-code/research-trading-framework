"""S011-T001 spike — Databento DBN trades archive boundary validation.

Not production API; not collected by pytest.

Validates Wave 0 binding decisions before MarketTrade + archive import contracts:

- DBN trades schema inspection (metadata, symbols, time range, checksum)
- chunked decode via databento DBNStore.to_df(count=...)
- prototype mapping: ts_event → event_at, ts_recv → received_at
- day partition histogram (UTC event_at)
- raw side semantics sample

Run (Tier 2 — local DBN required):

    uv run python tests/spike/run_databento_dbn_trades_spike.py \\
        --path user_data/samples/nq_trades.dbn.zst
    uv run python tests/spike/run_databento_dbn_trades_spike.py --path ... --json

Environment fallback:

    DATABENTO_DBN_PATH=/path/to/trades.dbn.zst
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

_SPIKE_DIR = Path(__file__).resolve().parent
if str(_SPIKE_DIR) not in sys.path:
    sys.path.insert(0, str(_SPIKE_DIR))

from _databento_trades_spike import (
    DEFAULT_CHUNK_SIZE,
    inspect_trades_dbn,
    iter_trades_chunks,
    map_trades_row,
    side_value_counts,
)

_DEFAULT_PATH_CANDIDATES = (
    Path(
        "user_data/market_data/NQ/databento/GLBX-20260712-DU3ML8YKBH/"
        "glbx-mdp3-20250713.trades.dbn.zst"
    ),
    Path("user_data/samples/nq_trades.dbn.zst"),
    Path("user_data/samples/nq_trades.dbn"),
)


@dataclass(frozen=True, slots=True)
class SpikeCheck:
    name: str
    passed: bool
    detail: str = ""


def _resolve_dbn_path(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    env_path = os.environ.get("DATABENTO_DBN_PATH")
    if env_path:
        return Path(env_path)
    for candidate in _DEFAULT_PATH_CANDIDATES:
        if candidate.exists():
            return candidate
    searched = ", ".join(str(path) for path in _DEFAULT_PATH_CANDIDATES)
    msg = (
        "trades DBN path required: pass --path, set DATABENTO_DBN_PATH, "
        f"or place a file at one of: {searched}"
    )
    raise FileNotFoundError(msg)


def _run_checks(path: Path, *, chunk_size: int, sample_rows: int) -> list[SpikeCheck]:
    checks: list[SpikeCheck] = []

    inspection = inspect_trades_dbn(path)
    checks.append(
        SpikeCheck(
            name="schema_is_trades",
            passed=inspection.databento_schema == "trades",
            detail=inspection.databento_schema,
        )
    )
    checks.append(
        SpikeCheck(
            name="source_checksum_computed",
            passed=len(inspection.source_checksum_sha256) == 64,
            detail=inspection.source_checksum_sha256[:16] + "...",
        )
    )
    checks.append(
        SpikeCheck(
            name="archive_has_byte_size",
            passed=inspection.nbytes > 0,
            detail=str(inspection.nbytes),
        )
    )

    first_chunk = next(iter_trades_chunks(path, chunk_size=chunk_size))
    first_row = next(first_chunk.itertuples(index=False))
    sample = map_trades_row(first_row)
    checks.append(
        SpikeCheck(
            name="event_at_from_ts_event",
            passed=sample.event_at.tzinfo is not None,
            detail=sample.event_at.isoformat(),
        )
    )
    checks.append(
        SpikeCheck(
            name="price_and_size_positive",
            passed=sample.price > 0 and sample.size > 0,
            detail=f"price={sample.price} size={sample.size}",
        )
    )

    day_keys: set[object] = set()
    rows_seen = 0
    for chunk in iter_trades_chunks(path, chunk_size=chunk_size):
        for row in chunk.itertuples(index=False):
            mapped = map_trades_row(row)
            day_keys.add(mapped.event_at.date())
            rows_seen += 1
            if rows_seen >= sample_rows:
                break
        if rows_seen >= sample_rows:
            break

    checks.append(
        SpikeCheck(
            name="chunked_decode_sample",
            passed=rows_seen > 0,
            detail=f"rows_sampled={rows_seen}",
        )
    )
    checks.append(
        SpikeCheck(
            name="day_partition_signal",
            passed=len(day_keys) >= 1,
            detail=f"distinct_days_in_sample={len(day_keys)}",
        )
    )

    sides = side_value_counts(path, chunk_size=chunk_size, max_rows=min(sample_rows, 10_000))
    checks.append(
        SpikeCheck(
            name="side_values_observed",
            passed=bool(sides),
            detail=json.dumps({str(key): value for key, value in sides.items()}),
        )
    )

    checks.append(
        SpikeCheck(
            name="symbols_or_symbology_present",
            passed=bool(inspection.symbols or inspection.symbology_instrument_ids),
            detail=(
                f"symbols={len(inspection.symbols)} "
                f"instrument_ids={len(inspection.symbology_instrument_ids)}"
            ),
        )
    )

    return checks


def _print_human(checks: list[SpikeCheck], path: Path) -> int:
    passed = sum(1 for check in checks if check.passed)
    total = len(checks)
    print(f"S011-T001 Databento trades DBN spike — {path}")
    print(f"Checks: {passed}/{total} passed\n")
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        detail = f" — {check.detail}" if check.detail else ""
        print(f"  [{status}] {check.name}{detail}")
    if passed < total:
        print("\nSpike FAILED — resolve blockers before S011-T002.")
        return 1
    print("\nSpike PASSED — proceed to archive import contracts (S011-T002+).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="S011-T001 Databento DBN trades spike")
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help="Path to local trades .dbn or .dbn.zst archive (Tier 2)",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON result")
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help="Rows per DBN decode chunk",
    )
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=5_000,
        help="Rows to sample for partition/side checks",
    )
    args = parser.parse_args(argv)

    try:
        dbn_path = _resolve_dbn_path(args.path)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if not dbn_path.exists():
        print(f"file does not exist: {dbn_path}", file=sys.stderr)
        return 2

    try:
        checks = _run_checks(
            dbn_path.resolve(),
            chunk_size=args.chunk_size,
            sample_rows=args.sample_rows,
        )
    except Exception as exc:
        print(f"spike error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        payload = {
            "path": str(dbn_path.resolve()),
            "checks": [asdict(check) for check in checks],
            "passed": all(check.passed for check in checks),
        }
        print(json.dumps(payload, indent=2))
        return 0 if payload["passed"] else 1

    return _print_human(checks, dbn_path.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
