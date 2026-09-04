# Sprint 055 T001 — `docs/reference/` Target Information Architecture

```text
Sprint: 055 (Documentation Architecture Rebuild, high-level to low-level)
Task:   T001 — Full-content audit of all 20 current docs/reference/ files;
        produce a target IA proposal calibrated against, but not bound by,
        the maintainer's example tree (D-S055-01).
Scope:  READ-ONLY. No docs/reference/ file was moved, renamed, split, merged
        or edited while producing this document (D-S055-03). docs/vision/ was
        not touched (T002 owns it, in parallel).
Method: Full read of all 20 files, no sampling. Overlap claims below cite the
        specific section headings that overlap, not impressions.
Status: PROPOSED — input to the T004 maintainer review gate. Nothing here is
        approved; T005/T007 may not start before T004 signs off.
```

---

## 0. Inventory read (20 files)

| Path | Approx. lines | Verdict headline |
|---|---:|---|
| `README.md` | 71 | Index only; must be rewritten by whichever task lands last (§7) |
| `ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md` | 1,103 | Misfiled at top level under "Other"; is system-tier |
| `system/SYSTEM_OVERVIEW.md` | 938 | Correct tier, correct name; keep |
| `system/MODULE_MAP.md` | 846 | Correct tier, correct name; keep (2 sections to de-duplicate) |
| `system/DEPENDENCY_RULES.md` | 95 | Correct tier, correct name; keep and make the single home |
| `system/DATA_REPRESENTATION_AUDIT.md` | 1,075 | **Three documents in one**; largest single navigability problem |
| `system/ARCHITECTURE_FOUNDATIONS.md` | 1,369 | Provenance-named, not subject-named; splits cleanly at its own headings |
| `system/ARCHITECTURE_TECHNICAL.md` | 1,394 | Heavy triplication with the two files above/below |
| `system/MULTITIMEFRAME_MARKET_MODEL.md` | 931 | Heavy triplication; its unique value is the MTF/alignment half |
| `system/WORKFLOWS_ARCHITECTURE.md` | 990 | **Misfiled** — is workflow tier by content and by its own title |
| `workflows/RESEARCH_METHODOLOGIES.md` | 807 | Correct tier; still one deliberately comparative document, do not split |
| `runbooks/LOCAL_BTC_FUTURES_DRY_RUN.md` | 112 | Correct tier; keep |
| `runbooks/AWS_BTC_FUTURES_DRY_RUN.md` | 512 | Correct tier; keep |
| `runbooks/LIVE_PAPER_PIPELINE_INSPECTION.md` | 90 | Correct tier; keep |
| `modules/DATA_MODULE.md` | 740 | Post-reclassification it is a **workflow** narrative, not a module reference |
| `modules/MARKET_ANALYSIS_MODULE.md` | 175 | Right place, **stale content** + broken relative links |
| `modules/MODEL_AUTHORING.md` | 63 | Correct; keep unchanged |
| `modules/STRATEGY_AUTHORING.md` | 831 | **Three subjects in one**; two are extractable with no new prose |
| `modules/OPERATOR_CLI.md` | 303 | Correct; keep unchanged (runbooks/ alternative rejected, §5.4) |
| `modules/PREDICTIVE_PROMOTION.md` | 361 | Correct; keep unchanged — the best-scoped file in the tree |
| `modules/DASHBOARD_APPLICATION.md` | 95 | Correct; keep unchanged |

---

## 1. Method

Same discipline as `SPRINT_054_T007_REFERENCE_FOLDER_AUDIT.md`, applied to a
larger scope. For every file, four questions:

1. **Tier** — is it system (cross-cutting, multi-module), workflow (one
   end-to-end capability), runbook (operator with a terminal open), or module
   (one package/app/surface)?
2. **Redundancy** — does another file state the same rule? Recorded only where
   the same *named concept* appears with the same *content* in two or more
   files, listed by heading.
3. **Navigability** — can a reader find "where is X documented" from the
   filename plus a folder index, without opening the file? A file fails this
   when its name describes its *provenance* ("Architecture Technical", "moved
   from vision") rather than its *subject*.
4. **Would executing the move require new prose?** If yes, it is not a move —
   it is authoring, and must be flagged for explicit T004 approval (D-S055-04),
   exactly as T007 refused to invent `MARKET_DATA.md` from nothing.

The maintainer's example tree is treated as a **granularity and naming
calibration**: subject-shaped filenames (`DOMAIN_MODEL`, `DEPENDENCY_RULES`,
`SIGNAL_RESEARCH`) at roughly 4–5 files per folder. It is not treated as a
content spec.

---

## 2. The central finding: the `system/` folder is organised by provenance, not by subject

Four of `system/`'s eight files (`ARCHITECTURE_FOUNDATIONS`,
`ARCHITECTURE_TECHNICAL`, `MULTITIMEFRAME_MARKET_MODEL`,
`WORKFLOWS_ARCHITECTURE`) exist as separate files **because they came from four
separate vision documents in Sprint 054 T004/T006c**, not because they cover
four separate subjects. Sprint 054's job was classification (current vs. future)
and it did that correctly — but the resulting file boundaries inherited the
vision tree's boundaries, and those overlap badly.

### 2.1 Measured triplication

Each row below is one concept stated in three or four separate files under
`system/`, in near-identical wording:

