# Sprint 026 — Research Hot-Path Performance

## Metadata

```text
Sprint: 026
Phase: Cross-cutting — Research Performance (Phases 5 / 6A / 7 repayment)
Status: COMPLETED
Planned Start: 2026-07-17
Planned End: 2026-07-17
Integrated: main via PR #215 (2026-07-17)
Sprint Goal Owner: Project Maintainer
Depends On: Strategy Research columnar/Numba path on main; Signal Research + Robustness MVP on main
Sprint Branch: sprint/research-hot-path-performance
Task branch convention: feat/ | fix/ | docs/ | test/ | refactor/
Wave 0 decisions: docs/planning/sprints/S026_WAVE0_DECISIONS.md
Architecture Sources:
  - docs/reference/RESEARCH_METHODOLOGIES.md
  - docs/planning/TECHNICAL_DEBT.md (TD-017, TD-018)
  - docs/adr/ADR-0011 / ADR-0013 / ADR-0016 / ADR-0019
Track choice: Research hot-path repayment selected over Phase 8A polish (S024/S025) and Phase 4B —
  Signal / Market Research and Robustness are unusable at NQ half-year scale relative to the
  ~6 s Strategy Research baseline (2026-07-17 inspection).
```

---

## 0. Slice Choice

Strategy Research already has a demonstrated fast path:

```text
columnar OHLCV preload → shared Polars model evaluation → Numba fixed-bars kernel
→ ~6 s on ~177k NQ 1m bars
```

Signal / Market Research and Robustness Research share the **same** Market Analysis + expression
evaluation layer, but each adds an expensive layer Strategy Research does not need:

| Workflow | After shared eval | Problem |
|----------|-------------------|---------|
| Signal / Market Research | Python occurrence materialization + forward outcomes | Algorithmic hot path: O(occurrences × bars) |
| Robustness Research | N× full `run_strategy_research` | No shared OHLCV / analysis / eval cache across variants |

This sprint **repays that debt**. It does not change research methodology questions, persisted
schemas (unless a migration is explicitly justified), or analytics/report contracts.

**Out of scope:** new robustness methods (PBO/CSCV/DSR), orderflow, multi-data strategy research,
distributed execution, Bayesian/genetic search, UI redesign, Phase 8A dry-run polish (S024/S025).

---

## 1. Sprint Goal

```text
NQ half-year Signal / Market Research
  → vectorized occurrence + outcome materialization
  → wall-clock competitive with Strategy Research order of magnitude

Robustness parameter / walk-forward cells that share market+signal models
  → reuse preloaded OHLCV + evaluate_models result
  → resimulate only what the variant changes (exit / risk / assumptions)
```

Success: a maintainer can run the NQ half-year model-research demo and a small robustness sweep
without the run being dominated by Python dict rebuilds or redundant full strategy pipelines.

---

## 2. MVP Scope Checklist

### Wave A — Signal / Market Research hot path (CRITICAL)

- [x] Build timestamp → index **once per run** (never inside `resolve_reference_price` per row).
- [x] Vectorize or batch-resolve reference prices for occurrences / market-model observations.
- [x] Vectorize `compute_forward_outcomes` / multi-horizon path (Polars or NumPy; no per-row Python
      window list comprehensions as the default path).
- [x] Preserve outcome semantics: horizons, incomplete-horizon policy, MFE/MAE, direction normalize.
- [x] Unit + regression tests proving identical facts on fixtures vs pre-change baseline.
- [x] Benchmark note: NQ half-year signal/market research wall-clock before/after (doc or script).

### Wave B — Robustness shared evaluation (HIGH)

- [x] Introduce an explicit shared context for child strategy runs in one experiment
      (preloaded columnar OHLCV + optional shared `evaluate_models` result).
- [x] Reuse that context across parameter-sweep / walk-forward / stress cells when market and
      signal models are unchanged.
- [x] Keep fingerprint / resume semantics correct (child `run_id` still reflects variant inputs).
- [x] Monte Carlo remains post-process on persisted trades (no full resim required).
- [x] Benchmark note: demo robustness sweep cell-count × wall-clock before/after.

