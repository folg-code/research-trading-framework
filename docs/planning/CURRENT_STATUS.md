# Current Status

Last status review: **2026-09-17**. This is a current-work snapshot, not the sprint history. The prior detailed snapshot is preserved in the [archive](../archive/snapshots/CURRENT_STATUS_2026-09-11.md).

## 1. Purpose

Locate the active increment, remaining work and the canonical planning records. For current implementation, use [Reference](../reference/README.md).

## 2. Status Metadata

| Item | State |
|---|---|
| Current phase | Phase 17 — Research Application (Local Workbench) |
| Completed increments | Phase 16: 16A–16D (16E–16G unplanned); Phase 17: 17A–17B |
| Current increment | 17C — Data Manager (still not opened as a sprint; superseded in priority by Phase 19, see below) |
| Completed sprints | 059–062 and 064 merged to `main` (064 via #546, 2026-09-15); 065 closed on `sprint/market-analysis-catalog-tooling` (#552-#555), integration PR to `main` pending review |
| Active sprint | None |
| Next draft | Sprint N+1 (Phase 19 Wave A, 20 remaining components — `structure.opening_gap` already delivered by Sprint 065) — not yet opened, ready once Sprint 065 integrates to `main` |
| Parallel state | Phase 15 complete; Phase 14A complete; 14B not planned; [Phase 17](roadmap/PHASE_17_RESEARCH_APPLICATION.md) 17A/17B closed 2026-09-15 (ADR-0037–0042), 17C/17D directional and unplanned; Sprint 062 closed (T001–T007 done); [Phase 18](roadmap/PHASE_18_DASHBOARD_RESEARCH_EVIDENCE.md) captured 2026-09-17, fully directional, no PRD/ADR/sprint yet; [Phase 19](roadmap/PHASE_19_MARKET_ANALYSIS_CATALOG_EXPANSION.md) approved 2026-09-17, Wave 0 complete and accepted, highest priority among unapproved tracks, Sprint 065 (Tooling) closed, integration to `main` pending |

## 3. Work in Progress

Phase 16D (Portfolio Dashboard) is complete: Sprints 059–061 are archived, and Sprint 062 (T001–T007, including the VPS deploy/rollback and 24-hour observation) is closed. See [Phase 16D detail](roadmap/PHASE_16D_PORTFOLIO_DASHBOARD.md) for that closeout and [Phase 16 detail](roadmap/PHASE_16_QUANT_WORKBENCH.md) for unplanned later increments (16E–16G). Sprint 064 (Phase 17, Research Application MVP: Signal Research entry point, job runner, first end-to-end workbench run) is **closed and merged to `main`** via #546 (2026-09-15) — T001–T009 done, see that sprint's Closeout section for the full PR list and a live-demoed end-to-end run. Sprint 065 (Phase 19, Market Analysis Component Registration Tooling: scaffolding CLI, promotion readiness report, `structure.opening_gap` pilot) is **closed** on `sprint/market-analysis-catalog-tooling` — T001–T005 done via [#552](https://github.com/folg-code/research-trading-framework/pull/552)-[#555](https://github.com/folg-code/research-trading-framework/pull/555), see that sprint's Closeout section; its integration PR to `main` is open for review. No sprint is currently active. 17C (Data Manager) and Sprint N+1 (Phase 19 Wave A) are both next candidates; Phase 19 is the maintainer's stated higher priority.

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
