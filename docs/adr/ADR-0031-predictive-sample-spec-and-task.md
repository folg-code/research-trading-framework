# ADR-0031 — Predictive Sample Universe (`SampleSpec`) and Research Task Taxonomy (`PredictiveTask`)

## Status

PROPOSED

Drafted for Sprint 056 (Phase 16, increment 16B — SampleSpec Foundation),
2026-09-04. Requires explicit maintainer acceptance; no agent may mark it
`ACCEPTED`. `SPRINT_056.md` Wave 1 does not start until it is.

## Context

`PredictiveStudySpec` (Sprint 039, ADR-0023) declares a dataset, a range,
features, one label and a purged walk-forward split. It does **not** declare
*which rows the study is about*. The matrix builder answers that implicitly:
`build_labelled_feature_matrix` emits **one row per complete evaluation bar**,
with a synthesized `direction="long"` occurrence per bar.

That makes every predictive study in the framework an answer to one question —
"what happens next, from anywhere?" — which is the least interesting question a
strategy-centric framework can ask. The questions the roadmap actually wants
(§13H.2, §13H.3, §13H.6) are conditioned on events: a signal firing, a simulated
trade, a labelled discretionary setup. Today, asking one of those would mean
forking the pipeline.

Two further facts constrain the shape of any answer:

1. **`definition_hash` is a published interface.** It is a SHA-256 over
   `PredictiveStudySpec.to_dict()`, it enters the dataset fingerprint, and it is
   recorded in committed study YAML header comments and in every persisted
   dataset manifest. Sprint 052 (Phase 15B) depends on a third party
   re-deriving it (`SPRINT_052.md` T007), and Phase 16's §13H.0 permits 16B to
   run *in parallel with* Sprint 052 on the explicit condition that it lands no
   change Sprint 052 would then be consuming.
2. **`research/predictive/` may not import `signal_model` or `strategy`.**
   ADR-0023 and the package's own `CLAUDE.md` forbid it, and
   `tests/unit/test_architecture_boundaries.py` walks every import node to
   enforce it. But resolving "the rows where this Signal Model fired" requires
   exactly those packages.

