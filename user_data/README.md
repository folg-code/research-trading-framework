# User Data

This directory is **user-owned** and excluded from version control except this README.

## Purpose

`user_data/` stores proprietary configuration, components, models, datasets and research outputs.
Framework code in `src/` must not import concrete modules from `user_data/`.

## Canonical Workspace Layout

`--storage-root` points at the **workspace root** (this directory), not at an ad-hoc `storage_*` folder.

```text
user_data/
├── market_data/
│   ├── raw/                 # immutable vendor archives (DBN, CSV, …)
│   ├── metadata/            # dataset registry JSON
│   ├── normalized/          # published Parquet market facts
│   └── continuous/          # roll schedules and related artifacts
├── research/
│   ├── market_research/     # Signal Research (market/signal model evaluation)
│   │   ├── runs/{run_id}/
│   │   └── experiments/{experiment_id}/
│   ├── strategy_research/
│   │   └── runs/{run_id}/
│   └── strategy_robustness/
│       └── experiments/{experiment_id}/
├── runtime/                 # execution dry-run state (operator-managed)
├── reports/                 # optional loose reports (prefer run-local report/)
├── config/
├── components/
└── models/
```

### Rules

- Keep **raw** archives immutable; rebuild normalized datasets from raw when needed.
- Do **not** create new top-level `storage_*` directories.
- Research outputs belong under `research/<track>/runs` or `.../experiments`.
- Prefer report HTML next to the run (`.../report/`) over loose files in `reports/`.

### Migration

Existing flat trees (for example `storage_nq_half_year/`) can be moved with:

```powershell
uv run python scripts/ops/migrate_user_data_workspace.py `
  --workspace user_data `
  --from-storage user_data/storage_nq_half_year `
  --relocate-raw-market-data `
  --dry-run
```

Remove `--dry-run` to apply. Then delete or archive empty legacy `storage_*` directories.

## Rules

- do not commit credentials, API keys or proprietary strategies,
- do not place secrets in tracked files,
- use published framework contracts for discovery and loading,
- keep proprietary logic out of `src/trading_framework/`.

## Related Documents

- `docs/adr/ADR-0002-separate-src-and-user-data.md`
- `src/trading_framework/infrastructure/storage/paths.py`
- `scripts/ops/migrate_user_data_workspace.py`
- `AGENTS.md`
