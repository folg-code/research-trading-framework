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

Building models and components (S006 tutorial):

```bash
# Recipe + run example models on fixture data
uv run python tests/spike/run_build_declarative_models_example.py

# List MVP components (outputs, parameters)
uv run python tests/spike/run_build_declarative_models_example.py --catalog

# Checklist for adding a new Market Analysis component
uv run python tests/spike/run_build_declarative_models_example.py --checklist

# Model-building recipe only
uv run python tests/spike/run_build_declarative_models_example.py --recipe
```

Reusable example code:

- ``tests/spike/run_dsl_models_example.py`` — target user-facing DSL API
- ``tests/spike/examples_model_building.py`` — low-level IR examples (legacy)
- ``src/trading_framework/model_authoring/`` — production DSL package
- ``src/trading_framework/application/model_evaluation/canonical_examples.py`` — production canonical set

Signal research spike (S008-T001):

```bash
uv run python tests/spike/run_signal_research_spike.py
uv run python tests/spike/run_signal_research_spike.py --json
```

Validates occurrence materialization, forward outcome semantics, run envelope write/read.

Signal research inspection (S008-T009):

```bash
uv pip install plotly
uv run python tests/spike/run_inspect_signal_research.py --generate --open
uv run python tests/spike/run_inspect_signal_research.py \\
  --storage-root user_data/storage --run-id <run_id> \\
  --occurrence-index 0 --horizon 5 --open
```

Overlays occurrence markers, reference price, horizon end, MFE/MAE and terminal outcome on OHLCV.
Inspection consumes persisted run facts only — no model evaluation or outcome recomputation.
