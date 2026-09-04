# Sprint 055 — Documentation Architecture Rebuild (High-Level to Low-Level)

## Metadata

```text
Sprint: 055
Phase: Cross-cutting docs architecture — not part of the Phase 15 predictive
       research track.
Status: IN PROGRESS — approved by maintainer, opened 2026-09-04.
Planned Start: 2026-09-04
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: Sprint 054 (Vision Reclassification and Reference Layering,
            #434) — closed on `main`. This sprint builds on Sprint 054's
            current/future classification and system/workflows/runbooks/
            modules layering rather than redoing it from scratch.
Depended On By: None known.
Sprint Branch: sprint/documentation-architecture-rebuild
Task branch convention: feat/ | fix/ | docs/ | test/ | refactor/
PR base: sprint/documentation-architecture-rebuild (never main until
         sprint integration)
Architecture Sources:
  - docs/planning/sprints/SPRINT_054.md and its T001-T010 artifacts —
    AUTHORITATIVE for what was already classified/moved; do not re-derive
  - docs/reference/README.md, docs/vision/README.md — current state
  - docs/planning/PROBLEM_REGISTRY.md, docs/planning/TECHNICAL_DEBT.md,
    docs/planning/ROADMAP.md — known gaps to cross-check against
```

## 1. Goal

Rebuild `docs/reference/` and `docs/vision/`'s information architecture so
both are navigable **high-level to low-level** by a fresh reader (human or
agent) with no prior context: every folder that holds more than a handful
of files gets its own index/context-map (not just the single top-level
`docs/reference/README.md`/`docs/vision/README.md`), so finding "how does
X work" takes 1-2 lookups instead of reading every file in a folder.
`docs/adr/` is out of scope — ADRs are immutable history; only their
existing navigational index may gain small pointer updates if content
moves.

This is explicitly **not** a mechanical re-shuffle into a pre-decided
folder tree. The maintainer supplied an illustrative target shape
(`system/{SYSTEM_OVERVIEW,MODULE_MAP,DOMAIN_MODEL,DEPENDENCY_RULES}.md`,
`workflows/{SIGNAL_RESEARCH,STRATEGY_RESEARCH,STRATEGY_EXECUTION,
MARKET_DATA}.md`, `modules/{DATA,MARKET_ANALYSIS,SIGNALS,STRATEGY,
EXECUTION}.md`) as a **calibration example of granularity and naming**,
not a literal spec — Sprint 054's T007 already demonstrated that forcing
content into an undertested guessed structure produces either duplication
or fabricated prose (it explicitly rejected splitting
`RESEARCH_METHODOLOGIES.md` and inventing `STRATEGY_EXECUTION.md`/
`MARKET_DATA.md` from non-existent source content). This sprint runs the
same audit-first discipline at a larger scope: read everything, propose a
target IA grounded in what actually exists, get it reviewed, then execute.

## 2. Scope

