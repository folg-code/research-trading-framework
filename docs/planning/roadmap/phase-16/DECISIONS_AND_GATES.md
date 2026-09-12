# Phase 16 decisions and gates

Return to the [Phase 16 index](../PHASE_16_QUANT_WORKBENCH.md).

<a id="13h8"></a>
## 13H.8 — Binding rules for the whole phase

```text
ONE catalog. Market Analysis components stay neutral analytical facts. No
    "ML feature" concept, no parallel feature library, no interpretation
    baked into a component
The SIMULATOR owns PnL. Entries, exits, fills, slippage, commissions, sizing,
    the trade ledger and the equity curve stay in Strategy Research. A
    prediction is never a trade
ML enters simulation ONLY through explicit strategy semantics (a declared
    score condition), never by loading model binaries inside Strategy Research
The DASHBOARD stays read-only over persisted artifacts: no fitting, no metric
    recomputation, no research-engine import, no silent promotion, no
    "validated" claim
LEAKAGE GUARDS are never relaxed to accommodate a new sample kind. ADR-0023
    §4 is strengthened or unchanged
CI stays synthetic-only and network-free (ADR-0023 §8 untouched)
NO REGISTRY appears as a side effect. ADR-0024 condition 5's negative
    constraint holds for the whole phase; TD-021 is repaid by confirming it
    against a real consumer, not by building the thing it forbids
NO WORKFLOW in this phase depends on reloading models/fold_{n}.bin (TD-022's
    safe operating boundary, unchanged)
THE FAMILY ALLOW-LIST is widened only behind an accepted ADR, and only in 16G
    (TD-029, Q6 = Option B). Until then the named refusal in
    infrastructure/ml/promotion.py is the only gate, and 16C additionally
    refuses a non-promotable family as a strategy gate at config load time
NO SILENT PRUNING in any planner this phase builds (PRB-012)
A NEGATIVE result is a deliverable. No increment is repaired by adding
    features until something sticks
Phase 15B / Sprint 052 is neither re-scoped nor absorbed (§13H.0), and
    remains separately gated on its own maintainer approval
APPROVING THIS PHASE IS NOT OPENING A SPRINT. Every increment still needs its
    own SPRINT_0XX.md and Wave 0 decisions before implementation
No increment of this phase constitutes trading approval of anything
```

---

<a id="13h9"></a>
## 13H.9 — Anticipated ADRs (none written; not required by phase approval)

| # | Increment | Decision | Why it is ADR-worthy |
|---|---|---|---|
| 1 | 16B | `SampleSpec` contract shape + `PredictiveTask` taxonomy | Every later increment depends on it; changing it later breaks persisted specs and `definition_hash` comparability |
| 2 | 16C | **Score delivery boundary** — how a model score reaches the simulator without coupling Strategy Research to model artifacts, and how a strategy config *references* its scorer (TD-021/TD-022 repayment surface) | Directly governs the phase's central boundary and decides whether ADR-0024's no-registry constraint survives a machine consumer |
| 3 | **16G** | **Tree/neural promoted-artifact serialization** — the version-pinned joblib/ONNX-style path TD-029's Repayment Direction prescribes | Changes the dry-run/live **runtime deployment footprint**, which ADR-0029 exists to keep at zero. Assigned to 16G by the resolved §13H.12 Q6 (Option B); it is explicitly **not** 16C's |
| 4 | 16E | Confirm or depart from Q4's default direction (port Signal Research's family contract) — with PRB-012's planner-limit defaults and the Q8 non-retrofit boundary recorded in its consequences | PRB-020 explicitly asks for this decision, and Q4 set a default, not a mandate |
| 5 | 16G | Promotion-candidate manifest and its relation to ADR-0024 / ADR-0029, including PRB-013's accepted parity tolerances | Touches the execution boundary and an existing accepted decision |

### Are ADR #2 and ADR #3 the same decision?

**No — they are two decisions, and this section says so deliberately.** The
Q6 resolution makes the separation structural: they now live in different
increments.

