# Sprint 054 — Vision Reclassification and Reference Layering (Phase 6b + 10a)

## Metadata

```text
Sprint: 054
Phase: Cross-cutting docs architecture — not part of the Phase 15 predictive
       research track (Sprint 052 / Phase 15B is unaffected).
Status: IN PROGRESS — approved by maintainer, opened 2026-09-03.
Planned Start: 2026-09-03
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: Sprint 053 (repo workflow & docs hygiene) — closed on `main`
            (#418). This sprint picks up the two items Sprint 053
            deliberately deferred as "larger than a single reviewable
            change": Phase 6b (vision file reclassification) and Phase 10a
            (docs/reference/ layering), both from
            docs/historical/REPO_WORKFLOW_DOCS_AUDIT.md.
Depended On By: None known.
Sprint Branch: sprint/vision-and-reference-reclassification
Task branch convention: feat/ | fix/ | docs/ | test/ | refactor/
PR base: sprint/vision-and-reference-reclassification (never main until
         sprint integration)
Architecture Sources:
  - docs/historical/REPO_WORKFLOW_DOCS_AUDIT.md, Phase 6a/6b/10a — AUTHORITATIVE
    for this sprint's findings, sequencing, and evidence base
  - docs/vision/README.md — current vision-folder taxonomy and precedence rules
  - docs/reference/README.md — current reference-folder index (flat, 12 files)
```

## 1. Goal

Turn the audit's two largest, explicitly-deferred recommendations into
finished work: (a) confirm which parts of the 5 largest `docs/vision/` files
describe already-built behavior vs. genuinely future architecture, and (b)
give `docs/reference/` a layered navigation model (`system/` → `workflows/`
→ `modules/`) instead of its current flat 12-file list. Both require reading
large files in full before moving anything — this sprint is sequenced so
that reading and classifying happens before any file is split or moved.

## 2. Scope

**In scope**, sequenced per the audit's own Phase 10a recommendation (do not
reorder — step 4 depends on steps 1-3 settling content ownership first):