**In scope**, sequenced so structure decisions never precede content
understanding (same discipline as Sprint 054's D-S054-01):

| # | Task | Size |
|---|---|---|
| T001 | Full-content audit of all 20 current `docs/reference/` files (already tier-tagged by Sprint 054 T007; this pass re-reads each for genuine subject-matter boundaries, redundancy between files, and whether the current `system/`/`workflows/`/`runbooks/`/`modules/` folders need internal indexes or further splitting/merging) — produces a target IA proposal for `docs/reference/`, calibrated against but not bound by the maintainer's example tree | Large (read-only) |
| T002 | Same audit for all 7 current `docs/vision/` files (2 are already-trimmed post-Sprint-054 remnants; `DATA_MODULE_FUTURE.md` is brand new) — produces a target IA proposal for `docs/vision/` | Large (read-only) |
| T003 | Targeted cross-check against `docs/planning/PROBLEM_REGISTRY.md`, `docs/planning/TECHNICAL_DEBT.md`, `docs/planning/ROADMAP.md`, and `docs/adr/README.md`'s index for known gaps or decisions not yet reflected in `reference/`/`vision/` — including the two items flagged when `DATA_MODULE.md` was reclassified (partitioning-policy divergence day-vs-month, continuous-futures roll/adjustment gap). **Not** a full read of all 106 sprint docs — mine sprint docs only where T001/T002 or this cross-check surfaces a specific, named gap that a sprint doc might resolve. Produces a short list of concrete content gaps for the target IA to account for (not new prose yet) | Medium (read-only, targeted) |
| T004 | **Maintainer review gate.** Present T001-T003's combined target IA proposal (final folder/file layout for both trees, with a one-line rationale per file and a note on which of the maintainer's example filenames were kept/renamed/dropped and why) for explicit sign-off before any file is moved, split, merged, or newly written | Decision gate |
| T005 | Add a context-map/index file to every `docs/reference/` subfolder that doesn't already have one beyond the top-level README (`system/`, `workflows/`, `runbooks/`, `modules/` each get a short index: what's in this folder, one line per file, when to open which) | Medium — depends on T004 |
| T006 | Add an equivalent context-map/index to `docs/vision/` (currently a flat file list with no per-topic grouping) | Small — depends on T004 |
| T007 | Execute `docs/reference/`'s approved target IA from T004: moves via `git mv` (verbatim content) plus only as much genuinely new prose as T004 explicitly approved (e.g. if a workflow file is approved to be written, not just guessed at) | Large — depends on T004 |
| T008 | Execute `docs/vision/`'s approved target IA from T004, same rules | Medium — depends on T004 |
| T009 | Update every inbound reference to anything moved/renamed/merged (`AGENTS.md`, `docs/README.md`, ADRs — path only, sprint docs where still-active) | Medium — mechanical once T007/T008 land |
| T010 | Phase-F-style validation re-run: the 5 checks Sprint 054 T010 already validated, plus a new 6th check specific to this sprint's goal — "open `docs/reference/modules/` (or `docs/vision/`) blind, find the module/topic you need via its folder's context-map alone, without opening every file in the folder" | Small |

**Out of scope:**
- Any change to `docs/adr/` beyond path-reference fixes if a linked file
  moves — ADR content is immutable history.
- Rewriting settled architecture decisions or vision content's substance —
  this sprint reorganizes and, where T004 explicitly approves it, fills
  genuine documentation gaps; it does not relitigate accepted decisions.
- A full read of all 106 `docs/planning/sprints/*.md` files — T003 is
  targeted, not exhaustive (see D-S055-02).
- Resolving the two open findings from `DATA_MODULE.md`'s reclassification
  (partitioning-policy divergence, continuous-futures roll/adjustment gap)
  as engineering work — T003 only checks whether the *documentation* about
  them needs a gap-note; fixing the underlying inconsistency is separate
  engineering work, tracked in `PROBLEM_REGISTRY.md`/`TECHNICAL_DEBT.md`.
- `.cursor/rules/project-architecture.mdc` (Sprint 053's deferred T008,
  still needs a Cursor-side maintainer pass) — unrelated to this sprint.

## 3. Decisions (Wave 0)

