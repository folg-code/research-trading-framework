# Sprint 054 T007 — `docs/reference/` Content Audit and Split Plan

```text
Sprint: 054 (Vision Reclassification and Reference Layering, Phase 6a)
Task: T007 — Content audit of all 12 current docs/reference/ files (+3 in
      modules/): tag each file/section as system-level, workflow-level,
      module-level, or operational-runbook-level. Produce the actual split
      plan, not the audit's untested guess.
Scope: READ-ONLY. No docs/reference/ file was moved, renamed, split, or
       edited while producing this document (D-S054-01). T008 executes the
       plan below in a later, reviewed task.
Method: Full read of every file (all 15), in full, no sampling. Line counts
        verified against `wc -l`. Directory listing verified against
        `docs/reference/README.md`'s own index.
```

## 0. Inventory confirmed

`docs/reference/README.md` claims "flat 12 files" plus a 3-file
`modules/` index. A `Glob` of `docs/reference/**/*.md` on this branch
confirms exactly that — 12 files directly under `docs/reference/` (including
`README.md` itself) and 3 under `docs/reference/modules/`, 15 total,
7,850 lines combined:

| File | Lines |
|---|---:|
| `ARCHITECTURE_AND_WORKFLOWS.md` | 929 |
| `AWS_BTC_FUTURES_DRY_RUN.md` | 506 |
| `DASHBOARD_APPLICATION.md` | 89 |
| `DATA_REPRESENTATION_AUDIT.md` | 1,069 |
| `LIVE_PAPER_PIPELINE_INSPECTION.md` | 84 |
| `LOCAL_BTC_FUTURES_DRY_RUN.md` | 106 |
| `MODULE_MAP.md` | 841 |
| `OPERATOR_CLI.md` | 297 |
| `PREDICTIVE_PROMOTION.md` | 355 |
| `README.md` | 40 |
| `RESEARCH_METHODOLOGIES.md` | 800 |
| `STRATEGY_AUTHORING.md` | 825 |
| `modules/DATA_MODULE.md` | 1,673 |
| `modules/MARKET_ANALYSIS_MODULE.md` | 174 |
| `modules/MODEL_AUTHORING.md` | 62 |

No `docs/reference/system/` directory exists on this branch. Per the task
brief, T004 (moving confirmed-current vision sections into `system/`) may be
landing concurrently on a different branch — if/when it merges, it is out of
scope for this audit; nothing in this document assumes its contents.

---

## 1. Methodology

For each file: read it in full (not sampled), then answered three
questions per the task brief's four tags:

1. **Scope of the content** — does it describe the *whole system*
   (cross-cutting, multiple modules/workflows at once), *one workflow*
   end-to-end (a research methodology or an operational process spanning
   several modules), *one component/module in isolation*, or *how to
   run/operate something*?
2. **Does the file mix levels?** Several files are single-purpose end to
   end (e.g. `MODULE_MAP.md` is system-level throughout); a few genuinely
   mix (e.g. `LIVE_PAPER_PIPELINE_INSPECTION.md` mixes an architecture
   verdict with an operator checklist). Mixed files are noted as such
   rather than forced into one tag.
3. **Does the audit's guessed destination fit the actual content**, or does
   moving/splitting the file that way create a false workflow-level
   narrative that doesn't exist in the source text (i.e. would T008 have to
   *write new prose* to make the guessed split file coherent, which is out
   of this sprint's scope — "relocates and reclassifies content, does not
   rewrite architecture decisions")?

No file was edited. No section was moved. No new file was created except
this one.

---

## 2. File-by-file tagging

