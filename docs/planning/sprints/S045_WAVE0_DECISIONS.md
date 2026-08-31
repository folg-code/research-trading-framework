# Sprint 045 — Wave 0 Decisions

Binding decisions for Binance USD-M historical OHLCV ingestion (Phase 2F,
opening increment). Date: 2026-08-31.

```text
Status: Proposed — requires maintainer approval (Wave 0 Checklist, §14)
Basis:  docs/product/PRD.md (confirmed)
        docs/adr/ADR-0025 (PROPOSED)
        docs/planning/sprints/SPRINT_045.md
        ADR-0007 / ADR-0008 / ADR-0014 / ADR-0015 / ADR-0022
        src/trading_framework/infrastructure/providers/binance/ as on main
```

Sprint 046 (operator CLI) is a **separate** sprint with its own Wave 0 and its
own ADR. Nothing here depends on it, and no decision below may be reopened to
accommodate CLI ergonomics.

---

## Inherited locks (do not reopen)

```text
ADR-0003: all internal timestamps are timezone-aware UTC
ADR-0007: WORKING → FINALIZED → PUBLISHED; published versions are immutable
ADR-0008: OHLCV bars live in a single bars.parquet per dataset version
ADR-0022: scripts/ stay thin — parse args, call an application API, write output
Sprint 019: standard CI is network-free; Binance network tests are opt-in
Research code never branches on the provider
```

---

## D-S045-01 — Problem statement

Historical bars can only enter the framework from a local Databento DBN archive
or a CSV file. Binance exists solely as a live adapter: `fetch_closed_klines`
returns the latest N closed candles (`limit ≤ 1500`, no `startTime`/`endTime`)
for Sprint 019 reconnect gap-fill.

Result: no Binance data can become a published `DatasetRef`, so no research
methodology in the framework can run on crypto — despite every layer above the
importer already being provider-agnostic.

**This sprint ships exactly:** a paginated, rate-limit-aware historical klines
import that publishes an ordinary OHLCV `DatasetRef` with `provider="binance"`,
plus a thin CLI.

**Not this sprint:** the operator CLI; spot; any authenticated endpoint;
`trades` mode; resume; a multi-exchange abstraction; any change to the live path.

---

## D-S045-02 — Sprint branch and PR base

```text
Integration branch: sprint/binance-historical-ohlcv   (cut from main)
Working branches:   feat/ | fix/ | docs/ | test/ + descriptive slug
PR base:            sprint/binance-historical-ohlcv   (never main until integration)
```

Working-branch PRs squash-merge into the sprint branch. When the sprint is
complete, one integration PR goes `sprint/binance-historical-ohlcv` → `main`.

---

## D-S045-03 — Sprint slice order

| Order | Slice | Why |
|-------|-------|-----|
| 0 | Wave 0 | Locks before any transport code |
| 1 | Fetch | Reader + backoff + optional key — the only genuinely new mechanics |
| 2 | Workflow | Lifecycle integration; reuses existing contracts wholesale |
| 3 | CLI + tests | Operator surface and the network-free round trip |
| 4 | Docs | Workflow docs, credential convention, roadmap/status |

Each slice is a shippable vertical piece: slice 1 can fetch bars, slice 2 can
publish them, slice 3 makes it usable, slice 4 makes it findable.

---

## D-S045-04 — Module placement

```text
NEW  src/trading_framework/infrastructure/providers/binance/futures_klines_history.py
NEW  src/trading_framework/application/market_data/import_binance_futures_ohlcv.py
NEW  scripts/market_data/import_binance_ohlcv.py
UNCHANGED  futures_rest.py, futures_websocket.py, futures_mapper.py,
           futures_streams.py, futures_reconnect.py
```

Network adapters belong under `providers/` (file-archive adapters stay under
`importers/`, per ADR-0014). The reader **reuses** `map_kline_payload` and
`normalize_stream_symbol`; it does not re-implement mapping.

**Locked:** `fetch_closed_klines` is not modified, not wrapped, and not
refactored. If sharing a private helper would alter its behaviour in any way,
duplicate the helper instead.

---

## D-S045-05 — Dataset identity

```text
instrument_id  operator-supplied, required, no auto-derivation   e.g. BTCUSDT.P
data_type      ohlcv
timeframe      Timeframe(interval), 1:1 with the Binance interval
provider       binance
source_id      binance-usdm-klines-v1
```

`DatasetId.provider` is already a free-form validated string — **no enum, no
schema and no migration is required**.

Rules:

- `instrument_id` is explicit in the CLI/request. It must not collide with the
  continuous (`.c.`) or contract identity patterns used for futures.
- v1 intervals: `1m`, `5m`, `15m`, `1h`, `4h`, `1d`. Exotic Binance intervals
  (`3d`, `1w`, `1M`) are simply not offered.
- `source_id` carries the `-v1` suffix so a future normalization change can
  allocate a new logical dataset rather than mutate an existing one.

---

## D-S045-06 — Pagination and the closed-bar rule

```text
range        half-open [start, end) in UTC
page size    limit = 1500
cursor       next start = last row close_time_ms + 1
open bar     drop every row with close_time_ms >= now_ms
termination  cursor > end_ms, or a page returns zero rows
ordering     ascending open_time; duplicates across page boundaries are dropped
```

**Locked:** a page returning zero rows inside the requested range is a **gap**.
It is recorded in the manifest and the cursor advances by one page window. It is
never an error, never retried indefinitely, and never filled with synthetic bars.

Idempotency is a hard requirement: the same `[start, end)` must produce an
identical bar set, so `finalize_dataset` computes an identical checksum.

---

## D-S045-07 — Rate limiting and backoff

