# Infrastructure — module guide

`src/trading_framework/infrastructure/` implements external-system boundaries defined by domain and application contracts. Provider SDKs, storage formats, network delivery and ML libraries terminate here; domain logic remains independent of those implementations.

## Adapter families

| Package | Responsibility | Consumer path |
|---|---|---|
| `providers/` | Historical and live market-data sources, including Binance adapters | Market Data application use cases |
| `normalization/`, `validation/` | Turn external records into checked canonical facts | Import and publication workflows |
| `storage/` | Parquet datasets, manifests, registries, execution state and read models | Market Data, Research and Execution via contracts |
| `ml/` | Versioned sklearn, tree and neural model adapters and promotion guards | Predictive Research application |
| `observability/` | Operational profiling and diagnostics | Application/infrastructure paths |

An adapter may depend inward on a domain or application port to implement it. The reverse dependency to a concrete adapter is prohibited; see [Dependency Rules](../system/DEPENDENCY_RULES.md) for what tests currently enforce and the documented exception.

## Read next

- [Market Data module](MARKET_DATA.md) and [Market Data workflow](../workflows/MARKET_DATA.md): importer, registry and storage paths.
- [Execution module](EXECUTION.md) and [Strategy Execution workflow](../workflows/STRATEGY_EXECUTION.md): runtime state and delivery.
- [Predictive promotion](PREDICTIVE_PROMOTION.md): artifact storage and load-time guards.
- [User Workspace](../system/USER_WORKSPACE.md): where user-owned data and generated artifacts reside.
