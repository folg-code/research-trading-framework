# Market data integration tests

## Tier 1 (CI)

Default integration tests run in CI without local Databento archives.

- `test_csv_import_flow.py` — OHLCV CSV vertical slice
- `test_databento_trades_import_flow.py` — trades import with injected fake reader
- `test_databento_trades_import_mocked.py` — full import → finalize → publish → query with mocked `DBNStore`

Run locally:

```bash
uv run pytest tests/integration/market_data -q
```

## Tier 2 (opt-in, local DBN required)

Tests marked with `@pytest.mark.tier2_databento` require a local trades DBN file under `user_data/`.
They are skipped automatically when the default archive path is absent.

Default path checked by `test_databento_adapter_tier2.py`:

```text
user_data/market_data/NQ/databento/GLBX-20260712-DU3ML8YKBH/glbx-mdp3-20250713.trades.dbn.zst
```

Run Tier 2 locally:

```bash
uv run pytest tests/integration/market_data/test_databento_adapter_tier2.py -m tier2_databento -q
```

CI excludes Tier 2 via `-m "not tier2_databento"` on the integration job.

Spike script (Wave 0 validation):

```bash
uv run python tests/spike/run_databento_dbn_trades_spike.py --path user_data/samples/nq_trades.dbn.zst
```

See also `tests/spike/README.md`.
