# ADR-0029 — Promoted Predictive Artifact: Parameter Format, Promotion Store, and the Narrow ADR-0023 §7 Amendment

## Status

ACCEPTED (Sprint 049)

Approved-by: Filip Folga (project maintainer), given directly in conversation
with the orchestrating Claude Code session on 2026-09-02, after being shown
this document's content in full (the parameter-format mechanism, the §6
two-comparison parity split with the `atol=1e-15` `y_proba` bar, the §7
narrow ADR-0023 amendment, and the three judgment calls the architect made
beyond the maintainer's original five Wave 0 answers: the `atol=1e-15`
tolerance value, the promotion-time `ml`-extra requirement and version guard,
and the `FittedNumpyPreprocessor` relocation touching Sprint 043's torch
tests). Answer: "Tak, zatwierdzam ADR-0029 jak napisany" — explicit approval
of the document as written, including those three judgment calls.

Numbering note (2026-09-02, no decision content changed): this ADR was
approved while the promotion sprint was provisionally numbered "Sprint 048 /
Phase 13A". Those numbers were already taken by merged work (Sprint 048 =
Exit/Risk Model Expansion and Catalog Growth, Phase 13, ROADMAP §13E). The
promotion sprint is **Sprint 049 / Phase 14A**, and its runtime successor —
referred to below as the sprint that closes conditions 2, 3 and Path B — is
**Sprint 050 / Phase 14B**. Only these identifiers were rewritten; every
decision, consequence and alternative is exactly as approved.

### Decisions this ADR records

The five questions below were put to the maintainer as open forks in
`S049_WAVE0_DECISIONS.md` and answered directly. They are recorded here as
answered, with the architect's own recommendation shown alongside so that
**where the maintainer overruled the recommendation is visible rather than
smoothed over**.

| # | Question | Maintainer's decision | Architect had recommended |
|---|---|---|---|
| Q1 | Serialization format | Framework-owned NumPy parameter format; linear **and** logistic in v1 | (same — set by the PRD before this ADR) |
| Q2 | Artifact source at promotion | **Extract from the existing joblib blob** — a one-time read at promotion time | same |
| Q3 | Which fold | **Last walk-forward fold** | (set by the PRD) |
| Q4 | Operator surface | **`trading-cli research promote`** | same |
| Q7 | Path A parity bar | **Keep both families: exact for linear, a documented ulp-bounded tolerance for logistic** | **exact for both, dropping logistic from v1 if it failed — OVERRULED** |
| Q8 | `FittedNumpyPreprocessor` location | **Move it into `research/predictive/`** | same |
| Q9 | Parameter values in the fingerprint | **Stay out** | same |

Q7 is the one place this ADR does not record the architect's preference. The
maintainer chose family coverage over an unconditionally exact cross-check, and
§6 states that trade-off in full rather than burying it in a tolerance keyword.

This ADR states a **mechanism**, not an authorization to promote any particular
model. No model is promoted by this document, and nothing here relaxes
ADR-0024's five conditions.

## Context

ADR-0024 named five conditions a model must satisfy before producing a Market
Analysis State, and deliberately **did not choose a serialization format** — it
priced that as the first cost of a promotion sprint (ADR-0024 condition 1,
"Cost, priced honestly"). Sprint 049 is that sprint, scoped by
`docs/product/PRD-ml-signal-promotion.md`.

Three constraints shape the answer:

1. **ADR-0023 §7 currently forbids the mechanism.** It reads, verbatim:
   "Reproduce by re-fitting from the manifest — never by deserializing a blob"
   and "No workflow may depend on reloading a fitted blob." The same policy
   string is written into every run's `manifest.json`
   (`research/datasets/predictive_run.py`). Promotion cannot exist without
   narrowing this, and narrowing an ACCEPTED ADR silently is exactly the drift
   ADR-0026 Amendment 1 exists as a lesson about.
