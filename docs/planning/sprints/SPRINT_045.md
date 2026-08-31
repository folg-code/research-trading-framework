# Sprint 045 — Binance USD-M Historical OHLCV Ingestion (Phase 2F)

## Metadata

```text
Sprint: 045
Phase: Phase 2F — Exchange REST Historical Import (opening increment)
Status: COMPLETE
Planned Start: TBD (on approval)
Planned End: 2026-08-31
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_002 (dataset lifecycle), SPRINT_011/012 (import pattern to mirror),
            SPRINT_019 (Binance mapper, symbol normalization, network-free CI rule)
Depended On By: SPRINT_046 (`trading-cli data fetch binance` wraps this workflow)
Sprint Branch: sprint/binance-historical-ohlcv
Task branch convention: feat/ | fix/ | docs/ | test/
PR base: sprint/binance-historical-ohlcv (never main until sprint integration)
Wave 0 decisions: docs/planning/sprints/S045_WAVE0_DECISIONS.md
Architecture Sources:
  - docs/product/PRD.md (confirmed)
  - docs/adr/ADR-0025 (Binance USD-M historical klines import) — ACCEPTED
  - docs/adr/ADR-0007 (dataset lifecycle), ADR-0008 (Parquet storage)
  - docs/adr/ADR-0014 / ADR-0015 (the import pattern being mirrored)
  - docs/adr/ADR-0022 (scripts/ stay thin)
  - docs/planning/ROADMAP_INCREMENT_PHASE_2F_AND_11.md (§13B)
```

---

## 0. Slice choice

The framework can research any instrument whose bars reach a published
`DatasetRef` — and it currently has exactly two ways to get there: a local
Databento DBN archive, or a CSV file. Binance exists in the repo only as a
**live** adapter: `fetch_closed_klines` returns the latest N closed candles for
dry-run reconnect gap-fill, with no date range, no pagination and no registry
integration.

So crypto data cannot enter research at all, even though every layer above the
importer is already provider-agnostic. This sprint closes that one gap and
nothing else.

**Out of scope by design:** the operator CLI. It is Sprint 046, has its own
ADR, its own branch and its own Wave 0. This sprint delivers a thin script
under `scripts/market_data/`, exactly like every other import path.

---

## 1. Sprint Goal

```text
Binance USD-M REST /fapi/v1/klines
    ↓ paginated over [start, end) UTC, weight-aware backoff, open bar dropped
map_kline_payload → MarketBar          (the same mapper the live path uses)
    ↓
OHLCV validation → bars.parquet + import_manifest.json
    ↓
register WORKING → finalize_dataset → publish_dataset
    ↓
DatasetRef  BTCUSDT.P|ohlcv|1m|binance|binance-usdm-klines-v1@1
```

Success: the maintainer pulls N months of BTCUSDT 1m bars from Binance, and
`run_strategy_research` / `build_predictive_dataset` consume the result with
**no change to any research code and no knowledge of the provider**.

---

## 2. In scope

- [ ] Paginated historical klines reader over an arbitrary UTC date range.
- [ ] Weight-aware rate limiting: header parsing, bounded jittered backoff, finite retry cap.
- [ ] Optional API key from one environment variable, market-data endpoints only.
- [ ] `import_binance_futures_ohlcv` application workflow with a `mode` selector (`ohlcv` only).
- [ ] `import_manifest.json` including recorded gaps and an `api_key_used` boolean.
- [ ] finalize + publish integration; idempotent re-import.
- [ ] Thin CLI `scripts/market_data/import_binance_ohlcv.py`.
- [ ] Tier 1 network-free tests; Tier 2 opt-in network smoke behind the existing marker.
- [ ] Boundary test: no signing code, no authenticated endpoint in the Binance provider package.
- [ ] Docs: DATA_WORKFLOWS, MODULE_MAP, credential convention documented once.

## 3. Out of scope

- The `trading-cli` operator CLI (Sprint 046).
- Binance **spot** market; any authenticated / account / order endpoint.
- Binance `trades` mode — the selector reserves it, this sprint does not build it.
- Resume-after-failure, incremental "top-up" imports, scheduled refresh.
- Changing `fetch_closed_klines` or any part of the live dry-run path.
- A generalized multi-exchange import abstraction (one provider is not a pattern).
- Gap **filling** or bar synthesis of any kind.

---

## 4. Provider boundary

ADR-0025 is binding.

```text
Allowed     providers/binance/ owns urllib, HTTP status, JSON, retry timing
Allowed     application/market_data/ owns lifecycle, validation, manifest
Allowed     reuse of map_kline_payload and normalize_stream_symbol
Forbidden   HTTP or Binance JSON above the infrastructure layer
Forbidden   any branch on provider == "binance" in research code
Forbidden   hmac / request signing / any authenticated endpoint path
Forbidden   reading a credential from any committed or user_data file
```

