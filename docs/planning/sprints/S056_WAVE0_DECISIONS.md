# Sprint 056 — Wave 0 Decisions

Binding decisions for the SampleSpec Foundation (Phase 16, increment 16B).
Date: 2026-09-04.

```text
Status: PROPOSED — requires the maintainer's Wave 0 Checklist sign-off
        (D-S056-10). `engineer` must refuse to start while any box is
        unchecked. No agent may check a box.

ADDITIONALLY GATED: D-S056-04 (the SampleSpec contract shape) and D-S056-09
        (the PredictiveTask taxonomy) are the substance of ADR-0031, which is
        drafted but `PROPOSED`. Wave 1 does not start until that ADR is
        `ACCEPTED`. If review changes the contract, this document is amended by
        S056-T001 and the checklist is re-signed.

Basis:  docs/planning/roadmap/PHASE_16_QUANT_WORKBENCH.md §13H.0, §13H.2,
                §13H.8, §13H.9 row 1, §13H.11, §13H.12 Q3 — AUTHORITATIVE
        docs/planning/ROADMAP.md (Status: ACCEPTED) §13H stub
        docs/planning/sprints/SPRINT_056.md
        docs/planning/sprints/SPRINT_052.md §5 (its FORBIDDEN paths)
        docs/adr/ADR-0023 (ACCEPTED) §4, §8
        docs/adr/ADR-0031 (PROPOSED, drafted with this sprint)
        src/trading_framework/ as on origin/main @ a004e8d (2026-09-04)
```

---

## Inherited locks (do not reopen)

```text
§13H.8: ONE component catalog; no "ML feature" concept; the simulator owns PnL;
        the dashboard stays read-only; leakage guards are never relaxed to
        accommodate a new sample kind; CI stays synthetic-only and network-free;
        no registry as a side effect; nothing depends on reloading
        models/fold_{n}.bin; the family allow-list is 16G's alone; a negative
        result is a deliverable; approving a phase is not opening a sprint
§13H.2 Out of scope: strategy_trades, labelled_setups, sessions_or_windows;
        any new estimator family, extra or dependency; MTF-capable FeatureSpec
ADR-0023 §4: purge, embargo, dataset fingerprint, matrix availability
        (available_at <= detected_at). Strengthened or unchanged, never widened
ADR-0023 §8: CI fixtures stay synthetic-only; standard CI stays network-free
ADR-0024, ADR-0029: consumed as constraints, not reopened, not amended here
research/predictive/CLAUDE.md: no sklearn / xgboost / lightgbm / catboost /
        torch imports; no signal_model import; no run_analysis call from the
        domain package. Enforced by tests/unit/test_architecture_boundaries.py
```

---

## D-S056-01 — Problem statement

Predictive rows today are evaluation bars, implicitly. The pipeline can only ask
"what happens next, from anywhere?" — the least interesting question for a
strategy-centric framework — and asking a different one would require forking
it.

**Sprint 056 ships exactly:** an explicit `sample:` block and a `PredictiveTask`
enum in `PredictiveStudySpec`, defaulting to today's behaviour with an
unchanged `definition_hash`; one new sample kind (`signal_occurrences`) whose
row count is asserted against the Signal Model's own occurrence table; sample
provenance persisted in the dataset manifest; and evidence that the leakage
guards still hold for irregularly-spaced rows.

**Not this sprint:** any study, any result, any verdict, any scorer, any
promotion, any dashboard change, and any of the deferred sample kinds.

---

## D-S056-02 — Non-interference with Sprint 052 (the reverse boundary)

§13H.0's Q3 carve-out lets 16B run in parallel with Sprint 052 and attaches one
obligation: **16B must not land a change Sprint 052 would then be consuming.**
Sprint 052 protects itself from the pipeline (`SPRINT_052.md` §5). This decision
is the mirror image and it has two halves.

**(a) Behavioural non-interference — the real guarantee.**

```text
LOCKED  The every_bar default is BYTE-IDENTICAL, not merely equivalent. Every
        existing spec must produce the SAME definition_hash it produces on main
        today (D-S056-04's default elision). Sprint 052 records that hash in a
        committed YAML header comment (its T002) and depends on a third party
        re-deriving it (its T007) — a churned hash would break its
        reproducibility record even if every number stayed the same.
LOCKED  The dataset fingerprint is unchanged by this sprint. It is derived from
        definition_hash + feature lineage + dataset_ref + time range; adding a
        manifest provenance block must not enter it (asserted by S056-T003).
LOCKED  No default value, threshold, span, or guard in the Phase 10 pipeline
        changes. A new field with a non-eliding default IS a pipeline
        modification for Sprint 052's purposes.
```

