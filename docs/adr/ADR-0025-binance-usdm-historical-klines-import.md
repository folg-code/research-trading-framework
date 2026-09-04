# ADR-0025 — Binance USD-M Historical Klines Import

## Status

ACCEPTED (Sprint 045)

Approved-by: Filip Folga (project maintainer), given directly in conversation
with the orchestrating Claude Code session on 2026-08-28, in response to a
summary of this ADR's key decisions (provider="binance" reusing the existing
DatasetId contract, no `fetch_closed_klines` modification, env-var-only
credential with no signing code as the leakage guard). Answer: "Tak,
zatwierdzam wszystko" (approving this ADR, ADR-0026, the roadmap increment,
and opening both sprints together, in one confirmation) — recorded here
rather than left to point at an external artifact, per the precedent set on
ADR-0024/PR #345 in Sprint 044.

## Context

`docs/product/PRD.md` records a confirmed gap: the framework can only obtain
historical bars from a **local Databento DBN archive**
(`import_databento_trades_archive` → `derive_ohlcv_from_trades`, ADR-0014 /
ADR-0015) or from a CSV file (`import_external_dataset`, ADR-0007 / ADR-0008).

The existing Binance surface is **live-only**:

```text
futures_websocket.py   streaming klines / book ticker      (Sprint 019)
futures_rest.py        fetch_closed_klines(symbol, limit)  reconnect gap-fill
futures_mapper.py      map_kline_payload → MarketBar
futures_streams.py     normalize_stream_symbol
futures_reconnect.py   reconnect / gap policy
```

`fetch_closed_klines` requests the **latest N** closed candles
(`limit ≤ 1500`, no `startTime` / `endTime`) and drops the newest row because
it may still be open. It is a runtime gap-fill helper, not an archive importer:
it cannot address a date range, has no pagination cursor, no rate-limit
backoff, and no dataset-registry integration.

Consequence: Binance data cannot become a queryable, published `DatasetRef`,
so Predictive Research (Phase 10) and Strategy Research (Phase 6A) cannot run
on crypto data at all — even though every downstream layer is already
provider-agnostic.

This ADR mirrors the shape of ADR-0014 (a new provider becomes a published
dataset) for a **REST/network** source instead of a file archive.

## Decision

### 1. A new provider, not a new dataset contract

`DatasetId.provider` is a free-form validated string (`market/datasets/identity.py`);
no enum change is needed. Binance OHLCV datasets are ordinary bar datasets:

```text
instrument_id  operator-supplied Identifier (e.g. BTCUSDT.P)
data_type      ohlcv
timeframe      1m | 5m | 15m | 1h | 4h | 1d   (Binance interval, 1:1)
provider       binance
source_id      binance-usdm-klines-v1
```

ADR-0007 (lifecycle) and ADR-0008 (single-file `bars.parquet`) apply
**unchanged**. Reuse `FileDatasetRegistry`, `ParquetDatasetRepository.write_bars`,
`OhlcvBarValidator`, `finalize_dataset`, `publish_dataset`, `query_historical`.

Downstream research must not be able to tell which provider produced the bars.
No branch on `provider == "binance"` outside the importer and its manifest.

### 2. Layer placement

```text
infrastructure/providers/binance/futures_klines_history.py
    paginated REST reader: date range → tuple[MarketBar, ...] + fetch stats
    reuses map_kline_payload + normalize_stream_symbol (no duplicate mapping)

application/market_data/import_binance_futures_ohlcv.py
    workflow: read → validate → write bars → register WORKING metadata
              + import_manifest.json

scripts/market_data/import_binance_ohlcv.py
    thin CLI (ADR-0022 rule 3)
```

Network adapters stay under `providers/` (file archive adapters stay under
`importers/`, per ADR-0014). Domain and application layers never see
`urllib`, HTTP status codes, or Binance JSON.

`fetch_closed_klines` is **not** modified. Both functions may share private
row-mapping helpers inside the provider module; the live reconnect path
(Sprint 019/024) must remain behaviour-identical.

### 3. Pagination and closed-bar rule

```text
cursor = start_ms
loop:
  GET /fapi/v1/klines?symbol&interval&startTime=cursor&endTime=end_ms&limit=1500
  drop rows whose close_time_ms >= now_ms          (never import an open bar)
  if no rows → stop
  cursor = last_row.close_time_ms + 1
  stop when cursor > end_ms or the page was short
```

Rules:

- the requested range is **half-open** `[start, end)` in UTC (ADR-0003);
- a page that returns zero rows inside the range is a **gap**, recorded in the
  manifest — never silently filled and never fabricated;
- imports are **idempotent**: the same range produces the same bars, so
  `finalize_dataset` computes the same checksum.

### 4. Rate limiting and backoff

Binance USD-M enforces a **weight** budget per IP per minute and answers
`429` (rate limited) / `418` (IP ban) when exceeded.

```text
read X-MBX-USED-WEIGHT-1M from every response; throttle before the limit
429 / 418 / 5xx  →  bounded exponential backoff with jitter, honouring
                    Retry-After when present
retries          →  finite cap; then fail the import with a typed error
```

No busy-loop retry. Backoff timing is injectable (`sleep` callable) so tests
never sleep. A partially fetched range never produces a `PUBLISHED` version —
same failure policy as ADR-0014.