The live reconnect path stays behaviourally identical. If Wave 1 finds that
sharing helpers with `fetch_closed_klines` would change its behaviour, the two
paths duplicate a few lines instead — a regression in the AWS dry-run path
costs more than the duplication saves.

---

## 5. Task breakdown

### Wave 0 — Planning

Binding locks: `S045_WAVE0_DECISIONS.md`. No numbered task. Wave 0 is DONE when
that file is on the sprint branch and the maintainer has checked off the Wave 0
Checklist.

### Wave 1 — Fetch

| Task | Description | Acceptance | Status |
|------|-------------|-----------|--------|
| S045-T001 | Paginated kline reader `providers/binance/futures_klines_history.py`: half-open `[start, end)` UTC, `limit=1500`, cursor = `last close_time_ms + 1`, injectable `urlopen`, returns bars + per-page stats | multi-page range assembled in order, no duplicate `open_time`, no bar with `close_time >= now`; empty page inside range recorded as a gap, not an error | DONE |
| S045-T002 | Rate-limit governor: parse `X-MBX-USED-WEIGHT-1M`, throttle before the limit, bounded exponential backoff with jitter on 429 / 418 / 5xx, honour `Retry-After`, finite retry cap, typed error on exhaustion | unit tests cover each status with an injectable `sleep` (no real sleeping) and assert no unbounded retry loop | DONE |
| S045-T003 | Optional API key: `TRADING_FRAMEWORK_BINANCE_API_KEY` → `X-MBX-APIKEY` header on market-data GETs; absent key = anonymous request | header present only when the variable is set; key never appears in any log line, error message, exception text or manifest | DONE |

Depends on: nothing. T002 and T003 are independent of each other.

### Wave 2 — Import workflow

| Task | Description | Acceptance | Status |
|------|-------------|-----------|--------|
| S045-T004 | `application/market_data/import_binance_futures_ohlcv.py`: request/result dataclasses, `mode` selector accepting only `ohlcv`, validate → `write_bars` → register WORKING metadata | a request with `mode: trades` is rejected with an explicit "not supported in v1" error; a valid range registers a WORKING version | DONE |
| S045-T005 | `import_manifest.json`: provider, mode, symbol, interval, requested range, page/request counts, rows decoded/rejected, recorded gaps, `normalization_version`, `api_key_used` boolean | manifest written beside the dataset; a test asserts no key material in any field | DONE |
| S045-T006 | Gap policy + validator interaction: confirm `OhlcvBarValidator` behaviour on a range with missing minutes; record gaps, never fill | a range containing a real gap either passes validation with the gap recorded, or fails with a message naming the gap — decided and documented, never silent | DONE |
| S045-T007 | finalize + publish integration and idempotency | published `DatasetRef` returned by `query_historical`; re-importing the same range produces an identical bar set and checksum | DONE |

Depends on: Wave 1 (T004 needs T001).

> **T006 outcome (recorded 2026-08-31):** `OhlcvBarValidator` checks required
> fields, non-negative volume, duplicate `observed_at` timestamps and
> non-decreasing ordering — it does **not** check that consecutive bars are
> exactly one interval apart. A range containing a genuine Binance gap
> therefore **passes validation**; `import_binance_futures_ohlcv` records the
> gap in `import_manifest.json` (`gaps`), never fills it. This is the
> "validation passes with the gap recorded" branch of D-S045-10, confirmed by
> a Tier 1 test (`test_import_binance_futures_ohlcv_gap_passes_validation_and_is_recorded`),
> not assumed.

### Wave 3 — CLI and tests

| Task | Description | Acceptance | Status |
|------|-------------|-----------|--------|
| S045-T008 | `scripts/market_data/import_binance_ohlcv.py`, same shape as sibling scripts (`main(argv: list[str] \| None = None) -> int`, argparse, `--json`) | end-to-end import from the command line; `--help` lists every option; exit code 1 on a handled error | DONE |
| S045-T009 | Tier 1 integration test: fake `urlopen` serving recorded multi-page fixtures → import → finalize → publish → `query_historical` round trip | passes with no network access | DONE |
| S045-T010 | Tier 2 opt-in network smoke behind `@pytest.mark.binance_network` + `TRADING_FRAMEWORK_RUN_BINANCE_NETWORK_SMOKE=1` (short range, e.g. one hour) | excluded from the standard CI job | DONE |
| S045-T011 | Architecture boundary test: the Binance provider package contains no `hmac`/signature usage and no authenticated endpoint path; no `urllib` outside infrastructure | test fails if signing code is ever added | DONE |

Depends on: Wave 2.

### Wave 4 — Documentation and closure

