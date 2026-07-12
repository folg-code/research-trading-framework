# Market Analysis technical spike scripts

Scripts in this directory are **not** production API and are **not** collected by pytest.

Run the Wave 0 backend benchmark:

```bash
uv run python tests/spike/run_market_analysis_backend_benchmark.py
uv run python tests/spike/run_market_analysis_backend_benchmark.py --json
```

Optional: install TA-Lib locally to include talib timings (skipped otherwise).

Interactive MTF swing inspection (S005-T014):

```bash
uv pip install plotly
uv run python tests/spike/run_inspect_mtf_swing.py --open
uv run python tests/spike/run_inspect_mtf_swing.py --output swing_inspection.html --pivot-range 2 --open
```

Writes zoomable HTML (not PNG) with OHLCV, all swing frame columns in hover, state
levels, event panel and RTH shading.

Model expression spike (S006-T001):

```bash
uv run python tests/spike/run_model_expression_spike.py
uv run python tests/spike/run_model_expression_spike.py --json
```

Validates AnalysisFrame → Polars adapter, three-valued logic and firing policies.

Declarative model inspection (S006-T020):

```bash
uv pip install plotly
uv run python tests/spike/run_inspect_declarative_models.py --open
uv run python tests/spike/run_inspect_declarative_models.py \\
  --market-models high_volatility \\
  --signal-models higher_low_long,high_vol_and_higher_low \\
  --output model_inspection.html --open
```

Overlays pre-computed Market Model state, Signal Model conditions and emission markers.
Chart helpers do not evaluate models or run Market Analysis.
