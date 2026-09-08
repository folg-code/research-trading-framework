# `trading-cli` example configs

One example per command group (S046-T011), following the locked YAML shape
in `docs/reference/modules/OPERATOR_CLI.md` (operator guide) / ADR-0026 §4 (design
record). Each file is a complete, schema-valid config you can point
`--config` at directly:

```powershell
uv run trading-cli data fetch --config apps/cli/examples/data_fetch_databento.yaml --dry-run
```

None of these commands wraps a capability that can run against a checked-in
fixture end to end without setup -- every one either fetches over a real
network, reads a real archive already on disk, or acts on a dataset/run that
was published by an earlier step. Each file says exactly what it needs
before it can run for real; every one of them **is** valid enough to pass
`--dry-run` (config validation + resolved-plan rendering) with no
side effect and no external dependency, which is the safe way to try any of
them first.

| File | Command | Runs as-is? |
|---|---|---|
| `data_fetch_binance.yaml` | `data fetch --config ...` (`data.provider: binance`) | No -- requires network; `TRADING_FRAMEWORK_BINANCE_API_KEY` optional (anonymous requests work) |
| `data_fetch_databento.yaml` | `data fetch --config ...` (`data.provider: databento`) | No -- requires a local `.dbn`/`.dbn.zst` archive already on disk |
| `research_run_predictive.yaml` | `research run --config ...` (`research.kind: predictive`) | No -- points at the real, committed Sprint 052 BTC study (regression pass, `predictive/btc_momentum_regime_study_regression.yaml` + `predictive/btc_momentum_regime_ridge.yaml`); requires BTCUSDT.P (2024-01-01 -> 2026-06-30, 1m) already published under `storage_root`, and the `ml` extra to fit |
| `research_promote.yaml` | `research promote --config ...` | No -- requires an existing Predictive Research `run_id` and the `ml` extra installed |
| `research_run_strategy.yaml` | `research run --config ...` (`research.kind: strategy`) | No -- requires a published `DatasetRef` (see the file's comment) |
| `research_run_strategy_candle_wick.yaml` | `research run --config ...` (`research.kind: strategy`, `strategy_file` set) | No -- requires a published `DatasetRef` **and** the gitignored `user_data/components/strategies/candle_wick_rejection.py` (recreate it from `docs/reference/modules/STRATEGY_AUTHORING.md`, Sprint 047 / ADR-0027) |
| `research_run_strategy_level_distance.yaml` | `research run --config ...` (`research.kind: strategy`, `strategy_file` set) | No -- requires a published `DatasetRef` **and** the gitignored `user_data/components/strategies/level_distance_pullback.py` (recreate it from `docs/reference/modules/STRATEGY_AUTHORING.md`, Sprint 047 / ADR-0027) |
| `dry_run_start.yaml` | `dry-run start --config ...` | No -- connects to the live Binance USD-M websocket feed |
| `report_render.yaml` | `report render --config ...` | No -- requires an existing `run_id` from a prior `research run predictive`/`strategy` |
| `predictive/signal_occurrences_sample_example.yaml` | `research run --config ...` (`research.kind: predictive`) | No -- parses and hashes cleanly (Sprint 056, ADR-0031) but has no `signal_model` supplied; fails fast with a named `PredictiveDatasetError` naming the missing input (TD-031: no `signal_model_file` loader exists yet) |
| `predictive/btc_momentum_regime_study_regression.yaml` | `research run --config ...` (`research.kind: predictive`, `definition`) | No -- Sprint 052 (Phase 15B) real-data BTC study, REGRESSION pass; parses and hashes cleanly (network-free, extra-free), requires BTCUSDT.P already published and the `ml` extra to fit (S052-T003, maintainer-executed) |
| `predictive/btc_momentum_regime_study_binary.yaml` | `research run --config ...` (`research.kind: predictive`, `definition`) | No -- Sprint 052 (Phase 15B) real-data BTC study, BINARY classification pass, same fold plan and features as the regression pass, different `label.kind`; same requirements as above |
| `predictive/btc_momentum_regime_ridge.yaml` | `research run --config ...` (`research.kind: predictive`, `estimator`) | No -- `sklearn.ridge` `EstimatorSpec` for the regression pass; parses cleanly, requires the `ml` extra to fit |
| `predictive/btc_momentum_regime_logistic.yaml` | `research run --config ...` (`research.kind: predictive`, `estimator`) | No -- `sklearn.logistic` `EstimatorSpec` for the binary pass; parses cleanly, requires the `ml` extra to fit |