| # | Task | Audit ref | Size |
|---|---|---|---|
| T001 | Full read + current-vs-future section classification of `docs/vision/ARCHITECTURE_FOUNDATIONS.md` (1,557 lines). Produces a section-by-section table (current/future/mixed) as this sprint's Decisions output — no file is moved yet. | Phase 6b | Large (read-only) |
| T002 | Same for `docs/vision/ARCHITECTURE_TECHNICAL.md` (2,459 lines) | Phase 6b | Large (read-only) |
| T003 | Same for `docs/vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` (1,332 lines) — already known to contain at least one shipped-behavior section inside a file the vision index calls entirely future (line ~1308 per the audit) | Phase 6b | Large (read-only) |
| T003b | Classify `docs/vision/WORKFLOWS_AI_ADR.md` §1-5/§8 (~1,620 lines of workflow architecture) current-vs-future, same method as T001-T003. Added per the accepted T006 recommendation — this content turned out to be architecture, not process. | Phase 6b | Large (read-only) |
| T004 | Move each file's confirmed-current sections (per T001-T003) to `docs/reference/system/` (new); leave confirmed-future sections in `docs/vision/`; leave genuinely ambiguous sections in `docs/vision/` with a one-line "as-built status unclear, see ADR-XXXX" note rather than guessing | Phase 6b | Medium — depends on T001-T003 |
| T005 | Maintainer decision: does `docs/vision/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md` (1,102 lines, self-describes as "authoritative" — a reference-tier claim) move to `docs/reference/` wholesale? | Phase 6b | Decision + move if yes |
| T006 | ~~Maintainer decision: where does `docs/vision/WORKFLOWS_AI_ADR.md` belong~~ — **RESCOPED**: maintainer accepted the T006 recommendation's three-way split (see `SPRINT_054_T006_WORKFLOWS_AI_ADR_RECOMMENDATION.md`) instead of either original option. Split into T006a/T006b/T006c below. | Phase 6b | Decision made — see T006a-c |
| T006a | Reconcile `WORKFLOWS_AI_ADR.md` §7.1-7.5, §7.9, §7.10 (ADR process, statuses, template) and §7.6-7.8 (decision register) into `docs/adr/README.md`; resolve the status-model/template/reading-order contradictions the recommendation identified; drop the "suggested location" fossil. | Phase 6b | Medium — independent of T001-T004/T003b |
| T006b | Reconcile `WORKFLOWS_AI_ADR.md` §6 (AI Agent Contract, ~589 lines) into `AGENTS.md` / `.cursor/rules/ARCHITECTURE_CONTROL.md`, selectively (per the recommendation: most of §6.4-6.17 is duplication to delete, not copy; §6.7/§6.8/§6.19/§6.23 look like genuinely new material) | Phase 6b | Medium — independent of T001-T004/T003b |
| T006c | Move confirmed-current sections of §1-5/§8 (per T003b's classification) to `docs/reference/`, alongside T004's output; leave future/ambiguous parts in `vision/` per D-S054-02 | Phase 6b | Medium — depends on T003b |
| T007 | Content audit of all 12 current `docs/reference/` files (+ 3 in `modules/`): tag each file/section as system-level, workflow-level, module-level, or operational-runbook-level. Produces the actual split plan — not assumed from filenames. | Phase 6a | Large (read-only) |
| T008 | Execute the `docs/reference/` split into `system/` (`SYSTEM_OVERVIEW.md` new, `MODULE_MAP.md` moved, `DEPENDENCY_RULES.md` consolidated from `AGENTS.md`/`ARCHITECTURE_CONTROL.md`/`ARCHITECTURE_AND_WORKFLOWS.md` pointers), `workflows/` (`SIGNAL_RESEARCH.md`, `STRATEGY_RESEARCH.md`, `STRATEGY_EXECUTION.md`, `MARKET_DATA.md` — extracted per T007's plan, not the audit's untested guess), and `modules/` (existing 3 files plus any new ones T007 identifies as missing) | Phase 6a | Large — depends on T007 |
| T009 | Update every inbound reference to a moved/renamed file (`AGENTS.md`, `docs/README.md`, ADRs, sprint docs as applicable) | Phase 6a, 6b | Medium — mechanical once T004/T008 land |
| T010 | Phase F validation re-run (the 4 checks from Sprint 053, plus a 5th: "how does strategy execution work" should resolve via `docs/reference/workflows/STRATEGY_EXECUTION.md` in 1-2 lookups, not a flat-file guess) | Phase F | Small |

**Out of scope:**
- Rewriting the substance of any section — this sprint relocates and
  reclassifies content, it does not rewrite architecture decisions.
- Any change to `docs/adr/` — ADRs are immutable history and untouched here.
- Sprint-doc archival backlog (separate, already-deferred Sprint 053 item).

## 3. Decisions (Wave 0)

Binding decisions to confirm with the maintainer before opening task
branches — several of these cannot actually be pre-decided (that's the
point of T001-T003, T007) and are listed here as **decision gates**, not
answers:

- **D-S054-01 — Sequencing is mandatory.** T004 and T008 may not start
  before T001-T003 and T007 (respectively) are complete and reviewed. This
  mirrors the audit's own explicit warning: "splitting file organization
  before content ownership is settled would just move the ambiguity
  around."
- **D-S054-02 — Ambiguous sections stay put.** Where T001-T003 can't cleanly
  classify a section as current or future, the default is to leave it in
  `docs/vision/` with a status note, not to guess and move it. False
  negatives (future content miscategorized as current) are worse than
  leaving something in `vision/` a little longer.
- **D-S054-03 — T005/T006 are maintainer calls, not agent calls.** The
  audit explicitly declined to reclassify `ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md`
  or relocate `WORKFLOWS_AI_ADR.md` unilaterally. This sprint does the same
  — these two tasks produce a recommendation, then wait for sign-off before
  moving anything. **Resolved for T006 on 2026-09-03**: maintainer accepted
  the recommendation's three-way split (see
  `SPRINT_054_T006_WORKFLOWS_AI_ADR_RECOMMENDATION.md`); T006 is rescoped
  into T003b/T006a/T006b/T006c per §2 above.
