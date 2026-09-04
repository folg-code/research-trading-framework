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
  **Correction (T003, see G-03b):** neither finding is in fact tracked in
  either register today; T003 found the partitioning question already
  settled by ACCEPTED ADR-0014/ADR-0018 (no entry needed) and flagged that
  the continuous-futures scope limit would justify a `TECHNICAL_DEBT.md`
  entry that does not exist. Both are maintainer referrals, not work items
  for this sprint.
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
| T003 | Targeted gap cross-check against planning docs | — | DONE |
| T004 | Maintainer review gate — approve combined target IA | T001, T002, T003 | DONE |
| T005 | Add context-map indexes to `docs/reference/` subfolders | T004 | TODO |
| T006 | Add context-map index to `docs/vision/` | T004 | TODO |
| T007 | Execute `docs/reference/` target IA | T004 | DONE |
| T008 | Execute `docs/vision/` target IA | T004 | DONE |
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
- 2026-09-04: T003 complete (read-only). Targeted cross-check of
  `docs/reference/` + `docs/vision/` content against `PROBLEM_REGISTRY.md`,
  `TECHNICAL_DEBT.md`, `ROADMAP.md` (all three in full) and
  `docs/adr/README.md`'s index produced
  `docs/planning/sprints/SPRINT_055_T003_PLANNING_CROSS_CHECK.md`. **23
  gaps (G-01..G-23): 5 HIGH, 11 MEDIUM, 7 LOW.** D-S055-02 honoured — no
  exhaustive sprint-doc mining; three ADR files (0008, 0014, 0018) and
  `DATA_MODULE_CLASSIFICATION.md` were opened because named gaps pointed
  at them, and the output recommends against exhaustive mining.

  Resolution of the three named follow-ups:
  - **Partitioning policy (G-01, HIGH)** — not an open divergence.
    ADR-0014 (day partitions) and ADR-0018 (`session_date` partitions,
    which itself records the divergence from Sprint 011's `day=` layout)
    are both ACCEPTED, and `ROADMAP.md` §6 already states the rule.
    `DATA_MODULE_FUTURE.md` §19.4's note mis-frames a settled decision as
    awaiting a maintainer call, and under-describes the real picture:
    `paths.py` has **three** coexisting layouts (unpartitioned
    `bars.parquet`, `session_date=`, legacy `day=`), none month-based.
  - **Continuous-futures roll/adjustment (G-02, HIGH)** — a deliberate
    ADR-0018 MVP scope (`price_adjustment = none`; "MVP limited to NQ
    trades / volume roll / no back-adjust"; back-adjusted series named as
    a separate future artifact), not an untracked gap.
    `DATA_MODULE_FUTURE.md` §21.3's note cites the Sprint 054
    classification doc but **not ADR-0018**, the actual decision source.
  - **PRB-020 (G-03, MEDIUM)** — `docs/vision/WORKFLOWS_AI_ADR.md` is
    correct: §4.5, §4.14 and §3.12 all carry Sprint 054 classification
    notes and do **not** present the gap as solved. Two residual issues:
    neither doc tree cites `PRB-020` by ID (zero grep hits), and
    `docs/reference/system/WORKFLOWS_ARCHITECTURE.md` lines 816 and 834
    still reference Strategy-Research "family analyses"/"strategy family"
    unqualified. The `experiments:` YAML at lines 284-301 is under
    *Signal* Research and is correctly backed by `FamilyExperimentPlan` —
    it must not be "fixed".

  Also surfaced for the maintainer, outside this sprint's scope: **G-14 —
  `ROADMAP.md` carries no document-level `Status:` field** (only §14 is
  marked ACCEPTED), which the `governance` skill treats as a precondition
  for opening a sprint and therefore bears on T004 itself; and G-15 —
  `ROADMAP.md` labels Phase 2B both COMPLETE (§3) and PLANNED (§6), so
  T001/T002 must not use §6 as the authority for build status. Highest
  new finding: **G-04** — the executor does not enforce inference-time
  `available_at` rejection (verified in Sprint 049, ADR-0030 PLANNED),
  but the Market Analysis reference docs read as though it does.
- 2026-09-04: T004 complete. Maintainer decided directly (not agent-inferred)
  on all T001-T003 proposals — full record in
  `docs/planning/sprints/SPRINT_055_T004_DECISIONS.md`. Headline: the
  9-file `system/` re-cut, all 4 reversed `workflows/` extractions, the
  `DATA_REPRESENTATION_AUDIT.md` split, and the 10-file `vision/` topic
  reorganization are all **APPROVED**. Evictions go to `docs/historical/`,
  not deletion. `PRODUCT_DIRECTION.md` accepted as the vision-tier name
  (diverging from the `product-architecture` skill's `ARCHITECTURE_FOUNDATIONS.md`
  convention, since the as-built half already owns that name in
  `docs/reference/`). G-14 (`ROADMAP.md` missing a document-level
  `Status:` field) resolved directly in this commit —
  `docs/planning/ROADMAP.md` now states `Status: ACCEPTED`. G-04, G-01/G-02,
  and G-03 are assigned to T007/T008 as flagged, verbatim-discipline fixes
  (not rewrites); F5 (possible D-018/D-028/D-029 vs ADR-MA-012/014
  contradiction) must be verified before `MARKET_ANALYSIS_DECISIONS.md` is
  finalized in T008. The remaining 14 T003 gaps (G-05 through G-13,
  G-15 through G-23) are explicitly deferred past this sprint. T005-T008
  are now unblocked per D-S055-03.
- 2026-09-04: T007 complete (executed across a resumed session after an
  earlier rate-limit checkpoint). `docs/reference/` now matches the
  approved target tree: `system/` re-cut into 9 subject-based files
  (`DOMAIN_MODEL.md`, `ARCHITECTURE_PRINCIPLES.md` from the former
  `ARCHITECTURE_FOUNDATIONS.md`; `MARKET_ANALYSIS_ARCHITECTURE.md`,
  `TIME_AND_ALIGNMENT.md` merged from the former `ARCHITECTURE_TECHNICAL.md`
  + `MULTITIMEFRAME_MARKET_MODEL.md`, both retired; `DATA_REPRESENTATION_POLICY.md`
  split from the former `DATA_REPRESENTATION_AUDIT.md` §4/§5.2/§5.3, whose
  point-in-time audit half now lives at
  `docs/planning/sprints/SPRINT_036_DATA_REPRESENTATION_AUDIT.md`;
  `ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md` moved up from the `docs/reference/`
  root). `workflows/` gained `SIGNAL_RESEARCH.md`, `STRATEGY_RESEARCH.md`,
  `STRATEGY_EXECUTION.md` (extracted from the retired
  `system/WORKFLOWS_ARCHITECTURE.md`) and `MARKET_DATA.md` (extracted from
  the retired `modules/DATA_MODULE.md` plus `SYSTEM_OVERVIEW.md` §3's Import
  Paths table). `modules/` gained `ANALYSIS_COMPONENT_CATALOG.md` and
  `STRATEGY_EXAMPLES.md` (both extracted/merged from `STRATEGY_AUTHORING.md`,
  now trimmed to ~200 lines). Fixed G-04 (new note in
  `MARKET_ANALYSIS_ARCHITECTURE.md`/`TIME_AND_ALIGNMENT.md` on the
  executor's inference-time `available_at` gap, citing ADR-0030 and
  `ROADMAP.md` §13F) and G-03 (qualified the two residual "family"
  references in `workflows/STRATEGY_RESEARCH.md`/`STRATEGY_EXECUTION.md`
  with PRB-020 citations). Opportunistically fixed `MARKET_ANALYSIS_MODULE.md`'s
  broken `../adr/` links and stale MVP Components table (T001 §6). Left
  explicit TODO markers (not guesses) on the two tier-inversion citations
  into `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md`
  (`system/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md`,
  `modules/MARKET_ANALYSIS_MODULE.md`) pending T008's parallel `docs/vision/`
  reorg. `docs/reference/README.md` rewritten for the final tree. One
  judgment call flagged for review: several sections of the two retired
  `system/` provenance files (`ARCHITECTURE_TECHNICAL.md`'s "Market Data
  Architecture", "Model Composition Architecture", "Research and Strategy
  Execution Boundaries", "Configuration Architecture", "Module Structure",
  "Tests Structure", "Final Technical Architecture Rules";
  `MULTITIMEFRAME_MARKET_MODEL.md`'s "Core Decision", "Boundary Between
  Market Analysis and Strategy", "Market Model Definition", "Family
  Analysis", "Multiple Testing", "Research Result Architecture") were not
  individually re-homed — they were judged, consistent with T001 §2.2's own
  finding that these two files uniquely own only 4 subjects, to duplicate
  content already present in `DOMAIN_MODEL.md`, `MODULE_MAP.md`,
  `SYSTEM_OVERVIEW.md`, or the new `workflows/SIGNAL_RESEARCH.md`. Not
  independently re-verified section-by-section against every claim; worth a
  spot-check by the `tester`/`reviewer` pass.

- 2026-09-04: T008 complete on the `docs/execute-vision-target-ia` working
  branch (branched from `sprint/documentation-architecture-rebuild`). Executed
  the T004-approved `docs/vision/` target IA: `PRODUCT_DIRECTION.md`,
  `TIME_MODEL_FUTURE.md`, and the `DATA_MODULE_FUTURE.md` →
  `MARKET_DATA_FUTURE.md` rename + `ARCHITECTURE_TECHNICAL.md` §3.x merge
  (all three from an earlier checkpoint commit); then, in this pass, created
  the remaining 7 topic files (`MARKET_ANALYSIS_FUTURE.md`,
  `MARKET_ANALYSIS_DECISIONS.md`, `RESEARCH_SPACE_AND_ANALYTICS.md`,
  `EXECUTION_RUNTIME_FUTURE.md`, `EVENT_SYSTEM_FUTURE.md`,
  `COMPONENT_PROMOTION_LIFECYCLE.md`, `RUN_IDENTITY_AND_CONFIGURATION.md`)
  by verbatim section moves plus provenance headers, evicted ~600 lines of
  superseded module/`user_data/` layout proposals (+ two Cursor/ADR-pending
  sections) to `docs/historical/SUPERSEDED_LAYOUT_PROPOSALS.md`, and deleted
  the 5 emptied monoliths after verifying every section was accounted for.
  **F5 verified**: read `ADR-MA-012` and `ADR-MA-014` in full — D-029 (no
  multitimeframe in Sprint 003) is confirmed superseded by `ADR-MA-012`
  (annotated in `MARKET_ANALYSIS_DECISIONS.md`, flagged as new prose per
  D-S055-04); D-018 and D-028 are **not** confirmed superseded (additional
  cache layers and a future-authorized-but-unimplemented bulk engine do not
  contradict their in-memory/sequential claims) — no annotation added, per
  T004's "only if confirmed" instruction. G-01/G-02 citation fixes
  (partitioning and continuous-futures framing → ADR-0008/0014/0018) were
  already present in `MARKET_DATA_FUTURE.md` from the earlier checkpoint.
  The closed Sprint-003 planning-note body was **not** duplicated into a new
  `docs/planning/sprints/` file — `SPRINT_003.md` and
  `S003_WAVE0_ARCHITECTURE_CLOSURE.md` already cover the same goal/scope/
  waves/DoR/DoD content in English, near-identically. `docs/vision/README.md`
  was replaced with a minimal working index (updated links + a redirects
  table) rather than left broken, deferring the full topic-grouped context
  map with maturity markers to T006. `docs/reference/` untouched (owned by
  T007, running in parallel). No PR opened yet — per the task instructions,
  work was pushed directly to `docs/execute-vision-target-ia` for review.

## 6. Outcome

T001-T004, T008 complete. T005, T006, T007, T009, T010 remain open.

## 7. Follow-ups (explicitly not this sprint)

- Full sprint-doc archival backlog (still deferred from Sprint 053 Phase
  E) — this sprint mines sprint docs only where T003 finds a specific gap,
  it does not execute the archival policy against the existing 106 files.
  **T003 note:** several sprint-scoped artifacts
  (`SPRINT_054_T003b_...`, `DATA_MODULE_CLASSIFICATION.md`,
  `S049_AVAILABILITY_FINDING.md`, `S051_BTC_DATA_INVENTORY.md`) are cited
  from `docs/reference/`/`docs/vision/`/`ROADMAP.md` as sources of truth;
  archiving them would break those citations.
- `.cursor/rules/project-architecture.mdc` trim (Sprint 053 T008, deferred
  to a Cursor-side maintainer session).
- Engineering fixes for the two `DATA_MODULE.md` findings (partitioning
  policy, continuous-futures roll/adjustment gap) — documentation-gap
  notes only here; the underlying code/decision work is tracked
  separately. **T003 correction:** per G-01/G-02 both are already settled
  by ACCEPTED ADRs, so no engineering fix is outstanding — what remains is
  a doc-citation correction (T007/T008) plus an optional
  `TECHNICAL_DEBT.md` entry for the continuous-futures scope limit, which
  is a maintainer decision.
- Translating `docs/vision/`'s Market Analysis decision register
  (D-001–D-036) from Polish to English — new prose, out of Sprint 055's
  scope per D-S055-04 (raised by T002 finding F4).