Separately, the statistical task type (`REGRESSION | BINARY | TERNARY` via
`LabelKind`, plus the estimator's own notion) does not express *research
intent*. "Binary classification" is the same statistical object whether it means
"will price rise?" or "was this signal worth taking?", and the framework has no
way to record which one a study is, or to refuse a combination that is
incoherent.

## Decision

### 1. `SampleSpec` — an explicit, defaulted sample universe

`PredictiveStudySpec` gains an optional `sample` block. Two kinds are
implemented:

```text
every_bar             one row per complete evaluation bar — today's behaviour,
                      made explicit. THE DEFAULT.
signal_occurrences    rows are a declared Signal Model's firings, referenced by
                      declaration (signal_model_file + signal_model_id) with an
                      optional direction filter (ANY | LONG | SHORT, default ANY)
```

`strategy_trades`, `labelled_setups` and `sessions_or_windows` are **reserved
names in the contract's design intent and refused at load time** with a named
error identifying the owning increment. They are not silently-accepted no-ops.

### 2. Default elision preserves `definition_hash`

`to_dict()` **omits** `sample` when the kind is `every_bar`, and **omits**
`task` when it is `FORWARD_RETURN`. An explicitly-declared default therefore
serializes — and hashes — identically to an omitted one, and every study spec
that exists today keeps the exact `definition_hash` it has now.

Elision is a serialization rule only. In memory the fields are always populated
and explicit; no downstream code branches on "absent versus default".

### 3. Declaration and resolution live in different layers

```text
research/predictive/        DECLARES.  SampleSpec and PredictiveTask are pure
                            data types with no new imports. The matrix builder
                            accepts an already-resolved, provenance-carrying row
                            selection.
application/predictive_research/
                            RESOLVES.  It may import evaluate_models and
                            materialize_signal_occurrences — the same functions
                            Signal Research uses — and hands the domain a
                            resolved selection.
```

The Signal Model is referenced by **declaration**, never by a run id or a
persisted occurrence artifact. No index, pointer or lifecycle field is
introduced (ADR-0024 condition 5, restated by §13H.8).

### 4. Sample selection is applied AFTER labelling, on the full grid

Labels and `label_end_at` are computed over the complete evaluation grid; the
sample filter is applied afterwards. The analysis frame is never pre-filtered to
the sampled rows before labelling.

This is the opposite implementation order to §13H.2's prose flow ("sample
universe resolved FIRST -> features computed AT those rows"). The outcome is
identical — features and labels on the evaluation grid are causal and
position-independent — but the order must be this way, because
`matrix.py::_label_end_timestamps` derives `label_end_at` **positionally**
(`timestamps[index + horizon_bars]`). On a pre-filtered sparse sequence, a
4-bar horizon over selective firings could span weeks, and purge would then be
computed against a fabricated label window. That is silent leakage.

### 5. `PredictiveTask` — research intent, distinct from statistical task type

```text
SHIPPED (accepted at load time)
        FORWARD_RETURN      default; valid with every_bar and signal_occurrences
        SIGNAL_QUALITY      valid with signal_occurrences only
RESERVED (refused at load time, error names the owner)
        TRADE_OUTCOME, NO_TRADE_FILTER            -> 16F
        REGIME_CLASSIFICATION, VOLATILITY_FORECAST,
        DISCRETIONARY_SETUP_CLASSIFICATION        -> later, unassigned
```

Compatibility matrix; anything not listed is refused with a named error:

| sample kind | task | |
|---|---|---|
| `every_bar` | `FORWARD_RETURN` | ACCEPTED (today's behaviour) |
| `signal_occurrences` | `FORWARD_RETURN` | ACCEPTED (plain forward return over a selected universe) |
| `signal_occurrences` | `SIGNAL_QUALITY` | ACCEPTED |
| `every_bar` | `SIGNAL_QUALITY` | REFUSED — there is no signal whose quality could be judged |

`PredictiveTask` does not replace or alter `LabelKind` or the estimator's task
type. It records what the study is *for*; those record what it *is*.

### 6. Sample provenance is persisted

The predictive dataset manifest records the resolved sample kind, the task, the
resolved row counts and the per-reason drop counts — for **both** kinds. "The
whole grid" is itself a sample choice and a reader should not have to infer it
from an absent key. Rows conditioned on a signal firing are a biased slice by
construction; the contract makes that visible rather than hiding it.

The provenance block does not enter the dataset fingerprint, which stays
`definition_hash` + feature lineage + `dataset_ref` + time range.

### 7. Leakage guards are unchanged

Purge, embargo, `min_train_rows`, the zero-TEST-rows error and the
`available_at <= detected_at` rule are strengthened or left alone, never widened
to accommodate a sparse sample (ADR-0023 §4, §13H.8). A selective signal that
cannot fill a fold raises the existing error; that is the correct outcome, and
this ADR authorizes no automatic accommodation of it.

## Alternatives Considered

**Unconditional serialization of `sample`/`task`, with a spec schema-version
bump.** More honest as a data format: the spec would always say what it is. But
it churns every `definition_hash` in the repo and in every persisted manifest,
for zero behavioural gain, and it breaks the reproducibility record Sprint 052
is planned to produce — while §13H.0's carve-out explicitly requires 16B not to
change what Sprint 052 consumes. Rejected on that basis, not on aesthetics.

**Resolving the sample universe inside `research/predictive/`.** Simpler call
graph, one fewer indirection. Requires importing `signal_model` into a package
whose architecture test forbids it. Rejected: the boundary is older, broader and
more valuable than this convenience.

**A separate `SampleSpec` file referenced by path.** Mirrors how strategies and
estimators are declared. Adds a second identity to fingerprint and a second file
to keep in sync, for no expressive gain at two kinds. Rejected as premature.

**Filtering the frame before labelling (the roadmap's literal flow).** Cheaper:
a selective signal would avoid computing labels for discarded bars. Produces
positionally-derived `label_end_at` over a sparse sequence, i.e. silent leakage.
Rejected outright; the waste is accepted as the price of correctness, and any
future optimization must preserve full-grid derivation of `label_end_at`.

**Shipping only `every_bar` now and deferring `signal_occurrences`.** Would make
the increment a pure refactor with no new capability and no evidence that the
contract can carry a second kind — which is exactly the evidence a
hard-to-reverse contract decision needs before every later increment builds on
it. Rejected.

## Consequences

**Positive**

- Existing specs, hashes, manifests and comparisons are untouched; the change is
  invisible to anyone not opting in.
- A new research question becomes a three-line YAML change rather than a fork of
  the pipeline.
- The `research/predictive/` import boundary survives a genuinely cross-domain
  feature, with the pressure absorbed by the application layer where it belongs.
- Sample selection bias becomes a persisted, readable fact.
- Reserved names publish the direction (16F and beyond) without inviting a
  premature implementation, because they are refused rather than ignored.

**Negative**

- Default elision creates an asymmetry between the in-memory spec and its
  serialized form. Anyone reading a persisted spec sees no `sample` key and must
  know the default. Mitigated by documentation and by the provenance block,
  which always states the resolved kind explicitly.
- Full-grid labelling followed by a late filter computes and discards work for
  selective signals. Accepted knowingly (§4).
- A selective Signal Model will often produce too few rows per fold and hit an
  existing hard error. The framework has no verdict vocabulary for that yet
  (16A's `REJECTED_LOW_SAMPLE` does not exist), so the user experience is a loud
  exception until it does.
- Two sample kinds is a thin base on which to fix a contract that 16C, 16F and
  later increments all depend on. Mitigated by keeping the contract small and by
  reserving — rather than guessing at — the names it does not yet implement.

**Neutral**

- `LabelKind`, the estimator protocol, `MODEL_FAMILY_ALLOWLIST`, promotion,
  the dashboard and every leakage guard are untouched.
- CI stays synthetic-only and network-free (ADR-0023 §8).

## Follow-up

- 16F implements `strategy_trades` and owns `TRADE_OUTCOME` / `NO_TRADE_FILTER`;
  it inherits this contract and must not widen it silently.
- 16C consumes `signal_occurrences` + `SIGNAL_QUALITY`; the score-delivery
  boundary is a separate ADR (§13H.9 row 2) and is not decided here.
- 16A, once it exists, may classify an under-powered sample as
  `REJECTED_LOW_SAMPLE`; until then a hard error is the only honest signal.
- MTF-capable `FeatureSpec` remains an open structural gap (§13G) and is
  untouched by this decision.

## Related

- `docs/adr/ADR-0023-predictive-research-boundary.md` — §4 leakage guards, §8
  synthetic-only network-free CI, and the import boundary this decision keeps
- `docs/adr/ADR-0024-machine-learned-state-promotion.md` — condition 5's
  no-registry constraint, upheld here
- `docs/planning/roadmap/PHASE_16_QUANT_WORKBENCH.md` §13H.0, §13H.2, §13H.8,
  §13H.9 row 1
- `docs/planning/sprints/SPRINT_056.md`,
  `docs/planning/sprints/S056_WAVE0_DECISIONS.md` (D-S056-04, D-S056-05,
  D-S056-09)
- `src/trading_framework/research/predictive/CLAUDE.md`