| File | Primary tag | Secondary tag | Notes |
|---|---|---|---|
| `README.md` | navigation index | — | Not content; becomes the top-level index for the new tree in T008. |
| `ARCHITECTURE_AND_WORKFLOWS.md` | **system-level** | — | Cross-cutting: covers all 8 architectural areas (Market Data, Market Analysis, Declarative Models, Research, Visualization, Live Execution, Operator CLI, Shared Domain Contracts) in one document, each with Problem/Approach/Workflow/Tech/Current Scope/Future Direction. This is exactly the audit's guessed `SYSTEM_OVERVIEW.md` shape and content. Confirms the guess. |
| `MODULE_MAP.md` | **system-level** | — | Package-to-workflow map, dependency rules (§12), test map (§13). Exactly matches the audit's guessed `MODULE_MAP.md`. Confirms the guess verbatim (even the filename). |
| `DATA_REPRESENTATION_AUDIT.md` | **system-level** | — | Cross-cutting technical-representation policy (Price/Volume/Timestamp carriers, canonical-type decisions D-REP-01..10) spanning market, market_analysis, research, execution and infrastructure. Binding policy that constrains every module, not documentation of one module or one workflow. The audit's 3-file guess (`SYSTEM_OVERVIEW.md`, `MODULE_MAP.md`, `DEPENDENCY_RULES.md`) did not anticipate this file; it belongs in `system/` on content grounds even though it wasn't named in the guess. |
| `RESEARCH_METHODOLOGIES.md` | **workflow-level** | — | Covers Signal, Model, Strategy, Robustness, Predictive and Portfolio Research as one deliberately comparative document — §1 (overview table), §10 ("Choosing a Methodology"), §11 ("Optional Research Progression") and §15 (methodology boundaries table) all cross-reference every methodology side by side. **This is one coherent document, not four separable ones.** |
| `AWS_BTC_FUTURES_DRY_RUN.md` | **operational-runbook-level** | — | Container image build/push, environment contract, ECS/Fargate notes, CloudWatch alarms, deploy/stop/restart/investigate/rollback runbook, cost estimates. Entirely "how do I run and operate this," zero architecture narrative. |
| `LOCAL_BTC_FUTURES_DRY_RUN.md` | **operational-runbook-level** | — | Run command, data flow, event log, CLI arguments, boundaries. Same shape as the AWS file, local variant. |
| `LIVE_PAPER_PIPELINE_INSPECTION.md` | **operational-runbook-level** | workflow-level (light) | Mostly an operator checklist (architecture verdict table, code path, local smoke test, live AWS checklist, status API fields) — but it opens with a short workflow-verdict section confirming execution vs. read-only boundaries across the whole live-paper pipeline. The workflow framing is thin (one table + one diagram); the bulk of the file is operational. |
| `DASHBOARD_APPLICATION.md` | **module-level** | — | Describes one deployable consumer (`apps/dashboard`): boundary, contracts, pages, "how to add a page/overlay," publishing runbook, cache limits. Parallel in shape and purpose to `modules/MARKET_ANALYSIS_MODULE.md` and `modules/MODEL_AUTHORING.md` — it is a per-app/per-module reference that happens to sit in the flat top level instead of `modules/`. |
| `OPERATOR_CLI.md` | **module-level** | operational-runbook (light) | Same shape as `DASHBOARD_APPLICATION.md`: describes one deployable consumer (`apps/cli` / `trading-cli`) — command groups, config schema pointer, exit codes, known limitations. It has an operator-usage flavor (it does explain how to invoke the tool) but its primary content is "what this component is and how it's organized," not a run/deploy/troubleshoot runbook — it points *out* to the runbook-style docs (`LOCAL_BTC_FUTURES_DRY_RUN.md`, `PREDICTIVE_PROMOTION.md`) rather than being one itself. |
| `PREDICTIVE_PROMOTION.md` | **module-level** | — | Deep reference for one specific mechanism (`research/predictive/promotion/`): parameter-file schema, store layout, fingerprint derivation, both guards, parity comparisons. This is a sub-module reference, same shape as `modules/MODEL_AUTHORING.md` (a focused deep-dive on one packaged capability), not a cross-cutting workflow description — Predictive Research the *workflow* is already covered in `RESEARCH_METHODOLOGIES.md` §8 and `MODULE_MAP.md` §8; this file is specifically the promotion sub-feature. |
| `STRATEGY_AUTHORING.md` | **module-level** | — | Deep reference for the `strategy_file` / custom-strategy-authoring convention: the loading contract, trust model, error table, worked examples, DSL composition. Same shape and purpose as `modules/MODEL_AUTHORING.md` (per-capability authoring guide), just for strategy composition instead of the base DSL. |
| `modules/DATA_MODULE.md` | **mixed — mostly future/vision-level, not as-implemented** | module-level (nominal) | See §3 below — this file does not actually belong in the "as-implemented reference" tier as currently written, and T007 flags this as a finding for the maintainer rather than silently relocating it. |
| `modules/MARKET_ANALYSIS_MODULE.md` | **module-level** | — | Correctly tiered already — states sprint status explicitly, describes actual implemented flow, MVP component table, verification test locations. No change needed. |
| `modules/MODEL_AUTHORING.md` | **module-level** | — | Correctly tiered already — short, as-implemented DSL guide with a working code example. No change needed. |

---

## 3. Finding: `modules/DATA_MODULE.md` is largely vision-tier content, not reference-tier