2. **The dry-run/live runtime runs the default install.** `ml` / `ml-trees` /
   `dl` are optional extras kept out of default CI and out of the runtime image
   (ADR-0023, ADR-0022). A format that requires scikit-learn at inference time
   changes the deployment footprint of the whole execution path.
3. **The parity bar is a release gate, not hardening** (ADR-0024 condition 4).
   The maintainer named offline/online agreement as the assumption the entire
   plan rests on. A format choice that makes exactness merely *aspirational*
   fails the gate before it is written.

Two facts found by reading the code make the chosen answer cheap:

- **NumPy is already a default-install dependency** (`pyproject.toml`,
  `numpy>=2.0.0,<2.5`) and `research/predictive/` already imports it in five
  modules. A NumPy-only evaluator adds **no** dependency anywhere.
- **The fitted preprocessing statistics are already extractable as plain
  numbers**: `FittedSklearnPreprocessor.statistics()` emits JSON-stable
  `impute_median`, `standardize_mean`, `standardize_scale` per column, and
  `FittedNumpyPreprocessor` (Sprint 043, D-S043-15) already implements the exact
  NumPy arithmetic that consumes them.

## Decision

### 1. The promoted artifact is a framework-owned parameter file, evaluated by pure NumPy

A promoted artifact is a **JSON file of plain numbers**, not a serialized
library object:

```text
artifact.json
    features            ordered list of feature OutputRef identities (positional)
    preprocessing       impute_median[], standardize_mean[], standardize_scale[]
                        — the statistics fitted on that fold's TRAIN rows
    coefficients        weights, one per feature, in the same positional order
    intercept           scalar
    model_family        sklearn.ridge | sklearn.elastic_net | sklearn.logistic
```

Evaluation is a closed-form NumPy expression, owned by the framework and living
in the **domain layer** (`research/predictive/`):

```text
x  := impute_median(features)          # NaN -> per-column fitted median
z  := (x - standardize_mean) / standardize_scale
y  := z @ coefficients + intercept
     and, for sklearn.logistic only, p := 1 / (1 + exp(-y))
```

**Consequences that follow, and are the point of the choice:** no
scikit-learn, XGBoost or torch dependency enters the dry-run/live runtime
image; the evaluator and its exactness tests run in **default CI**; and the
artifact is human-readable and diffable.

**v1 covers linear and logistic families only** — `sklearn.ridge`,
`sklearn.elastic_net`, `sklearn.logistic`. Promotion of a tree
(XGBoost/LightGBM/CatBoost) or neural (torch) model is **refused with an error
naming the family as deferred**, not silently unsupported. Those families need
the version-pinned joblib path described in Alternatives; it is deferred, not
rejected forever.

### 2. The promotion store is content-addressed, with no registry

```text
research/predictive_research/promoted/{artifact_fingerprint}/
    manifest.json     independently readable; never requires the payload
    artifact.json     the parameter file above
```

Nothing else lives in that directory: no index, no `latest` pointer, no status
field, no lock file. ADR-0024 condition 5 is a negative constraint and is
asserted by a test. TD-021 stays deferred; IDEA-003 stays deferred.

`artifact_fingerprint` = SHA-256 over canonical JSON
(`sort_keys=True, separators=(",", ":")` — identical canonicalization to
`compute_run_fingerprint`) of: `run_fingerprint`, `fold_id`, `format`,
`format_version`, `model_family`, the ordered feature `OutputRef` identities,
`preprocessing_spec`, and `estimator_spec`.

**The fitted parameter values are not hashed** (Q9). Rationale: identity is
"which run, which fold, which spec," so promoting the same run and fold twice
is the same artifact. The original reason for excluding payload bytes — that a
blob serializer may be non-deterministic — no longer applies to a JSON number
file, and the maintainer confirmed the exclusion should stand anyway. Feature
**order** and `model_family` are part of the identity, because the evaluator's
column order is positional.

### 3. The promoted fold is the last walk-forward fold

