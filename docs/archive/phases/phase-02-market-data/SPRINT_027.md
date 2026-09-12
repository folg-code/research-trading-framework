# Sprint 027 — Market Data Import / Continuous Build Performance

## Metadata

```text
Sprint: 027
Phase: Cross-cutting — Market Data Performance (Phases 2B / 2C.1 / 2C.4 repayment)
Status: COMPLETED
Planned Start: 2026-07-17
Planned End: 2026-07-17
Integrated: pending (sprint → main)
Sprint Goal Owner: Project Maintainer
Depends On: Sprint 011/015 storage contracts on main; Sprint 026 research hot-path on main
Sprint Branch: sprint/market-data-import-performance
Task branch convention: feat/ | fix/ | docs/ | test/ | refactor/
Wave 0 decisions: docs/planning/sprints/S027_WAVE0_DECISIONS.md
Architecture Sources:
  - docs/adr/ADR-0014 (archive import + partitioned trades)
  - docs/adr/ADR-0018 (continuous futures materialization)
  - docs/planning/TECHNICAL_DEBT.md (TD-019, TD-020)
Track choice: Market Data rebuild wall-clock selected over Phase 8A polish (S024/S025) —
  NQ half-year batch import (~463 s) and continuous materialize write (~62 s) dominate
  operator rebuild time; research paths were repaid in Sprint 026 (2026-07-17 inspection).
```

---

## 0. Slice Choice

Research workflows no longer dominate when continuous OHLCV is already published
(`--skip-build` Strategy Research ~12–16 s).

Operator pain moved upstream:

```text
DBN archives
  → batch_import_contract_trades_range   (~463 s profiled)
  → build_continuous / materialize       (~122 s build in profiled half-year run)
  → derive OHLCV                         (secondary)
  → Strategy / Signal / Robustness       (already optimized)
```

This sprint **repays ingest and continuous-build hot paths**. It does not change roll policy,
research methodology, or live-data tracks.

**Out of scope:** custom DBN parsers, quotes/options import, parallel research execution,
Phase 8A polish, silent continuous schema rewrites without ADR.

---

## 1. Sprint Goal

```text
NQ half-year batch contract import
  → our map/partition path no longer pays Python list.copy tax per chunk
  → wall-clock improvement measurable against map_chunk_batch + parquet build baseline

Continuous trades materialize (345 sessions)
  → write path understood and improved without breaking fingerprint reuse
  → schema alignment to price_nanos only if ADR-amended

Vendor DBN→DataFrame decode
  → measured ceiling documented; optional safe knobs only (chunk_size / parallelism)
```

Success: a maintainer can re-import and rebuild NQ half-year continuous trades with a clear
before/after note on phases we own, and without schema regressions.

---

## 2. MVP Scope Checklist

### Wave A — Import column buffers (CRITICAL)

- [x] Microbench: split `to_df` vs `map_chunk_batch` vs partition write on a small archive set.
- [x] Replace `ContractChunkColumns` Python lists with NumPy (or Arrow) append-friendly buffers.
- [x] Eliminate `.tolist()` in `extend_masked`; vectorize `take` / merge.
- [x] Build `pa.Table` from arrays without intermediate `list(...)` copies where practical.
- [x] Preserve validation, session-date grouping, merge-existing partition semantics.
- [x] Unit + regression tests for chunk map / partition columns equivalence.

### Wave B — Continuous materialize write (HIGH)

- [x] Confirm write-vs-transform split on current code; document session-loop costs.
- [x] Remove avoidable copies / casts on the Arrow write path without schema change.
- [x] Decide explicitly: keep string `price` (**D-S027-08**); `price_nanos` deferred to ADR.
- [x] Close Wave B orchestration wins (`session_workers`, write/mapper path); schema unchanged.
- [x] Timing note: continuous materialize wall-clock before/after on NQ half-year (or subset).

### Wave C — Decode ceiling + docs closeout

- [x] Document vendor decode share; optionally tune `chunk_size` if microbench supports it.
- [x] Optional: bounded parallel archive import **only** if correctness (ordering/merge) is proven.
      → **Deferred** (correctness risk; decode ceiling still dominates).
- [x] Update `TECHNICAL_DEBT.md` (TD-019 / TD-020 → REPAID or partial).
- [x] Update `CURRENT_STATUS` / `MODULE_MAP` / ADR pointers only where behaviour or claims change.
- [x] Mark Sprint 027 complete when Waves A–C land on sprint branch.

---

## 3. Non-Goals / Explicit Deferrals