This file is already inside `docs/reference/modules/` (i.e. it's not being
audited for its *location* the way the others are), but its content does
not match the tier it's filed under. Contrast it with its sibling
`modules/MARKET_ANALYSIS_MODULE.md`, which explicitly states
`**Status:** Sprint 004 complete on main...` and describes the actually
implemented flow with source-file pointers.

`DATA_MODULE.md` instead reads as a target-architecture design brief:

- Pervasive "should/must/suggested" language throughout (`Suggested
  metadata:`, `Suggested dataset states:`, `Suggested Module Structure`,
  `Recommended initial scope`) rather than "is implemented as."
- §26 "Suggested Module Structure" lays out an aspirational package layout
  (`market/models/instrument.py`, `market/models/bar.py`, `market/models/
  trade.py`, `market/models/quote.py`, `market/services/missing_ranges.py`,
  etc.) that does not match the actual `src/trading_framework/market/`
  layout documented in `MODULE_MAP.md` §5 — no sprint number, no "as of
  Sprint N" marker anywhere in the file.
- §29 "Initial Implementation Scope" and §2's roadmap table ("Phase 2B —
  Historical Archive Import Foundation PLANNED", "Phase 2C — Trades and
  Quotes PLANNED", "Phase 2E — Live Market Data GATED") describe *planned*,
  not built, capability — the same "current vs. future" ambiguity that
  T001–T003 of this sprint were built to resolve for `docs/vision/`.
