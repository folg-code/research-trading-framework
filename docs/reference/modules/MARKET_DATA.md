# Market Data — implementation map

This page records the existing packages and entry points for market data. Start with the [module map](../system/MODULE_MAP.md) for system-wide placement and follow the links below for contracts and workflows.

## Packages and entry points

### Responsibilities

| Responsibility | Package |
|---|---|
| Market-data domain types | `market/models/` |
| Instrument and dataset identity | `market/datasets/` |
| Dataset lifecycle | `market/datasets/` |
| Repository protocols | `market/repositories/` |
| Import and publication workflows | `application/market_data/` |
| Continuous trades materialize | `application/market_data/materialize_continuous_trades.py` (`session_workers`) |
| Provider adapters | `infrastructure/providers/` |
| Binance historical klines reader (paginated REST, rate-limit governor) | `infrastructure/providers/binance/futures_klines_history.py` |
| Binance historical OHLCV import workflow (validate, write, publish) | `application/market_data/import_binance_futures_ohlcv.py` |
| Binance historical OHLCV CLI (thin, ADR-0022) | `scripts/market_data/import_binance_ohlcv.py` |
| File and archive importers | `infrastructure/importers/` (Databento: NumPy `ContractChunkColumns`) |
| Normalization | `infrastructure/normalization/` |
| Validation | `infrastructure/validation/` |
| Dataset persistence | `infrastructure/storage/` |

### Public workflow surface

The Market Data application layer owns workflows for:

- importing external data,
- validating and normalizing records,
- publishing datasets,
- querying historical data,
- deriving new datasets,
- resolving stable dataset references.

### Dependency direction

```text
application/market_data
    → market
    → infrastructure adapters

infrastructure
    → market repository and domain contracts
```

### Tests

```text
tests/unit/market/
tests/unit/infrastructure/
tests/unit/application/market_data/
tests/integration/market_data/
```

### Deep references

- `SYSTEM_OVERVIEW.md`
- market-data module reference
- storage ADRs

---
