# Market Analysis technical spike scripts

Scripts in this directory are **not** production API and are **not** collected by pytest.

Run the Wave 0 backend benchmark:

```bash
uv run python tests/spike/run_market_analysis_backend_benchmark.py
uv run python tests/spike/run_market_analysis_backend_benchmark.py --json
```

Optional: install TA-Lib locally to include talib timings (skipped otherwise).