### Wave C — Docs and debt closeout

- [x] Update `TECHNICAL_DEBT.md` (TD-017 / TD-018 → REPAID or partial).
- [x] Update `RESEARCH_METHODOLOGIES.md` / `MODULE_MAP.md` only if operator-visible behaviour or
      performance claims change.
- [x] Record scale notes next to Strategy Research ~6 s baseline in README / CURRENT_STATUS.

---

## 3. Non-Goals / Explicit Deferrals

| Deferred | Why |
|----------|-----|
| Parallel child-run execution | Correctness of shared cache first; parallelism later |
| Family-run cross-variant MA cache for Signal Research | Same pattern as Wave B; schedule only if Wave A leaves family runs slow |
| Changing Robustness methodology to avoid strategy re-runs | Re-runs remain the contract; amortization is the fix |
| Rewriting analytics / Plotly reports | Read-only on persisted facts |

---

## 4. Task Breakdown

| Task | Outcome | Wave | Status |
|------|---------|------|--------|
| S026-T001 | Wave 0 decisions + baseline microbench harness (fixture + optional NQ) | 0 | DONE |
| S026-T002 | Fix `resolve_reference_price` / occurrence materialization index reuse | A | DONE |
| S026-T003 | Vectorize market-model observation materialization | A | DONE |
| S026-T004 | Vectorize forward outcomes (single + multi-horizon) | A | DONE |
| S026-T005 | Signal Research equivalence tests + half-year timing note | A | DONE |
| S026-T006 | Shared research evaluation context API for strategy child runs | B | DONE |
| S026-T007 | Wire robustness sweep / walk-forward / stress to shared context | B | DONE |
| S026-T008 | Robustness resume + fingerprint regression tests | B | DONE |
| S026-T009 | Robustness timing note + debt/docs closeout | C | DONE |

---

## 5. Acceptance Criteria

1. `resolve_reference_price` (or its replacement) does **not** rebuild an O(bars) map per occurrence.
2. Forward outcomes for the canonical multi-horizon demo produce **byte-identical or value-identical**
   facts vs the pre-sprint fixture baseline (explicit tolerance only if float path changes — prefer none).
3. NQ half-year Signal / Market Research compute is no longer dominated by occurrence/outcome Python
   loops; document measured wall-clock.
4. A robustness parameter cell that changes only `exit_after_bars` does **not** reload OHLCV or
   re-run Market Analysis / expression evaluation when a shared context is provided.
5. Existing robustness resume behaviour still skips completed fingerprints.
6. Quality gates pass: `ruff check`, `ruff format --check`, `mypy`, `pytest`.

---

## 6. Recommended PR Boundaries

One coherent outcome per PR (into `sprint/research-hot-path-performance`):

1. `feat/signal-reference-price-index` — T002 (+ tests)
2. `feat/signal-forward-outcomes-vectorized` — T003–T005
3. `feat/robustness-shared-evaluation-context` — T006–T008
4. `docs/research-performance-closeout` — T001 residual + T009

Do not bundle Signal vectorization and Robustness shared context in one PR.

---

## 7. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Silent outcome drift | Golden fixture comparisons before/after; keep schema stable |
| Shared context leaks across incompatible variants | Key context by dataset + range + model fingerprints; clear when market/signal change |
| Over-abstraction of “research session” | Minimal dataclass passed into existing application entry points; no new framework layer |
| Scope expands into family-run / distributed work | Keep family cache and parallelism out of MVP checklist |

---

## 8. Relationship to Other Sprints

| Sprint | Relationship |
|--------|--------------|
| 016 Robustness MVP | Capability complete; this sprint repays performance debt |
| 017 Model Research Methodology | Reports stay valid; compute underneath becomes usable at scale |
| 024 / 025 Phase 8A polish | Remain planned; research-track priority overtakes them until Wave A lands |
| Strategy Research Numba path | Reference implementation and benchmark baseline — do not regress |

---

## 9. Post-Sprint Direction

After closeout, choose among:

- Signal Research family shared-analysis cache (if still slow),
- optional parallel robustness child runs,
- return to Phase 8A (S024) or Phase 4B / 6B roadmap items.
