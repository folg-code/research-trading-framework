# Sprint 015 — Continuous Futures Materialization (Phase 2C.4)

## Metadata

```text
Sprint: 015
Phase: Phase 2C.4 — materialized continuous futures datasets
Status: COMPLETE
Planned Start: 2026-07-14
Planned End: 2026-07-14
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_011 (main), SPRINT_012 (main), SPRINT_013 (main)
Sprint Branch: sprint/continuous-futures-materialization
Task branch convention: feat/ | fix/ | docs/ (separate prefix, not nested under sprint ref)
Wave 0 decisions: docs/planning/sprints/S015_WAVE0_DECISIONS.md
Architecture Sources:
  - docs/planning/ROADMAP.md (§6 Phase 2C, §14 Research Data Strategy)
  - docs/vision/ARCHITECTURE_FOUNDATIONS_UPDATED.md (§4.13 continuous as derived)
  - docs/adr/ADR-0014-historical-archive-import-and-market-trade-storage.md
  - docs/adr/ADR-0015-derived-ohlcv-from-trades.md
  - docs/adr/ADR-0007-dataset-lifecycle-and-publication.md
Track choice: Continuous futures materialization selected over Phase 6B / 2C.2 / 4B / Phase 7 — 2026-07-14
```

---

## 0. Slice choice

Sprints 011–012 deliver **single-contract** Databento import and derived OHLCV. Strategy Research
(Sprint 013) and dashboard (Sprint 014) consume **published** `DatasetRef` values.

Long-horizon NQ/ES research requires a **versioned continuous artifact** built once and reused:

```text
Raw DBN (immutable)
    → Normalized Contract Dataset (per actual_contract)
    → Roll Schedule (versioned policy artifact)
    → Materialized Continuous Dataset (trades + derived OHLCV)
    → Backtest / Signal Research / Strategy Research (read-only)
```

Backtests must **not** decode DBN, resolve rolls or stitch contracts at run time.

**Out of scope:** price back-adjustment for trades/orderflow, open-interest roll, calendar roll,
quotes, orderflow bars, live rollover simulation, multi-product batch in one workflow (NQ first).

---

## 1. Sprint Goal

```text
Raw Databento DBN (user_data, immutable)
    ↓
import_contract_trades (split by actual_contract, session_date partitions)
    ↓
build_roll_schedule (volume @ RTH close, next-session switch)
    ↓
materialize_continuous_trades (roll_id, is_roll_boundary, actual_contract preserved)
    ↓
derive_continuous_ohlcv (same roll schedule)
    ↓
PUBLISHED DatasetRef (NQ.c.0|trades|tick|continuous|volume-rth-close@N)
    ↓
query_trades / query_historical / run_strategy_research (read-only)
```

Success: a maintainer runs one preprocessing command, then strategy research on multi-session NQ
continuous data **without** re-decoding DBN or recomputing rolls.

---

## 2. Four Outcomes

| Outcome | Deliverable |
|---------|-------------|
| **A — Contract normalization** | Per-contract trade datasets with `session_date` partitions and lineage columns |
| **B — Roll schedule** | Versioned volume-RTH-close schedule artifact + manifest |
| **C — Continuous materialization** | Partitioned continuous trades + manifest + fingerprint + incremental rebuild |
| **D — Continuous derived bars** | OHLCV 1m from continuous trades using shared roll schedule; `build_continuous` CLI |

---

## 3. Domain Boundary

```text
market/contracts/               product, contract code, session_date helpers
market/continuous/              roll policy, schedule, materialization config
market/models/                  MarketTrade (domain); storage schema extensions in infrastructure
application/market_data/        import_contract_trades, build_roll_schedule,
                                materialize_continuous_trades, derive_continuous_ohlcv
infrastructure/storage/         session_date partitions, continuous manifest, fingerprint
infrastructure/importers/       Databento decode only (unchanged boundary)
```

### Preprocessing vs consumer boundary (binding)

```text
build_continuous CLI / application workflows   — may write WORKING → PUBLISHED datasets
run_strategy_research / run_signal_research   — read PUBLISHED only; refuse if missing
```

Consumers must not call `import_databento_trades_archive` or roll builders implicitly.

### Price semantics (binding)