- **D-S055-01 — The maintainer's example tree is a calibration reference,
  not a spec.** T001/T002 must ground the target IA in actual content
  boundaries (mirroring Sprint 054 T007's method), keeping, renaming, or
  dropping any of the example's filenames based on evidence. T004 is where
  the maintainer confirms or corrects the result — the example does not
  pre-approve anything.
- **D-S055-02 — Sprint-doc mining is targeted, not exhaustive.** Reading
  all 106 sprint docs cover-to-cover is disproportionate. T003 only opens a
  specific sprint doc when a named gap points at it (e.g. "which sprint
  decided the partitioning default?"). If T001-T003 together suggest
  exhaustive mining would change the outcome materially, stop and ask the
  maintainer before expanding scope, rather than unilaterally reading all
  106.
- **D-S055-03 — No content is moved before T004 approves the target IA.**
  Same sequencing discipline as Sprint 054's D-S054-01: T005-T009 may not
  start before T004 signs off. This sprint is larger and touches more
  files than Sprint 054's vision-reclassification track, so the review
  gate is a hard stop, not a formality.
- **D-S055-04 — New prose is minimized and flagged.** Preference is always
  moving/consolidating verified existing content. Where T004 explicitly
  approves writing new material to fill a real gap (e.g. a folder-level
  context-map's connective prose, or a small gap T003 surfaces), it must
  be flagged as newly-authored in the PR description, not presented as
  moved/verified content.
- **D-S055-05 — This sprint is large; expect multiple waves.** 20
  `docs/reference/` files + 7 `docs/vision/` files, plus new index files
  per folder. Task branches follow normal PR-size discipline per file or
  per folder group, even though the audit tasks (T001-T003) are
  unavoidably large reads, mirroring Sprint 054's D-S054-04.

## 4. Tasks

| ID | Task | Depends on | Status |
|---|---|---|---|
| T001 | Audit `docs/reference/`, propose target IA | — | DONE |
| T002 | Audit `docs/vision/`, propose target IA | — | DONE |
| T003 | Targeted gap cross-check against planning docs | — | TODO |
| T004 | Maintainer review gate — approve combined target IA | T001, T002, T003 | TODO |
| T005 | Add context-map indexes to `docs/reference/` subfolders | T004 | TODO |
| T006 | Add context-map index to `docs/vision/` | T004 | TODO |
| T007 | Execute `docs/reference/` target IA | T004 | TODO |
| T008 | Execute `docs/vision/` target IA | T004 | TODO |
| T009 | Update inbound references | T007, T008 | TODO |
| T010 | Validation re-run (6 checks) | T001-T009 | TODO |

## 5. Progress

- 2026-09-04: Sprint opened on `sprint/documentation-architecture-rebuild`
  after maintainer approval. Starting T001 and T002 in parallel (both
  read-only audits, independent of each other).
- 2026-09-04: T001 complete (read-only). Full read of all 20 current
  `docs/reference/` files produced
  `docs/planning/sprints/SPRINT_055_T001_REFERENCE_TARGET_IA.md`. Central
  finding: 4 of `system/`'s 8 files (`ARCHITECTURE_FOUNDATIONS`,
  `ARCHITECTURE_TECHNICAL`, `MULTITIMEFRAME_MARKET_MODEL`,
  `WORKFLOWS_ARCHITECTURE`) are organized by which Sprint-054 vision
  document they came from, not by subject — 13 named concepts are each
  restated in 2-4 of them (Features/Structures/States taxonomy,
  `observed_at`/`available_at`, `LAST_CLOSED_BAR`, `MarketFieldReference`,
  `SignalOccurrence`, dependency direction, dataset lifecycle, the
  `user_data/` tree verbatim-duplicated in two files, etc.). Proposes a
  9-file subject-based `system/` re-cut (`SYSTEM_OVERVIEW`, `DOMAIN_MODEL`,
  `ARCHITECTURE_PRINCIPLES`, `MODULE_MAP`, `DEPENDENCY_RULES`,
  `MARKET_ANALYSIS_ARCHITECTURE`, `TIME_AND_ALIGNMENT`,
  `ANALYSIS_WORKSPACE_AND_DERIVED_DATA` moved up from the root,
  `DATA_REPRESENTATION_POLICY` split out of `DATA_REPRESENTATION_AUDIT`).
  **Reverses two of Sprint 054 T007's rejections**: `system/WORKFLOWS_ARCHITECTURE.md`
  (imported by T006c, after T007 ran) is already structured as three
  standalone workflow narratives, so `workflows/SIGNAL_RESEARCH.md`,
  `STRATEGY_RESEARCH.md`, and `STRATEGY_EXECUTION.md` now have real source
  content requiring pure extraction, not authoring; similarly
  `modules/DATA_MODULE.md` post-reclassification is a workflow narrative,
  not a module reference, supporting `workflows/MARKET_DATA.md`.
  `workflows/RESEARCH_METHODOLOGIES.md` and the `runbooks/` tier both stay
  as T007 found them. Rejects the example's `modules/{SIGNALS,STRATEGY,
  EXECUTION,DATA}.md` as unsupported by any source content. One proposal
  crosses out of `docs/reference/` entirely and needs explicit T004
  approval: splitting `DATA_REPRESENTATION_AUDIT.md`'s point-in-time
  Sprint-036 audit + decision register (Parts B/C) out to
  `docs/planning/sprints/`, keeping only the durable policy (Part A) as
  `DATA_REPRESENTATION_POLICY.md`. Flags a `DOMAIN_MODEL.md` naming
  coordination need with T002 (both may want the name — T002's proposal
  uses `PRODUCT_DIRECTION.md` for vision, so no actual collision). Six
  content defects logged for T003/T004 (stale component lists, broken
  relative links, tier-inversion cross-references into `docs/vision/`).
  No `docs/reference/` file was moved, renamed, merged, split, or edited;
  `docs/vision/` untouched (owned by T002).
- 2026-09-04: T002 complete (read-only). Full read of all 7 current
  `docs/vision/` files produced
  `docs/planning/sprints/SPRINT_055_T002_VISION_TARGET_IA.md`. **Recommends
  topic-based reorganization** over the current per-source-file boundaries:
  after Sprint 054 removed each monolith's CURRENT spine, the remaining
  files have ancestries rather than subjects, and four topics are each split
  across 3-4 files (execution runtime modes ×4, component promotion +
  fingerprints ×4, research-space bounding/planner observability ×3-4,
  superseded module/user_data layouts ×4). Proposed target tree: 10 flat
  topic files + a rewritten README (`PRODUCT_DIRECTION`, `TIME_MODEL_FUTURE`,
  `MARKET_DATA_FUTURE` ← renamed `DATA_MODULE_FUTURE`,
  `MARKET_ANALYSIS_FUTURE`, `MARKET_ANALYSIS_DECISIONS`,
  `RESEARCH_SPACE_AND_ANALYTICS`, `EXECUTION_RUNTIME_FUTURE`,
  `EVENT_SYSTEM_FUTURE`, `COMPONENT_PROMOTION_LIFECYCLE`,
  `RUN_IDENTITY_AND_CONFIGURATION`); all five monoliths dissolve. Also
  proposes evicting ~1,500 lines from the vision tier entirely (superseded
  module/user_data layout proposals, a closed Sprint-003 planning note, two
  tombstone sections). Ten new staleness findings (F1-F10), the most
  consequential being: `MARKET_ANALYSIS_WITH_DECISIONS.md` is ~70% a closed
  Sprint-003 planning note written in Polish with duplicated section
  numbering, its §17 "ADR required before implementation" gate closed ~50
  sprints ago, and its D-018/D-028/D-029 may be superseded by accepted
  ADR-MA-012/ADR-MA-014 despite `docs/adr/README.md` declaring the register
  authoritative (flagged as needing verification, not asserted). Six open
  questions raised for T004, including whether dissolving
  `docs/vision/ARCHITECTURE_FOUNDATIONS.md` is acceptable given it is a
  `product-architecture` pipeline-convention path. No `docs/vision/` file
  was moved, renamed, merged, split, or edited; `docs/reference/` untouched
  (owned by T001).

## 6. Outcome

TBD.

## 7. Follow-ups (explicitly not this sprint)

- Full sprint-doc archival backlog (still deferred from Sprint 053 Phase
  E) — this sprint mines sprint docs only where T003 finds a specific gap,
  it does not execute the archival policy against the existing 106 files.
- `.cursor/rules/project-architecture.mdc` trim (Sprint 053 T008, deferred
  to a Cursor-side maintainer session).
- Engineering fixes for the two `DATA_MODULE.md` findings (partitioning
  policy, continuous-futures roll/adjustment gap) — documentation-gap
  notes only here; the underlying code/decision work is tracked
  separately.
- Translating `docs/vision/`'s Market Analysis decision register
  (D-001–D-036) from Polish to English — new prose, out of Sprint 055's
  scope per D-S055-04 (raised by T002 finding F4).