```text
throttle     read X-MBX-USED-WEIGHT-1M; pause before the documented budget
429 / 418    backoff, honouring Retry-After when present
5xx          backoff
backoff      exponential with jitter, capped delay, finite retry cap
exhaustion   typed BinanceFuturesRestError-family error; import fails
sleep        injected callable — tests never sleep for real
jitter       seeded/injectable so tests are deterministic
```

**Locked:** no unbounded retry, no busy loop, no "retry forever until it
works". A failed import leaves no `PUBLISHED` version (ADR-0014 failure policy).

---

## D-S045-08 — Credential convention (security-relevant, one convention only)

```text
Storage      environment variable  TRADING_FRAMEWORK_BINANCE_API_KEY
Transport    header X-MBX-APIKEY on public market-data GETs only
Purpose      raise the weight limit; nothing else
Optional     unset = anonymous requests, lower limits, import still works
Forbidden    a secret key, HMAC signing, any signed/authenticated endpoint
Forbidden    a credential file under user_data/config/ or anywhere else
Forbidden    the key in logs, error messages, exception text, or the manifest
Manifest     api_key_used: true | false   (boolean only)
```

Rationale for env vars over `user_data/config/binance.yaml`:

- the project already standardises on `TRADING_FRAMEWORK_*`
  (`aws_btc_futures_runtime.py`, `TRADING_FRAMEWORK_STATUS_URL`),
- a file can be committed by accident; an environment variable cannot,
- two conventions guarantee drift and a second place to audit.

The strongest guarantee is structural: **no signing code exists**, so the key
cannot reach an account endpoint even by mistake. S045-T011 makes that a test.

---

## D-S045-09 — Mode selector

```text
mode: ohlcv     supported — direct klines
mode: trades    reserved — rejected with an explicit "not supported in v1" error
other           rejected as an invalid mode
```

The selector exists so a future `trades` mode (fetch aggregate trades → reuse
`derive_ohlcv_from_trades`, symmetric to ADR-0015) is additive. **Nothing in
this sprint may be built "for" that mode** — no abstract base class, no
strategy-pattern indirection, no unused parameters.

---

## D-S045-10 — Gap policy and validation

Binance ranges legitimately contain gaps (maintenance, listing dates, outages).

```text
Gaps are recorded in import_manifest.json as (start, end) pairs
Gaps are never filled, interpolated, or forward-carried
```

`OhlcvBarValidator`'s behaviour on a gapped range must be **determined in
S045-T006 before the workflow is written**, and the outcome recorded here as a
follow-up note. Two acceptable outcomes: validation passes with the gap
recorded, or validation fails with a message naming the gap. Silent acceptance
of an unrecorded gap is not acceptable.

> Open item for T006 — the only genuinely unknown behaviour in this sprint.

---

## D-S045-11 — Import manifest fields

```text
provider, mode, symbol, instrument_id, interval
requested_start, requested_end            (UTC, half-open)
first_bar_open_time, last_bar_close_time
page_count, request_count, retry_count
rows_decoded, rows_rejected
gaps: [ {start, end}, ... ]
normalization_version, schema_version
api_key_used: bool
```

Mirrors ADR-0014's manifest discipline. `DatasetMetadata.checksum` follows the
existing bar path (content checksum at finalize) — the trades-specific source
checksum rule from ADR-0014 does **not** apply here.

---

## D-S045-12 — Test tiers

```text
Tier 1 (CI)      fake urlopen serving recorded multi-page kline fixtures
                 covers: pagination, open-bar drop, gap, 429, 418, 5xx,
                 retry cap, key present/absent
Tier 2 (opt-in)  @pytest.mark.binance_network +
                 TRADING_FRAMEWORK_RUN_BINANCE_NETWORK_SMOKE=1
                 one short real range; excluded from standard CI
```

Both markers already exist. No new marker, no new CI job.

---

## D-S045-13 — Docs this sprint touches

```text
docs/planning/sprints/S045_WAVE0_DECISIONS.md   this file (new)
docs/planning/sprints/SPRINT_045.md             status + task progress
docs/adr/ADR-0025-...md                         PROPOSED → maintainer sets ACCEPTED
docs/adr/README.md                              index row
docs/planning/CURRENT_STATUS.md                 Active Sprint S045
docs/planning/ROADMAP.md                        Phase 2F (Wave 4, from the staged increment)
docs/reference/DATA_WORKFLOWS.md                Binance import flow (Wave 4)
docs/reference/MODULE_MAP.md                    new modules (Wave 4)
docs/onboarding/DEVELOPER_GUIDE.md              credential convention, once (Wave 4)
```

**Not this sprint:** anything under `apps/`, any CLI document, ADR-0026.

---

## D-S045-14 — Wave 0 Checklist (maintainer)

- [x] ADR-0025 approved (status moved PROPOSED → ACCEPTED)
- [x] D-S045-05 dataset identity confirmed, including the `instrument_id` convention (`BTCUSDT.P` or an alternative)
- [x] D-S045-08 credential convention confirmed: environment variable only, no file, no signing code
- [x] D-S045-09 confirmed: `ohlcv` only, `trades` reserved and rejected
- [x] D-S045-10 acknowledged as an open item to be resolved inside T006
- [x] Sprint 045 scope and 14-task breakdown approved
- [x] Branch `sprint/binance-historical-ohlcv` approved

Approved-by: Filip Folga (project maintainer), given directly in conversation
with the orchestrating Claude Code session on 2026-08-28 — "Tak, zatwierdzam
wszystko", after correcting the architect to open Sprint 045 and Sprint 046 as
two independent sprints (not one combined sprint), and choosing to run them
sequentially: Sprint 045 first, Sprint 046 after.

Implementation may start.