| Task | Description | Acceptance | Status |
|------|-------------|-----------|--------|
| S045-T012 | `docs/reference/ARCHITECTURE_AND_WORKFLOWS.md`: the Binance import flow beside the Databento/CSV import flows (`docs/reference/DATA_WORKFLOWS.md` does not exist in the repository; ARCHITECTURE_AND_WORKFLOWS.md §3 is the actual target, per Sprint 044 precedent) | a reader can tell which import path applies to which source | DONE |
| S045-T013 | Credential convention documented **once** (`docs/onboarding/DEVELOPER_GUIDE.md`), plus `MODULE_MAP.md` entries for the new modules | exactly one documented location for the API key across the repo | DONE |
| S045-T014 | Apply `ROADMAP_INCREMENT_PHASE_2F_AND_11.md` Block 1/2 + §13B into `ROADMAP.md`, delete the staging file (done at sprint open, PR #349); update `CURRENT_STATUS.md` §11/§12 and `ROADMAP.md` Phase 2F status to reflect Sprint 045 as complete | roadmap has no duplicate/staged section left | DONE |

**Progress:** 14 / 14 tasks

---

## 6. Recommended PR sequence

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 0 | `docs/binance-historical-planning` | Wave 0 locks + ADR-0025 |
| 1 | `feat/binance-klines-history-reader` | T001–T003 reader, backoff, optional key |
| 2 | `feat/binance-ohlcv-import-workflow` | T004–T006 workflow, manifest, gap policy |
| 3 | `feat/binance-ohlcv-publish-and-cli` | T007–T009 publish, CLI, Tier 1 round trip |
| 4 | `test/binance-credential-boundary` | T010–T011 opt-in smoke + boundary test |
| 5 | `docs/phase-2f-closure` | T012–T014 docs, roadmap, status |

PR 2 depends on PR 1; PR 3 on PR 2. PR 4 and PR 5 may run in parallel with each
other. Each PR targets `sprint/binance-historical-ohlcv`.

---

## 7. Acceptance criteria

1. A multi-month USD-M range imports and publishes one `DatasetRef` with `provider="binance"`.
2. `query_historical` returns those bars; no consumer needs provider-specific handling.
3. An existing research workflow (Strategy or Predictive) runs on the result unmodified.
4. No imported bar is an open candle; bars are ordered and free of duplicate `open_time`.
5. Re-importing an identical range yields an identical bar set and checksum.
6. 429 / 418 / 5xx trigger bounded, jittered backoff with a finite retry cap; tests never sleep for real.
7. A failed import leaves no `PUBLISHED` version.
8. Gaps are recorded in `import_manifest.json` and never filled.
9. `mode: trades` is rejected with an explicit unsupported-mode error.
10. The API key is optional; with it unset, the import still works.
11. No committed file, and no file under `user_data/`, is required to hold the key.
12. A boundary test proves the provider package has no signing code or authenticated endpoint.
13. `fetch_closed_klines` and the live dry-run path are behaviourally unchanged.
14. Standard CI is network-free and green: `ruff check`, `ruff format --check`, `mypy`, `pytest`.

---

## 8. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Touching `fetch_closed_klines` regresses the AWS dry-run | New module; live path untouched; duplicate a few lines rather than share risky helpers |
| Weight limits misread → 418 IP ban during a long import | Throttle on the used-weight header before hitting the limit; honour `Retry-After`; finite retry cap |
| Validator rejects legitimate market gaps | T006 decides the policy explicitly before the workflow is written |
| API key leaks into a log or manifest | Boolean-only in the manifest; a test asserts the key value never appears in output |
| Credential convention drifts to a second location | ADR-0025 §5 locks one convention; T013 documents it once |
| Long ranges make tests slow or flaky | Tier 1 fixtures only in CI; network smoke is opt-in and short |
| "One more provider" scope creep mid-sprint | Only Binance USD-M `ohlcv`; a second exchange needs its own increment |

---

## 9. Dependencies

**Required:** ADR-0007 / ADR-0008 lifecycle and storage; `FileDatasetRegistry`,
`ParquetDatasetRepository`, `OhlcvBarValidator`, `finalize_dataset`,
`publish_dataset`; the Sprint 019 mapper and `normalize_stream_symbol`.

**Not required:** the CLI (Sprint 046), any ML extra, any dashboard change, any
new third-party dependency.

---

## 10. Quality gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

Network tests stay excluded by default. Opt in with
`TRADING_FRAMEWORK_RUN_BINANCE_NETWORK_SMOKE=1` and the `binance_network` marker.

---

## 11. Post-sprint direction

Candidates, none scheduled by default:

- `trades` mode (fetch aggregate trades → `derive_ohlcv_from_trades`),
- resume-after-failure and incremental top-up imports,
- a second exchange, if and only if a real need appears,
- Binance-backed predictive/strategy studies as a research increment.