```text
trades / orderflow / execution simulation  — no back-adjustment
continuous records                       — actual_contract + is_roll_boundary + roll_id preserved
adjusted analytical series               — deferred separate artifact (not this sprint)
```

---

## 4. Storage and identity

### Raw layer (unchanged)

```text
user_data/market_data/<product>/databento/.../*.dbn.zst   — immutable source of truth
```

### Contract datasets

```text
instrument_id  = NQ.NQM5  (product + CME contract code)
data_type      = trades
timeframe      = tick
provider       = databento
partition key  = session_date (CME RTH session, not UTC calendar day)
```

### Continuous datasets

```text
instrument_id  = NQ.c.0
data_type      = trades | ohlcv
timeframe      = tick | 1m
provider       = continuous  (trades) | derived (ohlcv from continuous trades)
source_id      = volume-rth-close  (policy slug)
```

### Roll schedule artifact

```text
continuous/schedules/NQ/volume-rth-close/v<N>/
  schedule.parquet
  manifest.json
```

Referenced from continuous dataset lineage; shared by trades and OHLCV derivation.

---

## 5. Task Board

### Wave 0 — Decisions and spike

| Task | Description | Status |
|------|-------------|--------|
| S015-T001 | Wave 0 decisions (`S015_WAVE0_DECISIONS.md`) + roll-policy spike | DONE |

### Wave 1 — Contract normalization

| Task | Description | Status |
|------|-------------|--------|
| S015-T002 | Contract instrument identity (`NQ.<CONTRACT>`) + validation | DONE |
| S015-T003 | Multi-contract DBN decode and split by `actual_contract` | DONE |
| S015-T004 | `session_date` partition layout + `market-trade-contract-v1` Parquet schema | DONE |
| S015-T005 | `import_databento_contract_trades` workflow + import manifest | DONE |

### Wave 2 — Roll schedule

| Task | Description | Status |
|------|-------------|--------|
| S015-T006 | `RollPolicy` / `RollSchedule` domain types | DONE |
| S015-T007 | Volume-based roll builder (RTH close evaluation, confirmation sessions) | DONE |
| S015-T008 | Persist roll schedule artifact + manifest | DONE |

### Wave 3 — Continuous trades materialization

| Task | Description | Status |
|------|-------------|--------|
| S015-T009 | `materialize_continuous_trades` workflow | DONE |
| S015-T010 | Continuous manifest + source fingerprint | DONE |
| S015-T011 | Incremental rebuild window (default 10 sessions) | DONE |

### Wave 4 — Continuous derived OHLCV

| Task | Description | Status |
|------|-------------|--------|
| S015-T012 | `derive_continuous_ohlcv` using shared roll schedule | DONE |
| S015-T013 | Publish + query continuous `DatasetRef` through existing contracts | DONE |

### Wave 5 — CLI and integration

| Task | Description | Status |
|------|-------------|--------|
| S015-T014 | CLI `scripts/market_data/build_continuous.py` | DONE |
| S015-T015 | Integration test: multi-contract fixture → continuous → strategy research read | DONE |
| S015-T016 | Consumer boundary test (research paths do not import roll builders) | DONE |

### Wave 6 — ADR and closure

| Task | Description | Status |
|------|-------------|--------|
| S015-T017 | ADR-0018 — Continuous futures materialization | DONE |
| S015-T018 | `MODULE_MAP.md`, `DATA_WORKFLOWS.md`, `CURRENT_STATUS.md` | DONE |
| S015-T019 | Sprint closure | DONE |

**Progress:** 19 / 19 tasks (all waves complete)

---

## 6. Recommended PR sequence

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 1 | `docs/continuous-futures-planning` | Wave 0 decisions + sprint doc (this document) |
| 2 | `feat/contract-trades-import` | T002–T005 contract normalization |
| 3 | `feat/roll-schedule-builder` | T006–T008 roll schedule |
| 4 | `feat/continuous-trades-materialization` | T009–T011 continuous trades |
| 5 | `feat/continuous-derived-ohlcv` | T012–T013 continuous OHLCV |
| 6 | `feat/build-continuous-cli` | T014–T016 CLI + integration |
| 7 | `docs/continuous-futures-closure` | T017–T019 ADR-0018, docs, closure |