One promotion produces exactly one artifact: one `(run_id, fold_id)` pair, one
fingerprint, one directory. The promoted `fold_id` is recorded in the manifest,
never implicit.

**Honest limitation, documented rather than hidden:** the last fold's TRAIN
window ends before the last TEST window, so a promoted artifact is already
stale by one fold at promotion time. This was accepted deliberately in
preference to a final refit on all rows, whose out-of-sample performance would
be *by construction unmeasured* — the exact drift ADR-0024's "What is not
sufficient for promotion" warns about.

### 4. Promotion extracts from the existing fitted blob — once, explicitly

`promote_predictive_run` performs a **one-time, promotion-time read** of the
run's `models/fold_{last}.bin`, extracts the coefficients, intercept and fitted
preprocessing statistics, and writes them as the parameter file. It does **not**
re-fit.

Why this and not a re-fit: the promoted artifact must be numerically the same
model that produced the run's own `predictions.parquet`. A re-fit could drift
from the metrics the operator looked at when deciding to promote, which would
make the promoted model a different object from the evaluated one. Extraction
makes Path A a test of **the evaluator**, which is what actually needs proving.

Three obligations follow, and they are binding:

- **This read is the narrow thing ADR-0023 §7 is amended for** (§7 below). It is
  a single, explicit, operator-triggered extraction — not a standing "reload the
  blob" capability, and no other workflow gains one.
- **Promotion requires the `ml` extra**; loading the blob needs joblib and
  sklearn. This is acceptable because promotion is an **offline operator act on
  a research machine**, not a runtime path. The runtime still needs nothing.
- **A promotion-time library-version guard is required.** Unpickling a joblib
  blob under a different scikit-learn version than wrote it is unsafe. The guard
  that §5 removes from *load* time reappears at *promotion* time: promotion
  refuses if the run manifest's recorded `library_version` differs from the
  installed one, and the remedy is to re-run the study. This is not a
  contradiction of §5 — the two guards protect different operations.

### 5. The load-time guard, and one deliberate relaxation

`load_promoted_artifact` hard-fails, before any arithmetic, on:

- an unknown `format_version`,
- a `model_family` outside the linear/logistic allow-list,
- a `preprocessing_spec` step the evaluator does not implement,
- a feature-count or feature-order mismatch between manifest and payload.

There is **no bypass** — no `strict=False`, no `allow_mismatch`, no environment
variable, no compatible-range check. The API surface has no bypass parameter and
a test asserts that. The remedy for a refused load is re-promotion.

**The deliberate relaxation, stated plainly rather than slipped in:** a
difference in the *training* library version does **not** refuse a load. The
pre-decision plan guarded a library-version pin because a joblib blob is only
safe to unpickle under the library that wrote it. A parameter file has no such
coupling: the numbers mean the same thing under any scikit-learn version,
because scikit-learn is not involved in reading them. The training library and
version are still recorded in the manifest, **for provenance**. What replaces
that guard as the safety mechanism is §6's cross-check, which detects the real
residual risk: the framework's evaluator drifting from the library's.

### 6. Parity: two comparisons, two bars, and they must not be conflated

"Exact match" names two structurally different comparisons. Conflating them is
the single most likely way this mechanism gets misread later, so both are stated
here in full.

```text
COMPARISON 1 — OFFLINE vs ONLINE.  The release gate. Sprint 050, Path B.
    NumPy evaluator (batch research path) == NumPy evaluator (dry-run runtime path)
    Same code, same artifact, same float64 inputs.
    BAR: EXACT, unconditionally. Not negotiable under any option below.

COMPARISON 2 — NUMPY vs SKLEARN.   The cross-check. Sprint 049, Path A.
    NumPy evaluator == predictions.parquet, which scikit-learn produced.
    Two different implementations of the same mathematics.
    BAR: exact for linear; ulp-bounded for the logistic probability only.
```

