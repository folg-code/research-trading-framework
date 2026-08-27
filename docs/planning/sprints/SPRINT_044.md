# Sprint 044 — Predictive Research in the Dashboard and the IDEA-014 Gate (Phase 10C)

## Metadata

```text
Sprint: 044
Phase: Phase 10C — Neural Predictive Models (closing increment)
Status: IN PROGRESS (Wave 0)
Planned Start: 2026-08-27
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_041 (report), SPRINT_042 (leaderboard), SPRINT_043 (neural families)
Sprint Branch: sprint/predictive-dashboard-and-gate
Task branch convention: feat/ | fix/ | docs/ | test/
Wave 0 decisions: docs/planning/sprints/S044_WAVE0_DECISIONS.md
Architecture Sources:
  - docs/planning/ROADMAP.md (§13A Phase 10)
  - docs/adr/ADR-0022 (repository top-level layout; apps/* consumer boundary)
  - docs/planning/IDEA_INBOX.md (IDEA-014 Machine-Learned State Classifiers)
  - apps/dashboard/ (Streamlit + DuckDB consumer)
```

---

## 0. Slice choice

Two loose ends close Phase 10.

Studies are currently browsable only as loose HTML files, one per run. Comparing six runs means
opening six tabs. The dashboard already solves exactly this problem for Signal, Strategy and
Robustness research, and a Predictive page is a natural sibling.

The second is more consequential. Phase 10 was scoped from the start to stop short of trading, and
IDEA-014 — trained models producing Market Analysis States — was deferred pending mature research
infrastructure. That infrastructure now exists, so the question deserves a written answer rather
than quiet drift. This sprint produces the **decision**, not the implementation.

**Out of scope:** implementing an ML Market Analysis component; that is a future sprint gated by the
document this one writes.

---

## 1. Sprint Goal

```text
Persisted predictive datasets + runs
    ↓
DuckDB catalog scan (apps/dashboard, read-only)
    ↓
Predictive Research page: study picker → leaderboard → run detail → links to full HTML
    ↓
+
ADR-0024 + gate document: conditions under which a trained model may become
a Market Analysis State component (IDEA-014)
```

Success: predictive studies are browsable beside existing research in the dashboard, and the
maintainer holds a written, reviewable answer to "when may a model be promoted?".

---

## 2. In scope

- [ ] DuckDB catalog entries for predictive datasets and runs.
- [ ] Streamlit page `6_Predictive_Research.py` in `apps/dashboard`.
- [ ] Study picker, family leaderboard, run detail views.
- [ ] Reuse of existing chart builders and caching layers where they fit.
- [ ] Quality flags surfaced in the listing, not buried in run detail.
- [ ] Link out to the full offline HTML report per run.
- [ ] ADR-0024 — promotion conditions for machine-learned Market Analysis States.
- [ ] Gate document enumerating unresolved IDEA-014 questions and their required answers.
- [ ] Phase 10 closure: roadmap, status, methodology index.

## 3. Out of scope

- Implementing an ML-backed Market Analysis component or State.
- Triggering training from the dashboard — the page is read-only.
- Live inference, model serving, online parity implementation.
- A model registry product (stays deferred; see IDEA-003 and `TECHNICAL_DEBT.md`).
- Cross-study statistical comparison beyond the leaderboard already built in S042.

---

## 4. Dashboard boundary

ADR-0022 is binding: `apps/*` are separate deployable consumers and must not import research or
execution engines.

```text
Allowed      read persisted parquet / json through DuckDB and the dashboard's own contracts
Allowed      dashboard-local view models and chart builders
Forbidden    importing trading_framework research engines, estimators or adapters
Forbidden    installing scikit-learn, XGBoost or torch into the dashboard environment
```

The dashboard reads facts. If a number is not in `metrics.json` or `predictions.parquet`, the fix is
to persist it in a research sprint, not to compute it in the UI.

### Page structure

```text
Study picker            dataset fingerprint, instrument, label kind, horizon, run count
Leaderboard             one row per run: family, primary metric, baseline delta, flags
Run detail              per-fold metrics, stability, buckets, calibration, importance
Provenance              dataset fingerprint, estimator spec, seeds, library versions
Report link             path to the offline HTML from S041
```

The leaderboard shows the **baseline delta**, not the raw metric, as its primary sort. A run that
scores 0.61 AUC against a 0.58 permutation baseline should not outrank one scoring 0.57 against 0.50
— sorting by raw metric would invert exactly the judgement this track is meant to support.

---

## 5. The IDEA-014 gate

IDEA-014 asks five questions. The gate document answers each with a concrete, testable condition
rather than a principle. Draft positions to be confirmed in review:

**Training artifact identity.** A promoted model must be identified by a fingerprint that covers the
dataset, spec, seed and library versions, and that fingerprint must be recorded in the lineage of
every State it produces. Given the artifact policy in S040 §8, this likely requires a durable
serialization format decision — which is the main cost of promotion and must be priced honestly.

**Data leakage.** A model component consumes features at `available_at` like any other component.
The existing purge and embargo machinery covers training; the open risk is inference-time feature
availability, which must be enforced by the component contract, not by convention.

**Feature lineage.** Already solved in S039: features are declared `OutputRef` values. A model
component declares its feature dependencies the same way a rule-based component declares inputs, so
the DAG stays complete and cache identity stays correct.

**Offline/online parity.** The hard one. Batch research and the dry-run runtime must produce
identical State values for identical inputs, which means the preprocessing pipeline has to be part
of the artifact and executable in both paths. A parity test on recorded data is the minimum
acceptance bar.

**Model registry.** Deliberately not solved. The proposed position is that promotion requires only a
content-addressed artifact store, not a registry product — but this must be stated explicitly so a
future sprint does not assume registry infrastructure exists.

