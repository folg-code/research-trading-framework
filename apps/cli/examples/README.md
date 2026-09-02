# `trading-cli` example configs

One example per command group (S046-T011), following the locked YAML shape
in `docs/reference/OPERATOR_CLI.md` (operator guide) / ADR-0026 §4 (design
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
| `research_run_predictive.yaml` | `research run --config ...` (`research.kind: predictive`) | No -- requires an existing `PredictiveStudySpec` / `EstimatorSpec` pair and published market data for the study's target dataset |
| `research_promote.yaml` | `research promote --config ...` | No -- requires an existing Predictive Research `run_id` and the `ml` extra installed |
| `research_run_strategy.yaml` | `research run --config ...` (`research.kind: strategy`) | No -- requires a published `DatasetRef` (see the file's comment) |
| `research_run_strategy_candle_wick.yaml` | `research run --config ...` (`research.kind: strategy`, `strategy_file` set) | No -- requires a published `DatasetRef` **and** the gitignored `user_data/components/strategies/candle_wick_rejection.py` (recreate it from `docs/reference/STRATEGY_AUTHORING.md`, Sprint 047 / ADR-0027) |
| `research_run_strategy_level_distance.yaml` | `research run --config ...` (`research.kind: strategy`, `strategy_file` set) | No -- requires a published `DatasetRef` **and** the gitignored `user_data/components/strategies/level_distance_pullback.py` (recreate it from `docs/reference/STRATEGY_AUTHORING.md`, Sprint 047 / ADR-0027) |
| `dry_run_start.yaml` | `dry-run start --config ...` | No -- connects to the live Binance USD-M websocket feed |
| `report_render.yaml` | `report render --config ...` | No -- requires an existing `run_id` from a prior `research run predictive`/`strategy` |
