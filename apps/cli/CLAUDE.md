# apps/cli (`trading-cli`)

Responsibility: one operator-facing entry point (`trading-cli <group> <command> --config <path>`) over the existing application-layer research/data/execution workflows. See `docs/reference/MODULE_MAP.md` for the full component list.

## Conventions specific to this module

- **Import boundary differs from `apps/dashboard`** (ADR-0026 §2, D-S046-06). The dashboard may not import `trading_framework` at all; `apps/cli` MAY import `trading_framework.application.*` because its entire purpose is to invoke workflows, not just read persisted artifacts.
- **The boundary is an allow-list, enforced by `tests/unit/test_apps_boundaries.py::test_cli_only_imports_application_layer`, and it is wider than the application layer alone.** Wave 2 (S046-T005..T009) found that several application `Request` dataclasses take domain value objects and typed identifiers as constructor arguments (`EstimatorSpec`, `PredictiveDatasetRef`, `DatasetRef`, `TimeRange`, `Timeframe`, ...), and that two application workflows have a hardcoded default the CLI must supply itself (`SimulationAssumptions()`, `build_canonical_strategy_model()`, `CmeEsRthSessionResolver()` -- SPRINT_046.md §4 finding 2). The test's allow-list therefore lists a small, explicit set of non-`application.*` leaf modules, each with a one-line justification in the test file. **When adding a new command, check that list first** -- if you need a new import outside `trading_framework.application.*`, add it there deliberately (one leaf module, one reason), don't broaden a prefix, and don't route around the test.
- **Never**: reimplement research/simulation/execution logic in this package, or parse another command's stdout to compose commands. Composition (`research run predictive`) passes typed Python values between steps within one process (see `trading_cli/commands/research.py`).
- **Config schema is locked** (D-S046-07): `version` + `storage_root` are the only cross-group keys; per-group blocks are validated in `trading_cli/config.py`. Existing spec files (`PredictiveStudySpec`, `EstimatorSpec`) are referenced by path and parsed by their own loaders -- never re-encoded here.

## Gotchas

- `research run strategy` inherits a real limitation: the canonical strategy model, simulation assumptions and session resolver are hardcoded the same way `scripts/strategy_research/run_strategy_research.py` hardcodes them. There is no YAML key for this in v1 -- it's stated in `--help`, not silently implied.
- `data fetch databento` is a local archive **import**, not a network fetch (unlike `data fetch binance`). The config schema only carries `archive` + `instrument_id`; `source_id`/`provider_symbol` default to `instrument_id` rather than reopening the locked schema.
- `dry-run start` calls `asyncio.run()` inside a synchronous `run()`. `trading_cli.cli.main` is itself synchronous top-level code, so this is always safe -- don't call any dry-run command body from inside an already-running event loop.

## Tests

- `apps/cli/tests/` is this package's own suite (own CI job, `apps/dashboard` pattern). Tier 1, network-free, no ML extra (`ml`/`dl`) installed or required -- workflow bodies that need one (e.g. `research run predictive`'s estimator fit) are faked at the module boundary; the CLI's own coverage is the seam (config -> typed request -> typed result), not the wrapped workflow's internals, which already has its own test suite.
