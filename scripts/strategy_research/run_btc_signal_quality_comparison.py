"""Sprint 058 T005 worked example, stage 3: baseline vs. score-filtered.

Runs the RSI / relative-volatility BTC strategy
(``scripts/strategy_research/_btc_rsi_relative_volatility.py``) twice on
the same real ``BTCUSDT.P`` data: once unscored (baseline) and once gated
by the ``SIGNAL_QUALITY`` scorer promoted in stage 2
(``scripts/strategy_research/build_btc_signal_quality_study.py`` +
``run_predictive_research.py`` + ``promote_predictive_run.py``), and prints
a baseline-vs-filtered comparison -- signal counts, performance, rejected
losers, rejected winners -- per §13H.3's completion criteria. The
comparison is written down whether or not the score helps; a negative
result is a complete outcome.

Usage::

    uv run python scripts/strategy_research/run_btc_signal_quality_comparison.py \
        --storage-root /absolute/path/to/user_data/workspace \
        --artifact-fingerprint <fingerprint from promote_predictive_run.py> \
        --threshold 0.5
"""

from __future__ import annotations

import argparse
from pathlib import Path

try:  # package import (pytest, or `-m scripts.strategy_research...`)
    from scripts.strategy_research._btc_rsi_relative_volatility import build_strategy
except ImportError:  # standalone script execution -- own directory is on sys.path
    from _btc_rsi_relative_volatility import (  # type: ignore[no-redef,import-not-found]
        build_strategy,
    )

from trading_framework.application.strategy_research import (
    RunStrategyResearchRequest,
    RunStrategyResearchResult,
    run_strategy_research,
)
from trading_framework.infrastructure.storage.metadata.registry import (
    FileDatasetRegistry,
)
from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.research.simulation import SimulationAssumptions
from trading_framework.strategy import ScoreConditionSpec
from trading_framework.time.models.timeframe import Timeframe

_DATASET_REF = DatasetRef.parse("BTCUSDT.P|ohlcv|1m|binance|binance-usdm-klines-v1@1")


def _run(
    storage_root: Path, *, score_condition: ScoreConditionSpec | None
) -> RunStrategyResearchResult:
    metadata = FileDatasetRegistry(storage_root).get(_DATASET_REF)
    strategy_model = build_strategy(score_condition=score_condition)
    return run_strategy_research(
        RunStrategyResearchRequest(
            dataset_ref=_DATASET_REF,
            timeframe=Timeframe("1m"),
            requested_range=TimeRange(start=metadata.start_at, end=metadata.end_at),
            storage_root=storage_root,
            strategy_model=strategy_model,
            assumptions=SimulationAssumptions(),
            evaluation_timeframe=Timeframe("1m"),
            persist=True,
        )
    )


def _summarize(label: str, result: RunStrategyResearchResult) -> dict[str, object]:
    trades = result.trades
    trade_count = trades.height
    if trade_count == 0:
        return {
            "label": label,
            "run_id": result.run_id,
            "trade_count": 0,
            "win_count": 0,
            "loss_count": 0,
            "win_rate": None,
            "total_net_pnl": 0.0,
            "mean_net_pnl": None,
        }
    net_pnl = trades.get_column("net_pnl")
    win_count = int((net_pnl > 0).sum())
    loss_count = int((net_pnl <= 0).sum())
    return {
        "label": label,
        "run_id": result.run_id,
        "trade_count": trade_count,
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": win_count / trade_count,
        "total_net_pnl": float(net_pnl.sum()),
        "mean_net_pnl": float(net_pnl.mean()),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-root", required=True, type=Path)
    parser.add_argument("--artifact-fingerprint", required=True)
    parser.add_argument("--threshold", required=True, type=float)
    args = parser.parse_args(argv)

    baseline = _run(args.storage_root, score_condition=None)
    scored = _run(
        args.storage_root,
        score_condition=ScoreConditionSpec(
            artifact_fingerprint=args.artifact_fingerprint, threshold=args.threshold
        ),
    )

    baseline_summary = _summarize("baseline", baseline)
    scored_summary = _summarize("scored", scored)

    # trade_id encodes strategy_model_id (which deliberately differs between
    # the baseline and scored strategy_model, T003/T004's own required
    # distinctness -- see run_strategy_research.py::derive_strategy_run_id's
    # sibling, the trade ledger's own id scheme), so it can never match
    # across these two runs. entry_signal_at (the occurrence's own
    # available_at-equivalent) is the correct, run-independent join key.
    join_column = "entry_signal_at"
    baseline_entries = baseline.trades.get_column(join_column) if baseline.trades.height else None
    scored_entries = scored.trades.get_column(join_column) if scored.trades.height else None
    baseline_ids = set(baseline_entries.to_list()) if baseline_entries is not None else set()
    scored_ids = set(scored_entries.to_list()) if scored_entries is not None else set()
    rejected_ids = baseline_ids - scored_ids
    rejected_mask = baseline.trades.get_column(join_column).is_in(list(rejected_ids))
    rejected_trades = baseline.trades.filter(rejected_mask)
    rejected_pnl = rejected_trades.get_column("net_pnl") if rejected_trades.height else None
    rejected_winners = int((rejected_pnl > 0).sum()) if rejected_pnl is not None else 0
    rejected_losers = int((rejected_pnl <= 0).sum()) if rejected_pnl is not None else 0

    print("=== Baseline ===")
    print(baseline_summary)
    print(f"=== Scored (threshold={args.threshold:.3f}) ===")
    print(scored_summary)
    print("=== Rejected occurrences (in baseline, filtered out by score) ===")
    print(f"rejected_total: {len(rejected_ids)}")
    print(f"rejected_winners: {rejected_winners}")
    print(f"rejected_losers: {rejected_losers}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