- **D-S054-04 — This sprint is large; expect multiple waves.** Combined
  vision-file line count is ~9,000 lines across 5 files; `docs/reference/`
  is 15 files. Task branches should follow normal PR-size discipline (one
  coherent outcome per PR) even though the reading itself is unavoidably
  large — a single read-and-classify task is not the same PR as the move it
  produces.

## 4. Tasks

| ID | Task | Depends on | Status |
|---|---|---|---|
| T001 | Classify `ARCHITECTURE_FOUNDATIONS.md` sections | — | DONE |
| T002 | Classify `ARCHITECTURE_TECHNICAL.md` sections | — | DONE |
| T003 | Classify `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` sections | — | DONE |
| T003b | Classify `WORKFLOWS_AI_ADR.md` §1-5/§8 sections | — | DONE |
| T004 | Move confirmed-current sections to `docs/reference/system/` | T001, T002, T003 | DONE |
| T005 | Maintainer decision + move: `ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md` | — | DONE |
| T006 | Maintainer decision: `WORKFLOWS_AI_ADR.md` location | — | DECIDED — rescoped into T003b/T006a/T006b/T006c |
| T006a | Reconcile `WORKFLOWS_AI_ADR.md` §7 into `docs/adr/README.md` | — | DONE |
| T006b | Reconcile `WORKFLOWS_AI_ADR.md` §6 into `AGENTS.md`/`ARCHITECTURE_CONTROL.md` | — | TODO |
| T006c | Move confirmed-current §1-5/§8 sections to `docs/reference/` | T003b | TODO |
| T007 | Content audit of 12+3 `docs/reference/` files, produce split plan | — | DONE |
| T008 | Execute `docs/reference/` → `system/`/`workflows/`/`modules/` split | T007 | TODO |
| T009 | Update all inbound references | T004, T005, T006a-c, T008 | TODO |
| T010 | Phase F validation re-run (5 checks) | T001-T009 | TODO |

## 5. Progress

- 2026-09-03: Sprint opened on `sprint/vision-and-reference-reclassification`
  after maintainer approval. Starting with T001
  (`ARCHITECTURE_FOUNDATIONS.md` classification), per D-S054-01 sequencing.
- 2026-09-03: T001 complete (read-only). Produced
  `docs/planning/sprints/SPRINT_054_T001_ARCHITECTURE_FOUNDATIONS_CLASSIFICATION.md`
  — 27 CURRENT, 6 MIXED, 1 AMBIGUOUS, 0 pure FUTURE, 6 N/A (meta) sections/
  subsections. No section of `ARCHITECTURE_FOUNDATIONS.md` was moved or
  edited. Most consequential MIXED finding: §6.5 Execution Domain / §9 item 4
  — only `DRY_RUN` is a supported `ExecutionMode` in code today; Replay and
  Live Execution are named in the vision text but not yet implemented.
  §4.12's component-promotion lifecycle (`reproducibility_status`,
  five-stage promotion) has no code counterpart despite the underlying
  identity/versioning primitives being pervasive. PR: pending review before
  T004 (move) may start, per D-S054-01.
- 2026-09-03: T003 complete — full read + code-verified classification of
  `docs/vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` produced at
  `docs/planning/sprints/SPRINT_054_T003_MULTITIMEFRAME_MARKET_MODEL_CLASSIFICATION.md`.
  Confirms and extends the audit's line-1308 finding: the vision index's
  "(future)" label for this file is not accurate — §2–§10 are substantially
  CURRENT, while §14.4–§14.6 (sensitivity surfaces, Pareto/multi-objective
  scoring, complexity-penalty formula) are genuinely FUTURE with no code
  counterpart. No content moved (read-only per T003 scope); T004 gated on
  this classification being reviewed alongside T001/T002.
