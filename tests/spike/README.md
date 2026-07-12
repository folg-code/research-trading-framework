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
