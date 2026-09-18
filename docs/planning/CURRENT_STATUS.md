# Current Status

Last status review: **2026-09-17**. This is a current-work snapshot, not the sprint history. The prior detailed snapshot is preserved in the [archive](../archive/snapshots/CURRENT_STATUS_2026-09-11.md).

## 1. Purpose

Locate the active increment, remaining work and the canonical planning records. For current implementation, use [Reference](../reference/README.md).

## 2. Status Metadata

| Item | State |
|---|---|
| Current phase | Phase 17 — Research Application (Local Workbench) |
| Completed increments | Phase 16: 16A–16D (16E–16G unplanned); Phase 17: 17A–17B |
| Current increment | Phase 19 complete; Phase 18 increment 18A approved (2026-09-18) with Wave 0 accepted — [Sprint 068](sprints/SPRINT_068.md) (Milestone 1a) merged to `main` via #574; [Sprint 069](sprints/SPRINT_069.md) (Milestone 1b: `strategy_source_ref` + context expectancy) done, PR pending; Sprints N+2/N+3 not opened; 17C — Data Manager still not opened, lower priority |
| Completed sprints | 059–062, 064, 065, 066, 067 and 068 merged to `main` (064 via #546, 2026-09-15; 065 via #552-#556, 2026-09-17; 066 via #557-#566, 2026-09-17; 067 via #567-#571, 2026-09-17; 068 via #572-#574, 2026-09-18) |
| Active sprint | [Sprint 069](sprints/SPRINT_069.md) (Strategy Source Reference and Context Expectancy, Phase 18 18A Milestone 1b) — implemented and tested, PR pending. |
| Next draft | A follow-up on `trend.movement_efficiency`'s disposition (IDEA-029's third, out-of-scope-for-Wave-B component) — not yet opened, no urgency (small, independent, no shared-normalizer dependency) |
| Parallel state | Phase 15 complete; Phase 14A complete; 14B not planned; [Phase 17](roadmap/PHASE_17_RESEARCH_APPLICATION.md) 17A/17B closed 2026-09-15 (ADR-0037–0042), 17C/17D directional and unplanned; Sprint 062 closed (T001–T007 done); [Phase 18](roadmap/PHASE_18_DASHBOARD_RESEARCH_EVIDENCE.md) — 18A approved 2026-09-18 ([PRD](../product/PRD-dashboard-strategy-research-evidence.md)), 18B/18D directional, 18C folded into 18A; [Phase 19](roadmap/PHASE_19_MARKET_ANALYSIS_CATALOG_EXPANSION.md) approved 2026-09-17 and now **complete** — Wave 0, Sprint 065 (Tooling), Sprint 066 (Wave A) and Sprint 067 (Wave B) all closed and merged to `main` — the PRD's full 26+1-component scope is implemented (`trend.movement_efficiency` deliberately excepted) |

## 3. Work in Progress

Phase 16D (Portfolio Dashboard) is complete: Sprints 059–061 are archived, and Sprint 062 (T001–T007, including the VPS deploy/rollback and 24-hour observation) is closed. See [Phase 16D detail](roadmap/PHASE_16D_PORTFOLIO_DASHBOARD.md) for that closeout and [Phase 16 detail](roadmap/PHASE_16_QUANT_WORKBENCH.md) for unplanned later increments (16E–16G). Sprint 064 (Phase 17, Research Application MVP: Signal Research entry point, job runner, first end-to-end workbench run) is **closed and merged to `main`** via #546 (2026-09-15) — T001–T009 done, see that sprint's Closeout section for the full PR list and a live-demoed end-to-end run. Sprint 065 (Phase 19, Market Analysis Component Registration Tooling: scaffolding CLI, promotion readiness report, `structure.opening_gap` pilot) is **closed and merged to `main`** via [#552](https://github.com/folg-code/research-trading-framework/pull/552)-[#556](https://github.com/folg-code/research-trading-framework/pull/556), 2026-09-17 — T001–T005 done, see that sprint's Closeout section. Sprint 066 (Phase 19 Wave A — 20 components: 10 remaining `structure.*`/`session.*`, 5 `volatility.*`, 4 `candle.*`/`volume.*`, 1 `statistics.*`) is **closed and merged to `main`** via [#557](https://github.com/folg-code/research-trading-framework/pull/557)-[#566](https://github.com/folg-code/research-trading-framework/pull/566), 2026-09-17 — T001–T009 done (372 `market_analysis` tests, up from 279; all 20 components PASS `check_promotion_readiness.py`), see that sprint's Closeout section. [Sprint 067](sprints/SPRINT_067.md) (Phase 19 Wave B — 6 components: 2 `trend.*`/`momentum.*` normalized measures, `structure.distance_to_level` + 2 Fibonacci-level components, 1 session-anchored VWAP variant) is **closed and merged to `main`** via [#567](https://github.com/folg-code/research-trading-framework/pull/567)-[#571](https://github.com/folg-code/research-trading-framework/pull/571), 2026-09-17 — T001–T004 done (398 `market_analysis` tests, up from 372; all 6 components PASS `check_promotion_readiness.py`), see that sprint's Closeout section. This closes all three sprints planned for Phase 19 — the PRD's full 26+1-component scope is now implemented (`trend.movement_efficiency` deliberately excepted). Phase 19 is complete. 17C (Data Manager) remains a lower-priority, not-yet-opened candidate; Phase 18 is the next directional track but has no accepted PRD/ADR/sprint yet.

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