The document also states what is **not** sufficient for promotion: strong out-of-sample metrics
alone. A promoted model becomes a Market Analysis input, which means downstream strategies must
still pass Phase 7 robustness validation. Phase 10 metrics are a precondition, never a substitute.

---

## 6. Task breakdown

### Wave 0 — Planning

Binding locks: `S044_WAVE0_DECISIONS.md`. No numbered catalog task — T001–T018
are unchanged. Wave 0 is planning DONE when that file is on the sprint branch.

Catalog listing is a filesystem walk of `manifest.json` (same as existing
dashboard pages). DuckDB stays the Parquet read path, not a registry
(D-S044-04). ADR-0024 is Wave 3, not Wave 0.

### Wave 1 — Catalog

| Task | Description | Status |
|------|-------------|--------|
| S044-T001 | DuckDB catalog scan for predictive datasets and runs | TODO |
| S044-T002 | Dashboard-side contracts for predictive listings and run detail | TODO |
| S044-T003 | Caching + fingerprint invalidation reusing existing dashboard layer | TODO |

### Wave 2 — Page

| Task | Description | Status |
|------|-------------|--------|
| S044-T004 | Study picker view | TODO |
| S044-T005 | Leaderboard sorted by baseline delta, flags visible in the row | TODO |
| S044-T006 | Run detail: per-fold metrics, stability, buckets, calibration | TODO |
| S044-T007 | Importance panel (present only when the run persisted it) | TODO |
| S044-T008 | Provenance panel + offline report link | TODO |
| S044-T009 | Page registration `6_Predictive_Research.py` + navigation | TODO |
| S044-T010 | Empty-state and missing-artifact handling | TODO |

### Wave 3 — Gate

| Task | Description | Status |
|------|-------------|--------|
| S044-T011 | Gate document answering the five IDEA-014 questions | TODO |
| S044-T012 | ADR-0024 — promotion conditions for machine-learned States | TODO |
| S044-T013 | Parity test design sketch (offline vs runtime State values) | TODO |

### Wave 4 — Phase closure

| Task | Description | Status |
|------|-------------|--------|
| S044-T014 | Boundary test: dashboard imports no research engine or ML library | TODO |
| S044-T015 | IDEA_INBOX: IDEA-014 status updated with the gate outcome | TODO |
| S044-T016 | ROADMAP §13A marked COMPLETE; CURRENT_STATUS updated | TODO |
| S044-T017 | RESEARCH_METHODOLOGIES: Predictive Research methodology entry | TODO |
| S044-T018 | MODULE_MAP + DATA_WORKFLOWS final update for Phase 10 | TODO |

**Progress:** 0 / 18 tasks

---

## 7. Recommended PR sequence

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 0 | `docs/predictive-dashboard-planning` | Wave 0 locks (`S044_WAVE0_DECISIONS.md`) |
| 1 | `feat/dashboard-predictive-catalog` | T001–T003 catalog + contracts |
| 2 | `feat/dashboard-predictive-page` | T004–T010 page views |
| 3 | `docs/idea-014-promotion-gate` | T011–T013 gate + ADR-0024 |
| 4 | `docs/phase-10-closure` | T014–T018 boundary test + closure docs |

PR 3 is documentation only and can be reviewed in parallel with the dashboard work.

Each PR targets `sprint/predictive-dashboard-and-gate`.

---

## 8. Acceptance criteria

1. Predictive studies and runs appear in the dashboard catalog without manual registration.
2. The leaderboard sorts by baseline delta and shows quality flags in the row.
3. Run detail renders per-fold metrics; no view shows a pooled metric alone.
4. Importance and calibration panels degrade gracefully when a run lacks that data.
5. Provenance shows dataset fingerprint, estimator spec, seeds and library versions.
6. A boundary test proves the dashboard imports no research engine and no ML library.
7. The dashboard environment installs without `ml`, `ml-trees` or `dl` extras.
8. ADR-0024 answers all five IDEA-014 questions with testable conditions.
9. The gate document states explicitly what is not sufficient for promotion.
10. IDEA-014 status reflects the gate outcome rather than staying "DEFERRED".
11. ROADMAP §13A and CURRENT_STATUS record Phase 10 as complete.
12. CI green for both workspaces: `ruff check`, `ruff format --check`, `mypy`, `pytest`.

---

## 9. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Dashboard starts computing metrics | Read-only contract; boundary test; persist facts upstream instead |
| ML dependency creeps into the dashboard environment | Explicit install test without extras |
| Leaderboard sorted by raw metric misleads | Baseline delta is the primary sort, by design |
| Gate document written as vague principles | Each question must resolve to a testable condition |
| Promotion implied to be approved | ADR states conditions only; implementation needs its own sprint |
| Phase 10 quietly becomes strategy generation | Robustness (Phase 7) explicitly remains mandatory downstream |

---

## 10. Dependencies

**Required:** persisted predictive runs from S040–S043; existing dashboard catalog and caching
layers from S028–S034.

**Not required:** any ML library in the dashboard; execution or replay work.

---

## 11. Quality gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

Dashboard workspace checks run per its own `pyproject.toml`, as in Sprints 028–034.

---

## 12. Post-sprint direction

Phase 10 closes here. Candidate follow-ons, none scheduled by default:

- implementing a machine-learned Market Analysis State component, if ADR-0024 conditions are met,
- cross-sectional / multi-instrument predictive studies,
- feeding predictive outputs into Signal Models, which would require Phase 7 robustness validation
  of the resulting strategies,
- revisiting SHAP (S042 §9) or a content-addressed artifact store if promotion proceeds.