- 2026-09-03: T002 complete — full read + section classification of
  `docs/vision/ARCHITECTURE_TECHNICAL.md` (2,459 lines) produced in
  `docs/planning/sprints/SPRINT_054_T002_ARCHITECTURE_TECHNICAL_CLASSIFICATION.md`
  (37 CURRENT / 14 FUTURE / 32 MIXED / 10 AMBIGUOUS / 3 N/A-meta). Notable:
  the Event System (§8) is fully unbuilt (`events/` package is an empty
  stub); Replay/Live Execution modes remain unsupported
  (`execution/modes.py` only supports `DRY_RUN`), consistent with T001's
  independent finding for `ARCHITECTURE_FOUNDATIONS.md`; §10's suggested
  module layout has structurally diverged from the actual
  `src/trading_framework/` tree (per `docs/reference/MODULE_MAP.md`), which
  T004 will need to reconcile rather than move verbatim. No content in
  `ARCHITECTURE_TECHNICAL.md` was moved or edited.
- 2026-09-03: T007 complete (read-only). Full-text audit of all 15
  `docs/reference/` files (12 flat + 3 in `modules/`) produced
  `docs/planning/sprints/SPRINT_054_T007_REFERENCE_FOLDER_AUDIT.md` — a
  file-by-file tag table (system/workflow/module/operational-runbook) and a
  concrete split plan for T008. Confirms two of the audit's three guessed
  `system/` files (`SYSTEM_OVERVIEW.md` ← `ARCHITECTURE_AND_WORKFLOWS.md`,
  `MODULE_MAP.md` unchanged) and adds a fourth system file not in the
  original guess (`DATA_REPRESENTATION_AUDIT.md`, cross-cutting canonical
  type policy). Rejects the guessed `workflows/SIGNAL_RESEARCH.md` /
  `STRATEGY_RESEARCH.md` split — `RESEARCH_METHODOLOGIES.md` is one
  deliberately comparative document and moves wholesale instead. Rejects
  fabricating `workflows/MARKET_DATA.md` and `workflows/STRATEGY_EXECUTION.md`
  from existing content (no source text supports either as a standalone
  narrative without new prose, which is out of scope); proposes a new
  `docs/reference/runbooks/` tier for the three genuinely
  operational-runbook files (AWS/local BTC dry-run, live-paper pipeline
  inspection) instead. Identifies 4 more module-level files to add to
  `modules/` (`DASHBOARD_APPLICATION.md`, `OPERATOR_CLI.md`,
  `PREDICTIVE_PROMOTION.md`, `STRATEGY_AUTHORING.md`). Flags
  `modules/DATA_MODULE.md` as content-mismatched with its tier (reads as
  vision-tier target architecture, not as-implemented reference) — a
  maintainer decision candidate in the same family as T005/T006, left
  unmoved pending that decision. `system/DEPENDENCY_RULES.md` from the
  audit's guess is deferred entirely — it requires authoring new
  consolidated content from `AGENTS.md`/`ARCHITECTURE_CONTROL.md`, not a
  move of existing `docs/reference/` content, so it is out of T007/T008's
  scope. No `docs/reference/` file was moved, split, or edited. T008 may
  start once this plan is reviewed, per D-S054-01.

- 2026-09-03: T005 complete. Maintainer decided
  `docs/vision/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md` moves wholesale (no
  content rewrite) to `docs/reference/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md`
  via `git mv`, per D-S054-03. `docs/reference/system/` did not yet exist at
  move time (T004/T008 not yet landed), so the file was placed directly
  under `docs/reference/`. Updated `docs/vision/README.md` (removed from the
  vision index, added a pointer to the new location) and
  `docs/reference/README.md` (added to the navigation table). Updated
  inbound references in `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md`,
  `docs/adr/README.md`, `docs/adr/ADR-MA-007-analysis-workspace-and-derived-data.md`,
  and `.cursor/rules/documentation.mdc`. Left historical/closed-sprint
  references (`SPRINT_003.md`, `S003_WAVE0_ARCHITECTURE_CLOSURE.md`,
  `SPRINT_053.md`, `docs/historical/REPO_WORKFLOW_DOCS_AUDIT.md`) untouched
  as point-in-time records. No section content was edited (out of scope per
  this sprint).