**(b) File-level non-interference — the mechanical backstop.**

```text
FORBIDDEN to Sprint 056 (Sprint 052's outputs and inputs):
        apps/cli/examples/predictive/research_run_predictive.yaml
                (Sprint 052 T002 repoints its dangling reference; 16B must not
                 race it)
        apps/cli/examples/predictive/btc_*.yaml
        docs/reference/BTC_PREDICTIVE_STUDY.md
        docs/planning/sprints/SPRINT_051.md, SPRINT_052.md, S051_*, S052_*
        docs/planning/ROADMAP.md §13F / §13G
ALLOWED to Sprint 056 (Sprint 052's own FORBIDDEN list, which it will not touch):
        research/predictive/, application/predictive_research/,
        research/datasets/predictive.py
        -> These are forbidden to SPRINT 052, not to this sprint. There is no
           overlap: 052 consumes them unmodified, 056 modifies them. The only
           shared surface is behavioural, and (a) closes it.
STILL FORBIDDEN to both:
        infrastructure/ml/, research/predictive/promotion/, market_analysis/
```

**Sequencing is the maintainer's, not an agent's** — see D-S056-03.

---

## D-S056-03 — Merge ordering to `main` is a maintainer decision

```text
LOCKED  This sprint's integration PR into main is not merged while Sprint 052
        is mid-run without the maintainer saying so explicitly. Not because the
        change is unsafe — D-S056-02(a) is what makes it safe — but because
        "the pipeline did not change under me" should be a fact the operator
        confirmed, not one an agent asserted on their behalf.
LOCKED  If Sprint 052 has not opened by the time this sprint is ready to
        integrate, that is not a blocker: 16B depends on Sprint 052 EXISTING as
        a planned study, never on it running (§13H.0 Q3).
LOCKED  No agent may re-sequence, re-scope, widen, or "unblock" Sprint 052 from
        inside this sprint, in either direction.
```

---

## D-S056-04 — The SampleSpec contract shape (ADR-0031's substance)

Declared shape, YAML surface:

```yaml
study:
  # ... existing fields unchanged ...
  task: FORWARD_RETURN            # optional; default FORWARD_RETURN
  sample:                         # optional; default {kind: every_bar}
    kind: every_bar
```

```yaml
  task: SIGNAL_QUALITY
  sample:
    kind: signal_occurrences
    signal_model_file: <path to the declared Signal Model>
    signal_model_id: <id within that file>
    direction: ANY                # ANY | LONG | SHORT, default ANY
```

```text
LOCKED  DEFAULT ELISION. PredictiveStudySpec.to_dict() OMITS `sample` when the
        kind is every_bar and OMITS `task` when it is FORWARD_RETURN. An
        explicitly-declared default therefore hashes identically to an omitted
        one. This is the whole of D-S056-02(a)'s mechanism and it is the
        sprint's single most load-bearing decision.
LOCKED  Elision is asymmetric ONLY in serialization. In memory the fields are
        always populated and always explicit; nothing downstream branches on
        "absent vs default".
LOCKED  LAYERING (Finding 2 of SPRINT_056.md). research/predictive/ owns the
        DECLARATION (SampleSpec / PredictiveTask are pure data with no new
        imports) and accepts an already-resolved row selection.
        application/predictive_research/ owns the RESOLUTION (it may import
        evaluate_models and materialize_signal_occurrences). The domain package
        gains NO import of signal_model, strategy, or application.
LOCKED  The Signal Model is referenced by declaration (file + id), never by a
        run id and never by a persisted occurrence artifact. 16B introduces no
        index, no pointer and no lifecycle field — ADR-0024 condition 5's
        negative constraint holds for this increment too (§13H.8).
LOCKED  Only two kinds are ACCEPTED: every_bar, signal_occurrences. The names
        strategy_trades, labelled_setups and sessions_or_windows are RESERVED
        and REFUSED at load time with a named error that says which increment
        owns them (16F / later). Silent acceptance is forbidden.
```

Rejected alternatives, recorded so they are not re-litigated mid-sprint:

```text
REJECTED  Unconditional serialization of `sample`/`task` with a spec
          schema-version bump. Honest, but it churns every definition_hash in
          the repo and in every persisted manifest, and it breaks Sprint 052's
          reproducibility record for zero behavioural gain.
REJECTED  Resolving the sample universe inside research/predictive/. It would
          require importing signal_model, which ADR-0023 and the module's own
          architecture test forbid.
REJECTED  A separate SampleSpec file referenced by path from the study spec. It
          adds a second identity to fingerprint for no expressive gain at two
          kinds.
```

