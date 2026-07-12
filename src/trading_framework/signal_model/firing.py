"""Signal firing policies for sparse emission materialization."""

from typing import assert_never

import polars as pl

from trading_framework.signal_model.definitions import SignalFiringPolicy


def apply_firing_policy(
    condition_met: pl.Series,
    *,
    policy: SignalFiringPolicy | str,
) -> pl.Series:
    """Return a boolean mask selecting rows that emit under the given policy."""
    resolved = SignalFiringPolicy(policy)
    if resolved is SignalFiringPolicy.ON_TRUE_EDGE:
        return _on_true_edge(condition_met)
    if resolved is SignalFiringPolicy.ON_EVENT:
        return _on_event(condition_met)
    assert_never(resolved)


def _on_true_edge(condition_met: pl.Series) -> pl.Series:
    frame = pl.DataFrame({"condition_met": condition_met})
    return frame.select(
        pl.when(pl.col("condition_met").is_null())
        .then(False)
        .when(pl.col("condition_met").shift(1).is_null() & pl.col("condition_met").eq(True))
        .then(True)
        .when(pl.col("condition_met").shift(1).eq(False) & pl.col("condition_met").eq(True))
        .then(True)
        .otherwise(False)
        .alias("result")
    )["result"]


def _on_event(condition_met: pl.Series) -> pl.Series:
    frame = pl.DataFrame({"condition_met": condition_met})
    return frame.select(
        (pl.col("condition_met").fill_null(False) & pl.col("condition_met").eq(True)).alias(
            "result"
        )
    )["result"]