- **#2 is a research-side boundary decision (16C).** Its question is: what does
  Strategy Research *consume* at simulation time — a pre-materialized score
  column joined under `available_at`, or an in-process call to a loaded
  model? Its blast radius is the Strategy Research / Predictive Research
  boundary. It changes no deployment artifact and adds no runtime dependency.
- **#3 is a deployment-footprint decision (16G).** Its question is: can a
  fitted tree or neural estimator become a portable, version-pinned artifact
  that is safe to load *outside* the research process at all? Its blast radius
  is the dry-run/live runtime image — ADR-0029's entire rationale was keeping
  scikit-learn, XGBoost/LightGBM/CatBoost and torch out of it.

They are related but not equivalent, and under Option B the relationship is
one-directional and settled:

```text
16C's answer to #2 must not require #3. If #2's chosen mechanism would make a
    non-promotable family necessary for the research loop, that is a design
    failure of #2 under Option B, not a trigger to pull #3 forward
Because #3 is not written, 16C's config-load refusal of non-promotable
    families as strategy gates is the only honest boundary, and it is a
    completion criterion, not a nicety
```

Collapsing them into one ADR would bury a runtime-footprint change inside a
research-boundary decision — precisely the "added as a side effect of another
sprint" outcome TD-029's Repayment Direction forbids.

These are **named, not written.** Writing them now would over-specify
increments this roadmap requires to stay directional (§2.9). Each is authored
when its increment is proposed for a sprint.

---

<a id="13h10"></a>
## 13H.10 — Phase dependencies

- Phase 10A/10B/10C — complete (Sprints 039–044).
- Phase 15B / Sprint 052 — **the entry condition** (§13H.0); Phase 16 does not
  open before it has run, with the single exception of 16B (Q3 carve-out).
- Phase 5 (Signal Research) and Phase 6A (Strategy Research) — consumed.
- Phase 7 (Robustness) — consumed by 16C and 16G.
- Phase 14 (promotion mechanism) — consumed by 16G; **Phase 14B / Sprint 050
  is not planned, resized or pre-empted by this phase.** Their relative
  sequencing is a deliberately deferred decision (§13H.12 Q5): it is revisited
  once Sprint 052 supplies its Q5 input, and Phase 16's approval neither
  resolves nor pre-empts it.
- Phase 11/12/13 (CLI, authoring, exit/risk catalog) — consumed as precedent.
- ADR-0023, ADR-0024, ADR-0029 — consumed as binding constraints. Only
  ADR-0029's family allow-list may be widened by this phase, only in 16G, and
  only behind a new ADR (§13H.9 row 3).

---

<a id="13h11"></a>
## 13H.11 — Out of scope for Phase 16

- Replacing rule-based strategies with opaque ML strategies.
- Automatic feature or strategy search of any unbounded kind.
- A remote or dedicated feature store (§17 deferred; local reuse must first be
  proven insufficient).
- MTF-capable `FeatureSpec` and the contract change it needs (§13G).
- Orderflow, options-derived or cross-asset features (Phases 4B/4C).
- Online/incremental learning, live inference, GPU or distributed training
  (§17).