---

## D-S056-05 — Filter LATE, never early (the leakage lock)

```text
LOCKED  Labels and label_end_at are computed on the FULL evaluation grid FIRST;
        the sample selection is applied AFTERWARDS. The frame is never
        pre-filtered to the sampled rows before labelling.
REASON  matrix.py::_label_end_timestamps derives label_end_at positionally as
        timestamps[index + horizon_bars]. On a pre-filtered sparse sequence a
        4-bar horizon over selective firings could span weeks, and purge would
        then be computed against a fabricated label window. That is silent
        leakage, and no test would catch it unless the test knew to look.
LOCKED  This is a DELIBERATE DEVIATION from §13H.2's prose flow ("sample
        universe resolved FIRST -> features computed AT those rows"). The
        outcome is identical — features and labels on the evaluation grid are
        causal and position-independent — but the implementation order is the
        opposite, and it must be, for the reason above. Surfaced here rather
        than resolved silently; the maintainer signs it off at D-S056-10.
LOCKED  Cost accepted: computing the full grid and discarding most of it is
        wasteful for a selective signal. Wasteful and correct beats cheap and
        leaky. Any future optimization must preserve the full-grid derivation of
        label_end_at and is out of scope here.
```

---

## D-S056-06 — Occurrence direction is passed through

```text
LOCKED  A signal_occurrences row carries the occurrence's own `direction`, and
        forward outcomes are computed by the SAME
        compute_forward_outcomes_for_horizons call Signal Research has used
        since Sprint 008. No bespoke outcome logic is written.
LOCKED  entity_id for a signal_occurrences row is the occurrence_id (from
        derive_occurrence_id), not the bar timestamp. every_bar rows keep their
        current bar-timestamp entity_id, unchanged.
LOCKED  `direction: LONG|SHORT` in the sample block filters occurrences; it does
        not rewrite them. ANY is the default.
REASON  Forcing every occurrence to long would be MORE code and would mislabel
        every short signal. The direction column already exists end to end.
```

---

## D-S056-07 — An under-powered sample is a STOP, not an accommodation

```text
LOCKED  The existing guards stay errors: zero TEST rows in a fold, and TRAIN
        rows below min_train_rows, both raise PredictiveMatrixError. A selective
        signal will trip these, and that is the correct outcome.
LOCKED  Nothing in this sprint auto-relaxes fold_count, test_span, embargo_span,
        min_train_rows or the horizon to make a sparse sample fit. Not as a
        default, not as a flag, not as a warning-and-continue.
LOCKED  16A's REJECTED_LOW_SAMPLE verdict — §13H.2's named mitigation for this
        risk — DOES NOT EXIST. 16A has not been planned, let alone shipped, and
        is gated on Sprint 052 having run. No task, test or document in this
        sprint may reference it as a live mitigation. The honest mitigation
        today is a loud error.
```

---

## D-S056-08 — How the row-count identity is asserted

The completion criterion is "asserted, not assumed" (§13H.2). Concretely:

```text
MECHANISM  A synthetic-fixture unit/integration test that:
        1. runs evaluate_models over the fixture to obtain the Signal Model's
           emissions, then materialize_signal_occurrences to obtain the
           canonical occurrence table (the SAME functions Signal Research
           calls — not a re-implementation, which would assert nothing);
        2. builds a predictive dataset over the SAME dataset_ref, time range
           and evaluation_timeframe with sample.kind = signal_occurrences;
        3. asserts  manifest.exclusion_counts.candidate_rows
                    == occurrences.height        (EQUALITY, not a bound)
        4. asserts every non-labelled occurrence is attributed to exactly one
           exclusion reason, and that the reasons sum back to the occurrence
           count — so a silently dropped row cannot hide inside a slack
           inequality;
        5. asserts the same identity survives fold assignment: the set of
           distinct entity_ids across all folds is a subset of the occurrence
           ids, with the difference explained by declared roles only.
LOCKED  The comparison is against candidate_rows, NOT labelled_rows. Occurrences
        near the end of the range legitimately lose their label to an incomplete
        horizon; hiding that behind a looser assertion would defeat the point.
LOCKED  The fixture is synthetic and network-free (ADR-0023 §8). A real-data
        check is not a substitute and is not performed here.
LOCKED  If the identity does not hold, that is a STOP-and-report finding about
        occurrence semantics — not a reason to relax the assertion.
```