Comparison 1 is what the PRD's success metric 1 means and what ADR-0024
condition 4 gates on. **It is exact and this ADR does not weaken it.**

Comparison 2 is a *quality* check on the framework's own arithmetic against the
library's. Exactness is achievable for most of it but not all: sklearn's
`LogisticRegression.predict_proba` applies `scipy.special.expit`, which is not
required to agree bit-for-bit with a NumPy `1 / (1 + exp(-z))`.

**The maintainer's decision (Q7): keep both families in v1, and accept a
documented ulp-bounded tolerance for the logistic probability**, rather than
dropping logistic from v1 to preserve an unconditionally exact cross-check. The
architect had recommended the latter. The trade accepted is: broader model
coverage now, at the cost of one named, bounded, single-function inexactness in
a sprint whose headline is exactness.

Because `predictions.parquet` carries `y_pred` and `y_proba` as separate
columns, that tolerance is confined far more tightly than "logistic is
approximate." The bar is:

| Compared value | Family | Bar |
|---|---|---|
| `y_pred` | ridge, elastic_net | **exact** (`==` on float64) |
| `y_pred` (class label) | logistic | **exact** — labels are integral; a tie at `z == 0` is a defect, not a rounding artifact |
| decision function `z = Xw + b` | logistic | **exact** — asserted separately, so the tolerance cannot hide an error upstream of the sigmoid |
| `y_proba` | logistic | **`rtol=0, atol=1e-15`** (≈4 ulp of 1.0), and only here |

Binding rules on that tolerance:

- It applies to **exactly one column of one family in Comparison 2**. Anywhere
  else, a non-exact result is a defect.
- The implementation **measures and records** the observed maximum deviation.
  An observed deviation **above** the ceiling is a **STOP-and-report**, never a
  reason to widen the ceiling. Widening it mid-sprint is a STOP-and-ask
  requiring a new decision, per ADR-0024's posture: "a mismatch is a parity
  defect, not a flaky test."
- Every parity test carries a **mutation check** — a deliberately perturbed
  coefficient must make it fail — so a vacuously-passing assertion cannot ship.
- The tolerance is **not** inherited by Sprint 050. If Comparison 1 is ever
  non-exact, that is a failure of the release gate.

### 7. The narrow amendment to ADR-0023 §7

ADR-0023 §7 stands, with one narrow, named exception:

```text
AMENDED  "No workflow may depend on reloading a fitted blob" gains exactly one
         exception: the promote_predictive_run workflow performs a single,
         explicit, operator-triggered read of one fold's fitted blob, for the
         sole purpose of extracting numeric parameters into a promoted artifact.

UNCHANGED  Research-run blobs remain opaque, version-tagged, and non-reloadable
           by every other workflow. Reporting, metrics, and reproduction still
           go through predictions + manifest, never through a blob.
UNCHANGED  The run manifest's policy string is NOT edited. Reproduction of a
           RUN is still "re-fit from the manifest, never deserialize."
UNCHANGED  The blob remains non-portable across library upgrades — which is why
           §4 requires a promotion-time version guard rather than pretending
           otherwise.
NOT GRANTED  Any general "blobs are loadable now" capability. Collapsing the two
           categories would make every research blob a de-facto production
           dependency, which is precisely what §7 exists to prevent.
```

The promoted artifact is a **separate category**: separately produced,
separately addressed, loadable by contract, and — unlike a research blob — not a
blob at all. Promotion never mutates the source run directory.

### 8. Operator surface

Promotion is exposed as **`trading-cli research promote`**, a subcommand of the
existing `research` group, alongside a thin script. It reuses ADR-0026's config
contract rather than inventing an ML-only path, matching the PRD's requirement
that promotion "feel like the existing `strategy_file` flow."

If wiring it requires a new module on ADR-0026 Amendment 1's `apps/cli` import
allow-list, that is a **fresh amendment with maintainer approval** — never a
test-file edit. That is the standing lesson ADR-0026 Amendment 1 records.