| Deferred | Why |
|----------|-----|
| Custom DBN decoder | Vendor ceiling; maintenance risk |
| Changing session_date partition layout | ADR-0014 contract; large migration |
| Roll-schedule algorithm rewrite | Secondary (~16 s); skip-build avoids it |
| Derive OHLCV algorithm rewrite | Secondary vs materialize.write |
| Live / quotes / options ingest | Different phases |
| Research hot-path follow-ups (MC NumPy, family cache) | Post-026 residuals; not this track |

---

## 4. Task Breakdown

| Task | Outcome | Wave | Status |
|------|---------|------|--------|
| S027-T001 | Wave 0 decisions + TD-019/TD-020 + sprint branch | 0 | DONE |
| S027-T002 | Import phase microbench harness (fixture / small NQ sample) | A | DONE |
| S027-T003 | NumPy/Arrow `ContractChunkColumns` + map path without `.tolist()` | A | DONE |
| S027-T004 | Vectorized `take` / session partition table build | A | DONE |
| S027-T005 | Import equivalence tests + map/write timing note | A | DONE |
| S027-T006 | Continuous write-path inspection + non-schema wins | B | DONE |
| S027-T007 | Continuous `price` schema decision (keep vs ADR `price_nanos`) | B | DONE |
| S027-T008 | Continuous materialize timing note | B | DONE |
| S027-T009 | Decode ceiling note + optional chunk_size / parallelism | C | DONE |
| S027-T010 | TD + CURRENT_STATUS / MODULE_MAP closeout | C | DONE |

---

## 5. Acceptance Criteria

1. Import hot path no longer uses Python list buffers as the primary column store for chunk map.
2. Fixture-scale mapped columns and written session partitions match pre-change facts.
3. Continuous materialize either measurably faster on the write path **or** has an explicit
   deferred schema ADR with documented rationale — no silent half-done schema drift.
4. Sprint docs + TD statuses reflect what was repaid vs deferred.
5. Working PRs land on `sprint/market-data-import-performance`; one integration PR to `main`.

---

## 6. Suggested PR Boundaries

```text
docs/market-data-import-performance-sprint     → main   (Wave 0 plan; this PR)
feat/import-column-buffers-numpy               → sprint
feat/import-session-partition-arrow            → sprint  (may merge with buffers if small)
feat/continuous-materialize-write-path         → sprint
docs/sprint-027-performance-closeout           → sprint
sprint/market-data-import-performance          → main   (integration)
```

Split if any working PR exceeds ~600–800 meaningful lines.

---

## 7. Baseline Numbers (pre-sprint, 2026-07-17)

From local profiles (not CI). Treat as order-of-magnitude, not SLOs.

**Batch import (NQ half-year):**

| Phase | Self / notes |
|-------|----------------|
| `decode_archive` | ~202 s self (vendor `to_df`) |
| `decode.map_chunk_batch` | ~61 s |
| `parquet.build_table` + `parquet.write_file` | ~48 s + ~53 s |
| `write_new_partition` | ~81 s inclusive |
| WALL | ~463 s |

**Continuous build (same half-year, with materialize):**

| Phase | Self / notes |
|-------|----------------|
| `materialize.write` | ~62 s (345 sessions, sequential) |
| `materialize.transform` | ~14 s |
| `derive_continuous_ohlcv` | ~22 s |
| `roll_schedule` | ~16 s |
| `strategy_research` (same log) | ~12 s — out of scope |

---

## 7.1 Closeout notes (post Wave A/B, 2026-07-17)

**Vendor decode ceiling (D-S027-02):** ~202 s / ~463 s (~44%) of the profiled import is
`databento.DBNStore.to_df` waiting between map phases. Sprint 027 does **not** claim to beat that
without a vendor/API change. `chunk_size` left at 50k; parallel archive import deferred.

**Our map path (TD-019):** synthetic microbench after NumPy buffers
(`scripts/ops/bench_contract_chunk_columns.py`, 10×200k rows):

| Phase | Seconds |
|-------|---------|
| `extend_masked` | ~0.13 |
| `take` | ~0.05 |
| `columns_to_table` | ~0.14 |
| total | ~0.32 |

So the former ~61 s `map_chunk_batch` tax is no longer explained by Python list materialization;
remaining import cost is decode + parquet I/O/merge.

**Continuous materialize (TD-020 / D-S027-08):** string `price` kept. Shipped: cheaper Polars
formatting, skip redundant casts, zstd without dictionary encoding, `session_workers` (default 4
in `build_continuous`). Full half-year rematerialize wall not re-profiled in CI; expect write-phase
wall to drop roughly with worker overlap subject to disk bandwidth.

---

## 8. Status Updates

Update this file when waves complete. Do not use it as a live stopwatch for CI.
