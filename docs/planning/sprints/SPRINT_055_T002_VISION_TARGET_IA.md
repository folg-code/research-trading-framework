# Sprint 055 T002 — `docs/vision/` Target Information Architecture (Proposal)

```text
Status: PROPOSED — requires maintainer approval at T004 (D-S055-03)
Task: Sprint 055 T002 (read-only audit)
Scope: docs/vision/ only. docs/reference/ is owned by T001 and was not touched.
Method: full read of all 7 current docs/vision/ files, cross-read against
        SPRINT_054 T001/T002/T003/T003b classification artifacts and
        docs/planning/DATA_MODULE_CLASSIFICATION.md, plus targeted checks
        against docs/adr/README.md and docs/adr/ADR-MA-*.
Nothing was moved, renamed, merged, split, or edited.
```

---

## 1. What is actually in `docs/vision/` today

7 files. Five are post-Sprint-054 remnants (their CURRENT sections already
moved to `docs/reference/`), one is a brand-new remnant, one was never
touched by Sprint 054.

| File | Approx. lines | Origin | State |
|---|---|---|---|
| `README.md` | 52 | index | Flat 3-group index; partly stale (§6) |
| `ARCHITECTURE_FOUNDATIONS.md` | 285 | S054 T001/T004 remnant | 6 orphan sections from 3 different chapters |
| `ARCHITECTURE_TECHNICAL.md` | 1,340 | S054 T002/T004 remnant | Still the largest file; spans 8 unrelated domains |
| `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` | 603 | S054 T003/T004 remnant | Spans market analysis + research methodology + layouts |
| `WORKFLOWS_AI_ADR.md` | 946 | S054 T003b/T006 remnant | Research + execution + 2 pure tombstone sections |
| `MARKET_ANALYSIS_WITH_DECISIONS.md` | 1,178 | **untouched by Sprint 054** | ~70% closed Sprint-003 planning note, ~30% binding decisions |
| `DATA_MODULE_FUTURE.md` | 1,004 | post-054 follow-up split | Best-annotated file in the folder |

---

## 2. Per-file assessment

### 2.1 `README.md`