- Compare directly to `ARCHITECTURE_AND_WORKFLOWS.md` §3 (Market Data),
  which *does* describe current, shipped scope ("normalized historical
  datasets, reusable dataset references, derived datasets...") and labels
  the rest "Future Direction" explicitly.

**This is out of scope to fix under T007** (no rewriting, and T005/T006's
maintainer-decision pattern for exactly this kind of vision/reference
boundary question is D-S054-03, not an agent call). It is flagged here as a
candidate follow-up in the same family as T005/T006: a maintainer decision
on whether `modules/DATA_MODULE.md` should be reclassified toward
`docs/vision/` (it is Market Data's *target* architecture, closer in kind to
`docs/vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` than to
`modules/MARKET_ANALYSIS_MODULE.md`), rewritten to strip the "suggested/
should" framing and describe only what's built, or left as-is with an
explicit status banner. **The split plan below leaves this file's location
unchanged** (still `modules/DATA_MODULE.md`) pending that decision — moving
it without resolving the content question would just relocate the same
ambiguity, which is the exact anti-pattern D-S054-01's binding sequencing
rule exists to prevent.

---

## 4. Split plan

### 4.1 Comparison to the audit's guessed structure

The audit (`SPRINT_054.md` §2, T008 row) guessed:

```text
system/     SYSTEM_OVERVIEW.md (new), MODULE_MAP.md (moved),
            DEPENDENCY_RULES.md (consolidated from AGENTS.md /
            ARCHITECTURE_CONTROL.md / ARCHITECTURE_AND_WORKFLOWS.md)
workflows/  SIGNAL_RESEARCH.md, STRATEGY_RESEARCH.md,
            STRATEGY_EXECUTION.md, MARKET_DATA.md
modules/    existing 3 + any new ones T007 identifies
```

Against the actual content:

| Guessed item | Verdict | Why |
|---|---|---|
| `system/SYSTEM_OVERVIEW.md` | **Confirmed** | `ARCHITECTURE_AND_WORKFLOWS.md` already *is* this document in content and shape — rename-on-move, not a new write. |
| `system/MODULE_MAP.md` | **Confirmed** | Exact match, including filename. Move as-is. |
| `system/DEPENDENCY_RULES.md` | **Adjusted — not a T007/T008 move.** | No existing `docs/reference/` file is this document; the guess itself says it must be "consolidated from `AGENTS.md`/`ARCHITECTURE_CONTROL.md`/`ARCHITECTURE_AND_WORKFLOWS.md` pointers" — i.e., it requires *authoring new consolidated content* from three sources outside this audit's 15-file scope. That is new-document creation, not a content split of an existing `docs/reference/` file, so it is out of T007's read-only audit and out of a mechanical T008 move. Recommend T008 either defer this file to a dedicated follow-up task, or the maintainer treats it as new-content-with-approval rather than part of the "split, don't rewrite" T008 execution. |
| `workflows/SIGNAL_RESEARCH.md`, `STRATEGY_RESEARCH.md` | **Rejected as separate files.** | No source content splits cleanly this way. `RESEARCH_METHODOLOGIES.md` deliberately treats all methodologies as one comparative document (see §2 above); pulling out Signal Research and Strategy Research into standalone files would either duplicate the shared foundations/principles sections (§2, §3, §13) in every split file, or break the cross-methodology comparison tables (§1, §10, §11, §15) that are the document's main navigational value. Move `RESEARCH_METHODOLOGIES.md` wholesale into `workflows/` instead — one file, not four. |
| `workflows/MARKET_DATA.md` | **Rejected — no source content to move.** | No existing `docs/reference/` file is a Market Data *workflow* narrative. What exists is: `ARCHITECTURE_AND_WORKFLOWS.md` §3 (system-level architecture description of the module), `MODULE_MAP.md` §5 (system-level package map), and `modules/DATA_MODULE.md` (mostly vision-tier, §3 above). None of these is a workflow-tier "how does the Market Data workflow run end to end" document standing on its own; producing one would mean writing new prose, which is out of scope ("relocates and reclassifies content, does not rewrite architecture decisions"). Do not create this file in T008 from existing content. |
| `workflows/STRATEGY_EXECUTION.md` | **Adjusted — group, don't merge-write.** | The audit's validation goal (T010: "how does strategy execution work" resolves in 1–2 lookups) is legitimate, but the actual content for this workflow is three separate, already-complete operational-runbook documents (`AWS_BTC_FUTURES_DRY_RUN.md`, `LOCAL_BTC_FUTURES_DRY_RUN.md`, `LIVE_PAPER_PIPELINE_INSPECTION.md`), not one narrative that can be relocated intact. Writing a single merged `STRATEGY_EXECUTION.md` would require composing new connective prose across three documents — out of scope. Recommend instead: introduce the runbooks tier (§4.2) and group these three files there; the workflow-level "what is Strategy Execution architecturally" narrative already exists as `ARCHITECTURE_AND_WORKFLOWS.md` §8 (destined for `system/SYSTEM_OVERVIEW.md`) and `MODULE_MAP.md` §9 (destined for `system/MODULE_MAP.md`) — two lookups, both already satisfied by the `system/` moves above, without inventing a new file. |
| `modules/` + new files T007 identifies | **Confirmed, expanded.** | `DASHBOARD_APPLICATION.md`, `OPERATOR_CLI.md`, `PREDICTIVE_PROMOTION.md`, and `STRATEGY_AUTHORING.md` are all module-level (§2) and belong in `modules/` alongside the existing three. |

### 4.2 New tier proposed: `docs/reference/runbooks/`

The task brief explicitly asks T007 to decide whether
operational-runbook-level content "needs its own tier or fits elsewhere."
Verdict: **yes, a fourth tier**, distinct from `workflows/` (conceptual,
"what is this methodology/workflow and why") and `modules/` (per-component
implementation reference, "what does this package do and how is it
organized"). The runbook documents are neither — they are entirely
"how do I deploy/run/troubleshoot this," addressed to an operator with a
terminal open, not a reader trying to understand the system. Mixing them
into `workflows/` would dilute that tier's conceptual/narrative character
(confirmed by `RESEARCH_METHODOLOGIES.md`, the one workflow document that
exists); mixing them into `modules/` would dilute that tier's
implementation-reference character (confirmed by `MARKET_ANALYSIS_MODULE.md`
and `MODEL_AUTHORING.md`).

### 4.3 Full destination table

| File | Destination | Split needed? |
|---|---|---|
| `README.md` | `docs/reference/README.md` (rewritten in T008 to index the new tree) | No — content, not structure. Update links only. |
| `ARCHITECTURE_AND_WORKFLOWS.md` | `docs/reference/system/SYSTEM_OVERVIEW.md` | No — move and rename wholesale. |
| `MODULE_MAP.md` | `docs/reference/system/MODULE_MAP.md` | No — move wholesale, filename unchanged. |
| `DATA_REPRESENTATION_AUDIT.md` | `docs/reference/system/DATA_REPRESENTATION_AUDIT.md` | No — move wholesale. (Not in the audit's original guess; added on content grounds, §2.) |
| — | `docs/reference/system/DEPENDENCY_RULES.md` | **Deferred**, not a T007/T008 move — requires new consolidated content from `AGENTS.md`/`ARCHITECTURE_CONTROL.md`, out of this audit's scope (§4.1). |
| `RESEARCH_METHODOLOGIES.md` | `docs/reference/workflows/RESEARCH_METHODOLOGIES.md` | No — move wholesale, do not split into per-methodology files (§4.1). |
| `AWS_BTC_FUTURES_DRY_RUN.md` | `docs/reference/runbooks/AWS_BTC_FUTURES_DRY_RUN.md` | No — move wholesale. |
| `LOCAL_BTC_FUTURES_DRY_RUN.md` | `docs/reference/runbooks/LOCAL_BTC_FUTURES_DRY_RUN.md` | No — move wholesale. |
| `LIVE_PAPER_PIPELINE_INSPECTION.md` | `docs/reference/runbooks/LIVE_PAPER_PIPELINE_INSPECTION.md` | No — move wholesale (the light workflow-verdict opening section stays with the rest; splitting one table out is not worth a second file). |
| `DASHBOARD_APPLICATION.md` | `docs/reference/modules/DASHBOARD_APPLICATION.md` | No — move wholesale. |
| `OPERATOR_CLI.md` | `docs/reference/modules/OPERATOR_CLI.md` | No — move wholesale. |
| `PREDICTIVE_PROMOTION.md` | `docs/reference/modules/PREDICTIVE_PROMOTION.md` | No — move wholesale. |
| `STRATEGY_AUTHORING.md` | `docs/reference/modules/STRATEGY_AUTHORING.md` | No — move wholesale. |
| `modules/DATA_MODULE.md` | `docs/reference/modules/DATA_MODULE.md` (unchanged location) | **Content flagged, not moved** — see §3; maintainer decision needed before any relocation or rewrite. |
| `modules/MARKET_ANALYSIS_MODULE.md` | `docs/reference/modules/MARKET_ANALYSIS_MODULE.md` (unchanged) | No. |
| `modules/MODEL_AUTHORING.md` | `docs/reference/modules/MODEL_AUTHORING.md` (unchanged) | No. |

**No file in this audit requires splitting into multiple destination
files.** Every file that moves, moves as one coherent unit — the audit's
assumption that some files (particularly `RESEARCH_METHODOLOGIES.md`) would
need to be split turned out to be the one guess this pass overturns most
clearly: the document's value is in *not* being split.

### 4.4 Resulting tree (after T008, once executed)

```text
docs/reference/
├── README.md                          (rewritten index)
├── system/
│   ├── SYSTEM_OVERVIEW.md             ← ARCHITECTURE_AND_WORKFLOWS.md
│   ├── MODULE_MAP.md                  ← MODULE_MAP.md
│   ├── DATA_REPRESENTATION_AUDIT.md   ← DATA_REPRESENTATION_AUDIT.md
│   └── DEPENDENCY_RULES.md            (deferred — new content, not a move)
├── workflows/
│   └── RESEARCH_METHODOLOGIES.md      ← RESEARCH_METHODOLOGIES.md (wholesale)
├── runbooks/
│   ├── AWS_BTC_FUTURES_DRY_RUN.md     ← AWS_BTC_FUTURES_DRY_RUN.md
│   ├── LOCAL_BTC_FUTURES_DRY_RUN.md   ← LOCAL_BTC_FUTURES_DRY_RUN.md
│   └── LIVE_PAPER_PIPELINE_INSPECTION.md ← LIVE_PAPER_PIPELINE_INSPECTION.md
└── modules/
    ├── DATA_MODULE.md                 (unchanged; content flagged, §3)
    ├── MARKET_ANALYSIS_MODULE.md      (unchanged)
    ├── MODEL_AUTHORING.md             (unchanged)
    ├── DASHBOARD_APPLICATION.md       ← DASHBOARD_APPLICATION.md
    ├── OPERATOR_CLI.md                ← OPERATOR_CLI.md
    ├── PREDICTIVE_PROMOTION.md        ← PREDICTIVE_PROMOTION.md
    └── STRATEGY_AUTHORING.md          ← STRATEGY_AUTHORING.md
```

---

## 5. Handoff to T008

T008 may proceed once this document is reviewed, per D-S054-01. Concretely,
T008 should:

1. Execute the moves in §4.3 (`git mv`, one PR per coherent outcome per
   `git-workflow` sizing — e.g. one PR for the `system/` moves, one for
   `runbooks/` + `workflows/`, one for the `modules/` additions).
2. Leave `system/DEPENDENCY_RULES.md` and the `modules/DATA_MODULE.md`
   content question out of T008's move PRs — both need a decision or new
   content beyond "relocate what already exists," which is this task's
   explicit boundary.
3. Update every inbound link touched by a move as part of the same PR that
   moves the file (not deferred to T009, which is for *other* documents'
   inbound references — `AGENTS.md`, `docs/README.md`, ADRs, sprint docs).
4. Rewrite `docs/reference/README.md`'s navigation table to the tree in
   §4.4 as the last of the T008 PRs, once all moves have landed.
