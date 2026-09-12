# Sprint 055 T003 — Planning/Decision Cross-Check of `docs/reference/` + `docs/vision/`

```text
Task:      S055-T003 (targeted cross-check, read-only)
Status:    DONE
Method:    PROBLEM_REGISTRY.md, TECHNICAL_DEBT.md, ROADMAP.md read in full;
           docs/adr/README.md index read in full; docs/reference/README.md and
           docs/vision/README.md read as indexes only. Individual ADR files and
           sprint docs opened ONLY where a named gap pointed at one (per
           D-S055-02) — see "Sprint/ADR files actually opened" below.
Scope:     CONTENT gaps only. Internal organisation of docs/reference/ and
           docs/vision/ is T001/T002's job and is deliberately not assessed here.
Output:    An input list for the T004 review gate and for T007/T008 execution.
           This document proposes NO prose for either doc tree and edits nothing
           under docs/reference/, docs/vision/, PROBLEM_REGISTRY.md,
           TECHNICAL_DEBT.md or ROADMAP.md.
```

## 0. How to read this

Each entry states: the **claim/fact**, where it **currently lives** (its source of
truth), what `docs/reference/`/`docs/vision/` **currently says** (reflects /
silent / contradicts), and what the **target IA should account for**.

Severity is about the cost of leaving the gap open, not implementation urgency:

```text
HIGH    a reader can currently be actively misled about what is built or decided
MEDIUM  a real, decided fact has no home in either tree; a reader must go to
        docs/planning/ or docs/adr/ to learn it
LOW     a pointer/attribution improvement; nothing is wrong, just hard to find
```

**Sprint/ADR files actually opened** (all others deliberately not read):
`ADR-0008`, `ADR-0014`, `ADR-0018` (partitioning + continuous-futures decision
sources), `docs/planning/DATA_MODULE_CLASSIFICATION.md`,
`docs/vision/DATA_MODULE_FUTURE.md`, `docs/planning/sprints/SPRINT_055.md`.
`S049_AVAILABILITY_FINDING.md` was located by grep and cited but only its
headline finding was read. No exhaustive sprint-doc mining was performed and
none is recommended (see §6).

---

## 1. The three named follow-ups (task brief items 4a–4c)

### G-01 — Partitioning policy: month-vs-day is a SETTLED ADR decision, not an open divergence · HIGH

**Claim/fact.** `docs/vision/DATA_MODULE_FUTURE.md` §19 gives **month** as the
default partitioning for intraday bars, finalized live bars and continuous
futures bars, with a worked `bars/1m/year=2026/month=06/data.parquet` example
and §19.2 explicitly stating "daily partitioning is normally too granular".

**Where the real decision lives.** Two **ACCEPTED** ADRs, not an accident:

- **ADR-0014** (Sprint 011) §"Day-partitioned Parquet layout": partition key =
  UTC calendar day of `event_at`, `partitions/day=YYYY-MM-DD/trades.parquet`,
  with "day partitions support partition pruning on query" listed as a
  consequence.
- **ADR-0018** (Sprint 015): `partition key = session_date (CME RTH, via
  CmeEsRthSessionResolver)`; `partitions/session_date=*/bars.parquet`; and it
  *already records the divergence itself* in Consequences — "`session_date`
  partitions diverge from Sprint 011 UTC `day=` layout".
- **ADR-0008** (Sprint 002) Consequences: "partitioning, compaction and DuckDB
  adapters remain future work" — i.e. the Phase 2A/2F published OHLCV path was
  never partitioned at all.
- `ROADMAP.md` §6 Phase 2C already states this correctly: "Default
  partitioning: by day (trades, quotes) for legacy single-contract import;
  **by `session_date` for contract-layer datasets** (Sprint 015)."

**Verified in code** (`infrastructure/storage/paths.py`): **three** coexisting
physical layouts, none month-based — an unpartitioned `bars.parquet` (line
219), `session_date=<date>/bars.parquet` OHLCV partitions (line 246),
`day=<date>` legacy trade partitions (line 446), and `session_date=` contract/
continuous trade partitions (lines 434, 462).

**What the docs currently say.** `DATA_MODULE_FUTURE.md` §19.4 carries a
"Verified divergence from implementation" note added during Sprint 054's
reclassification. It is **accurate but mis-framed on two counts**:

1. It points only at `docs/planning/DATA_MODULE_CLASSIFICATION.md` and says the
   divergence "is worth a maintainer decision on whether to update this default
   or treat the divergence as a gap" — but the maintainer decision **already
   happened**, twice, in ADR-0014 and ADR-0018, both ACCEPTED. Presenting a
   settled ADR outcome as an open question is the misleading part.
2. It says the actual key is `session_date=` "for both OHLCV bars and trades",
   which under-describes the real three-layout picture above (notably the
   unpartitioned `bars.parquet` path that Phase 2A/2F Binance imports use).

**Target IA should account for.** `docs/vision/`'s partitioning text must not
be the authority for a question two ACCEPTED ADRs have answered. Options for
T004: (a) reduce §19 to the genuinely-still-open parts (compaction policy, row
groups, quarterly compaction) and point the *default* question at
ADR-0008/0014/0018 plus `ROADMAP.md` §6; or (b) move the as-built layout
description into `docs/reference/modules/DATA_MODULE.md` (which currently says
nothing about physical partition keys) and leave `docs/vision/` with the
forward-looking policy only. Either way the "awaiting a maintainer decision"
framing should go.

**Registry check (task brief).** No `PROBLEM_REGISTRY.md` or
`TECHNICAL_DEBT.md` entry exists for this. **That is correct and no entry
should be created** — this is not an unresolved problem or an accepted
shortcut; it is a documented decision whose consequence ADR-0018 already
records. `SPRINT_055.md` §2's out-of-scope bullet asserting these findings are
"tracked in `PROBLEM_REGISTRY.md`/`TECHNICAL_DEBT.md`" is **factually wrong**
for this item — see G-03b.

---

### G-02 — Continuous-futures roll/adjustment: a deliberate ADR-0018 MVP scope, not an untracked gap · HIGH

**Claim/fact.** `DATA_MODULE_FUTURE.md` §21 enumerates 4 possible roll policies
and an adjustment-method axis (backward/forward × diff/ratio × unadjusted), with
§21.2 examples treating "volume roll / backward ratio / v3" as a routine
dataset identity and §21.3 showing a
`derived/futures/NQ/continuous/volume_roll_backward_ratio/` storage path.
`DATA_MODULE_CLASSIFICATION.md` "Notable findings" records that only 1 roll
policy and 0 adjustment methods exist.

**Where the real decision lives.** **ADR-0018 (ACCEPTED, Sprint 015)**, which
decided this explicitly rather than leaving it unfinished:

- `price_adjustment = none` (§ADR-0018 line 73),
- "Trade and orderflow facts used for simulation and execution research are
  **not** back-adjusted",
- "Back-adjusted analytical series are a separate future artifact with distinct
  `source_id`",
- Consequences: "MVP limited to NQ trades / volume roll / no back-adjust".