| Concept | `ARCH_FOUNDATIONS` | `ARCH_TECHNICAL` | `MULTITIMEFRAME` | Also in |
|---|---|---|---|---|
| Features / Structures / States taxonomy | "Market Analysis as a Reusable Language" | "Market Analysis Architecture" → Feature/Structure | "Market Analysis Categories" + Features + Structures | — |
| `observed_at` / `available_at` semantics | "Multitimeframe Is a Property of Analytical Requests" | "Observed Time and Available Time" | "Observed Time and Available Time" | `DATA_REPRESENTATION_AUDIT` D-REP-05 |
| `LAST_CLOSED_BAR` default alignment | same section as above | "Temporal Alignment" | "Default Alignment Policy" + "As-Of Alignment" | — |
| source / computation / evaluation timeframe | same section as above | "Component Request" | "Source, Computation and Evaluation Timeframe" | — |
| `MarketFieldReference` contract | "Models as Declarative Compositions" | "MarketFieldReference" | "MarketFieldReference" | `WORKFLOWS_ARCHITECTURE` "Market Model and Signal Model Semantics" |
| Market Model / Signal Model = declarative expression | "Models as Declarative Compositions" | "Model Composition Architecture" | "Market Model as Expression Tree" | `WORKFLOWS_ARCHITECTURE` (twice) |
| `SignalOccurrence` field list | "Signal Occurrence" (Strategy Domain) | "Signal Model" | — | `WORKFLOWS_ARCHITECTURE` "SignalOccurrence" |
| Signal Research three scopes | "Signal Research" (Research Domain) | "Signal Research Scopes" | Rule 14 | `WORKFLOWS_ARCHITECTURE` "Research Scope" |
| Strategy = Market × Signal × Exit × Risk | "Strategy as Composition" | "Strategy Model" | — | `WORKFLOWS_ARCHITECTURE` "Strategy Model" |
| Dependency direction / `src/` never imports `user_data/` | "Stable Dependency Direction", "Framework and User Space" | Final rules 27–31 | — | `DEPENDENCY_RULES` §1, `MODULE_MAP` §1 + §12, `SYSTEM_OVERVIEW` §2 |
| Dataset lifecycle `WORKING→FINALIZED→PUBLISHED` | "Trusted and Reproducible Market Data" | "Dataset Lifecycle" | — | `modules/DATA_MODULE.md` §8 |
| Parquet-as-primary-storage rationale | — | "Historical Storage" | — | `SYSTEM_OVERVIEW` §3, `modules/DATA_MODULE.md` §18.1 |
| `user_data/` workspace tree | — | "User Data Structure" (pointer) | — | `MODULE_MAP` §11 **and** `modules/DATA_MODULE.md` §18.3 (identical tree, two copies) |

Two of these files also acknowledge the duplication in their own as-built
notes: `ARCHITECTURE_TECHNICAL.md`'s "Module Structure" and "Tests Structure"
sections carry notes saying the authoritative layout is in `MODULE_MAP.md`, and
`MULTITIMEFRAME_MARKET_MODEL.md`'s "Source, Computation and Evaluation
Timeframe" note points at `ARCHITECTURE_FOUNDATIONS.md` for the same fact.

**Consequence for a fresh reader:** the question "what is the default
higher-timeframe alignment policy, and is it enforced?" currently requires
opening three files to discover they agree. The maintainer's stated goal (1–2
lookups per folder) is not achievable while `system/` is split this way.

### 2.2 What the four files *do* uniquely own

Stripping the triplicated content leaves four genuinely distinct subjects,
which is what the target tree is built from:

- **Domain ownership** (`ARCHITECTURE_FOUNDATIONS` "Domains", "Domain
  Relationships", "Framework and User Space", "Accepted Clarifications",
  "System Capabilities") — five domains with explicit Owns / Does Not Own
  lists, an allowed-consumption diagram, and an entity list (`Instrument`,
  `MarketBar`, `SignalOccurrence`, `Order`…). This is a domain model.
- **Cross-cutting principles** (`ARCHITECTURE_FOUNDATIONS` "Core Philosophy" +
  "Architectural Principles") — priority order, separation of concerns,
  reproducibility/lineage, immutability, no-god-objects, modular monolith.
- **Time, multitimeframe and alignment** (`ARCHITECTURE_TECHNICAL` "Time
  Model" + `MULTITIMEFRAME` "Multitimeframe Architecture", "Resampling",
  "Temporal Alignment and Look-Ahead Protection") — UTC policy, Clock
  abstraction, contract rolls, three timeframes, resampling as a graph node,
  as-of alignment, look-ahead protection.
- **The Market Analysis engine** (`ARCHITECTURE_TECHNICAL` "Market Analysis
  Architecture" + "Market Analysis Engine") — component contract, registry,
  DAG, lazy execution, cache identity, execution context, output forms.

`WORKFLOWS_ARCHITECTURE.md` owns none of these — see §3.

---

## 3. `system/WORKFLOWS_ARCHITECTURE.md` is workflow-tier content in the wrong folder

Its own H1 is "Workflows Architecture" and its three top-level sections are
literally **Signal Research**, **Strategy Research**, **Strategy Execution** —
each with purpose, scopes, inputs, outputs, persistence, reuse rules and (for
Execution) a runtime flow with as-built notes tying it to
`execution/runtime/decision_step.py`, `live_signals.py`, `safety.py` and
`broker_sim/paper_broker.py`.

This is the single most consequential change since Sprint 054 T007. **T007
rejected `workflows/SIGNAL_RESEARCH.md` / `STRATEGY_RESEARCH.md` because the
only candidate source (`RESEARCH_METHODOLOGIES.md`) was one deliberately
comparative document that could not be split without duplication.** That
verdict was correct then and remains correct for `RESEARCH_METHODOLOGIES.md`.
But it is no longer the only source: Sprint 054 T006c imported an entirely
different document — one that *is already* structured as three separate
workflow narratives — and filed it under `system/`.

So the maintainer's example filenames `SIGNAL_RESEARCH.md`,
`STRATEGY_RESEARCH.md` and `STRATEGY_EXECUTION.md` are now supported by real,
already-written, already-classified content requiring **no new prose** — they
are section extractions from one file, not merges across three.

The file's opening "Workflow Architecture" section (Core Rule — the three
capabilities are not a pipeline; Workflow Definitions; Computation vs.
Analytics) is the shared preamble to all three, and duplicates
`ARCHITECTURE_FOUNDATIONS.md`'s "System Capabilities" section almost verbatim
(same "Incorrect / Correct" pipeline diagrams). It should become the body of
the `workflows/` folder index (T005), with the canonical statement living once
in `system/DOMAIN_MODEL.md`.

---

## 4. Files that are several documents in one

### 4.1 `system/DATA_REPRESENTATION_AUDIT.md` (1,075 lines) — three tiers in one file

