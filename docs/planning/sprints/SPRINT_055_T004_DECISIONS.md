# Sprint 055 T004 — Maintainer Decisions (Review Gate)

```text
Task:   Sprint 055, T004 — the hard review gate per D-S055-03. Nothing in
        docs/reference/ or docs/vision/ was moved, split, merged, or
        newly written before this decision record.
Date:   2026-09-04
Inputs: SPRINT_055_T001_REFERENCE_TARGET_IA.md
        SPRINT_055_T002_VISION_TARGET_IA.md
        SPRINT_055_T003_PLANNING_CROSS_CHECK.md
Status: DECIDED — T005-T008 unblocked as of this record.
```

This document records the maintainer's decisions on T001-T003's proposals,
made directly (not inferred by an agent). It is the authority T007/T008
execute against.

## 1. `docs/reference/` target IA (T001)

| Decision | Ruling |
|---|---|
| 9-file subject-based `system/` re-cut (`DOMAIN_MODEL`, `ARCHITECTURE_PRINCIPLES`, `MARKET_ANALYSIS_ARCHITECTURE`, `TIME_AND_ALIGNMENT`, plus `SYSTEM_OVERVIEW`/`MODULE_MAP`/`DEPENDENCY_RULES` unchanged, `ANALYSIS_WORKSPACE_AND_DERIVED_DATA` moved up, `DATA_REPRESENTATION_POLICY` split out) | **APPROVED** |
| Reverse T007's two rejections: `workflows/SIGNAL_RESEARCH.md`, `STRATEGY_RESEARCH.md`, `STRATEGY_EXECUTION.md`, `MARKET_DATA.md` as pure extractions from `WORKFLOWS_ARCHITECTURE.md` and reclassified `DATA_MODULE.md` | **APPROVED** — confirmed as extraction, not authoring |
| `DATA_REPRESENTATION_AUDIT.md` split: Part A (binding policy) stays as `system/DATA_REPRESENTATION_POLICY.md`; Parts B+C (Sprint-036 point-in-time audit + decision register/PR board) move to `docs/planning/sprints/SPRINT_036_DATA_REPRESENTATION_AUDIT.md` | **APPROVED** — the one cross-folder move |
| `RESEARCH_METHODOLOGIES.md` / `SIGNAL_RESEARCH.md` adjacency (§5.2 of T001) | **APPROVED, option (a)**: keep both, `workflows/README.md` (T005) states the split in one line each, reciprocal one-line pointer at the top of each file |
| `modules/{SIGNALS,STRATEGY,EXECUTION,DATA}.md` (maintainer's example names with no source content) | **CONFIRMED REJECTED** per T001 — do not fabricate |
| Six content defects (T001 §6: stale component list, broken relative links, tier-inversion cross-references into `docs/vision/`) | **Fix opportunistically during T007** wherever the touched file is already being edited; do not open new files solely to fix these |
| `modules/ANALYSIS_COMPONENT_CATALOG.md` and `modules/STRATEGY_EXAMPLES.md` extractions from `STRATEGY_AUTHORING.md` | **APPROVED** (part of the approved target tree, no separate objection raised) |

## 2. `docs/vision/` target IA (T002)

| Decision | Ruling |
|---|---|
| Dissolve the 5 provenance-shaped remnants into 10 topic-grouped files (`PRODUCT_DIRECTION`, `TIME_MODEL_FUTURE`, `MARKET_DATA_FUTURE`, `MARKET_ANALYSIS_FUTURE`, `MARKET_ANALYSIS_DECISIONS`, `RESEARCH_SPACE_AND_ANALYTICS`, `EXECUTION_RUNTIME_FUTURE`, `EVENT_SYSTEM_FUTURE`, `COMPONENT_PROMOTION_LIFECYCLE`, `RUN_IDENTITY_AND_CONFIGURATION`) | **APPROVED** |
| Evictions (~600 lines superseded module/user_data layouts; ~815-line closed Sprint-003 planning note; `DATA_MODULE_FUTURE.md` §29 Sprint-002 scope note) | **APPROVED, destination = `docs/historical/`** — not deletion. Superseded layouts → `docs/historical/SUPERSEDED_LAYOUT_PROPOSALS.md`; the Sprint-003 planning-note body → `docs/planning/sprints/S003_MARKET_ANALYSIS_PLANNING_NOTE.md` (or fold into existing `SPRINT_003.md` materials if T008 finds a cleaner fit — executor's call, verbatim content either way) |
| `docs/vision/ARCHITECTURE_FOUNDATIONS.md`'s pipeline-convention-path question (T002 §8 item 1) | **Use `PRODUCT_DIRECTION.md`** as T002 proposed — the divergence from the `product-architecture` skill's canonical filename is accepted; the as-built half already lives at `docs/reference/system/ARCHITECTURE_FOUNDATIONS.md` |
| `ARCHITECTURE_FOUNDATIONS.md` §5.5 (Composition Over Inheritance) and §5.14 (Controlled Technology Adoption) — route to `.cursor/rules/ARCHITECTURE_CONTROL.md` and `docs/adr/README.md` respectively | **APPROVED**, but the `ARCHITECTURE_CONTROL.md` edit is out of Sprint 055's scope (same Cursor-side constraint as Sprint 053 T008) — leave a note in `PRODUCT_DIRECTION.md` pointing at the pending Cursor-side pass rather than silently dropping the content |
| F5 (T002 §6): possible contradiction between `MARKET_ANALYSIS_WITH_DECISIONS.md`'s D-018/D-028/D-029 and accepted ADR-MA-012/ADR-MA-014 | **Verify before finalizing `MARKET_ANALYSIS_DECISIONS.md`.** If confirmed superseded, add a one-line per-decision status annotation (flagged as newly-authored per D-S055-04, since this is new prose, not a move) rather than silently carrying forward a possibly-wrong "authoritative" claim |
| Polish → English translation of the D-001–D-036 register | **OUT OF SCOPE**, confirmed (already logged as a Sprint 055 follow-up) |
| `TIME_MODEL_FUTURE.md` (~90 lines, smallest proposed file) — keep separate or fold into `MARKET_DATA_FUTURE.md` | **Keep separate**, as T002 originally proposed (no objection raised to the default) |

## 3. Cross-check findings (T003) — what T007/T008 must additionally do

| Finding | Ruling |
|---|---|
| **G-14** — `ROADMAP.md` has no document-level `Status:` field | **RESOLVED directly in this commit**: `Status: ACCEPTED` added to `docs/planning/ROADMAP.md`, right after its title. Not part of T007/T008 — a standalone one-line fix. |
| **G-04** — the executor does not enforce inference-time `available_at`, but Market Analysis reference docs read as though it does | **Add during T007.** Place a clearly-flagged, newly-authored note (per D-S055-04) in the appropriate `system/` file (`MARKET_ANALYSIS_ARCHITECTURE.md` or `TIME_AND_ALIGNMENT.md` — executor's call based on where `available_at` semantics land) stating the as-built distinction: alignment honours `available_at`; the executor does not reject a component reading an unavailable feature. Point at ADR-0030 (PLANNED) and `ROADMAP.md` §13F. |
| **G-01 / G-02** — `docs/vision/DATA_MODULE_FUTURE.md`'s partitioning and continuous-futures sections frame settled ADR decisions (ADR-0014/0018) as "awaiting a maintainer decision" | **Fix during T008.** This is a citation/framing correction under D-S055-04's verbatim-move discipline — replace the "awaiting a maintainer decision" language with a citation to ADR-0014/ADR-0018 (partitioning) and ADR-0018 (continuous-futures scope), not a rewrite of the surrounding technical content. |
| **G-03** — `docs/reference/system/WORKFLOWS_ARCHITECTURE.md` lines 816/834 use unqualified "family analyses"/"strategy family" language for Strategy Research, where PRB-020 established no such concept exists in code | **Fix during T007.** Qualify or flag both lines (e.g. "not yet implemented for Strategy Research — see PRB-020") without rewriting the surrounding verbatim content. Also add a `PRB-020` citation where the Strategy Research gap is discussed, so the durable tracking ID survives outside the originating sprint doc. |
| **G-05 through G-13, G-15 through G-23** (14 remaining gaps, mostly MEDIUM/LOW) | **DEFERRED to a follow-up outside Sprint 055.** Do not fold these into T007/T008 — they are citation/cross-reference gaps against `PROBLEM_REGISTRY.md`/`TECHNICAL_DEBT.md`/`ROADMAP.md`/`docs/adr/`, not IA problems, and Sprint 055 is scoped to reorganize + fix the 3 explicitly-named + G-14 items only. Log as a follow-up (see `SPRINT_055.md` §7). |

## 4. What is now unblocked

Per D-S055-03, T005 (reference context-maps), T006 (vision context-map),
T007 (execute reference IA), and T008 (execute vision IA) may all proceed.
Recommended execution order: T007 and T008 first (in parallel, different
folders), since the folder indexes (T005/T006) describe the *result* of
those moves; T009 (inbound references) after both land; T010 (validation)
last.