- 2026-09-03: T004 complete. Created `docs/reference/system/` with three new
  files (`ARCHITECTURE_FOUNDATIONS.md`, `ARCHITECTURE_TECHNICAL.md`,
  `MULTITIMEFRAME_MARKET_MODEL.md`) holding the content classified CURRENT
  by T001-T003, reproduced verbatim with a top-of-file pointer back to the
  source vision doc and classification artifact. FUTURE sections were left
  untouched in `docs/vision/`. AMBIGUOUS sections were left in `docs/vision/`
  with a one-line as-built-status note per D-S054-02. MIXED sections were
  split at the sub-section grain the classification docs already flagged as
  clean (e.g. §4.12 promotion lifecycle, §6.5/§7.3 Runtime Modes, the whole
  Event System in `ARCHITECTURE_TECHNICAL.md` §8, §14.4-§14.6 in the
  multitimeframe doc); MIXED sections without a clean flagged split (notably
  `ARCHITECTURE_TECHNICAL.md`'s suggested Module Structure §10 and User Data
  Structure §11, which have diverged structurally from the actual
  `src/trading_framework/` tree) were left whole in `docs/vision/` with a
  pointer to `docs/reference/MODULE_MAP.md` for the authoritative layout,
  rather than attempted as risky per-bullet rewrites. `docs/reference/README.md`
  now lists the three new `system/` files. `docs/adr/` untouched; T005-T009
  intentionally out of scope for this task.
- 2026-09-03: T006 recommendation produced (not DONE — per D-S054-03 this
  is a maintainer call). `docs/vision/WORKFLOWS_AI_ADR.md` was read in full
  (2,584 lines). Output:
  `docs/planning/sprints/SPRINT_054_T006_WORKFLOWS_AI_ADR_RECOMMENDATION.md`.
  Nothing was moved, edited or rewritten. Headline: neither of the sprint
  doc's two options fits — the file is ~63% target workflow architecture
  (§1–§5, §8), not process, and is the most-cited architecture source in
  the sprint record (8 sprint docs, all citing §3/§4, none citing §6/§7).
  Recommendation is a three-way split: §1–§5/§8 join the T001–T004 vision-
  reclassification track (proposed new classification task T003b), §6 (AI
  Agent Contract) folds into `AGENTS.md`/`ARCHITECTURE_CONTROL.md`, §7
  process sections fold into `docs/adr/README.md`; §7.6–7.8 are decision
  content to reconcile against the ADR index, not process. Two live
  contradictions found: agent required-reading-order (§6.2 vs `AGENTS.md`)
  and ADR status model + template (§7.4/§7.5 vs `docs/adr/README.md`). T006
  remains open pending maintainer decision on this recommendation.
- 2026-09-03: Maintainer accepted the T006 recommendation's three-way
  split. `SPRINT_054.md` §2/§4 rescoped: T006 marked DECIDED and split
  into T003b (classify `WORKFLOWS_AI_ADR.md` §1-5/§8), T006a (reconcile §7
  into `docs/adr/README.md`), T006b (reconcile §6 into
  `AGENTS.md`/`ARCHITECTURE_CONTROL.md`), and T006c (move §1-5/§8's
  confirmed-current sections per T003b, depends on T003b). T003b/T006a/T006b
  are independent of each other and of T004; T006c depends on T003b.
