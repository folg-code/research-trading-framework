"""S015-T001 spike — volume-based roll policy probe on local Databento DBN.

Not production API; not collected by pytest.

Validates Wave 0 roll-policy assumptions before contract import contracts:

- per-contract symbol volume in archive
- RTH session volume by trading_day (CmeEsRthSessionResolver)
- proposed front-month contract per session (max RTH volume)

Run (Tier 2 — local DBN required):

    uv run python tests/spike/run_continuous_roll_policy_spike.py \\
        --path user_data/market_data/NQ/databento/.../glbx-mdp3-20250713.trades.dbn.zst
    uv run python tests/spike/run_continuous_roll_policy_spike.py --path ... --json

Environment fallback: DATABENTO_DBN_PATH
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import polars as pl

from trading_framework.infrastructure.importers.databento import DatabentoDBNTradeReader
from trading_framework.time.sessions import CmeEsRthSessionResolver

_DEFAULT_PATH_CANDIDATES = (
    Path(
        "user_data/market_data/NQ/databento/GLBX-20260712-DU3ML8YKBH/"
        "glbx-mdp3-20250713.trades.dbn.zst"
    ),
    Path("user_data/samples/nq_trades.dbn.zst"),
)

_SPREAD_MARKER = "-"


@dataclass(frozen=True, slots=True)
class SessionVolumeRow:
    session_date: str
    contract: str
    rth_volume: int


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


def _is_outright_symbol(symbol: str) -> bool:
    return _SPREAD_MARKER not in symbol and symbol.startswith("NQ") and len(symbol) >= 4


def _run_spike(path: Path, *, chunk_size: int) -> dict[str, object]:
    reader = DatabentoDBNTradeReader(chunk_size=chunk_size)
    resolver = CmeEsRthSessionResolver()

    total_by_symbol: dict[str, int] = defaultdict(int)
    rth_by_session_contract: dict[tuple[date, str], int] = defaultdict(int)
    total_rows = 0
    spread_rows = 0

    for chunk in reader.iter_raw_chunks(path):
        for row in chunk.itertuples(index=False):
            total_rows += 1
            symbol = str(getattr(row, "symbol", ""))
            size = int(getattr(row, "size", 0))
            total_by_symbol[symbol] += size
            if not _is_outright_symbol(symbol):
                spread_rows += 1
                continue

            event_at = pl.Series([row.ts_event])
            resolved = resolver.resolve(event_at)
            if not resolved.row(0, named=True)["is_rth"]:
                continue
            trading_day: date = resolved.row(0, named=True)["trading_day"]
            rth_by_session_contract[(trading_day, symbol)] += size

    proposed_front: dict[str, str] = {}
    sessions = sorted({session for session, _ in rth_by_session_contract})
    for session in sessions:
        contracts = {
            contract: volume
            for (sess, contract), volume in rth_by_session_contract.items()
            if sess == session
        }
        if contracts:
            proposed_front[str(session)] = max(contracts, key=contracts.get)  # type: ignore[arg-type]

    session_rows = [
        SessionVolumeRow(
            session_date=str(session),
            contract=contract,
            rth_volume=volume,
        )
        for (session, contract), volume in sorted(rth_by_session_contract.items())
    ]

    return {
        "path": str(path),
        "total_rows": total_rows,
        "spread_rows_excluded": spread_rows,
        "symbols_total_volume": dict(sorted(total_by_symbol.items())),
        "rth_session_contract_volume": [
            {
                "session_date": row.session_date,
                "contract": row.contract,
                "rth_volume": row.rth_volume,
            }
            for row in session_rows
        ],
        "proposed_front_month_by_session": proposed_front,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Probe volume-based roll policy on a trades DBN.")
    parser.add_argument("--path", type=Path, default=None, help="Path to trades .dbn or .dbn.zst")
    parser.add_argument("--chunk-size", type=int, default=5000)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        path = _resolve_dbn_path(args.path)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if not path.exists():
        print(f"archive not found: {path}", file=sys.stderr)
        return 1

    payload = _run_spike(path, chunk_size=args.chunk_size)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"path: {payload['path']}")
        print(f"total_rows: {payload['total_rows']}")
        print(f"spread_rows_excluded: {payload['spread_rows_excluded']}")
        print("symbols_total_volume:", payload["symbols_total_volume"])
        print("proposed_front_month_by_session:", payload["proposed_front_month_by_session"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