### 9. Layering

```text
research/predictive/     the pure-NumPy EVALUATOR, the PromotedPredictor
                         Protocol, error types, fingerprint derivation.
                         NumPy only — no sklearn/xgboost/lightgbm/catboost/torch.
research/datasets/       PromotedArtifactManifest / Ref / Repository
infrastructure/ml/       promotion.py — blob read + parameter extraction; the
                         ONLY place sklearn is touched, inside lazy imports
application/             promote_predictive_run — orchestration only
apps/cli/, scripts/      thin operator surface
```

The evaluator lives in the **domain**, not in `infrastructure/ml/`, because
Sprint 050's Market Analysis component must reach it and `market_analysis/` may
not import `infrastructure/ml/`. Placing it in infrastructure would create a
forbidden edge next sprint.

Per Q8, `FittedNumpyPreprocessor` / `fit_numpy_preprocessor` **move** from
`infrastructure/ml/torch/preprocessing.py` into the domain layer, and the torch
adapter imports them downward from there. It is not copied (a second copy of the
same arithmetic is what later drifts and breaks parity silently), and the
architecture boundary allow-list is **not** widened.

## Consequences

### Positive

- **The dry-run/live runtime gains no dependency at all.** Sprint 050's
  deployment footprint is known today to be zero, and the parity gate runs in
  default CI rather than behind an opt-in `ml` job.
- **Exactness becomes achievable rather than aspirational** for the comparison
  that is actually the release gate, directly de-risking the maintainer's named
  riskiest assumption.
- The artifact is human-readable, diffable, and reviewable — a promoted model
  can be inspected without installing anything.
- A promoted artifact does not expire on a scikit-learn upgrade, because no
  scikit-learn is involved in reading it.
- The ADR-0023 §7 amendment is genuinely narrow: one workflow, one read, one
  purpose, with the research-blob category untouched.
- Reuses `FittedNumpyPreprocessor`, which already exists and is already tested.

### Negative

- **v1 covers linear and logistic only.** If the first real BTC candidate model
  that shows structure is a tree model, the operator hits a refusal and the
  deferred joblib path becomes the next increment rather than a distant one.
- **The framework now owns a `predict` implementation** that must stay in step
  with scikit-learn's. Only the Path A cross-check detects drift, and that check
  runs in the `ml` job, not default CI.
- **The logistic probability cross-check is not exact** (Q7). A sprint whose
  headline is exactness contains one named, bounded inexactness. It is confined
  to one column of one family in one comparison — but it exists, and pretending
  otherwise would be worse than recording it.
- **Promotion requires the `ml` extra and a promotion-time version guard**,
  because §4 reads a joblib blob. Promotion is not runnable from a default
  install, and a scikit-learn upgrade invalidates *promotion from old runs*
  (though not already-promoted artifacts).
- Moving `FittedNumpyPreprocessor` touches Sprint 043's torch path and its
  tests — bounded churn in a sprint that otherwise touches no existing behaviour.

### Neutral

- TD-022 (opaque fitted artifacts) is **partially** addressed: promoted
  artifacts are portable and inspectable; research-run blobs are unchanged.
