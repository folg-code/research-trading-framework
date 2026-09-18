"""Drawdown-episode extraction from a persisted Strategy Research equity curve.

Phase 18, 18A Milestone 1a (Sprint 068) / D-P18-05. Computed purely
post-hoc from an already-persisted ``equity.parquet`` -- no simulator
rerun, no new raw data.
"""

from __future__ import annotations

import polars as pl

DRAWDOWN_EPISODES_SCHEMA_VERSION = "strategy_research_drawdown_episodes.v1"


def drawdown_episodes_schema() -> dict[str, pl.DataType]:
    return {
        "schema_version": pl.String(),
        "run_id": pl.String(),
        "episode_id": pl.Int64(),
        "peak_at": pl.Datetime(time_unit="us", time_zone="UTC"),
        "peak_equity": pl.Float64(),
        "trough_at": pl.Datetime(time_unit="us", time_zone="UTC"),
        "trough_equity": pl.Float64(),
        "depth_pct": pl.Float64(),
        "duration_bars": pl.Int64(),
        "recovery_bars": pl.Int64(),
    }


def empty_drawdown_episodes_dataframe() -> pl.DataFrame:
    return pl.DataFrame(schema=drawdown_episodes_schema())


def compute_drawdown_episodes(*, run_id: str, equity: pl.DataFrame) -> pl.DataFrame:
    """Extract peak-to-recovery drawdown episodes from an equity curve.

    An episode runs from one running-maximum equity value to the next time
    equity reaches at least that same running maximum again (recovery).
    ``recovery_bars`` is ``null`` when the run ends before that recovery --
    an explicit "not yet recovered" episode, not a fabricated value. No
    minimum-depth threshold: every peak-to-recovery cycle counts, however
    shallow. A run whose equity never dips below its running peak produces
    zero rows, not an error.
    """
    if equity.height == 0:
        return empty_drawdown_episodes_dataframe()

    ordered = equity.sort("observed_at")
    observed_at = ordered.get_column("observed_at").to_list()
    values = ordered.get_column("equity").to_list()

    peak_idx = 0
    peak_value = values[0]
    trough_idx = 0
    trough_value = values[0]
    in_episode = False

    rows: list[dict[str, object]] = []

    for idx in range(1, len(values)):
        value = values[idx]
        if value >= peak_value:
            if in_episode:
                rows.append(
                    {
                        "schema_version": DRAWDOWN_EPISODES_SCHEMA_VERSION,
                        "run_id": run_id,
                        "episode_id": len(rows),
                        "peak_at": observed_at[peak_idx],
                        "peak_equity": peak_value,
                        "trough_at": observed_at[trough_idx],
                        "trough_equity": trough_value,
                        "depth_pct": trough_value / peak_value - 1.0,
                        "duration_bars": trough_idx - peak_idx,
                        "recovery_bars": idx - trough_idx,
                    }
                )
                in_episode = False
            peak_idx = idx
            peak_value = value
        else:
            if not in_episode or value < trough_value:
                trough_value = value
                trough_idx = idx
            in_episode = True

    if in_episode:
        rows.append(
            {
                "schema_version": DRAWDOWN_EPISODES_SCHEMA_VERSION,
                "run_id": run_id,
                "episode_id": len(rows),
                "peak_at": observed_at[peak_idx],
                "peak_equity": peak_value,
                "trough_at": observed_at[trough_idx],
                "trough_equity": trough_value,
                "depth_pct": trough_value / peak_value - 1.0,
                "duration_bars": trough_idx - peak_idx,
                "recovery_bars": None,
            }
        )

    if not rows:
        return empty_drawdown_episodes_dataframe()

    return pl.DataFrame(rows, schema=drawdown_episodes_schema())