- A model registry, index or lifecycle field (ADR-0024 condition 5 stands;
  TD-021's repayment is a confirmation, not a construction).
- Making never-promoted research-run blobs portable (TD-022's residual).
- **Lifting ADR-0029's tree/neural runtime-promotion deferral anywhere before
  16G** (TD-029, §13H.12 Q6 = Option B). 16C explicitly may not touch
  `MODEL_FAMILY_ALLOWLIST`; 16G owns the repayment behind its own ADR.
- **Retrofitting PRB-012's planner limits to Signal Research's existing
  `family_planning.py`** (§13H.12 Q8, decided not to). Revisited only on a
  concrete incident or need.
- Deciding Phase 16's sequencing relative to Phase 14B / Sprint 050 (§13H.12
  Q5, deferred by decision).
- Treating any backtest, metric or verdict produced here as live-trading
  approval.

---

<a id="13h12"></a>
## 13H.12 — Maintainer decisions (all RESOLVED 2026-09-04)

All eight questions this phase was proposed with were **resolved by the
maintainer on 2026-09-04**. Three of them (Q5, Q7, Q8) were resolved *as
deliberate deferrals or refusals* — those are decisions with a recorded
rationale, not questions still hanging.

| # | Question | Resolution (maintainer, 2026-09-04) |
|---|---|---|
| Q1 | Phase number and shape | **APPROVED.** Phase 16, increments 16A–16G, as a new top-level capability track rather than an extension of Phase 10 |
| Q2 | The §13H.0 reconciliation | **APPROVED as recommended.** Sprint 052 stays exactly as planned, unmodified and not widened; the verdict artifact becomes 16A |
| Q3 | Entry condition | **APPROVED with a carve-out.** Phase 16 does not open before Sprint 052 has run — **except 16B**, which may start in parallel. 16A and everything after it still wait |
| Q4 | PRB-020's direction | **Default direction set: port** the Signal Research pattern. Not unconditional — a genuine combinatorics difference found by 16E's design work is surfaced at 16E's Wave 0 |
| Q5 | Sequencing vs. Phase 14B / Sprint 050 | **Deferred, by decision.** Explicitly NOT decided now; revisited once Sprint 052 supplies its Q5 input |
| Q6 | TD-029 scope for 16C | **Option B chosen.** 16C stays narrow; TD-029's repayment moves to 16G. Option A is historical, not a live alternative |
| Q7 | PRB-013's parity tolerances | **Deferred, by decision.** Numeric tolerances are NOT part of this approval; set at 16G's Wave 0 against real suite data, with maintainer sign-off |
| Q8 | PRB-012 back-application to Signal Research | **Not retrofitted, by decision.** PRB-012 closes for the new Strategy Research planner only; the asymmetry is accepted explicitly |

### Q1 — Phase number and shape (RESOLVED: approved)

Phase 16 is a new top-level capability track in §3's Research Capability
Track, with increments 16A–16G numbered independently of sprints.

### Q2 — The Sprint 052 reconciliation (RESOLVED: approved as recommended)

Sprint 052 is **not** widened to also build the verdict artifact; doing so
would break its consumed-not-modified rule. The verdict artifact is 16A.
Sprint 052's own opening remains gated on its own separate maintainer
approval, unchanged by Phase 16's approval.

### Q3 — Entry condition (RESOLVED: approved, with the 16B carve-out)

```text
16B  MAY start in parallel with Sprint 052 — it depends on Sprint 052
     existing as a study, not on its result
16A  and every increment after it wait for Sprint 052 to have ACTUALLY RUN
```

Applied in §13H.0, §13H.1 Dependencies, §13H.2 Dependencies and §13H.10.

### Q4 — PRB-020's direction (RESOLVED: default direction, not a mandate)

Port `research/signal_research/family_planning.py`'s pattern to a new
`research/strategy_research/family_planning.py`, mirroring the Signal Research
design. **Unless** 16E's own design work finds Strategy Research's
combinatorics genuinely differ (multi-model composition vs. single-model
parameter sweeps) — in which case that finding is surfaced **explicitly at
16E's Wave 0** and decided there, never decided unilaterally by an architect
mid-implementation. This is the maintainer's chosen default direction, and
16E's ADR records whichever way it lands.

### Q5 — Sequencing against Phase 14B / Sprint 050 (RESOLVED: deferred)

**This decision is explicitly NOT made now.** It is revisited once Sprint 052
supplies its Q5 input, per Sprint 052's own scope. Phase 16 does not resolve
or pre-empt Phase 14B's sequencing, and no increment of Phase 16 may assume an
answer. Recorded here so the deferral is visible rather than lost.

### Q6 — TD-029 scope for 16C (RESOLVED: Option B)

**16C's scope stays narrow.** Estimator comparison that may gate a strategy is
restricted to promotable families (`sklearn.ridge`, `sklearn.elastic_net`,
`sklearn.logistic` today); tree and neural scorers are research-only and are
**refused at config load time, with a named error**, as a strategy gate.
TD-029's repayment moves to **16G**.

Option A — growing 16C to design the version-pinned joblib/ONNX-style
promotion path in the same increment — was **considered and not chosen**,
because it lands a runtime-deployment-footprint change inside the phase's
central vertical slice. It is recorded as history. Reopening it is a new
maintainer decision.

Accepted cost, stated plainly: 16C cannot claim "the best model gates the
strategy", only "the best promotable model does", and Phase 10B/10C's shipped
tree/neural capability stays unreachable from the workbench until 16G. That
was the trade knowingly made to keep the vertical slice a vertical slice.

Applied in §13H.3, §13H.7, §13H.8, §13H.9 (row 3 and the #2-vs-#3 note),
§13H.11, §13H.13 and the increment-family summary.

### Q7 — PRB-013's accepted parity tolerances (RESOLVED: deferred)

**Numeric tolerances are not part of Phase 16's approval.** They are deferred
to 16G's own Wave 0 planning, once real parity-suite data exists to set
numbers against. A tolerance is a risk acceptance requiring maintainer
sign-off, not an implementation detail an architect picks. 16G may not be
planned as a gate with parity deferred out of it — only the *numbers* are
deferred, never the suite.

### Q8 — PRB-012 back-application to Signal Research (RESOLVED: not retrofitted)

Signal Research's existing `family_planning.py` is **not** retrofitted with
16E's default limits. This is a deliberate decision, consistent with §2.7
("do not introduce infrastructure for hypothetical scale"): Signal Research's
planner has run without a reported runaway incident, so retrofitting now would
change existing working configs' behaviour with no demonstrated trigger.
PRB-012 closes for the **new Strategy Research planner only**; the resulting
asymmetry is noted explicitly as accepted, and is revisited if a concrete
incident or need arises.

---

<a id="13h13"></a>
## 13H.13 — Registry entries this phase plans to close

Each entry below keeps its current status until the owning increment ships.
This table is the forward index; the annotations in `PROBLEM_REGISTRY.md` /
`TECHNICAL_DEBT.md` are the back-links.

| Entry | Current status | Owning increment | How it is repaid |
|---|---|---|---|
| `PRB-012` — planner limits need defaults | OPEN / MEDIUM | 16E (§13H.5) | Conservative defaults, explicit override, planner tests, no silent pruning — in 16E's completion criteria. Scoped to the new Strategy Research planner only (Q8) |
| `PRB-013` — parity not measurable | OPEN / HIGH | 16G (§13H.7) | Formal parity suite, versioned numeric tolerances (numbers set at 16G's Wave 0, Q7), documented unavoidable differences — the concrete meaning of 16G's "offline/online parity test" step |
| `PRB-020` — Strategy Research lacks family machinery | OPEN / MEDIUM | 16E (§13H.5) | Bounded candidate generation with generated/evaluated/skipped bookkeeping, along Q4's default port direction (or a Wave 0 divergence recorded with rationale) |
| `TD-021` — no model registry | **REPAID** (2026-09-09) | 16C (§13H.3) | Confirmed, against a real config consumer, that content-addressed fingerprint reference suffices; ADR-0024 condition 5 upheld, no registry built |
| `TD-022` — opaque fitted blobs | ACCEPTED / LOW — promotion branch **repaid** (2026-09-09), residual still open | 16C (§13H.3) | Score path provably depends on no `models/fold_{n}.bin`; promotion branch repaid, never-promoted-blob residual explicitly left open |
| `TD-029` — tree/neural promotion deferred | ACCEPTED / LOW | **16G** (§13H.7) | Q6 = Option B: 16C refuses non-promotable families as strategy gates at config load time; the version-pinned serialization ADR and any allow-list widening belong to 16G |

None of these is closed by approving this phase. Approval only makes the
routes above the *planned* routes.
