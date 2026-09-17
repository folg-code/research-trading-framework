# Current Status

Last status review: **2026-09-17**. This is a current-work snapshot, not the sprint history. The prior detailed snapshot is preserved in the [archive](../archive/snapshots/CURRENT_STATUS_2026-09-11.md).

## 1. Purpose

Locate the active increment, remaining work and the canonical planning records. For current implementation, use [Reference](../reference/README.md).

## 2. Status Metadata

| Item | State |
|---|---|
| Current phase | Phase 17 — Research Application (Local Workbench) |
| Completed increments | Phase 16: 16A–16D (16E–16G unplanned); Phase 17: 17A–17B |
| Current increment | 17C — Data Manager (next candidate; not yet opened as a sprint) |
| Completed sprints | 059–062 and 064 merged to `main` (064 via #546, 2026-09-15) |
| Active sprint | None |
| Next draft | [Sprint 063](sprints/SPRINT_063.md) (Phase 16D content enrichment, unapproved; independent of 17C) |
| Parallel state | Phase 15 complete; Phase 14A complete; 14B not planned; [Phase 17](roadmap/PHASE_17_RESEARCH_APPLICATION.md) 17A/17B closed 2026-09-15 (ADR-0037–0042), 17C/17D directional and unplanned; Sprint 062 closed (T001–T007 done) |

## 3. Work in Progress

Phase 16D (Portfolio Dashboard) is complete: Sprints 059–061 are archived, and Sprint 062 (T001–T007, including the VPS deploy/rollback and 24-hour observation) is closed. See [Phase 16D detail](roadmap/PHASE_16D_PORTFOLIO_DASHBOARD.md) for that closeout and [Phase 16 detail](roadmap/PHASE_16_QUANT_WORKBENCH.md) for unplanned later increments (16E–16G). Sprint 064 (Phase 17, Research Application MVP: Signal Research entry point, job runner, first end-to-end workbench run) is **closed and merged to `main`** via #546 (2026-09-15) — T001–T009 done, see that sprint's Closeout section for the full PR list and a live-demoed end-to-end run. No sprint is currently active; 17C (Data Manager) is the next candidate. Its import-path technical direction (streaming Parquet importer) is already bound by the D-S064-01 amendment, so 17C is not blocked on that decision — it still needs its own Wave 0 for the remaining implementation choices (batch/row-group size, temp-file convention, Parquet reader) before a sprint opens.

## 4. Blocked Work

No blocker was recorded at the last review.

## 5. Open Problems, Decisions, and Risks

- [Problem Registry](PROBLEM_REGISTRY.md) — open problem entries.
- [Technical Debt](TECHNICAL_DEBT.md) — accepted debt.
- [ADR index](../adr/README.md) — accepted and planned decisions.
- [Roadmap](ROADMAP.md) — capability sequencing.

## 6. Sprint Progress

[Active sprints](README.md#active-work) remain under `planning/sprints/`. Completed sprint records are grouped by phase in the [Archive](../archive/README.md). The detailed historical progress table remains in the [2026-09-11 snapshot](../archive/snapshots/CURRENT_STATUS_2026-09-11.md#6-sprint-progress).

## 7. Status Update Rules

Update this page when active work or phase status changes. Keep task-level progress in the active sprint; move completed evidence to the archive instead of appending another closure narrative here.