### 5. Optional API key — market data only

An API key raises the weight limit on public market-data endpoints. It is
optional and **never required**.

```text
transport      header X-MBX-APIKEY on public market-data GETs only
endpoints      /fapi/v1/klines (and future public market-data reads) only
never          signed endpoints, no HMAC signing code, no secret key,
               no account / order / position / balance surface
storage        environment variable TRADING_FRAMEWORK_BINANCE_API_KEY
logging        never logged, never echoed, never written to a manifest
```

Environment variables are the single credential convention, matching the
existing `TRADING_FRAMEWORK_*` pattern
(`application/execution/aws_btc_futures_runtime.py`,
`TRADING_FRAMEWORK_STATUS_URL`). Credential files under `user_data/config/`
are **rejected** for this scope (see Alternatives).

Because no signing code exists, the key cannot be used to place an order even
by mistake. This is enforced by an architecture boundary test asserting the
Binance provider package contains no `hmac` / `signature` usage and no
authenticated endpoint path.

### 6. Mode selector — `ohlcv` only in v1

The import request carries `mode`, and v1 accepts exactly `ohlcv` (direct
klines). Any other value — including `trades` — is rejected with an explicit
"not supported in v1" error, not a silent fallback.

`trades` mode (fetch aggregate trades, then `derive_ohlcv_from_trades`, the
symmetric Databento path) stays reserved so it is an additive change.

### 7. Import manifest

Every import writes `import_manifest.json` beside the dataset, mirroring
ADR-0014:

```text
provider, mode, symbol, interval, requested range (UTC)
page count, request count, rows decoded / rejected
observed gaps (start, end) with no bars
normalization_version, framework version
api_key_used: true | false        (boolean only — never the key)
```

### 8. Test tiers

```text
Tier 1 (CI)     fake urlopen returning recorded kline pages; no network
Tier 2 (opt-in) @pytest.mark.binance_network, gated by
                TRADING_FRAMEWORK_RUN_BINANCE_NETWORK_SMOKE=1 (existing marker)
```

Standard CI stays network-free (Sprint 019 rule).

## Consequences

### Positive

- Binance USD-M history becomes a published `DatasetRef` usable by every
  existing research workflow without touching Databento code.
- Rate-limit behaviour is explicit and testable rather than incidental.
- The credential surface is one environment variable with no signing code, so
  "no account endpoint" is a structural property, not a promise.
- Reuses the mapper already validated by the live dry-run path, so live and
  historical bars share one normalization.

### Negative

- A second, network-shaped import path exists next to the file-archive path;
  operators must know which one applies.
- Long ranges take real wall-clock time under weight limits (a year of 1m bars
  is hundreds of pages); no resume-after-failure in v1.
- Binance history is vendor-revisable; re-importing a range may produce a new
  dataset version. Reproducibility rests on the published version, not on the
  vendor.
- Gaps are recorded, not repaired — downstream consumers must tolerate them.

### Neutral

- `provider` stays a free-form string; no registry of provider names.
- Interval → `Timeframe` is 1:1 for v1 intervals; exotic Binance intervals
  (`3d`, `1w`, `1M`) are simply not offered.

## Alternatives Considered

1. **Extend `fetch_closed_klines` with `startTime`/`endTime`.** Rejected: it
   is on the live reconnect hot path (Sprint 019/024); widening it couples
   runtime gap-fill to archive import and risks a regression in a path that
   already runs in AWS.
2. **Fetch aggregate trades and reuse `derive_ohlcv_from_trades`.** Rejected
   for v1: orders of magnitude more requests and storage for an identical
   result, since Binance publishes klines directly. Kept as the reserved
   `trades` mode.
3. **Credentials in `user_data/config/binance.yaml`.** Rejected: two
   conventions invite drift, a file can be committed by accident, and the
   project already standardises on `TRADING_FRAMEWORK_*` environment variables.
   A file convention may be revisited if multi-account support ever arrives —
   that would need a new ADR.
4. **A new `python-binance` / `ccxt` dependency.** Rejected: the endpoint is
   one public GET; the existing `urllib` provider style already covers it, and
   both libraries carry an authenticated-trading surface this scope explicitly
   excludes.
5. **A separate "crypto" dataset contract.** Rejected: it would leak provider
   identity into research and break ADR-0007's provider-agnostic promise.

## Follow-up

- Sprint 045 Wave 0 (`S045_WAVE0_DECISIONS.md`) binds symbol/instrument
  mapping, validator behaviour on gaps, and the exact manifest fields.
- `trades` mode, Binance spot, and resume-after-failure are deliberately
  deferred; each needs its own increment.
- `docs/reference/workflows/MARKET_DATA.md` and `docs/reference/system/MODULE_MAP.md` gain the new path
  during Sprint 045.

## Related

- `docs/adr/ADR-0007-dataset-lifecycle-and-publication.md`
- `docs/adr/ADR-0008-parquet-historical-storage.md`
- `docs/adr/ADR-0014-historical-archive-import-and-market-trade-storage.md`
- `docs/adr/ADR-0015-derived-ohlcv-from-trades.md`
- `docs/adr/ADR-0021-live-dry-run-execution-demo.md`
- `docs/adr/ADR-0022-repository-top-level-layout.md`
- `docs/product/PRD.md`
- `docs/planning/sprints/SPRINT_045.md`
