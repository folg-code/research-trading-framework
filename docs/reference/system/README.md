# System — Context Map

Cross-cutting architecture: read `SYSTEM_OVERVIEW.md` first, always. This is
Sprint 055 T005's context-map for the folder — see
`docs/planning/sprints/SPRINT_055_T001_REFERENCE_TARGET_IA.md` §5.1/§8 for
the full rationale behind this 9-file, subject-based split (it replaces an
earlier 8-file layout organized by which Sprint 054 vision document each
file came from, which caused the same concepts to be restated 2-4 times).

## Which file answers which question

| Question | File |
|---|---|
| "What's the big picture — modules, problems solved, workflow boundaries?" | [`SYSTEM_OVERVIEW.md`](SYSTEM_OVERVIEW.md) — **read this first** |
| "What does each domain (Market, Market Analysis, Strategy, Research, Execution) own vs. not own?" | [`DOMAIN_MODEL.md`](DOMAIN_MODEL.md) |
| "What are the cross-cutting build principles (priority order, separation of concerns, reproducibility)?" | [`ARCHITECTURE_PRINCIPLES.md`](ARCHITECTURE_PRINCIPLES.md) |
| "How does the Market Analysis engine work — components, DAG, cache, execution?" | [`MARKET_ANALYSIS_ARCHITECTURE.md`](MARKET_ANALYSIS_ARCHITECTURE.md) — includes the executor `available_at`-enforcement gap (G-04) |
| "What's the default higher-timeframe alignment policy? How are contract rolls handled?" | [`TIME_AND_ALIGNMENT.md`](TIME_AND_ALIGNMENT.md) |
| "What type should carry a price/quantity here? What's the canonical representation policy?" | [`DATA_REPRESENTATION_POLICY.md`](DATA_REPRESENTATION_POLICY.md) |
| "How is the execution-scoped analysis workspace managed? What are derived-data invariants?" | [`ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md`](ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md) — **not** the `user_data/` storage root, see the naming-collision note below |
| "Which package implements X? What's the module/package map?" | [`MODULE_MAP.md`](MODULE_MAP.md) |
| "May module A import module B? Is that enforced by a test?" | [`DEPENDENCY_RULES.md`](DEPENDENCY_RULES.md) — distinguishes test-enforced rules from documented-only ones |

## Naming collision to watch for

"Workspace" means two different things in this tree:

- the execution-scoped `AnalysisWorkspace` — [`ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md`](ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md)
- the user's `user_data/` storage root — [`MODULE_MAP.md`](MODULE_MAP.md)'s "User Workspace Map"

Check the question above before opening either file.

## Where the point-in-time Sprint 036 measurement record went

`DATA_REPRESENTATION_POLICY.md` carries only the durable, binding policy.
The Sprint 036 representation audit (commit-pinned benchmarks, PR-numbered
decision register, stage/PR board) now lives at
[`docs/planning/sprints/SPRINT_036_DATA_REPRESENTATION_AUDIT.md`](../../planning/sprints/SPRINT_036_DATA_REPRESENTATION_AUDIT.md)
— it's a sprint artifact, not ongoing reference material.