Its own front matter says sections §1–§3/§5.1/§6 are "descriptive" and §4/§5.2/
§7–§8 are "prescriptive". Reading it confirms three separable things:

| Part | Sections | What it actually is | Decays? |
|---|---|---|---|
| A. Binding representation policy | §4 (canonical carrier per kind of work, six directional rules, non-goals), §5.2 (target primitives), §5.3 (null semantics) | Durable cross-cutting policy constraining every module — the same kind of artifact as `DEPENDENCY_RULES.md` | No |
| B. Point-in-time audit | §1–§3 (representation map, transformation map with ~90 file:line citations), §5.1, §6 (benchmarks at commit `f0a82c5`, PR numbers #274–#283) | A Sprint 036 measurement record, explicitly pinned to a code baseline that is now ~19 sprints old | Yes, already |
| C. Decision register + refactoring plan | §7 (D-REP-01..10 with statuses), §8 (Stage 0–6 with PR tables and `DONE`/`DEFERRED` markers), §10.2 open items | A decision log plus a staged task board with per-PR status | Yes — is a second task board |

Part C in particular is exactly what `docs/planning/PROJECT_MANAGEMENT.md`'s
own principle warns against ("the operational status of individual tasks has
one source of truth"), sitting inside the as-implemented reference tier.

Note also that §7's `ADR impact` column and D-REP-01's outcome reference
`ADR-MA-014` — the binding decisions already have ADRs, so the reference tier
does not need to carry the decision register to be complete.

**Proposal:** extract Part A as `system/DATA_REPRESENTATION_POLICY.md`; move
Parts B+C out of `docs/reference/` to
`docs/planning/sprints/SPRINT_036_DATA_REPRESENTATION_AUDIT.md`, with the new
policy file linking to it as the evidence record. **This crosses out of
`docs/reference/` and therefore needs explicit T004 approval** — it is the one
proposal here that changes a folder other than `docs/reference/`. Conservative
fallback if rejected: keep one file, but rename it
`system/DATA_REPRESENTATION_POLICY_AND_AUDIT.md` and reorder so §4/§5 lead.

### 4.2 `modules/STRATEGY_AUTHORING.md` (831 lines) — three subjects in one

| Part | Sections | Subject |
|---|---|---|
| A. The `strategy_file` convention | §1 convention, §2 trust model/no sandbox, §3 error table, §6 advisory imports, §7 boundary-test blind spot, §8 related | How to author and run your own strategy file — matches the file's own stated purpose in its intro |
| B. The analysis component catalog | §4 — `candle.wick`, `structure.level_distance`, and the six Sprint 051 components (`momentum.rsi`/`macd`/`stochastic`, `volatility.relative_volatility`, `statistics.return_autocorrelation`/`return_distribution`) with warm-up, output and zero-denominator conventions per component | Market Analysis component reference — nothing to do with strategy files. §4 itself says these are "consumable identically by a rule-based Signal Model or declared as a predictive `FeatureSpec`", i.e. explicitly *not* strategy-authoring-specific |
| C. Six worked example strategies | §5 — ~450 lines of `build_strategy()` code plus the Sprint 048 Exit/Risk semantics block | A cookbook |

Part B is the more important extraction: **the component catalog currently has
no home and is split across three files that disagree**.
`modules/MARKET_ANALYSIS_MODULE.md`'s "MVP Components" table lists 7 components
and stops at Sprint 005. `system/MODULE_MAP.md` §6 crams every component added
since into a single ~15-line table *cell*. `modules/STRATEGY_AUTHORING.md` §4
has the actual per-component semantics. A reader asking "what components exist
and what does `momentum.stochastic` return on a zero-range window?" has no way
to know the answer is in a file called `STRATEGY_AUTHORING`.

Part C is separable on the file's own terms (it calls them "Worked examples")
and is nearly all code. Extracting it takes `STRATEGY_AUTHORING.md` from 831 to
roughly 250 lines without deleting anything.

The Sprint 048 Exit/Risk semantics (`BracketExitModel` two fill conventions,
`EquityPercentRiskModel` static sizing, the operator-owned stop-consistency
caveat) **stay in `STRATEGY_AUTHORING.md`** — they describe what you compose a
strategy *from*, and separating them would create a fourth thin file. Noted
because it is the one place I considered a further split and rejected it.

### 4.3 `modules/DATA_MODULE.md` (740 lines) — is a workflow document post-reclassification

After the `DATA_MODULE_CLASSIFICATION` follow-up stripped its future-tier
content, what remains splits in two:

- **Already stated elsewhere:** §3 Domain Ownership (= `ARCHITECTURE_FOUNDATIONS`
  "Market Domain" Owns/Does Not Own), §4 Architectural Layers (= `MODULE_MAP` §5),
  §7 dataset metadata list (= `ARCHITECTURE_TECHNICAL` "Dataset Identity"), §8
  lifecycle states (= `ARCHITECTURE_TECHNICAL` "Dataset Lifecycle", same five
  states), §12.3 access rules (= `ARCHITECTURE_TECHNICAL` "Dataset Access"),
  §18.1 Parquet rationale (= `ARCHITECTURE_TECHNICAL` "Historical Storage", same
  bullet list), §18.3 workspace tree (= `MODULE_MAP` §11, identical tree).
- **Unique, and workflow-shaped:** §11 External Dataset Import (including
  §11.3 "Inspect Before Import" and §11.4 provider-vs-importer contract split),
  §12 Local Historical Data Access query flow, §15 Partition Finalization
  workflow, §16 Dataset Publication workflow, §20 Futures Contract Identity,
  §23 Validation stages, §27 Prohibited Designs.

Every unique section is a step in one end-to-end pipeline: acquire → import →
normalize → validate → finalize → publish → query. That is a workflow
narrative, not a per-package module reference — it names no package it owns
(its own header defers package/test paths to `MODULE_MAP` §5).

**This retires T007's second rejection.** T007 refused to create
`workflows/MARKET_DATA.md` because "no existing `docs/reference/` file is a
Market Data *workflow* narrative." That was accurate at the time, when
`DATA_MODULE.md` was still a mixed vision/reference document full of
"suggested/should" target architecture. The reclassification changed the input:
there is now a real, current-tier Market Data workflow document — it is just
filed under `modules/` and named after a package.

**Proposal:** `modules/DATA_MODULE.md` → `workflows/MARKET_DATA.md`, with the
seven duplicated sections above dropped in favour of pointers.
`SYSTEM_OVERVIEW.md` §3's "Import Paths" table (the three concrete entry points
and their adapter layers) is the one piece of new material this file should
absorb, so the reader gets "which import path do I use" and "what happens next"
in one lookup — that is a *move* of an existing table, not new prose.

Residual "suggested/should" language survives in this file (§4's "Suggested
location:", §7's "Suggested metadata:", §8's "Suggested dataset states:", and
§4.3's list of Rithmic / MetaTrader 5 / DuckDB adapters that have no package in
`src/`). That is a **content** defect, not an IA defect — flagged for T003/T004,
not fixed by any move proposed here.

---

## 5. File-by-file comparison against the maintainer's example tree

### 5.1 `system/`

| Example filename | Verdict | Evidence |
|---|---|---|
| `SYSTEM_OVERVIEW.md` | **Confirmed, unchanged** | Already exists, already correct in both name and content: 13 sections covering all architectural areas with Problem/Approach/Workflow/Tech/Current Scope/Future Direction. |
| `MODULE_MAP.md` | **Confirmed, unchanged** | Already exists with the exact filename. Coherent end to end (repo boundaries → package map → workflow map → per-area maps → workspace → test map). Two de-duplications only: §12 "Dependency Rules" becomes a pointer to `DEPENDENCY_RULES.md`, and §6's inline component-catalog cell becomes a pointer to the new component catalog (§5.4). |
| `DEPENDENCY_RULES.md` | **Confirmed, unchanged** | Already exists (authored after T007 deferred it). Uniquely valuable because it distinguishes *enforced by a named test* (§2) from *stated but untested* (§3) and records the one known unenforced exception. Should become the single home; `MODULE_MAP` §12 and `ARCHITECTURE_FOUNDATIONS` "Stable Dependency Direction" point here rather than restating. |
| `DOMAIN_MODEL.md` | **Confirmed as a rename/extraction — real content exists** | `ARCHITECTURE_FOUNDATIONS.md`'s "Domains" section is a domain model in all but name: five bounded contexts (Market, Market Analysis, Strategy, Research, Execution) each with a Question, an Owns list, a Does Not Own list; a Domain Relationships diagram of allowed consumption; entity/value-object definitions (`Instrument`, `MarketBar`, `MarketTrade`, `SignalOccurrence` with its field list, `Order`, `DatasetRef`); aggregate composition (`Strategy Model = Market × Signal × Exit × Risk`); and 11 numbered "Accepted Clarifications" that are ubiquitous-language decisions ("the third capability is named `Strategy Execution`", "the shared runtime is named `Market Analysis Engine`"). **No `docs/vision/DOMAIN_MODEL.md` exists**, so this filename is unclaimed. Note for T002/T004: `docs/vision/` owning a future-tier domain model and `docs/reference/system/` owning the as-built one is coherent, but the two tasks must not both claim the name — coordinate at T004. |

Beyond the example, four more `system/` files are required by content that the
example did not anticipate (the same situation as T007 adding
`DATA_REPRESENTATION_AUDIT.md` to a three-file guess):

| Proposed file | Why it must exist separately |
|---|---|
| `ARCHITECTURE_PRINCIPLES.md` | `ARCHITECTURE_FOUNDATIONS.md`'s other half ("Core Philosophy" + "Architectural Principles") is cross-cutting *how we build*, not *what the domains are*: priority order (correctness > reproducibility > … > scalability), separation of concerns, stable dependency direction, single source of truth, reproducibility/lineage, immutable published definitions, testability, technology independence, no god objects, modular monolith, simplicity before scale. Merging it into `DOMAIN_MODEL.md` would reproduce today's problem — one 1,369-line file where the reader cannot predict which half holds the answer. |
| `MARKET_ANALYSIS_ARCHITECTURE.md` | The engine (registry, DAG, lazy execution, cache identity, execution context, component contract, output forms) is the single most-referenced subsystem in the tree and currently has no file of its own — it is spread across `ARCHITECTURE_TECHNICAL` and `MULTITIMEFRAME`. |
| `TIME_AND_ALIGNMENT.md` | Absorbs the triplication in §2.1 rows 2–4. One home for UTC policy, naive-datetime prohibition, `Clock` abstraction, futures contract rolls, `observed_at`/`available_at`, the three timeframes, resampling-as-a-graph-node, `LAST_CLOSED_BAR` and as-of alignment. This is the concept a reader most often needs and currently least reliably finds. |
| `ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md` | Exists already; only its **location** changes (top-level "Other" → `system/`). It is cross-cutting policy (workspace ownership, output identity vs. aliases, dedup, memory lifecycle, persistence of derived data, 12 architectural invariants, ADR-MA-007) that constrains every analytical module — the same tier test that put `DATA_REPRESENTATION_AUDIT.md` in `system/`. Leaving it stranded in an "Other" bucket at the top level guarantees it is never found. |
| `DATA_REPRESENTATION_POLICY.md` | See §4.1. |

**Naming-collision warning for T005/T007:** "workspace" means two different
things in this tree — the execution-scoped `AnalysisWorkspace`
(`ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md`) and the user's `user_data/` storage
root (`MODULE_MAP` §11, "User Workspace Map"). The folder index must
disambiguate these explicitly or readers will open the wrong file.

### 5.2 `workflows/`

| Example filename | Verdict | Evidence |
|---|---|---|
| `SIGNAL_RESEARCH.md` | **Confirmed — now has source content (reverses T007)** | `system/WORKFLOWS_ARCHITECTURE.md` "Signal Research" (~420 lines): purpose, three scopes with per-scope example questions, inputs, model semantics, independent-expansion vs. logical-composition, single-condition models, `SignalOccurrence`, Market Model results, shared dependency plan, computation output, reuse rule, 14 numbered rules. Extraction, not authoring. |
| `STRATEGY_RESEARCH.md` | **Confirmed — now has source content (reverses T007)** | Same file, "Strategy Research" (~250 lines): purpose, core question, Strategy Model, composition rules, historical simulation, computation output, analytics, walk-forward, Monte Carlo, robustness, reuse rule. |
| `STRATEGY_EXECUTION.md` | **Confirmed — now has source content (reverses T007's "group, don't merge-write")** | Same file, "Strategy Execution" (~170 lines): core question, inputs and explicit non-inputs, runtime flow with as-built code pointers, position management, strategy-risk vs. operational-risk separation, persistence. T007's alternative (rely on `SYSTEM_OVERVIEW` §8 + `MODULE_MAP` §9 and group the runbooks) was right when the only alternative was writing new connective prose across three runbooks. It is no longer necessary. |
| `MARKET_DATA.md` | **Confirmed — now has source content (reverses T007)** | `modules/DATA_MODULE.md`'s unique sections, see §4.3, plus `SYSTEM_OVERVIEW` §3's Import Paths table. |

`workflows/RESEARCH_METHODOLOGIES.md` stays exactly as it is — **T007's
strongest finding survives this audit unchanged.** §1's overview table, §10
"Choosing a Methodology", §11 "Optional Research Progression" and §15
"Methodology Boundaries" compare all six methodologies side by side; §2/§3/§13
are shared foundations that every split file would have to duplicate. It is one
document.

**Overlap risk to flag for T004:** `RESEARCH_METHODOLOGIES.md` §4 (Signal
Research) and the proposed `workflows/SIGNAL_RESEARCH.md` will sit in the same
folder describing the same workflow. They are *not* duplicates — the
methodology file answers "what question does this answer and when should I
choose it", the architecture file answers "what are its scopes, contracts,
persisted outputs and rules". But the distinction is not visible from the two
filenames, and this is precisely the kind of adjacency that decays into
divergence. Two options for T004:

- **(a) Recommended:** keep both; make the `workflows/` index state the split
  in one line each, and add a reciprocal one-line pointer at the top of each
  file. Cheapest, no content risk.
- **(b)** rename the architecture files `SIGNAL_RESEARCH_ARCHITECTURE.md` etc.
  Clearer, but diverges from the maintainer's example filenames for no content
  reason. Not recommended.

### 5.3 `runbooks/` — not in the maintainer's example, and should stay

The example tree has no runbook tier. T007 introduced one on content grounds
and this audit confirms it: all three files are addressed to an operator with a
terminal open (docker build commands, IAM policy JSON, CloudWatch alarm
definitions, "Investigate Stale Heartbeat" step lists, cost tables), which is
neither the conceptual character of `workflows/` nor the
implementation-reference character of `modules/`. No change.

One observation for T005, not a file change: all three runbooks are about
**one** thing — the BTC futures dry-run demo (local variant, AWS variant, and a
pipeline-verification checklist). Nothing in the three filenames says they are
one family, and there are **no runbooks for the research side** (`data fetch`,
`research run`, `report render` have operator surfaces documented only inside
`modules/OPERATOR_CLI.md`). That is a genuine gap; per T007's discipline I am
**not** proposing to invent research runbooks here — recorded for T003.

### 5.4 `modules/`

The example proposes one file per domain (`DATA`, `MARKET_ANALYSIS`, `SIGNALS`,
`STRATEGY`, `EXECUTION`). **The real `modules/` folder is not organised by
domain and should not be** — it is organised by *deliverable surface*: a
deployable app (`DASHBOARD_APPLICATION`), an operator CLI (`OPERATOR_CLI`), an
authoring DSL (`MODEL_AUTHORING`), an authoring convention
(`STRATEGY_AUTHORING`), one packaged mechanism (`PREDICTIVE_PROMOTION`), one
implementation guide (`MARKET_ANALYSIS_MODULE`). Domain-level content lives in
`system/DOMAIN_MODEL.md` (what each domain owns) and `system/MODULE_MAP.md`
(which package implements it) — which is where a reader should find it.

| Example filename | Verdict |
|---|---|
| `modules/DATA.md` | **Rejected as a module file.** Its would-be content is a workflow (§4.3) and belongs in `workflows/MARKET_DATA.md`. Package/test/adapter facts already live in `MODULE_MAP` §5. Creating `modules/DATA.md` would either duplicate `MODULE_MAP` §5 or be an empty shell. |
| `modules/MARKET_ANALYSIS.md` | **Maps to the existing `MARKET_ANALYSIS_MODULE.md`** (rename optional, no content reason to do it). Content needs refreshing, not restructuring — see §6. |
| `modules/SIGNALS.md` | **Rejected — no source content; do not fabricate.** There is no signal-module implementation reference anywhere in the 20 files. What exists is: Signal Model *semantics* (system tier, triplicated — going to `DOMAIN_MODEL.md`), the Signal Research *workflow* (going to `workflows/SIGNAL_RESEARCH.md`), and the `signal_model/` package's location (`MODULE_MAP` §7). Writing `modules/SIGNALS.md` would mean composing new prose, which D-S055-04 forbids without explicit approval — and there is no reader question it would answer that the three above do not. |
| `modules/STRATEGY.md` | **Rejected as named; partially maps to `STRATEGY_AUTHORING.md`.** Same reasoning: strategy composition semantics are domain-tier, Strategy Research is workflow-tier, and the only module-tier strategy content is the `strategy_file` authoring convention, which already has a file. |
| `modules/EXECUTION.md` | **Rejected — no source content; do not fabricate.** Execution is covered by `workflows/STRATEGY_EXECUTION.md` (architecture + as-built code pointers), the three runbooks (how to operate it), and `MODULE_MAP` §9 (packages). There is no fourth, module-level execution document to write from existing material. |

Proposed `modules/` additions, both extractions with no new prose:

| Proposed file | Source | Rationale |
|---|---|---|
| `ANALYSIS_COMPONENT_CATALOG.md` | `STRATEGY_AUTHORING.md` §4 + `MARKET_ANALYSIS_MODULE.md`'s "MVP Components" table + the component list currently inlined in `MODULE_MAP` §6's table cell | Gives the component catalog one findable home and resolves a three-way disagreement about which components exist (§4.2). Highest-value single change in `modules/`. |
| `STRATEGY_EXAMPLES.md` | `STRATEGY_AUTHORING.md` §5 | ~450 lines of example `build_strategy()` code, self-described as "worked examples"; extracting them makes the authoring convention readable. |

`OPERATOR_CLI.md` stays in `modules/` — I re-tested T007's call now that a
`runbooks/` tier exists and reached the same answer: it documents one
deployable component's whole surface (command tree, config contract, exit-code
taxonomy, known limitations with TD references) and *points out* to runbooks
rather than being one. Recorded because it is the closest call in the folder.

`PREDICTIVE_PROMOTION.md` stays unchanged and is worth naming as the model the
rest of the tree should follow: it states its own boundary against the ADR
("the why lives in ADR-0029; a future agent should be able to operate promotion
from this document alone"), and it explicitly claims sole ownership of the
store-layout tree ("this is the **only** place this tree appears — do not
duplicate it"), with `MODULE_MAP` §8 honouring that by linking instead of
repeating. That is exactly the anti-duplication contract the `system/` files
lack.

---

## 6. Content problems found (not fixed by any move here)

Recorded for T003/T004 so they are not mistaken for IA problems:

1. **`modules/MARKET_ANALYSIS_MODULE.md` is stale.** Its status line stops at
   Sprint 004/005 and its "MVP Components" table lists 7 components; `MODULE_MAP`
   §6 and `STRATEGY_AUTHORING` §4 between them document at least 8 more added
   in Sprints 047/048/051 (`candle.wick`, `structure.level_distance`,
   `trend.ema_distance`, `volatility.range_expansion`, `momentum.rsi`/`macd`/
   `stochastic`, `volatility.relative_volatility`,
   `statistics.return_autocorrelation`/`return_distribution`).
2. **`modules/MARKET_ANALYSIS_MODULE.md` has broken relative links.** Its
   "Where to Read Next" §3 uses `../adr/ADR-MA-012...` and `../adr/ADR-MA-013...`
   from inside `modules/`, which resolve to `docs/reference/adr/` — a directory
   that does not exist. Correct depth is `../../adr/`. (Its header links, added
   later, use the correct `../../adr/` form — so the file is internally
   inconsistent.)
3. **`ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md` is written in Sprint 003 tense.**
   §23 "Persistence Decision for Sprint 003", §29 "Sprint 003 Requirements",
   §30 "Out of Scope for Sprint 003" are planning content inside the reference
   tier; §33 embeds ADR-MA-007 in full rather than linking `docs/adr/`. Its
   architecture (§1–§22, §32) is durable; the sprint framing is not.
4. **`modules/DATA_MODULE.md` still carries target-architecture language**
   despite reclassification — §4's "Suggested location:", §7's "Suggested
   metadata:", §8's "Suggested dataset states:", and §4.3's Rithmic / MetaTrader 5
   / DuckDB adapters with no matching package. (`ARCHITECTURE_TECHNICAL.md`
   already carries an as-built note recording that Rithmic and MT5 have no
   provider package; `DATA_MODULE.md` does not.)
5. **`ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md` points into `docs/vision/`** for
   authority ("For engine contracts … see `MARKET_ANALYSIS_WITH_DECISIONS.md`",
   with a precedence clause). A reference-tier file deferring to a vision-tier
   file for current contracts is a tier inversion — coordinate with T002.
6. **`modules/MARKET_ANALYSIS_MODULE.md` also cites vision as binding**
   ("Binding decisions (vision): `MARKET_ANALYSIS_WITH_DECISIONS.md`,
   `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md`") — same inversion, same
   coordination need.

---

## 7. Proposed target tree

```text
docs/reference/
├── README.md                                    (rewritten: 4 folders, when to open which)
├── system/
│   ├── README.md                                (NEW index — T005)
│   ├── SYSTEM_OVERVIEW.md                       unchanged
│   ├── DOMAIN_MODEL.md                          ← ARCHITECTURE_FOUNDATIONS (domains half)
│   ├── ARCHITECTURE_PRINCIPLES.md               ← ARCHITECTURE_FOUNDATIONS (principles half)
│   ├── MODULE_MAP.md                            unchanged except §6/§12 pointers
│   ├── DEPENDENCY_RULES.md                      unchanged; becomes single home
│   ├── MARKET_ANALYSIS_ARCHITECTURE.md          ← ARCHITECTURE_TECHNICAL + MULTITIMEFRAME (engine parts)
│   ├── TIME_AND_ALIGNMENT.md                    ← ARCHITECTURE_TECHNICAL + MULTITIMEFRAME (time/MTF parts)
│   ├── ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md   ← moved up from docs/reference/ root
│   └── DATA_REPRESENTATION_POLICY.md            ← DATA_REPRESENTATION_AUDIT §4/§5
├── workflows/
│   ├── README.md                                (NEW index — T005; carries the
│   │                                             "three capabilities, not a pipeline" preamble)
│   ├── RESEARCH_METHODOLOGIES.md                unchanged — still one document
│   ├── SIGNAL_RESEARCH.md                       ← WORKFLOWS_ARCHITECTURE §Signal Research
│   ├── STRATEGY_RESEARCH.md                     ← WORKFLOWS_ARCHITECTURE §Strategy Research
│   ├── STRATEGY_EXECUTION.md                    ← WORKFLOWS_ARCHITECTURE §Strategy Execution
│   └── MARKET_DATA.md                           ← modules/DATA_MODULE.md (workflow sections)
│                                                  + SYSTEM_OVERVIEW §3 Import Paths table
├── runbooks/
│   ├── README.md                                (NEW index — T005)
│   ├── LOCAL_BTC_FUTURES_DRY_RUN.md             unchanged
│   ├── AWS_BTC_FUTURES_DRY_RUN.md               unchanged
│   └── LIVE_PAPER_PIPELINE_INSPECTION.md        unchanged
└── modules/
    ├── README.md                                (NEW index — T005)
    ├── MARKET_ANALYSIS_MODULE.md                kept; content refresh needed (§6)
    ├── ANALYSIS_COMPONENT_CATALOG.md            ← STRATEGY_AUTHORING §4 + MARKET_ANALYSIS_MODULE table
    ├── MODEL_AUTHORING.md                       unchanged
    ├── STRATEGY_AUTHORING.md                    kept, trimmed to §1-3/§6-8 + Exit/Risk semantics
    ├── STRATEGY_EXAMPLES.md                     ← STRATEGY_AUTHORING §5
    ├── OPERATOR_CLI.md                          unchanged
    ├── PREDICTIVE_PROMOTION.md                  unchanged
    └── DASHBOARD_APPLICATION.md                 unchanged

  Leaves docs/reference/ entirely (needs explicit T004 approval):
    docs/planning/sprints/SPRINT_036_DATA_REPRESENTATION_AUDIT.md
        ← DATA_REPRESENTATION_AUDIT §1-3, §5.1, §6, §7, §8, §10
```

Counts: `system/` 9 + index (from 8), `workflows/` 5 + index (from 1),
`runbooks/` 3 + index (unchanged), `modules/` 8 + index (from 7). Net one file
leaves `docs/reference/`; nine files change name or folder; seven are untouched.

### 7.1 One-line rationale per changed file

| Target file | Change | Rationale (from what was read) |
|---|---|---|
| `system/DOMAIN_MODEL.md` | new, from `ARCHITECTURE_FOUNDATIONS.md` | That file's "Domains"/"Domain Relationships"/"Framework and User Space"/"Accepted Clarifications" sections are five bounded contexts with Owns/Does-Not-Own lists, entities, an aggregate, and 11 ubiquitous-language decisions — a domain model under a provenance name. |
| `system/ARCHITECTURE_PRINCIPLES.md` | new, from `ARCHITECTURE_FOUNDATIONS.md` | Its "Core Philosophy" + "Architectural Principles" sections are cross-cutting build rules, a different question from "what does each domain own"; keeping them in one 1,369-line file is why neither is findable. |
| `system/MARKET_ANALYSIS_ARCHITECTURE.md` | new, merge | `ARCHITECTURE_TECHNICAL` "Market Analysis Architecture"/"Market Analysis Engine" and `MULTITIMEFRAME` "Market Analysis Responsibilities"/"Categories"/"Features"/"Structures" state the same taxonomy twice; the engine has no file of its own today. |
| `system/TIME_AND_ALIGNMENT.md` | new, merge | Collapses four triplicated concepts (§2.1 rows 2–4 plus contract rolls) into one home: `observed_at`/`available_at`, `LAST_CLOSED_BAR`, the three timeframes, resampling as a graph node. |
| `system/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md` | moved from root | Cross-cutting policy (workspace ownership, alias-vs-identity, dedup, 12 invariants) constraining every analytical module — the same tier test T007 used to place `DATA_REPRESENTATION_AUDIT.md` in `system/`; currently stranded in an "Other" bucket. |
| `system/DATA_REPRESENTATION_POLICY.md` | new, split | §4/§5's canonical-carrier table, six directional rules and target primitives are durable binding policy; §1-3/§6-8's benchmarks at commit `f0a82c5`, PR numbers and Stage 0–6 status board are a Sprint 036 record that decays and duplicates a task board. |
| `workflows/SIGNAL_RESEARCH.md` | new, extract | `system/WORKFLOWS_ARCHITECTURE.md`'s "Signal Research" section is already a standalone ~420-line workflow narrative (scopes, inputs, dependency plan, dataset, reuse rule, 14 rules) filed in the wrong tier. |
| `workflows/STRATEGY_RESEARCH.md` | new, extract | Same file's "Strategy Research" section: composition rules, simulation, dataset, analytics, walk-forward, Monte Carlo, robustness, reuse rule. |
| `workflows/STRATEGY_EXECUTION.md` | new, extract | Same file's "Strategy Execution" section, including a runtime flow annotated with real as-built code pointers (`decision_step.py`, `live_signals.py`, `safety.py`, `paper_broker.py`). |
| `workflows/MARKET_DATA.md` | renamed from `modules/DATA_MODULE.md` | Post-reclassification its unique sections (§11 import, §12 query, §15 finalization, §16 publication, §23 validation, §27 prohibited designs) form one end-to-end pipeline; it names no package it owns and defers package facts to `MODULE_MAP` §5. |
| `modules/ANALYSIS_COMPONENT_CATALOG.md` | new, extract + merge | `STRATEGY_AUTHORING` §4 holds per-component semantics (warm-up, outputs, zero-denominator conventions incl. `momentum.stochastic`'s deliberate `50.0` divergence) under a filename that hides it; `MARKET_ANALYSIS_MODULE`'s table is stale at Sprint 005 and `MODULE_MAP` §6 crams the rest into one table cell. |
| `modules/STRATEGY_EXAMPLES.md` | new, extract | `STRATEGY_AUTHORING` §5 is ~450 lines of `build_strategy()` code the file itself labels "Worked examples"; removing it makes the convention (§1-3) readable. |
| `modules/STRATEGY_AUTHORING.md` | trimmed | Retains its own stated purpose — convention, no-sandbox trust model, error table, advisory imports, TD-025 blind spot — plus Exit/Risk model semantics, at roughly 250 lines instead of 831. |
| `system/MODULE_MAP.md` | two pointers | §12 "Dependency Rules" restates `DEPENDENCY_RULES.md` §1 without its enforced/unenforced distinction; §6's component cell duplicates the new catalog. |
| `system/ARCHITECTURE_FOUNDATIONS.md`, `ARCHITECTURE_TECHNICAL.md`, `MULTITIMEFRAME_MARKET_MODEL.md`, `WORKFLOWS_ARCHITECTURE.md` | **retired** | Every section is relocated by the rows above; nothing is deleted. These four names describe where content came from (four vision documents), not what it is about, which is the root cause of §2's triplication. |
| `docs/reference/README.md` | rewritten | Must index the new tree and drop the "Other" bucket; written last, after T007's moves land. |

### 7.2 What is explicitly *not* proposed

- No split of `workflows/RESEARCH_METHODOLOGIES.md` (T007's finding stands).
- No `modules/SIGNALS.md`, no `modules/EXECUTION.md`, no `modules/DATA.md` — no
  source content, and inventing them means writing new prose (D-S055-04).
- No new research-side runbooks, despite the gap in §5.3.
- No deletion of any content anywhere: every retirement in §7.1 is a
  redistribution, and T007's `git mv`/verbatim discipline applies to all of it.
- No fix for the six content problems in §6 — those need T003/T004, not a move.

---

## 8. Folder context-map assessment (informing T005, not implementing it)

| Folder | Files after T007 | Index needed? | What the index must do |
|---|---:|---|---|
| `system/` | 9 | **Yes — highest priority** | Nine files, nine different subjects, and this is the folder a fresh reader hits first. The index must be a **question→file** table, not a file list: "what does each domain own?" → `DOMAIN_MODEL`; "what may import what, and is it tested?" → `DEPENDENCY_RULES`; "what is the default higher-timeframe alignment policy?" → `TIME_AND_ALIGNMENT`; "which package implements X?" → `MODULE_MAP`; "what type should carry a price here?" → `DATA_REPRESENTATION_POLICY`. It must also state the reading order (`SYSTEM_OVERVIEW` first, always) and disambiguate the two meanings of "workspace" (§5.1). |
| `workflows/` | 5 | **Yes** | Must carry the "three independent capabilities, not a pipeline" framing (from `WORKFLOWS_ARCHITECTURE`'s Core Rule, which otherwise has no home) and — critically — draw the line between `RESEARCH_METHODOLOGIES` ("which methodology should I choose, and what question does it answer") and the four per-workflow files ("what are this workflow's scopes, contracts and persisted outputs"), per §5.2's overlap risk. |
| `runbooks/` | 3 | **Yes, but short** | Three files is below the threshold where an index earns its keep on count alone, but it earns it on *framing*: the index must say that all three cover one demo (local run / AWS deployment / pipeline verification) and that the safety boundary is identical in all three (simulated only, no credentials, no real orders). It should also state plainly that there are no research-workflow runbooks, so a reader stops looking — pointing at `modules/OPERATOR_CLI.md` instead. |
| `modules/` | 8 | **Yes** | The folder holds two different kinds of document and the filenames do not signal which: *implementation references* (`MARKET_ANALYSIS_MODULE`, `ANALYSIS_COMPONENT_CATALOG`, `PREDICTIVE_PROMOTION`, `DASHBOARD_APPLICATION`) and *operator/author-facing guides* (`MODEL_AUTHORING`, `STRATEGY_AUTHORING`, `STRATEGY_EXAMPLES`, `OPERATOR_CLI`). The index should group under those two headings, and state that domain-level questions belong in `system/DOMAIN_MODEL.md`, not here — otherwise readers will keep expecting a `SIGNALS.md`/`EXECUTION.md` that deliberately does not exist. |

Top-level `docs/reference/README.md` remains necessary and should shrink to the
four folders plus a one-line "when to open which", delegating detail to the four
new indexes. Its current "Other" section disappears with
`ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md`'s move.

---

## 9. Divergences from the maintainer's example, summarised

| # | Divergence | Why |
|---|---|---|
| 1 | Four of the example's five `workflows/` and three of its `modules/` filenames are **accepted**, but four `system/` files are added beyond the example (`ARCHITECTURE_PRINCIPLES`, `MARKET_ANALYSIS_ARCHITECTURE`, `TIME_AND_ALIGNMENT`, `DATA_REPRESENTATION_POLICY`) plus two moved in | The example's 4-file `system/` cannot absorb ~5,900 lines of real cross-cutting content without recreating today's unnavigable mega-files. Same precedent as T007 adding `DATA_REPRESENTATION_AUDIT.md` to a three-file guess. |
| 2 | `modules/` is organised by **deliverable surface**, not by domain — `SIGNALS.md`, `EXECUTION.md` and `DATA.md` are refused | No source content exists for a signal-module or execution-module implementation reference; those questions are answered by `system/DOMAIN_MODEL.md`, `workflows/`, and `MODULE_MAP`. Writing them means fabricating prose. |
| 3 | A **`runbooks/` tier the example does not have** is retained | Three documents that are purely "how do I deploy/run/troubleshoot" fit neither `workflows/` nor `modules/`; T007's reasoning re-verified against the actual files. |
| 4 | `workflows/` gets **five** files, not four — `RESEARCH_METHODOLOGIES.md` survives alongside the four example names | It is one deliberately comparative document (§1/§10/§11/§15 compare all six methodologies); splitting it duplicates §2/§3/§13 into every fragment. |
| 5 | One file is proposed to leave `docs/reference/` for `docs/planning/sprints/` | `DATA_REPRESENTATION_AUDIT.md` §6–§8 are a commit-pinned measurement record and a staged PR board — planning artifacts, not as-implemented reference. Flagged as the one cross-folder move requiring explicit approval. |

---

## 10. Handoff

T004 should decide, in this order:

1. **The `system/` re-cut** (§2, §5.1) — accept the nine-file subject-based
   split, or keep provenance-based files and accept the triplication.
2. **The four reversals of T007** (§3, §4.3, §5.2) — `SIGNAL_RESEARCH`,
   `STRATEGY_RESEARCH`, `STRATEGY_EXECUTION`, `MARKET_DATA` now have real
   source content; confirm they are extractions and not authoring.
3. **The `DATA_REPRESENTATION_AUDIT.md` cross-folder move** (§4.1) — the only
   proposal that touches a folder outside `docs/reference/`; fallback offered.
4. **`DOMAIN_MODEL.md` name ownership** — coordinate with T002 so
   `docs/vision/` and `docs/reference/system/` do not both claim it.
5. **The `RESEARCH_METHODOLOGIES` / `SIGNAL_RESEARCH` adjacency** (§5.2) —
   option (a) recommended.
6. **The six content defects in §6** — which are in scope for this sprint at
   all, versus logged for later.

Then T005 (indexes) and T007 (moves) may proceed, per D-S055-03.
