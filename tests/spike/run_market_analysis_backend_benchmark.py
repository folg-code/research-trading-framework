"""Technical spike: Market Analysis backend and workspace representation benchmark.

Not part of the production API. Run manually:

    uv run python tests/spike/run_market_analysis_backend_benchmark.py

Optional backends are skipped when not installed (pandas, TA-Lib).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import tracemalloc
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

# Default: ~252 US equity sessions x 390 one-minute bars (synthetic NQ 1m scale).
DEFAULT_BAR_COUNT = 98_280
WARMUP_PERIOD = 14


@dataclass(frozen=True)
class TimingResult:
    name: str
    wall_seconds: float
    peak_bytes: int


@dataclass(frozen=True)
class BenchmarkReport:
    bar_count: int
    timings: list[TimingResult]
    notes: list[str]


def _peak_memory_bytes(fn: Any, *args: Any, **kwargs: Any) -> tuple[Any, int]:
    tracemalloc.start()
    try:
        result = fn(*args, **kwargs)
    finally:
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    return result, peak


def _time_named(name: str, fn: Any, *args: Any, **kwargs: Any) -> TimingResult:
    _, peak = _peak_memory_bytes(fn, *args, **kwargs)
    start = time.perf_counter()
    fn(*args, **kwargs)
    elapsed = time.perf_counter() - start
    return TimingResult(name=name, wall_seconds=elapsed, peak_bytes=peak)


def generate_synthetic_ohlcv(n_bars: int, seed: int = 42) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    close = 20_000.0 + np.cumsum(rng.normal(0.0, 2.0, n_bars))
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    spread = rng.uniform(0.5, 3.0, n_bars)
    high = np.maximum(open_, close) + spread
    low = np.minimum(open_, close) - spread
    volume = rng.integers(100, 5_000, n_bars, dtype=np.int64)
    return {
        "open": open_.astype(np.float64),
        "high": high.astype(np.float64),
        "low": low.astype(np.float64),
        "close": close.astype(np.float64),
        "volume": volume.astype(np.float64),
    }


def true_range_numpy(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]
    tr1 = high - low
    tr2 = np.abs(high - prev_close)
    tr3 = np.abs(low - prev_close)
    return np.maximum(tr1, np.maximum(tr2, tr3))


def atr_numpy(true_range: np.ndarray, period: int) -> np.ndarray:
    out = np.full(true_range.shape, np.nan, dtype=np.float64)
    if true_range.size < period:
        return out
    kernel = np.ones(period, dtype=np.float64) / period
    valid = np.convolve(true_range, kernel, mode="valid")
    out[period - 1 :] = valid
    return out


def ema_numpy(close: np.ndarray, period: int) -> np.ndarray:
    out = np.full(close.shape, np.nan, dtype=np.float64)
    if close.size < period:
        return out
    alpha = 2.0 / (period + 1.0)
    out[period - 1] = np.mean(close[:period])
    for i in range(period, close.size):
        out[i] = alpha * close[i] + (1.0 - alpha) * out[i - 1]
    return out


def rolling_max_numpy(values: np.ndarray, period: int) -> np.ndarray:
    out = np.full(values.shape, np.nan, dtype=np.float64)
    for i in range(period - 1, values.size):
        out[i] = np.max(values[i - period + 1 : i + 1])
    return out


def numpy_pipeline(ohlcv: dict[str, np.ndarray], period: int) -> dict[str, np.ndarray]:
    tr = true_range_numpy(ohlcv["high"], ohlcv["low"], ohlcv["close"])
    atr = atr_numpy(tr, period)
    ema = ema_numpy(ohlcv["close"], period)
    roll = rolling_max_numpy(ohlcv["close"], period)
    return {"true_range": tr, "atr": atr, "ema": ema, "rolling_max": roll}


def map_of_arrays_storage(outputs: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {name: arr.copy() for name, arr in outputs.items()}


def wide_dataframe_concat(outputs: dict[str, np.ndarray]) -> Any:
    import pandas as pd

    frame = pd.DataFrame(outputs)
    for name, arr in outputs.items():
        frame[name] = arr
    return frame


def incremental_concat(outputs: dict[str, np.ndarray]) -> Any:
    import pandas as pd

    frame = pd.DataFrame()
    for name, arr in outputs.items():
        frame = pd.concat([frame, pd.DataFrame({name: arr})], axis=1)
    return frame


def deferred_assembly(ohlcv: dict[str, np.ndarray], outputs: dict[str, np.ndarray]) -> Any:
    import pandas as pd

    combined = {**ohlcv, **outputs}
    return pd.DataFrame(combined)


def pandas_pipeline(ohlcv: dict[str, np.ndarray], period: int) -> dict[str, np.ndarray]:
    import pandas as pd

    frame = pd.DataFrame(ohlcv)
    prev_close = frame["close"].shift(1)
    tr = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - prev_close).abs(),
            (frame["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr = tr.rolling(period).mean()
    ema = frame["close"].ewm(span=period, adjust=False).mean()
    roll = frame["close"].rolling(period).max()
    return {
        "true_range": tr.to_numpy(dtype=np.float64),
        "atr": atr.to_numpy(dtype=np.float64),
        "ema": ema.to_numpy(dtype=np.float64),
        "rolling_max": roll.to_numpy(dtype=np.float64),
    }


def talib_pipeline(ohlcv: dict[str, np.ndarray], period: int) -> dict[str, np.ndarray]:
    import talib

    high = ohlcv["high"]
    low = ohlcv["low"]
    close = ohlcv["close"]
    tr = talib.TRANGE(high, low, close)
    atr = talib.ATR(high, low, close, timeperiod=period)
    ema = talib.EMA(close, timeperiod=period)
    roll = talib.MAX(close, timeperiod=period)
    return {
        "true_range": np.asarray(tr, dtype=np.float64),
        "atr": np.asarray(atr, dtype=np.float64),
        "ema": np.asarray(ema, dtype=np.float64),
        "rolling_max": np.asarray(roll, dtype=np.float64),
    }


def shared_dependency_reuse_numpy(
    ohlcv: dict[str, np.ndarray], period: int
) -> dict[str, np.ndarray]:
    tr = true_range_numpy(ohlcv["high"], ohlcv["low"], ohlcv["close"])
    atr_from_tr = atr_numpy(tr, period)
    atr_recompute = atr_numpy(
        true_range_numpy(ohlcv["high"], ohlcv["low"], ohlcv["close"]),
        period,
    )
    if not np.allclose(atr_from_tr, atr_recompute, equal_nan=True):
        msg = "shared dependency reuse must match recomputed ATR"
        raise AssertionError(msg)
    return {"true_range": tr, "atr": atr_from_tr}


def run_benchmark(bar_count: int) -> BenchmarkReport:
    ohlcv = generate_synthetic_ohlcv(bar_count)
    timings: list[TimingResult] = []
    notes: list[str] = []

    numpy_outputs = numpy_pipeline(ohlcv, WARMUP_PERIOD)
    timings.append(_time_named("numpy_pipeline", numpy_pipeline, ohlcv, WARMUP_PERIOD))
    timings.append(_time_named("numpy_map_of_arrays", map_of_arrays_storage, numpy_outputs))
    timings.append(
        _time_named("numpy_shared_dependency", shared_dependency_reuse_numpy, ohlcv, WARMUP_PERIOD)
    )

    try:
        import pandas  # noqa: F401

        pandas_outputs = pandas_pipeline(ohlcv, WARMUP_PERIOD)
        timings.append(_time_named("pandas_pipeline", pandas_pipeline, ohlcv, WARMUP_PERIOD))
        timings.append(
            _time_named("pandas_deferred_frame", deferred_assembly, ohlcv, pandas_outputs)
        )
        timings.append(_time_named("pandas_incremental_concat", incremental_concat, pandas_outputs))
        timings.append(_time_named("pandas_wide_concat", wide_dataframe_concat, pandas_outputs))
    except ImportError:
        notes.append("pandas not installed — pandas benchmarks skipped")

    try:
        import talib  # noqa: F401

        timings.append(_time_named("talib_pipeline", talib_pipeline, ohlcv, WARMUP_PERIOD))
    except ImportError:
        notes.append("TA-Lib not installed — talib benchmarks skipped")

    return BenchmarkReport(bar_count=bar_count, timings=timings, notes=notes)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bars", type=int, default=DEFAULT_BAR_COUNT)
    parser.add_argument("--json", action="store_true", help="Print JSON report to stdout")
    args = parser.parse_args()

    report = run_benchmark(args.bars)
    if args.json:
        print(json.dumps(asdict(report), indent=2))
        return 0

    print(f"Bars: {report.bar_count:,}")
    for item in report.timings:
        print(
            f"  {item.name}: {item.wall_seconds:.4f}s, peak {item.peak_bytes / 1024 / 1024:.2f} MiB"
        )
    for note in report.notes:
        print(f"Note: {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