---

## D-S056-09 — The PredictiveTask taxonomy and what is accepted at load

```text
SHIPPED (accepted at load time):
        FORWARD_RETURN      default; valid with every_bar and with
                            signal_occurrences
        SIGNAL_QUALITY      valid with signal_occurrences ONLY
RESERVED (refused at load time, with a named error naming the owner):
        TRADE_OUTCOME                        -> 16F
        NO_TRADE_FILTER                      -> 16F
        REGIME_CLASSIFICATION                -> later increment, unassigned
        VOLATILITY_FORECAST                  -> later increment, unassigned
        DISCRETIONARY_SETUP_CLASSIFICATION   -> later increment, unassigned

Compatibility matrix (anything not listed is refused):
        every_bar          + FORWARD_RETURN   ACCEPTED  (today's behaviour)
        signal_occurrences + FORWARD_RETURN   ACCEPTED  (plain forward return on
                                                         a selected universe)
        signal_occurrences + SIGNAL_QUALITY   ACCEPTED
        every_bar          + SIGNAL_QUALITY   REFUSED   (there is no signal to
                                                         judge the quality of)

LOCKED  PredictiveTask records RESEARCH INTENT. It does NOT replace and does not
        alter LabelKind (REGRESSION | BINARY | TERNARY) or the estimator's own
        task type, which stay exactly as they are.
LOCKED  A reserved name is never a silently-accepted no-op. Each refusal is
        covered by its own test (SPRINT_056.md acceptance criterion 7).
LOCKED  Adding a task to the SHIPPED set later requires a shipped sample/label
        builder for it — the enum is not the feature.
```

---

## D-S056-10 — Wave 0 Checklist (maintainer)

Nothing below may be checked off by an agent. `engineer` must refuse to start
while any box is unchecked.

- [ ] **Opening Sprint 056 is approved**, in parallel with Sprint 052, on the basis of §13H.0's Q3 carve-out — and this approval is **not** an approval of Sprint 052's own opening, which remains a separate, unmade decision.
- [ ] **Sprint number 056 confirmed** (051-055 taken, 050 reserved for Phase 14B and untouched).
- [ ] **ADR-0031 reviewed** — `SampleSpec` contract shape and `PredictiveTask` taxonomy — and either `ACCEPTED` or returned with corrections. Wave 1 does not start before it is `ACCEPTED`.
- [ ] **D-S056-02 confirmed** — both halves of the Sprint 052 boundary: byte-identical default behaviour, and the file-level reverse-FORBIDDEN list.
- [ ] **D-S056-03 confirmed** — merge ordering to `main` relative to Sprint 052 is the maintainer's call, not an agent's.
- [ ] **D-S056-04 confirmed** — the contract shape, and specifically **default elision** in `to_dict()` (an explicit `every_bar` hashes identically to an omitted one), plus the declaration/resolution layering split.
- [ ] **D-S056-05 confirmed — this one needs a deliberate read.** The implementation filters **late** (labels and `label_end_at` on the full grid first), which is the **opposite order** to §13H.2's prose flow. The outcome is identical; the ordering is not. Accepting this is accepting a documented deviation from the approved phase text.
- [ ] **D-S056-06 confirmed** — occurrence direction passed through, `entity_id` becomes `occurrence_id` for the new kind.
- [ ] **D-S056-07 confirmed** — an under-powered sparse sample raises an error and is a stop-and-report; **16A's `REJECTED_LOW_SAMPLE` may not be cited as a mitigation because it does not exist yet.**
- [ ] **D-S056-08 confirmed** — row-count identity asserted as an equality against `candidate_rows`, on a synthetic fixture, using the same occurrence functions Signal Research uses.
- [ ] **D-S056-09 confirmed** — the shipped/reserved split and the compatibility matrix; reserved names are refused with named errors, never silently accepted.
- [ ] **Sprint 056 scope approved as 7 tasks, 4 waves**, shipping **no** study, **no** verdict, **no** scorer, **no** promotion and **no** new dependency.
- [ ] **Branch `sprint/sample-spec-foundation` approved**, to be cut from `main` at its then-current head.

Approved-by: _(pending — no agent may fill this in.)_

Once every box is checked and ADR-0031 is `ACCEPTED`, the first task for
`engineer` is **S056-T001** (ADR acceptance follow-through and Wave 0
amendments, docs only) on `docs/sample-spec-contract-adr`, cut from
`sprint/sample-spec-foundation`.