- TD-021 (no model registry) and IDEA-003 stay deferred, restated not repaid.
- ADR-0024 conditions 2, 3 and the online half of 4 are untouched by this ADR
  and remain open for Sprint 050.

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| **Version-pinned joblib blob for v1** (the cheapest option, covers every family) | Puts scikit-learn — and per family, XGBoost or torch — into the dry-run/live runtime image, and pulls the parity gate out of default CI. **Deferred, not rejected**: it is the intended path for tree and neural families once this mechanism is proven. |
| **ONNX or another cross-library exchange format** | Introduces a **second numerical implementation** of the model, which directly threatens the exact-match bar this ADR exists to make achievable; adds a new runtime dependency requiring approval; conversion coverage is uneven across tree and torch families. Explicitly rejected in the PRD's Non-goals. |
| **Re-fit the fold at promotion time** instead of extracting | Never touches ADR-0023 §7 — genuinely attractive — but costs a full re-fit and can produce an artifact that differs from the one whose metrics the operator evaluated. "No re-fit drift" was the deciding requirement. |
| **Extract the parameters at run time** (write them alongside the blob during `run_predictive_research`) | The cleanest answer to §7, needing no blob read at all. Rejected for **scope**, not merit: it changes the Phase 10 run pipeline, which Sprint 049 does not touch. Recorded in Follow-up as the natural successor. |
| **Final refit on all non-embargoed rows** as the promoted artifact | Produces an artifact whose out-of-sample performance is by construction unmeasured — the exact drift ADR-0024 warns about. |
| **Per-fold artifacts, resolved by as-of date at inference** | Pushes an as-of resolution rule into the runtime; Sprint 050 scope, and would have been decided here by accident. |
| **Drop logistic from v1** to keep Comparison 2 unconditionally exact | The architect's recommendation. **Overruled by the maintainer (Q7)**, who chose keeping both families over an exact cross-check for a single column. |
| **Call `scipy.special.expit` in the evaluator** so the sigmoid matches by construction | Would put SciPy into the runtime evaluation path, undoing the entire point of the format choice. |
| **Copy the NumPy preprocessing arithmetic** into the evaluator, or **widen the boundary allow-list** so the domain may import `infrastructure/ml/torch/` | Copying creates a second implementation that later drifts silently; widening inverts the dependency direction the boundary test protects. Moving the module was chosen instead (Q8). |

## Follow-up

- **Sprint 050** closes ADR-0024 conditions 2, 3 and the online half of 4:
  Comparison 1 as a release gate, the model-backed State, executor availability
  enforcement (sized by the S049-T001 spike, possibly needing ADR-0030), and the
  registry-injection seam in the dry-run runtime.
- **Tree and neural promotion** via a version-pinned joblib path — deferred here,
  and to be given a tracked owner (Technical Debt or Idea Inbox) rather than
  living only as a Non-goal in a PRD.
- **Extracting parameters at run time** (the rejected-for-scope alternative
  above) would retire the §7 amendment's exception entirely. Worth revisiting
  once promotion has been exercised.
- **Record the observed maximum `y_proba` deviation** measured by Path A. If it
  is comfortably below the ceiling, a future ADR may tighten it; if it is at the
  ceiling, that is a signal to revisit Q7.
- **`predict_proba` for regression families** is undefined and out of scope;
  `y_proba` is compared only for `sklearn.logistic`.

## Related

- `docs/product/PRD-ml-signal-promotion.md` — the maintainer's discovery record;
  authoritative on scope, format, fold selection and the parity bar
- `docs/adr/ADR-0024-machine-learned-state-promotion.md` — the five conditions;
  this ADR pays condition 1's deferred serialization cost
- `docs/adr/ADR-0023-predictive-research-boundary.md` §7 — **amended narrowly by
  this ADR**; §4 (leakage) and §8 (synthetic CI fixtures) unchanged
- `docs/adr/ADR-0022-repository-top-level-layout.md` — extras and apps boundary
- `docs/adr/ADR-0026-operator-cli-framework-and-placement.md` + Amendment 1 —
  the CLI config contract and import allow-list
- `docs/adr/ADR-0027-operator-authored-strategy-loading.md` — the `strategy_file`
  flow promotion must feel like
- `docs/adr/ADR-MA-002` / `ADR-MA-005` / `ADR-MA-009` — component identity,
  `Lineage`/`OutputRef`, availability
- `docs/planning/sprints/SPRINT_049.md`, `S049_WAVE0_DECISIONS.md`,
  `S044_GATE.md` §4 (parity sketch)
- `docs/planning/TECHNICAL_DEBT.md` — TD-021, TD-022
- `docs/planning/IDEA_INBOX.md` — IDEA-014, IDEA-003
