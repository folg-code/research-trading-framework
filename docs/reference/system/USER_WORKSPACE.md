# User workspace — implementation map

This page records the existing packages and entry points for user workspace. Start with the [module map](MODULE_MAP.md) for system-wide placement and follow the links below for contracts and workflows.

## Packages and entry points

The framework core is reusable, while each user maintains an independent workspace.

Canonical layout (``--storage-root`` = workspace root, usually ``user_data/``):

```text
user_data/
├── market_data/
│   ├── raw/                 # immutable vendor archives
│   ├── metadata/            # dataset registry JSON
│   ├── normalized/          # published Parquet market facts
│   └── continuous/          # roll schedules
├── research/
│   ├── market_research/     # Signal Research runs + family experiments
│   ├── strategy_research/   # Strategy Research runs
│   ├── strategy_robustness/ # robustness experiments
│   └── predictive_research/ # Predictive Research datasets + runs (Phase 10)
├── runtime/                 # execution dry-run state
├── reports/                 # optional loose reports
├── config/
├── components/
└── models/
```

| User-owned area | Purpose |
|---|---|
| `market_data/raw/` | vendor archives (DBN, CSV, …); never overwritten |
| `market_data/metadata/` | dataset registry and lifecycle metadata |
| `market_data/normalized/` | published Parquet market facts |
| `market_data/continuous/` | roll schedules and related artifacts |
| `research/market_research/` | Signal Research runs and model-family experiments |
| `research/strategy_research/` | Strategy Research runs |
| `research/strategy_robustness/` | robustness experiments |
| `research/predictive_research/` | Predictive Research datasets (`datasets/{dataset_id}/`) and runs (`runs/{run_id}/`) |
| `components/` | custom analytical components |
| `models/` | Market Model and Signal Model definitions |
| `runtime/` | local execution state and operational data |

Path helpers: `src/trading_framework/infrastructure/storage/paths.py`.<br>
Migration: `scripts/ops/migrate_user_data_workspace.py`.

Users extend the system through:

- public component contracts,
- the model-authoring DSL,
- research definition contracts,
- strategy composition contracts,
- runtime configuration.

Users should not need to modify framework internals to:

- add components,
- compose models,
- define strategies,
- run research,
- inspect results.

---