**What the docs currently say.** `DATA_MODULE_FUTURE.md` §21.3 carries a Sprint
054 note ("`market/continuous/` implements one roll policy
(`VolumeRthCloseRollPolicy`) and no adjustment methods today") that points at
`DATA_MODULE_CLASSIFICATION.md` §21 — **but not at ADR-0018**, which is the
actual decision source and the only place the *rationale* and the *intended
future shape* ("separate future artifact with distinct `source_id`") are
recorded. A reader of §21 today learns that reality is narrower, but not that
the narrowing was decided, why, or what the sanctioned expansion path is.

**Target IA should account for.** §21's future matrix should cite ADR-0018 as
its baseline and distinguish "decided out of v1 scope, expansion path defined"
(back-adjustment) from "never evaluated" (calendar/open-interest/fixed-date roll
policies). The as-built side — one policy, `continuous_manifest.json` roll
lineage, the `is_roll_boundary`/`roll_id` columns from ADR-0018 — belongs in
`docs/reference/modules/DATA_MODULE.md`, which is currently silent on it.

**Registry check (task brief).** No `PROBLEM_REGISTRY.md` or
`TECHNICAL_DEBT.md` entry exists. Unlike G-01, a **`TECHNICAL_DEBT.md` entry
would be defensible here** ("continuous futures supports one roll policy and no
price adjustment"; reason = ADR-0018 MVP scoping; safe boundary = no workflow
may assume back-adjusted continuous series exist; repayment trigger = the first
research question needing a non-volume roll or an adjusted series). Compare
TD-023, TD-027 and TD-029, all of which are exactly this shape. **Flagged, not
created** — creating registry entries is out of T003's scope and out of Sprint
055's scope entirely (§2 out-of-scope bullet 4).

---

### G-03 — PRB-020 (Strategy Research family asymmetry): correctly reflected in `docs/vision/`, partially contradicted in `docs/reference/` · MEDIUM

**Claim/fact.** `PROBLEM_REGISTRY.md` **PRB-020** (OPEN, MEDIUM, logged
2026-09-03 during Sprint 054 T003b): Signal Research has
`research/signal_research/family_planning.py` +
`research/datasets/signal_research_family.py` with real
`candidates_generated`/`evaluated`/`skipped` bookkeeping; Strategy Research has
**no** equivalent, and `WORKFLOWS_AI_ADR.md` §4.5 presents `experiments:` YAML
as already-working syntax.

**`docs/vision/WORKFLOWS_AI_ADR.md` — reflects it, does not present it as
solved.** Verified: §4.5 carries a MIXED classification note stating outright
"The `experiments:` YAML example below is presented as already-working syntax
but has no implementing module"; §4.14 Strategy Families carries a FUTURE note
("there is no Strategy-Research-side 'family' concept in code at all", plus the
observation that §4.20's suggested `families/` storage subfolder is itself
inconsistent); §3.12 correctly narrows the planner-telemetry claim. **No
correction needed to the substance.**

**Gap (a) — neither tree cites PRB-020 by ID.** All three notes point at
`SPRINT_054_T003b_WORKFLOWS_AI_ADR_ARCHITECTURE_CLASSIFICATION.md`, a
sprint-scoped artifact. A grep for `PRB-020` across `docs/reference/` and
`docs/vision/` returns **zero hits**. The durable tracking ID is invisible from
the documents the problem is about. Contrast PRB-007, which
`docs/reference/modules/MARKET_ANALYSIS_MODULE.md` §148 cites by ID — the
pattern already exists in the repo.

**Gap (b) — `docs/reference/system/WORKFLOWS_ARCHITECTURE.md` has two residual
"family" claims on the Strategy Research side.** This is the as-built reference
tier, so these read as descriptions of built behaviour:

- line 816 (Strategy Research → Reuse Rule): "New rankings, filters and
  **family analyses** should not trigger a new backtest automatically."
- line 834 (Strategy Execution → Core Question, what it does *not* answer):
  "which **strategy family** is most robust."

Neither is flagged; both name a concept PRB-020 established does not exist for
Strategy Research. (Line 115's generic "a new report, filter, ranking or family
analysis" in the cross-cutting Computation/Analytics section is defensible,
since Signal Research families are real — but it is ambiguous as written.)

**Correctly clean, for the record.** The `experiments:` YAML block at
`WORKFLOWS_ARCHITECTURE.md` lines 284–301 sits under **Signal Research →
Independent Experiment Expansion**, where `FamilyExperimentPlan` genuinely backs
it. That one is fine and must not be "fixed" by T007. Strategy Analytics
(lines 717–738) correctly omits family analysis from its metric list.

**Target IA should account for.** (i) A convention for citing open PRB/TD IDs
from the doc that carries the claim, so classification findings survive their
originating sprint doc; (ii) T007 flagging or qualifying the two
`WORKFLOWS_ARCHITECTURE.md` family references — verbatim-move discipline
(D-S055-04) means this is a T004 call, not a silent edit.

---

### G-03b — `SPRINT_055.md` §2 states these findings are registry-tracked; they are not · MEDIUM

`SPRINT_055.md` §2, out-of-scope bullet 4, says the partitioning-policy and
continuous-futures findings are "tracked in
`PROBLEM_REGISTRY.md`/`TECHNICAL_DEBT.md`". **Neither appears in either
register** (verified by full read of both). §7 follow-up bullet 3 repeats the
implication ("the underlying code/decision work is tracked separately").

Per G-01 this is *harmless* for partitioning (nothing needs tracking — an ADR
decided it) but *substantive* for continuous futures (G-02's proposed TD entry
does not exist). Reported as a planning-doc accuracy gap for the maintainer;
not fixed here, since T003 is read-only with respect to the registers and the
sprint file's §2 scope statement is maintainer-owned.

---

## 2. `PROBLEM_REGISTRY.md` — entries whose status the doc trees do not reflect

### G-04 — S049-T001's finding (the executor does NOT enforce inference-time `available_at`) is absent from the Market Analysis reference docs · HIGH

**Fact.** `ROADMAP.md` §13F: "S049-T001 verified line-by-line that the executor
does not enforce inference-time `available_at` rejection today (`executor.py`,
`planner.py`, `assembler.py` all checked; **no such mechanism exists**)".
`docs/adr/README.md` carries **ADR-0030 — Inference-Time Availability
Enforcement, PLANNED**. Full finding: `S049_AVAILABILITY_FINDING.md`.

**What the docs say.** `docs/reference/modules/PREDICTIVE_PROMOTION.md` §310–312
records it — but only as an *out-of-scope note for the promotion module*. The
documents a reader would actually consult about executor semantics do not
mention it and read as though availability is enforced:

- `docs/reference/system/ARCHITECTURE_TECHNICAL.md` line 1377, in a numbered
  rules list: "Higher-timeframe alignment uses legal `available_at` semantics";
  line 947: "use the latest result whose `available_at <= evaluation
  timestamp`"; line 163: "`available_at` identifies when the output **may
  legally be consumed**".
- `docs/reference/modules/MARKET_ANALYSIS_MODULE.md` line 163 documents
  look-ahead handling via `LAST_CLOSED_BAR` + backward `join_asof`.
- `ROADMAP.md` §16 states a **Temporal Correctness Gate**: "No result uses
  information before its legal `available_at`."

Both statements are true *for batch MTF alignment* and both are silent about the
absence of any executor-level rejection mechanism. Nothing here is false; the
composite impression is.

**Target IA should account for.** The as-built distinction — *alignment honours
`available_at`; the executor does not reject a component that reads an
unavailable feature* — is a first-class architectural fact that today lives only
in `ROADMAP.md` §13F, one sprint artifact, and a promotion-module aside. It
needs a home in the Market Analysis reference tier, with a pointer to ADR-0030
(PLANNED). This is the single highest-value content gap found by T003.

### G-05 — PRB-013 (Research/runtime parity is not measurable) has no reference-tier home · MEDIUM

`PROBLEM_REGISTRY.md` PRB-013 (OPEN, **HIGH**): parity criteria and tests
between Research and Strategy Execution are not defined. `docs/reference/`
mentions research/runtime parity only as a *motivation* for `available_at`
(`ARCHITECTURE_TECHNICAL.md` line 170; `MULTITIMEFRAME_MARKET_MODEL.md` line
563) and never states that no parity suite exists. `PREDICTIVE_PROMOTION.md`'s
"parity" hits are a *different* parity (offline NumPy vs sklearn / vs runtime,
ADR-0029) and could easily be misread as covering PRB-013. Target IA: the
execution/workflow reference should name this open gap and disambiguate the two
uses of "parity".

### G-06 — PRB-004 (`user_data` component discovery) is unresolved; neither tree says so · MEDIUM

PRB-004 (OPEN, HIGH). `ROADMAP.md` §7 Phase 3 completion criteria carries an
explicitly unchecked box: "`[ ]` working components can be loaded from
controlled user space (deferred — no `user_data/` loader in MVP)". Meanwhile
`docs/reference/modules/STRATEGY_AUTHORING.md` documents a *strategy_file*
loader (ADR-0027) — a different mechanism for a different object. A reader can
plausibly conclude user-space **component** loading exists because user-space
**strategy** loading does. Target IA: state the boundary explicitly where the
component catalog is documented.

### G-07 — PRB-017 (test/research data tiers) is cited from `docs/vision/` only · LOW

`DATA_MODULE_FUTURE.md` line 87 cites PRB-017 and `ROADMAP.md` §15.1. Nothing
in `docs/reference/` mentions the Tier 1/2/3 model, although Tier 1 fixtures are
what every documented workflow actually runs on. Target IA: decide whether the
tier model is vision (aspiration) or reference (current CI reality) — it is
arguably both, split at Tier 1/Tier 2.

### G-08 — PRB-018 / PRB-019 have no reference-tier home because no contributor/testing reference doc exists · LOW

Both are LOW-severity environment/tooling traps (torch smoke-test false failure
without the `dl` extra; `mypy .` duplicate `test_config`) that
`PROBLEM_REGISTRY.md` records as having **repeatedly cost review time across
Sprints 044–046**. `docs/reference/README.md`'s index has no testing/tooling/
contributor-workflow entry at all, so there is nowhere for a "known false
failures" note to live. Target IA: T001 should decide whether
`docs/reference/` gains a tooling/testing index entry, or whether these stay
`CLAUDE.md`/`AGENTS.md` content. (Note: this task's own pre-push guidance
depends on PRB-018 being known — evidence the gap is real.)

### G-09 — PRB-015 / TD-010 name doc consistency as the open problem this sprint exists to mitigate · LOW

PRB-015 (PARTIALLY_MITIGATED) and TD-010 (ACCEPTED, MEDIUM — "documentation
consistency is reviewed manually before automation") are the registry entries
Sprint 055 is a payment against. Neither doc tree references them. Target IA /
T010: consider whether the validation re-run's 6 checks are the beginning of
TD-010's "lightweight checks for deprecated terms, required files and broken
internal references", and whether PRB-015's resolution criteria can be
partially closed by this sprint. **Decision for the maintainer at T004, not an
assumption.**

---

## 3. `TECHNICAL_DEBT.md` — entries whose limitations the doc trees do not reflect

Overall the TD register is **well reflected**: TD-011/012/013/014/015/016/019
are cross-referenced from `DATA_REPRESENTATION_AUDIT.md` (including a full
status table at lines 1026–1032), TD-023 from `OPERATOR_CLI.md` §5 and §277,
TD-021/022/029 from `PREDICTIVE_PROMOTION.md`, TD-025/026 from
`STRATEGY_AUTHORING.md`, TD-028 from `MODULE_MAP.md` line 408. The gaps below
are the exceptions.

### G-10 — TD-027 (delay stress rejects bracket exits) is not reflected where robustness is documented · HIGH

`TECHNICAL_DEBT.md` TD-027 (ACCEPTED, MEDIUM): the entry/exit **delay stress
dimension raises `ValidationError` for any `BracketExitModel`**, deliberately.
`ROADMAP.md` §13F additionally records this as a live constraint on Phase 14B's
mandatory robustness plan.

`docs/reference/workflows/RESEARCH_METHODOLOGIES.md` §7 Robustness Research
lists "stress testing" and "stress scenarios" among available capabilities
(lines 348–375) with **no mention of the limitation** — and TD-027 does not
appear anywhere in `docs/reference/`. Since Phase 13 shipped `BracketExitModel`
as a headline capability, the most likely reader is exactly the one who will hit
the refusal. Target IA: the robustness workflow doc must carry this, in the
style `OPERATOR_CLI.md` already uses for TD-023 ("Known limitation — TD-023
(binding)").

### G-11 — TD-022's Sprint 049 disposition is subtler than the reference doc conveys · MEDIUM

`TECHNICAL_DEBT.md` TD-022's "Sprint 049 disposition" is emphatic: promoted
artifacts got portability, **research-run blobs (`models/fold_{n}.bin`) are
completely unchanged** — "A run that is never promoted is exactly as opaque as
it was before this sprint. Do not describe TD-022 as repaid."
`PREDICTIVE_PROMOTION.md` cites TD-022 in its References (line 356) but the
document's subject is the promotion path, so a reader who only reads
`docs/reference/` can come away believing predictive artifacts are portable in
general. Target IA: wherever Predictive Research *runs* (as opposed to
promotion) are documented, the un-repaid half belongs there.

### G-12 — TD-030 (nested `user_data/` not gitignored) has no reference-tier home · LOW

TD-030 (ACCEPTED, LOW) documents a real, data/credential-leak-adjacent operator
trap: a relative `storage_root` resolved from a non-repo-root cwd creates an
**untracked, not ignored** `<subdir>/user_data/`. It is documented in
`apps/cli/CLAUDE.md` only. `docs/reference/modules/OPERATOR_CLI.md` — which
already has a "Known limitations" section for TD-023 — does not mention it, nor
do the runbooks. Target IA: an operator-gotcha slot in the CLI module reference
and/or the runbooks index.

### G-13 — Phase-conditional planned debt (TD-005, TD-006, TD-007, TD-009) is invisible to both trees · LOW

Four ACCEPTED entries describe boundaries for capabilities that are partly or
wholly unbuilt (in-memory EventBus, local-Parquet-only storage, calendar library
wrapping — related to PRB-007 which *is* cited — and the limited backtest fill
model, HIGH priority, "no claim of live parity is allowed"). None is referenced
from `docs/reference/` or `docs/vision/`. TD-009 is the notable one: it forbids
live-parity claims about the simulator, which is a constraint on how the
Strategy Research reference doc may describe itself. Target IA: at minimum,
TD-009's boundary should be visible near the simulation/backtest description.

---

## 4. `ROADMAP.md` — durable content with no home, and one governance blocker

### G-14 — `ROADMAP.md` has NO document-level `Status:` field · HIGH (process, blocks T004→T005)

`ROADMAP.md` §1–§3 carry no `Status: Accepted`/`Proposed` header. The only
`Status:` in the file is **§14 Research Data Strategy — "Status: ACCEPTED
(2026-07-12)"**, scoped to that section alone. Per the `governance` skill and
this project's own architect checklist, a sprint must not be opened against a
roadmap that is not `Status: Accepted`; T004 is precisely such a gate, and
`SPRINT_055.md` itself is `Status: PLANNED — requires maintainer approval`.

This is a **planning-hygiene blocker to surface at T004**, not something T003
fixes (editing `ROADMAP.md` is explicitly forbidden for this task, and an agent
may never set `Accepted` itself). The maintainer should either add the header
or state that the roadmap's acceptance is tracked elsewhere.

### G-15 — Phase 2B is labelled both COMPLETE and PLANNED inside `ROADMAP.md` · MEDIUM

§3's track list: "Phase 2B — Historical Archive Import Foundation **COMPLETE**
(Sprint 011 trades; OHLCV archive PLANNED)". §6's section heading: "## Phase 2B
— Historical Archive Import Foundation **(PLANNED)**", with a "First vertical
slice (recommended Sprint 011)" block written in the future tense as though
Sprint 011 had not happened. `DATA_MODULE_CLASSIFICATION.md` independently
found the same class of staleness in `DATA_MODULE.md`'s own roadmap-alignment
subsection (since removed — verified: no `Phase 2`/`PLANNED`/`GATED` strings
remain in `docs/reference/modules/DATA_MODULE.md`).

Consequence for this sprint: **T001/T002 must not use `ROADMAP.md` §6 as the
authority for Phase 2B/2C build status** when deciding what `docs/reference/`
should claim. `docs/reference/system/MODULE_MAP.md` §5 and the code are the
reliable sources. Fixing `ROADMAP.md` is out of scope here.

### G-16 — `ROADMAP.md` §16 "Cross-Phase Architectural Gates" is durable normative architecture living in a planning file · MEDIUM

Seven named gates — Reproducibility, Temporal Correctness, Domain Ownership,
Workflow Independence, User-Space, Complexity, Test — each a binding
cross-cutting constraint ("A phase must not be considered complete if it
violates these gates"). Grep finds no equivalent list in `docs/vision/` or
`docs/reference/`. By the `product-architecture` division of responsibility this
is `ARCHITECTURE_FOUNDATIONS.md` material (principles/constraints), not roadmap
material. **Strong candidate for the target IA**; note the Temporal Correctness
Gate is exactly what G-04 shows is not enforced by the executor, so moving it
without G-04's caveat would make things worse, not better.

### G-17 — `ROADMAP.md` §14 "Research Data Strategy" (Status: ACCEPTED) is accepted architecture living in a planning file · MEDIUM

§14 is the only part of `ROADMAP.md` explicitly marked ACCEPTED. It contains
durable, decision-grade content: *store facts not indicators*; vendor
independence ("providers terminate at importer boundaries only; the framework
must not depend on any vendor API at runtime"); MBP-10 rejected as a primary
dataset with a stated reason (~2 TB/year); options snapshots preferred over
option tick streams; the per-provider acquisition table. This is vision-tier
material by any reading. Neither `docs/vision/DATA_MODULE_FUTURE.md` nor
`docs/vision/ARCHITECTURE_FOUNDATIONS.md` carries it.

### G-18 — `ROADMAP.md` §15.2 "Live Market Data Entry Gate" is a durable decision rule with no doc-tree home · LOW

Five named opening conditions plus an explicit "**not sufficient alone:** a
positive backtest does not justify live feed cost". Same character as §16/§17:
a standing rule, not a schedule. Currently reachable only via the roadmap.

### G-19 — In-flight phase status: Sprints 049 and 051 are COMPLETE but "final integration PR to `main` pending" · LOW

`ROADMAP.md` §13F and §13G both note the integration PR is pending. This is a
consistency trap for T001/T002: `docs/reference/modules/PREDICTIVE_PROMOTION.md`
and `MODULE_MAP.md` §604 describe Phase 14A machinery as built. Whether the
reference tier should describe sprint-branch state as as-built is a real
question for T004 — flagged, not answered. Also note **Phase 14 and Phase 15 are
each explicitly NOT complete** (14B/Sprint 050 and 15B/Sprint 052 unplanned);
neither doc tree should imply an end-to-end promoted-model path exists.

---

## 5. `docs/adr/README.md` index — ACCEPTED/PLANNED ADRs vs the doc trees

### G-20 — The four PLANNED ADRs are never cited from `docs/reference/` · MEDIUM

Grep for `ADR-0004`, `ADR-0009`, `ADR-0010` across `docs/reference/`: **zero
hits**. Only ADR-0030 is cited (once, in `PREDICTIVE_PROMOTION.md`; see G-04
for why that placement is insufficient).

- **ADR-0004** — Independent Research and Execution Workflows: the workflow
  independence rule it would formalise *is* asserted in
  `WORKFLOWS_ARCHITECTURE.md` and `RESEARCH_METHODOLOGIES.md` §104–108, with
  nothing saying it is not yet an accepted ADR.
- **ADR-0009** — Batch Backtest vs Replay Execution: relevant to
  `WORKFLOWS_ARCHITECTURE.md`'s Strategy Execution section, which per Sprint
  054's own header note describes a runtime where **only the `DRY_RUN` path
  exists**.
- **ADR-0010** — Working Component and Model Fingerprints: the open remainder of
  PRB-002 (`implementation_hash`/transitive dependency hashing), while
  `MARKET_ANALYSIS_MODULE.md` documents the parameter-fingerprint half.

Target IA: a convention for marking a documented rule as "asserted in prose,
ADR PLANNED" so the reference tier does not read as more settled than it is.

### G-21 — The ADR Backlog's six unnumbered established decisions are described in prose but not identified as awaiting ADRs · MEDIUM

`docs/adr/README.md` "ADR Backlog" lists six *established* decisions with no ADR
number: Strategy Composition (`Market × Signal × Exit × Risk`), Position Sizing
inside the Risk Model in v1, `MarketFieldReference` as the only controlled
model-expression market access, Persistent Research Datasets, Hybrid
Communication, Configuration Boundaries (Pydantic at boundaries only). All six
are described somewhere in `docs/reference/`/`docs/vision/` (verified by grep:
`WORKFLOWS_ARCHITECTURE.md`, `ARCHITECTURE_FOUNDATIONS.md`,
`ARCHITECTURE_TECHNICAL.md`, `MULTITIMEFRAME_MARKET_MODEL.md`), but **nothing
links the prose to the backlog**, so a reader cannot tell which paragraphs carry
binding-decision weight. Note the overlap with TD-004 (Position Sizing in the
Risk Model) and PRB-011 (`MarketFieldReference` bypass risk) — the same decision
appears in three registers and one prose tree with no cross-links.

### G-22 — `MARKET_ANALYSIS_WITH_DECISIONS.md` D-001–D-036 vs the ADR-MA-* set is unmapped · MEDIUM

`docs/adr/README.md` states: "Market Analysis binding decisions D-001–D-036
remain authoritative in `docs/vision/MARKET_ANALYSIS_WITH_DECISIONS.md`. Sprint
003 materialized the engine subset above as accepted ADRs." **Which D-numbers
became which ADR-MA-* is recorded nowhere.** A reader wanting the authority for
a Market Analysis rule has two overlapping sources and no map. Scattered
individual references exist (TD-012 cites D-027; TD-013 cites D-004/D-005;
TD-015 cites D-011) but only from the debt register.

This is a **vision-tier IA problem squarely in T002's scope** — flagged here
because the mapping is a *content* deliverable, and building it is real work
that T004 must budget for rather than assume falls out of a file move.

### G-23 — ADR status-vocabulary reconciliation (Sprint 054 T006a) is not reflected in `docs/vision/` beyond the retirement note · LOW

`docs/adr/README.md`'s Status Model section records that
`WORKFLOWS_AI_ADR.md` §7.4's competing six-status vocabulary was retired and the
richer 9-section ADR template was **not** adopted. `WORKFLOWS_AI_ADR.md` §7 now
carries a pointer. Verified as consistent — **no gap**, recorded here so T002
does not re-open a question Sprint 054 already closed.

---

## 6. Recommendation on sprint-doc mining (D-S055-02 checkpoint)

**Exhaustive mining of the ~106 sprint docs is NOT recommended, and T003 did
not do it.** Every gap above was reachable from the four planning/decision
sources plus three targeted ADR reads. The two named `DATA_MODULE.md` findings
in particular resolved *fully* against ADR-0008/0014/0018 — the decisions were
in the ADR tree the whole time, and the reclassification notes simply did not
cite them.

Two observations for the maintainer, offered rather than acted on:

1. **The recurring failure mode is citation, not discovery.** G-01, G-02, G-03a,
   G-04, G-20 and G-22 are all the same shape: a fact is correctly recorded
   *somewhere* and the document that carries the claim points at the wrong
   place, a sprint-scoped artifact, or nothing. A T005/T006 index convention
   that requires "authority: ADR-XXXX / PRB-XXX / TD-XXX" next to
   status-bearing claims would prevent recurrence more cheaply than any
   reorganisation. This is also the concrete, testable form of TD-010's
   repayment direction.
2. **Sprint-scoped artifacts are being used as durable authorities.**
   `SPRINT_054_T003b_...md`, `DATA_MODULE_CLASSIFICATION.md`,
   `S049_AVAILABILITY_FINDING.md` and `S051_BTC_DATA_INVENTORY.md` are all cited
   from `docs/reference/`/`docs/vision/`/`ROADMAP.md` as sources of truth, while
   Sprint 053 Phase E's sprint-doc **archival** backlog remains open (see
   `SPRINT_055.md` §7). Archiving a sprint doc that a reference document depends
   on would break these citations. Worth a T004 decision on whether such
   findings should be promoted out of `sprints/` before archival resumes.

---

## 7. Summary

```text
Total gaps: 23   (G-01..G-23, incl. G-03b)

By severity:  HIGH 5     G-01, G-02, G-04, G-10, G-14
              MEDIUM 11  G-03, G-03b, G-05, G-06, G-11, G-15, G-16, G-17,
                         G-20, G-21, G-22
              LOW 7      G-07, G-08, G-09, G-12, G-13, G-18, G-19, G-23
                         (G-23 is a confirmed non-gap, recorded to prevent rework)

By nature:    mis-attributed / uncited authority   G-01, G-02, G-03, G-04,
                                                   G-20, G-21, G-22
              limitation not stated where the
                capability is documented           G-04, G-10, G-11, G-13
              durable content stranded in
                docs/planning/                     G-16, G-17, G-18
              open problem with no doc-tree home   G-05, G-06, G-07, G-08, G-09,
                                                   G-12
              planning-doc accuracy / process      G-03b, G-14, G-15, G-19

By source:    PROBLEM_REGISTRY.md   G-03, G-04, G-05, G-06, G-07, G-08, G-09
              TECHNICAL_DEBT.md     G-02, G-10, G-11, G-12, G-13
              ROADMAP.md            G-14, G-15, G-16, G-17, G-18, G-19
              docs/adr/README.md    G-01, G-20, G-21, G-22, G-23
              SPRINT_055.md itself  G-03b
```

**Highest-value items for T004 to rule on, in order:** G-04 (executor
availability enforcement — the only gap where a reader can conclude a safety
property holds when it does not), G-10 (TD-027 absent from the robustness
workflow doc), G-01/G-02 (both settled by ACCEPTED ADRs that the vision doc does
not cite), G-14 (roadmap has no acceptance status — a governance precondition
for this very sprint), and G-16/G-17 (durable normative content stranded in
`ROADMAP.md`).

**Nothing in this document should be written into `docs/reference/` or
`docs/vision/` before T004 approves it.** Several entries (G-01, G-02, G-03b,
G-14, G-15) call for changes to files this sprint places out of scope entirely
— those are maintainer referrals, not T007/T008 work items.