Each PR targets `sprint/continuous-futures-materialization`. Final integration PR → `main` when
all required tasks complete.

---

## 7. Acceptance criteria

1. Multi-contract DBN decodes into separate contract datasets with `session_date` partitions.
2. Roll schedule for NQ volume-RTH-close is versioned, persisted and reproducible from manifest.
3. Continuous trades dataset preserves `actual_contract`, `roll_id`, `is_roll_boundary` per row.
4. Continuous OHLCV 1m uses the **same** roll schedule as continuous trades.
5. `build_continuous` CLI materializes or reuses dataset based on fingerprint; incremental append
   rebuilds only the trailing window.
6. `run_strategy_research` succeeds on published continuous OHLCV without DBN import.
7. No price back-adjustment applied to trade or bar facts.
8. CI green: `ruff check`, `ruff format --check`, `mypy`, `pytest`.
9. ADR-0018 ACCEPTED; module map and data flows updated.

---

## 8. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| UTC `day=` vs `session_date` mismatch | Binding: contract layer uses `session_date`; document mapping in ADR-0018 |
| Spread symbols (`NQU5-NQZ5`) in DBN | Exclude spread rows in contract import; document filter |
| Roll lookahead | Evaluate volume only after RTH close; switch at next session open |
| Large rebuild on every import | Incremental window + fingerprint reuse |
| Breaking existing single-contract import | Keep `import_databento_trades_archive` unchanged; new workflow alongside |
| Scope creep into orderflow/quotes | Explicit out-of-scope; NQ trades only in MVP |

---

## 9. Dependencies

**Required on main:**

- ADR-0014 trades import, ADR-0015 derived OHLCV, ADR-0007 lifecycle
- `CmeEsRthSessionResolver` (Sprint 005)
- Strategy Research consumer path (Sprint 013)

**Not required:**

- Sprint 014 Phase B inspection API
- Phase 6B, 4B orderflow, quotes

---

## 10. Quality gates

Every implementation PR must pass:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

---

## 11. Post-sprint direction

After Sprint 015 merges to `main`:

- Strategy Research on multi-year NQ continuous OHLCV,
- Signal Research on continuous bars,
- optional open-interest / calendar roll policies,
- orderflow bars from shared roll schedule (Phase 4B),
- Sierra SCID contract import adapter.

See `ROADMAP.md` §6 Phase 2C.4 and `CURRENT_STATUS.md`.

---

## 12. Sprint Closure (2026-07-14)

### Delivered outcomes

```text
A — Contract normalization   multi-contract DBN import, session_date partitions, contract schema v2
B — Roll schedule              volume-rth-close policy, versioned artifact + manifest
C — Continuous materialization partitioned trades, manifest + fingerprint, incremental rebuild
D — Continuous derived OHLCV   per-session Polars aggregation, partitioned bars, build_continuous CLI
```

### PRs (working → sprint branch)

| PR | Outcome |
|----|---------|
| #115 | Contract-level Databento trades import |
| #116 | Volume-based roll schedule builder |
| #117 | Materialize continuous trades from roll schedule |
| #118 | Derive continuous OHLCV and query routing |
| #119 | `build_continuous` CLI and integration tests |
| #120 | Pipeline optimization (batch import, partitioned OHLCV) |
| #121 | Arrow roll-schedule RTH volumes |
| pending | Wave 6 — ADR-0018 ACCEPTED, reference docs, closure |

### Quality at closure

```text
570 tests passed
ruff / mypy / pre-commit green
half-year NQ operator validation: ~44M continuous trades, ~177k 1m bars, strategy research read OK
```

### Deferred (explicit)

```text
Price back-adjustment for trades/orderflow     separate future artifact
Open-interest / calendar roll policies         follow-up increment
Spread symbol import                           excluded in MVP
Consumer query columnar path (TD-011)          list[MarketTrade]/list[MarketBar] unchanged
Sprint 014 Phase B inspection API              deferred
```

### Post-sprint decision

Merge `sprint/continuous-futures-materialization` → `main`, then choose continuous OHLCV strategy
research at scale, Phase 6B, 2C.2, or 4B — see `CURRENT_STATUS.md` §11.