- 2026-09-03: T003b complete (read-only). Full read + code-verified
  classification of `docs/vision/WORKFLOWS_AI_ADR.md` §1-5 and §8 (lines
  1-1577, 2542-2584; §6 AI Agent Contract and §7 ADR process explicitly out
  of scope, handled by T006b/T006a) produced at
  `docs/planning/sprints/SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md`
  (~34 CURRENT / 4 FUTURE / 19 MIXED / 3 AMBIGUOUS / 5 N/A-meta). Confirms
  the T006 recommendation's headline claim: Signal Research (§3) is
  essentially fully built (14 of 17 subsections CURRENT, several
  near-verbatim against `research/scope.py`'s `ResearchScope` enum and
  `strategy/signal_occurrence.py`). Strategy Execution (§5) is the most
  FUTURE-heavy part of the file — Broker Abstraction (§5.11), Reconciliation
  (§5.12) and Recovery (§5.13) have zero code counterpart, consistent with
  T001/T002's independent finding that only `ExecutionMode.DRY_RUN` is
  supported; the Order Lifecycle (§5.7) exists only as a narrower 3-state
  dry-run version of the vision doc's 8-state machine. Strategy Research
  (§4) has an asymmetry not previously documented: the "family"/bounded
  multi-dimension research-space machinery that is CURRENT for Signal
  Research (`family_planning.py`) has no counterpart for Strategy Research
  (§4.5, §4.14, §4.18 all independently found this gap). No content in
  `WORKFLOWS_AI_ADR.md` was moved or edited; T006c (the actual move) is
  gated on this classification being reviewed, per D-S054-01.
- 2026-09-03: T006a complete. Sampled ADR-0026/0028/0029 to verify actual
  ADR practice before choosing between the two competing status
  vocabularies/templates (per the recommendation's open question 3): all
  sampled ADRs use the uppercase `PROPOSED/ACCEPTED/DEPRECATED/SUPERSEDED`
  vocabulary already in `docs/adr/README.md` (never the mixed-case
  `Proposed/Accepted/Rejected/Deferred/Superseded/Deprecated` from
  `WORKFLOWS_AI_ADR.md` §7.4), and the lean `Status/Context/Decision/
  Consequences/References` template extended with two informally-recurring
  optional sections (`Alternatives Considered`, `Follow-up`) — never the
  richer 9-section §7.5 template. `docs/adr/README.md` now has a
  consolidated "Process" section (when an ADR is required, numbering/
  location, review, ownership — from §7.1-7.5/7.9/7.10), an updated Status
  Model that adds `PLANNED` as a fifth status (already used by ADR-0004/
  0009/0010/0030 in the index but previously undocumented), an updated
  Template section documenting the two optional sections, and a new "ADR
  Backlog" section carrying forward every §7.6-7.8 decision/deferred-item/
  trigger that has no `ACCEPTED` ADR yet (nothing dropped silently).
  Cross-referenced all 21 §7.6 "Accepted Decisions" against the ADR index:
  Modular Monolith, Market Analysis Domain, Market Analysis Taxonomy,
  Declarative Models, Signal Research Scope, SignalOccurrence Ownership,
  Market Analysis Engine, Dataset Lifecycle, Framework and User Space, UTC
  Policy and Historical Storage already have matching `ACCEPTED` ADRs
  (0001, 0005, 0006, 0012, 0011, ADR-MA-006, 0007, 0002, 0003, 0008) and
  were dropped as duplicates; Independent Capabilities and Research/
  Execution Separation map to already-`PLANNED` ADR-0004/0009; Working
  Fingerprints maps to already-`PLANNED` ADR-0010; the remaining six
  (Strategy Composition, Position Sizing, MarketFieldReference, Persistent
  Research Datasets, Hybrid Communication, Configuration Boundaries) plus
  all of §7.7's deferred items and §7.8's reconsideration triggers have no
  ADR number yet and were moved verbatim into the new ADR Backlog section.
  `WORKFLOWS_AI_ADR.md` §7.1-7.10 replaced with a short pointer note to
  `docs/adr/README.md`; §1-§6 and §8 untouched (out of scope, per T003b/
  T006b/T006c). No file under `docs/adr/` (the ADR files themselves) was
  touched.

## 6. Outcome

TBD.

## 7. Follow-ups (explicitly not this sprint)

- Any full ADR supersession pass triggered by findings in T001-T003 (e.g. if
  a vision section turns out to contradict an existing ADR rather than just
  predate it) — flag as a new ADR or problem-registry item, don't resolve
  inline.
- Sprint-doc archival backlog (still deferred from Sprint 053).