- **Navigable?** Partially. Three groups ("Core Architecture", "Domain
  Design", "Process") and a one-line purpose per file. But the groups are
  organizational (which monolith) not topical, so "what's the plan for the
  Event System / for Replay Execution / for continuous-futures rolls" is
  not answerable from the index — every one of those spans 2-4 files.
- **Stale content:** see §6 findings F8.
- **Verdict:** rewrite as a topic-grouped context map (T006 implements).

### 2.2 `ARCHITECTURE_FOUNDATIONS.md`

- **Navigable?** No. What remains is six sections retaining their original
  numbering (§3, §4.10, §4.12, §5.5, §5.14, §6.5) from three chapters whose
  other subsections are gone. The numbering now signals nothing.
- **Overlap:** heavy.
  - §4.12 (component promotion lifecycle + fingerprints) duplicates
    `ARCHITECTURE_TECHNICAL.md` §5.12 and §6.4 and
    `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` §18 — four near-verbatim
    restatements of the same unbuilt `reproducibility_status` model.
  - §6.5 (Replay/Paper/Live runtime modes) duplicates
    `ARCHITECTURE_TECHNICAL.md` §7.3 and `WORKFLOWS_AI_ADR.md` §5.4, and is
    cross-referenced by `MULTITIMEFRAME…` §19 rule 23.
  - §4.10 (planner observability metadata) duplicates
    `WORKFLOWS_AI_ADR.md` §3.12 and overlaps
    `MULTITIMEFRAME…` §11.5.
- **Misplaced content:** §5.5 "Composition Over Inheritance" is a
  repo-wide *coding style convention*, not a future architecture — it is
  the same kind of rule that Sprint 054 T006b consolidated into
  `.cursor/rules/ARCHITECTURE_CONTROL.md`. §5.14 "Controlled Technology
  Adoption" is a *governance rule about when an ADR is required* — its
  natural home is `docs/adr/README.md`'s process section.
- **Verdict:** dissolve. No coherent residual subject.

### 2.3 `ARCHITECTURE_TECHNICAL.md`

- **Navigable?** No — and it is the worst case in the folder. 1,340 lines
  spanning Time Model, Market Data, Market Analysis, MA Engine, Model
  Composition, Execution, Event System, Configuration, Module Structure and
  User Data Structure. A reader after "what is the plan for holidays" must
  scan a document that also contains the Event System spec.
- **Overlap:** the highest in the folder.
  - §3.10 partitioning table ≈ `DATA_MODULE_FUTURE.md` §19 table.
  - §3.15 live-ingestion diagram ≈ `DATA_MODULE_FUTURE.md` §13.2 diagram.
  - §3.16 replay ≈ `DATA_MODULE_FUTURE.md` §17.
  - §3.3 provider/importer contracts ⊂ `DATA_MODULE_FUTURE.md` §24.
  - §3.9 storage layers ≈ `DATA_MODULE_FUTURE.md` §18.2.
  - §4.4 States ≈ `MULTITIMEFRAME…` §3.5.
  - §5.9 intrabar ≈ `MULTITIMEFRAME…` §8.5.
  - §5.12/§6.4 promotion+fingerprints ≈ `ARCHITECTURE_FOUNDATIONS.md`
    §4.12 ≈ `MULTITIMEFRAME…` §18.
  - §7.3 execution modes ≈ `ARCHITECTURE_FOUNDATIONS.md` §6.5 ≈
    `WORKFLOWS_AI_ADR.md` §5.4.
- **Content that is neither current nor future:** §10 (Module Structure)
  and §11 (User Data Structure) are ~400 lines self-annotated as
  historical/illustrative and superseded by
  `docs/reference/system/MODULE_MAP.md`. They document a layout that was
  never built and will not be built.
- **Zero-value section:** §2.10 is a stub whose entire body says the rule
  list lives in the reference copy — an anchor with no content.
- **Coherent, genuinely-vision block:** §8 Event System (~145 lines,
  classified FUTURE in full, largest single unbuilt block found across all
  of Sprint 054). This is the one part of the file that stands alone.
- **Verdict:** dissolve into topic files; route §10/§11 out of `vision/`.

### 2.4 `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md`

- **Navigable?** No. The title promises multitimeframe/market-model
  architecture, but the post-054 remnant is dominated by *research
  methodology* (§13 staged research, §14.1–§14.6 automated analysis of
  large result spaces) — which is not what the filename advertises.
- **Overlap:** §3.5, §7.2, §8.5, §9 overlap `ARCHITECTURE_TECHNICAL.md`
  §4.4/§5.9; §11.5 overlaps `WORKFLOWS_AI_ADR.md` §3.12/§4.5; §17/§18 are
  the third and fourth copies of superseded module/user_data trees.
- **Internal defect (pre-existing, noted by T003, still unfixed):** §12's
  subsections are numbered §11.1/§11.2; §15's subsections are numbered
  §14.x. Section numbers cannot be used to navigate or cite this file.
- **Genuinely coherent block:** §13 + §14.x + §11.5 + §19 rules 17/18/20
  together form a complete "how research spaces are bounded, staged and
  screened" story — but that story is split across this file and
  `WORKFLOWS_AI_ADR.md` §3.12/§4.5/§4.13/§4.14/§4.18.
- **Verdict:** dissolve.

### 2.5 `WORKFLOWS_AI_ADR.md`

- **Navigable?** Partially — the §3 Signal Research / §4 Strategy Research
  / §5 Strategy Execution split is real and survives. But two of its eight
  top-level sections (§6 AI Agent Contract, §7 ADRs) are now pure
  tombstones: prose explaining that the content moved elsewhere, with no
  remaining content. They inflate the file and the title
  (`WORKFLOWS_AI_ADR`) now advertises two subjects the file no longer
  contains.
- **Overlap:** §5.4 execution modes (third copy); §3.12 planner telemetry
  (third copy); §4.9 replay-vs-backtest (second copy); §2.5 workflow
  identity overlaps `ARCHITECTURE_TECHNICAL.md` §9.10 configuration
  versioning almost field-for-field.
- **Internal contradiction (in-file, unresolved):** §4.20's suggested
  storage layout lists a `families/` directory that its own §4.14 confirms
  has zero code counterpart.
- **Verdict:** dissolve; execution content is a coherent topic file, the
  research content merges with `MULTITIMEFRAME…`'s research-methodology
  block.

### 2.6 `MARKET_ANALYSIS_WITH_DECISIONS.md` — the outlier

This file was never classified by Sprint 054 and is the least
tier-appropriate file in the folder.

- **It is a sprint planning note, not a vision document.** Its own H1 is
  `SPRINT 003 — Market Analysis Architecture and MVP Planning Note`.
  Roughly 815 of its 1,178 lines are Sprint-003 execution planning: Sprint
  Goal, Sprint Scope (In/Out), §15 Proposed Work Waves (Wave 0-6), §16/§20
  Definition of Ready, §17/§21 Definition of Done, §18 Main Risks, §13
  Technical Spike plan, §18 Entry Criteria, §19 Recommended PR Breakdown
  (PR 1-11). Sprint 003 closed ~50 sprints ago;
  `docs/planning/sprints/SPRINT_003.md`,
  `S003_WAVE0_ARCHITECTURE_CLOSURE.md` and `S003_WAVE0_SPIKE_REPORT.md`
  already exist and are the correct home for this material.
- **Only ~360 lines are durable:** §15 Decision Register (D-001–D-036),
  §16 Decisions Deferred Beyond Sprint 003, and §17 ADR Required Before
  Implementation. `docs/adr/README.md` explicitly declares D-001–D-036
  authoritative, so the register must survive.
- **Staleness / defects:** see F1-F5 in §6.
- **Verdict:** split. Register survives as its own file; the planning-note
  body leaves `docs/vision/`.

### 2.7 `DATA_MODULE_FUTURE.md`

- **Navigable?** The best of the seven. Every section carries a
  classification header, staleness annotations are explicit and dated, and
  the pointer back to `docs/planning/DATA_MODULE_CLASSIFICATION.md` works.
  Its section numbering is inherited from the source file and has gaps
  (§2, §5, §6, §9, §10, §13, §14, §17, §18.2, §19, §20.2, §21…), which is
  tolerable because the headers are self-describing.
- **Overlap:** with `ARCHITECTURE_TECHNICAL.md` §3.x (see §2.3) — the two
  files describe the same unbuilt market-data pipeline at two different
  levels of verification rigour (F6).
- **Content that is neither current nor future:** §26 (third copy of a
  superseded module tree), §29 (a Sprint-002-era "initial implementation
  scope" planning artifact, self-flagged partially stale).
- **Name:** `DATA_MODULE_FUTURE.md` encodes the *provenance* (it was split
  from `modules/DATA_MODULE.md`) rather than the subject.
- **Verdict:** keep as the nucleus of the market-data topic file, renamed,
  absorbing `ARCHITECTURE_TECHNICAL.md` §3.x.

---

## 3. Topic-based vs. per-source-file organization

**Recommendation: reorganize by topic.** Evidence, not preference:

1. **Every current boundary is a provenance boundary, not a subject
   boundary.** All five remnants descend from monoliths that each covered
   the *whole system* at a different altitude. After Sprint 054 removed
   their CURRENT spine, what remains in each is an unrelated set of
   leftovers — the files no longer have subjects, only ancestries.
2. **Four topics are each split across 3-4 files.** Counted in §2:
   execution runtime modes (4 files), component promotion + fingerprints
   (4), research-space bounding/planner observability (3-4), superseded
   module/user_data layouts (4). A reader answering "what's the plan for
   Replay Execution" today must open four files and reconcile four
   near-identical, independently-annotated restatements.
3. **The duplicates have already started to diverge in accuracy** — F6
   below is a live example where the same partitioning table carries a
   verified finding in one file and an unverified caveat in another. Left
   per-file, this divergence compounds every time someone verifies one copy.
4. **The reorganization is almost entirely verbatim moves.** Every section
   proposed for relocation is already an independently-headed, individually
   classified block, thanks to Sprint 054's work. This is not Sprint 054
   T007's rejected case (inventing `STRATEGY_EXECUTION.md`/`MARKET_DATA.md`
   from non-existent prose) — here the prose exists, in quadruplicate.
5. **Counter-evidence, honestly stated:** `WORKFLOWS_AI_ADR.md`'s
   §3/§4/§5 (Signal Research / Strategy Research / Strategy Execution) is
   a genuine subject split that survives Sprint 054, and
   `DATA_MODULE_FUTURE.md` is already effectively a topic file. The
   proposal below preserves both — the Strategy Execution block becomes a
   topic file nearly intact, and `DATA_MODULE_FUTURE.md` is renamed rather
   than rebuilt.

**Deduplication policy for the merges (needs T004 sign-off):** where N
copies of a topic exist, keep the *longest* copy verbatim as the body, and
append the other copies' unique material plus a provenance list
(`Merged from: ARCHITECTURE_FOUNDATIONS.md §6.5, ARCHITECTURE_TECHNICAL.md
§7.3, WORKFLOWS_AI_ADR.md §5.4`). Do not paraphrase or re-synthesize. Under
D-S055-04 the only newly-authored prose is each file's short header and the
provenance lists.

---

## 4. Proposed target tree

```text
docs/vision/
├── README.md                              REWRITE  (topic-grouped context map — T006)
├── PRODUCT_DIRECTION.md                   NEW
├── TIME_MODEL_FUTURE.md                   NEW
├── MARKET_DATA_FUTURE.md                  RENAME + MERGE (nucleus: DATA_MODULE_FUTURE.md)
├── MARKET_ANALYSIS_FUTURE.md              NEW
├── MARKET_ANALYSIS_DECISIONS.md           SPLIT out of MARKET_ANALYSIS_WITH_DECISIONS.md
├── RESEARCH_SPACE_AND_ANALYTICS.md        NEW
├── EXECUTION_RUNTIME_FUTURE.md            NEW
├── EVENT_SYSTEM_FUTURE.md                 NEW
├── COMPONENT_PROMOTION_LIFECYCLE.md       NEW
└── RUN_IDENTITY_AND_CONFIGURATION.md      NEW

dissolved (content fully relocated, files removed):
    ARCHITECTURE_FOUNDATIONS.md
    ARCHITECTURE_TECHNICAL.md
    MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md
    WORKFLOWS_AI_ADR.md
    MARKET_ANALYSIS_WITH_DECISIONS.md
    DATA_MODULE_FUTURE.md  (renamed → MARKET_DATA_FUTURE.md)

routed out of docs/vision/ (see §5 — each needs an explicit T004 decision):
    docs/historical/SUPERSEDED_LAYOUT_PROPOSALS.md      NEW
    docs/planning/sprints/S003_MARKET_ANALYSIS_PLANNING_NOTE.md   NEW (or delete)
```

10 content files + README, flat, no subfolders.

### 4.1 Rationale, one line per file

| Target file | Change | Sources | Rationale |
|---|---|---|---|
| `README.md` | rewrite | — | Current index groups by provenance; a topic-grouped map with a per-file maturity marker makes "what's the plan for X" a 1-lookup question (T006) |
| `PRODUCT_DIRECTION.md` | new | `ARCHITECTURE_FOUNDATIONS.md` §1, §3, §5.14; `WORKFLOWS_AI_ADR.md` §1, §8 | The only genuinely product-level, aspirational material (target asset classes, planned extensions, the three-capability contract) — currently orphaned inside two engineering documents |
| `TIME_MODEL_FUTURE.md` | new | `ARCHITECTURE_TECHNICAL.md` §2.1, §2.4, §2.5, §2.6 | Calendars/holidays/sessions are a distinct domain (`src/trading_framework/time/`) and are the stated precondition for missing-range detection — keeping them inside a market-data file would hide that dependency |
| `MARKET_DATA_FUTURE.md` | rename + merge | `DATA_MODULE_FUTURE.md` (whole, minus §26/§29); `ARCHITECTURE_TECHNICAL.md` §3.3, §3.5, §3.7, §3.9, §3.10, §3.15, §3.16 | Two files describe the same unbuilt market-data pipeline at different verification rigour (F6); name states the subject rather than the file it was split from |
| `MARKET_ANALYSIS_FUTURE.md` | new | `ARCHITECTURE_TECHNICAL.md` §4.4, §5.9; `MULTITIMEFRAME…` §3.5, §7.2, §8.5, §9 | States taxonomy, intrabar contract and `ComponentRequest` shape are each duplicated across exactly these two files; one home ends the divergence |
| `MARKET_ANALYSIS_DECISIONS.md` | split | `MARKET_ANALYSIS_WITH_DECISIONS.md` §15 Decision Register, §16 Deferred | `docs/adr/README.md` declares D-001–D-036 authoritative, so the register stays in `vision/`; separating it from the closed sprint-003 planning note makes that authority findable |
| `RESEARCH_SPACE_AND_ANALYTICS.md` | new | `ARCHITECTURE_FOUNDATIONS.md` §4.10; `MULTITIMEFRAME…` §11.1, §11.2, §11.5, §13, §14.1, §14.2, §14.4, §14.5, §14.6, §19 rules 17/18/20; `WORKFLOWS_AI_ADR.md` §3.12, §3.14, §4.5, §4.13, §4.14, §4.18 | Bounded search spaces → staged research → automated screening → multi-objective selection is one continuous argument currently split across three files and buried under a "multitimeframe" filename |
| `EXECUTION_RUNTIME_FUTURE.md` | new | `ARCHITECTURE_FOUNDATIONS.md` §6.5; `ARCHITECTURE_TECHNICAL.md` §7.3, §9.9; `WORKFLOWS_AI_ADR.md` §4.9, §5.1, §5.4, §5.7, §5.8, §5.11, §5.12, §5.13, §5.15, §5.16; `MULTITIMEFRAME…` §19 rule 23 | Replay/Paper/Live is stated four times in four files; broker abstraction, reconciliation and recovery (all confirmed zero-code) only make sense next to it |
| `EVENT_SYSTEM_FUTURE.md` | new | `ARCHITECTURE_TECHNICAL.md` §8 (all), §10.10; `WORKFLOWS_AI_ADR.md` §5.6 | The largest single fully-unbuilt block in the repo (`events/` is an empty stub) and already self-contained — it deserves to be findable by name, not buried at §8 of a 1,340-line file |
| `COMPONENT_PROMOTION_LIFECYCLE.md` | new | `ARCHITECTURE_FOUNDATIONS.md` §4.12; `ARCHITECTURE_TECHNICAL.md` §5.12, §6.4; `MULTITIMEFRAME…` §18 | Four near-verbatim restatements of the same unbuilt five-stage promotion + `reproducibility_status` model; one canonical statement, three provenance lines |
| `RUN_IDENTITY_AND_CONFIGURATION.md` | new | `ARCHITECTURE_TECHNICAL.md` §9.1, §9.2, §9.4, §9.6, §9.10; `WORKFLOWS_AI_ADR.md` §2.3, §2.5, §3.16, §4.3, §4.7, §4.10, §4.20, §4.21 | "What a run resolves, records and fingerprints" — config layering, workflow identity and execution assumptions are the same reproducibility question, currently answered in two files with overlapping field lists |

### 4.2 Files that stay put by name

None. `DATA_MODULE_FUTURE.md` is the only file whose *content* survives
intact, and only its name changes.

---

## 5. Content that should leave `docs/vision/` entirely

Each needs an explicit maintainer decision at T004 — these are removals
from the vision tier, not moves within it.

| Content | Approx. size | Why it isn't vision | Proposed destination |
|---|---|---|---|
| `ARCHITECTURE_TECHNICAL.md` §10 + §11; `MULTITIMEFRAME…` §17 + §18; `DATA_MODULE_FUTURE.md` §26; `WORKFLOWS_AI_ADR.md` §3.16 + §4.20 layouts | ~600 lines total | All six self-annotate as superseded by `docs/reference/system/MODULE_MAP.md`. They describe a layout that was never built *and is not planned* — neither current (reference) nor intended (vision) | `docs/historical/SUPERSEDED_LAYOUT_PROPOSALS.md`, or delete (git history preserves them). Maintainer's call |
| `MARKET_ANALYSIS_WITH_DECISIONS.md` §1-§14, §15 Waves, §16-§21 | ~815 lines | A closed Sprint-003 planning note (goal, scope, waves, DoR/DoD, PR breakdown, risks, entry criteria) living in the vision tier | `docs/planning/sprints/S003_MARKET_ANALYSIS_PLANNING_NOTE.md`, or delete given `SPRINT_003.md` + `S003_WAVE0_*` already exist |
| `DATA_MODULE_FUTURE.md` §29 "Initial Implementation Scope" | ~65 lines | Same category: a Sprint-002-era increment plan, self-flagged partially stale | `docs/planning/` or delete |
| `ARCHITECTURE_FOUNDATIONS.md` §5.5 Composition Over Inheritance | ~25 lines | A repo-wide coding-style convention, not future architecture — same family as content Sprint 054 T006b consolidated into `.cursor/rules/ARCHITECTURE_CONTROL.md` | `.cursor/rules/ARCHITECTURE_CONTROL.md` (out of scope for T008 — flag for a Cursor-side pass) |
| `ARCHITECTURE_FOUNDATIONS.md` §5.14 Controlled Technology Adoption | ~15 lines | A governance rule about when a decision requires an ADR | `docs/adr/README.md` process section. Alternative: keep in `PRODUCT_DIRECTION.md` as a stated principle |
| `MARKET_ANALYSIS_WITH_DECISIONS.md` §17 "ADR Required Before Implementation" | ~20 lines | Fully satisfied — every listed ADR exists and is accepted (F1). Reads as pending work | Delete, or convert to a D→ADR cross-reference table inside `MARKET_ANALYSIS_DECISIONS.md` |
| `ARCHITECTURE_TECHNICAL.md` §2.10 | 7 lines | Content-free anchor stub | Delete |
| `WORKFLOWS_AI_ADR.md` §6 + §7 | ~35 lines | Pure tombstones — redirects to `AGENTS.md` and `docs/adr/README.md` with no remaining content | Record the two redirects as one line each in the rewritten `docs/vision/README.md`; delete the sections |

---

## 6. Newly-found staleness

Beyond what Sprint 054 and `DATA_MODULE_CLASSIFICATION.md` already flagged.

| # | Finding | Evidence | Severity |
|---|---|---|---|
| F1 | `MARKET_ANALYSIS_WITH_DECISIONS.md` §17 lists 11 ADRs "required before implementation" (ADR-MA-001…011). All 11 exist in `docs/adr/` as accepted, plus ADR-MA-012 and ADR-MA-014 beyond the list. The section reads as an open gate that closed ~50 sprints ago | `docs/adr/` file listing | Medium — misleads a fresh reader into thinking Market Analysis is pre-implementation |
| F2 | Same file: ~815 of 1,178 lines are a closed Sprint-003 planning note in the vision tier | File's own H1 and §14-§21 | High — tier mismatch, the largest single instance in `docs/vision/` |
| F3 | Same file: headings §15, §16, §17, §18, §19, §20 and §21 each appear **twice** (once in the planning-note half, once in the decision-register half). Section numbers cannot be used to cite or navigate this file | Lines 582-816 vs 816-1178 | Medium |
| F4 | Same file is written **in Polish**; every other file in `docs/` is English. `docs/adr/README.md` points at it as the authoritative home of D-001–D-036, so an English-reading contributor or agent is routed to a document they may not be able to use | Whole file | Medium — direct hit on this sprint's navigability goal |
| F5 | Same file: **candidate contradictions between the "authoritative" register and accepted ADRs.** D-029 states Sprint 003 does not implement multitimeframe and "MVP forces `source = computation = evaluation`", yet `ADR-MA-012-batch-multitimeframe-computation-with-polars.md` is accepted. D-018 (in-memory exact-match execution cache only) and D-028 (sequential executor, in-memory materialization) sit alongside `ADR-MA-014-marketframe-polars-committed-bulk-engine.md`. **Not fully verified** — assessed from ADR titles and the register text, not a full ADR read; T003 or T004 should confirm before annotating | `docs/adr/ADR-MA-012`, `ADR-MA-014` vs D-018/D-028/D-029 | High if confirmed — a document declared authoritative may be superseded in part |
| F6 | **Verified findings did not propagate between duplicate copies.** `DATA_MODULE_FUTURE.md` §19 carries a verified divergence note (actual partition key is `session_date=<date>`, no `year=`/`month=` partitioning exists). The near-identical table in `ARCHITECTURE_TECHNICAL.md` §3.10 carries only an "AMBIGUOUS / not verified against partition-writer code" caveat. Same content, two confidence levels, one of them now known to be wrong | Both tables | Medium — and it is the concrete cost of the duplication argued in §3 |
| F7 | `WORKFLOWS_AI_ADR.md` §4.20's suggested storage layout includes `families/`, which its own §4.14 confirms has zero code counterpart. Flagged in-file but left unresolved | §4.14 vs §4.20 | Low |
| F8 | `docs/vision/README.md` is post-054-stale in three ways: (a) it still labels `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` "(future)" — the exact label Sprint 054 T003 found inaccurate — with no note that the file is now a remnant; (b) it describes `MARKET_ANALYSIS_WITH_DECISIONS.md` purely as "Market Analysis decisions D-001–D-036", concealing F2; (c) it carries no note that five of its six content files are deliberate Sprint-054 remnants, so a fresh reader cannot tell why the files are shaped as they are | `docs/vision/README.md` lines 16-27 | Medium |
| F9 | Three "suggested module tree" sections and four "user_data layout" sections across four files, all self-annotated as superseded by `MODULE_MAP.md` (~600 lines of content that is neither current nor intended) | §5 table row 1 | Medium — pure navigational noise |
| F10 | `ARCHITECTURE_TECHNICAL.md` §2.10 is a heading plus a note saying the content lives in the reference copy — a section with no content | Lines 223-228 | Low |

---

## 7. Does `docs/vision/` need a context map beyond the flat README?

**Yes, but a single lightweight one — no per-folder indexes.**

- Ten content files in one flat folder is under the threshold that
  justifies subfolders; adding `vision/system/`, `vision/modules/` etc.
  would mirror `docs/reference/`'s shape without `docs/reference/`'s
  20-file pressure, and would re-introduce provenance-shaped grouping.
- What the current README lacks is not depth but **two columns**: subject
  grouping, and a maturity marker.

Suggested shape for T006 (implementation detail, not binding here):

```text
docs/vision/README.md
  ├── How to read these documents (intent vs. as-built; pointer to reference/)
  ├── Direction and principles      → PRODUCT_DIRECTION.md
  ├── Domain target architecture    → TIME_MODEL_FUTURE, MARKET_DATA_FUTURE,
  │                                    MARKET_ANALYSIS_FUTURE, MARKET_ANALYSIS_DECISIONS
  ├── Research and execution        → RESEARCH_SPACE_AND_ANALYTICS,
  │                                    EXECUTION_RUNTIME_FUTURE
  ├── Cross-cutting capabilities    → EVENT_SYSTEM_FUTURE,
  │                                    COMPONENT_PROMOTION_LIFECYCLE,
  │                                    RUN_IDENTITY_AND_CONFIGURATION
  └── Redirects (content that left vision/)
        AI Agent Contract    → AGENTS.md / .cursor/rules/ARCHITECTURE_CONTROL.md
        ADR process          → docs/adr/README.md
        Workspace/derived    → docs/reference/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md
        Superseded layouts   → docs/historical/ (or removed)
```

Per file, three fields: **subject** (one line), **maturity**
(`FUTURE` / `MIXED` / `BINDING DECISIONS`), **verified against code as of**
(sprint). The third field is what makes the T010 blind-navigation check
pass — it is the question every reader of a vision file actually has.

The redirect block is load-bearing: dissolving five filenames that are
referenced from `AGENTS.md`, `docs/adr/`, `.cursor/rules/` and ~30 sprint
docs means the README must answer "where did `ARCHITECTURE_TECHNICAL.md`
go?" without a git-log archaeology session.

---

## 8. Open questions for T004

1. **`docs/vision/ARCHITECTURE_FOUNDATIONS.md` is a pipeline-convention
   path.** The `product-architecture` skill treats it (and
   `docs/vision/PRODUCT_VISION.md`, `docs/vision/DOMAIN_MODEL.md`) as
   canonical filenames. This proposal dissolves it. Options: (a) accept the
   divergence — the current-state half already lives at
   `docs/reference/system/ARCHITECTURE_FOUNDATIONS.md`; (b) name the new
   direction file `ARCHITECTURE_FOUNDATIONS.md` instead of
   `PRODUCT_DIRECTION.md` to preserve the convention. **Maintainer's call.**
2. **Neither `PRODUCT_VISION.md` nor `DOMAIN_MODEL.md` exists in this
   repo.** `PRODUCT_DIRECTION.md` would partially fill the first. Whether
   the gap matters is a T003 question (documentation gap vs. deliberate
   omission), not something T002 should decide.
3. **F5 needs verification before T008** — if D-018/D-028/D-029 are
   genuinely superseded by ADR-MA-012/014, `MARKET_ANALYSIS_DECISIONS.md`
   needs per-decision status annotations, which is newly-authored content
   requiring explicit D-S055-04 approval.
4. **Polish → English translation of the decision register (F4)** is
   arguably in scope for this sprint's navigability goal but is
   unambiguously new prose. Recommend: **out of scope**, log as a
   follow-up. Flagging here so the omission is deliberate.
5. **Destination for the §5 evictions** — `docs/historical/` vs. delete.
   `docs/historical/` already exists (`REPO_WORKFLOW_DOCS_AUDIT.md`), so
   the tier is available; deletion is defensible since git preserves
   everything and nothing links to the superseded trees except the
   annotations themselves.
6. **File-count sanity check:** `TIME_MODEL_FUTURE.md` (~90 lines) is the
   smallest proposed file. If the maintainer prefers fewer files, folding
   it into `MARKET_DATA_FUTURE.md` as a "Time Model prerequisites" section
   is the cheapest merge — flagged rather than pre-decided.

---

## 9. What T008 would execute (if approved)

Rough shape, for sizing only — PR boundaries are the executing agent's
call per `git-workflow`:

1. Evictions first (§5) — `git mv` out of `docs/vision/`, no content edits.
2. `git mv DATA_MODULE_FUTURE.md MARKET_DATA_FUTURE.md` + absorb
   `ARCHITECTURE_TECHNICAL.md` §3.x.
3. Split `MARKET_ANALYSIS_WITH_DECISIONS.md` into the register file and
   the evicted planning note.
4. Build the seven new topic files by verbatim section moves + provenance
   headers.
5. Delete the five emptied monoliths.
6. README rewrite is T006, inbound references are T009.

Every step is a move of already-headed, already-classified blocks. The
only newly-authored prose is per-file headers and provenance lists — which
D-S055-04 requires be flagged as such in the PR description.

---

```text
STATUS: Proposed — requires your approval
What exactly needs confirmation: the target `docs/vision/` tree in §4
  (10 topic files replacing 6 provenance-shaped ones), the evictions in §5,
  and the six open questions in §8 — reviewed together with T001/T003 at
  the T004 gate.
What happens once approved: T006 (vision context map) and T008 (execute
  the vision target IA) become unblocked; no `docs/vision/` file is touched
  before then, per D-S055-03.
```
