"""S012-T001 spike — Databento DBN OHLCV archive boundary validation.

Not production API; not collected by pytest.

Validates Wave 0 binding decisions before OHLCV archive import contracts:

- DBN ohlcv-1m schema inspection (metadata, symbols, time range, checksum)
- prototype mapping: ts_event → observed_at, available_at = observed_at + 1m
- sample OHLCV row decode

Run (Tier 2 — local DBN required):

    uv run python tests/spike/run_databento_dbn_ohlcv_spike.py \\
        --path user_data/samples/nq_ohlcv_1m.dbn.zst
    uv run python tests/spike/run_databento_dbn_ohlcv_spike.py --path ... --json

Environment fallback:

    DATABENTO_OHLCV_DBN_PATH=/path/to/ohlcv.dbn.zst
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

from _databento_ohlcv_spike import inspect_ohlcv_dbn, sample_ohlcv_rows

_DEFAULT_PATH_CANDIDATES = (
    Path("user_data/samples/nq_ohlcv_1m.dbn.zst"),
    Path("user_data/samples/nq_ohlcv_1m.dbn"),
)


@dataclass(frozen=True, slots=True)
class SpikeCheck:
    name: str
    passed: bool
    detail: str = ""


def _resolve_dbn_path(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit
    env_path = os.environ.get("DATABENTO_OHLCV_DBN_PATH")
    if env_path:
        return Path(env_path)
    for candidate in _DEFAULT_PATH_CANDIDATES:
        if candidate.exists():
            return candidate
    searched = ", ".join(str(path) for path in _DEFAULT_PATH_CANDIDATES)
    msg = (
        "OHLCV DBN path required: pass --path, set DATABENTO_OHLCV_DBN_PATH, "
        f"or place a file at one of: {searched}"
    )
    raise FileNotFoundError(msg)


def _run_checks(path: Path, *, sample_rows: int) -> list[SpikeCheck]:
    checks: list[SpikeCheck] = []
    inspection = inspect_ohlcv_dbn(path)
    checks.append(
        SpikeCheck(
            name="schema_is_ohlcv_1m",
            passed=inspection.databento_schema == "ohlcv-1m",
            detail=inspection.databento_schema,
        )
    )
    checks.append(
        SpikeCheck(
            name="checksum_present",
            passed=len(inspection.source_checksum_sha256) == 64,
            detail=inspection.source_checksum_sha256[:16] + "...",
        )
    )

    samples = sample_ohlcv_rows(path, max_rows=sample_rows)
    checks.append(
        SpikeCheck(
            name="sample_rows_decoded",
            passed=len(samples) > 0,
            detail=str(len(samples)),
        )
    )
    if samples:
        first = samples[0]
        checks.append(
            SpikeCheck(
                name="available_at_after_observed_at",
                passed=first.available_at > first.observed_at,
                detail=f"{first.observed_at.isoformat()} -> {first.available_at.isoformat()}",
            )
        )
    return checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Databento DBN OHLCV spike (S012-T001)")
    parser.add_argument("--path", type=Path, default=None, help="Path to local OHLCV DBN archive")
    parser.add_argument("--json", action="store_true", help="Print JSON report")
    parser.add_argument("--sample-rows", type=int, default=5, help="Rows to sample")
    args = parser.parse_args(argv)

    path = _resolve_dbn_path(args.path)
    checks = _run_checks(path, sample_rows=args.sample_rows)
    passed = all(check.passed for check in checks)

    if args.json:
        print(
            json.dumps(
                {"path": str(path), "passed": passed, "checks": [asdict(c) for c in checks]},
                indent=2,
            )
        )
    else:
        print(f"path: {path}")
        for check in checks:
            status = "PASS" if check.passed else "FAIL"
            print(f"[{status}] {check.name}: {check.detail}")
        print(f"overall: {'PASS' if passed else 'FAIL'}")

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
