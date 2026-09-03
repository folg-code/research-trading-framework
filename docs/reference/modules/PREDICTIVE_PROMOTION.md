# Predictive Model Promotion (Phase 14A, Sprint 049)

> Moved from `docs/reference/PREDICTIVE_PROMOTION.md` to
> `docs/reference/modules/PREDICTIVE_PROMOTION.md` by Sprint 054 T008
> (`docs/reference` system/workflows/runbooks/modules split). Content
> unchanged.

Practical reference for `promote_predictive_run` / `trading-cli research
promote` and the pure-NumPy evaluator that loads their output. This is the
"what is this and how do I use it" document. The "why was it designed this
way" record — the alternatives considered, the ADR-0023 §7 amendment's exact
wording, and the maintainer's decisions on each open question — lives in
`docs/adr/ADR-0029-promoted-predictive-artifact.md`. A future agent should be
able to operate promotion correctly from this document alone, without opening
that ADR.

**A promoted artifact is not a tradeable verdict.** Promotion turns one
Predictive Research run's last fold into a portable, inspectable parameter
file. It says nothing about whether the model is any good, whether it has
been robustness-tested, or whether it is wired into anything that trades.
Strong Phase 10 metrics are a *precondition* for promoting a model, never
proof that it should trade (ADR-0024, "What is not sufficient for
promotion"). As of this sprint (14A), promotion produces **no Market
Analysis component, no State, no executor wiring, and no dry-run
composition** — that is Sprint 050 (Phase 14B), not yet built. See §9.

---

## 1. What a promoted artifact is, and is not

**Is:**

- a JSON file of plain numbers (weights, intercept, fitted preprocessing
  statistics) extracted, once, from one Predictive Research run's last
  walk-forward fold,
- evaluated by a pure-NumPy closed-form expression that lives in the domain
  layer (`research/predictive/promotion/`) and needs no optional extra,
- content-addressed by an `artifact_fingerprint` derived from identity
  (dataset, estimator spec, fold, format, feature order) — never from the
  fitted numbers themselves,
- linear or logistic only in v1 (`sklearn.ridge`, `sklearn.elastic_net`,
  `sklearn.logistic`).

**Is not:**

- a registry entry, a `latest` pointer, or a lifecycle state — the store has
  no index file and no status field anywhere (ADR-0024 condition 5),
- a re-fit of the model — promotion extracts the exact fold that produced the
  run's own `predictions.parquet`; it never re-fits,
- a Market Analysis component, a State, or anything reachable from a
  strategy — that is Sprint 050,
- a serialized library object — no scikit-learn `Pipeline`/estimator travels
  in the promoted artifact; only its extracted numbers do,
- a tradeable verdict, ever, regardless of how the parity checks below turn
  out.

---

## 2. The parameter-file schema

Two files make up one promoted artifact, together:

**`manifest.json`** (`research/datasets/promoted_artifact.py`,
`PromotedArtifactManifest`) — identity, provenance, declared shape:

```text
schema_version               "promoted_artifact.v1"
artifact_fingerprint         SHA-256, see §4
run_fingerprint              the source Predictive Research run's fingerprint
dataset_fingerprint          the source run's dataset fingerprint
fold_id                      the promoted (last) walk-forward fold, see §7
features                     ORDERED list of feature identity strings —
                              canonical-JSON encodings of the declared
                              FeatureSpec (component/parameters/output/alias),
                              positional: column order is part of the
                              artifact's meaning, because the evaluator's
                              arithmetic is positional
model_family                 sklearn.ridge | sklearn.elastic_net | sklearn.logistic
format                       "numpy_parameter_file"
format_version               "v1"
preprocessing_spec           the fold-local PreprocessingSpec (IMPUTE_MEDIAN,
                              STANDARDIZE by default)
estimator_spec                the source EstimatorSpec (family + hyperparameters)
training_library              "sklearn" — PROVENANCE ONLY, see §5
training_library_version      recorded sklearn version — PROVENANCE ONLY, see §5
created_at_utc                promotion timestamp
```

**`artifact.json`** (`research/predictive/promotion/parameters.py`,
`PromotedArtifactParameters`) — the fitted numbers:

```text
coefficients          one weight per feature, same positional order as
                       manifest.features
intercept             scalar
impute_median          optional, per-column — present only if IMPUTE_MEDIAN
                       was fitted
standardize_mean       optional, per-column — present only if STANDARDIZE
                       was fitted
standardize_scale      optional, per-column — present only if STANDARDIZE
                       was fitted
```

Evaluation (`research/predictive/promotion/evaluator.py`):

```text
x := impute_median(features)              # NaN -> per-column fitted median
z := (x - standardize_mean) / standardize_scale
y := z @ coefficients + intercept
     and, for sklearn.logistic only, p := 1 / (1 + exp(-y))
```

The fitted preprocessing statistics travel **inside** the artifact as one
unit with the estimator parameters — never re-fitted or re-implemented
elsewhere.

---

## 3. Store layout

This is the **only** place this tree appears in the documentation set — do
not duplicate it. `docs/reference/system/MODULE_MAP.md`'s Predictive Research
section links here instead of repeating it.

```text
<workspace>/research/predictive_research/promoted/{artifact_fingerprint}/
    manifest.json     PromotedArtifactManifest, see §2
    artifact.json      PromotedArtifactParameters, see §2
```

Nothing else lives in that directory and nothing else lives in
`research/predictive_research/promoted/`: no index, no `latest` pointer, no
status field, no lock file. `PromotedArtifactRepository.write` refuses to
overwrite an existing directory; `read_manifest` reads only `manifest.json`
and never touches `artifact.json`, so it succeeds even against a corrupt or
missing payload. This is a deliberate negative constraint (ADR-0024
condition 5, ADR-0029 §2) — TD-021 (no model registry) stays deferred; a
plan that starts adding an index file or a `latest` pointer here has misread
the ADR.

---

## 4. Fingerprint derivation

`compute_promoted_artifact_fingerprint`
(`research/datasets/promoted_artifact.py`) is SHA-256 over canonical JSON
(`sort_keys=True, separators=(",", ":")`, mirroring
`compute_run_fingerprint`) of:

```text
run_fingerprint, fold_id, format, format_version, model_family,
the ORDERED feature identities, preprocessing_spec, estimator_spec
```

**Fitted parameter values are never hashed.** Identity is "which run, which
fold, which spec" — promoting the same run and fold twice produces the same
fingerprint, and the function's signature has no coefficient/intercept
parameter at all, so a perturbed fitted value cannot reach the hashed
payload. Feature **order** is part of identity (positional arithmetic), so
permuting feature order changes the fingerprint even though the same
features are present.

---

## 5. Both guards

Two separate guards exist, at two separate times, protecting two separate
things. Confusing them is the most common way to misread this mechanism.

### Load-time guard — `load_promoted_artifact` (`research/predictive/promotion/evaluator.py`)

Runs every time a promoted artifact is loaded. Hard-fails, **before any
arithmetic**, on:

- an unknown `format_version`,
- a `model_family` outside the linear/logistic allow-list,
- a `preprocessing_spec` step the evaluator does not implement,
- a feature-count mismatch between the manifest and the payload.

Raises `PromotedArtifactFormatError`
(`research/predictive/errors.py`). **There is no bypass** — no
`strict=False`, no `allow_mismatch`, no environment variable, anywhere in
the API surface.

**What to do when it fires:** re-promote the run. The artifact directory is
content-addressed and immutable by design; there is no repair path other
than producing a fresh, correct artifact.

**The one deliberate relaxation:** a difference between the artifact's
recorded `training_library_version` and the installed scikit-learn version
does **not** refuse a load. `training_library` / `training_library_version`
are provenance fields only — a parameter file has no coupling to
scikit-learn, because scikit-learn is not involved in reading it. The
numbers mean the same thing under any installed scikit-learn version.

### Promotion-time guard — `require_promotion_sklearn_version` (`infrastructure/ml/promotion.py`)

Runs once, during `promote_predictive_run`, **before any blob is unpickled**.
Compares the source run manifest's recorded `library` / `library_version`
against the installed `sklearn.__version__`. A mismatch raises
`PromotionVersionMismatchError` and the promotion **writes nothing**.

**What to do when it fires:** re-run the study under the installed
scikit-learn version, then promote the new run. Already-promoted artifacts
are unaffected — they carry no library coupling at all (see the load-time
guard's relaxation above).

A separate check, `require_supported_model_family`, also runs at promotion
time, before touching any blob: a family outside the linear/logistic
allow-list raises `PromotedFamilyUnsupportedError` naming the family, and
**writes nothing**. See §6.

**Why two guards, not one:** the load-time guard protects a parameter file
that has no library coupling. The promotion-time guard protects a joblib
blob unpickle, which is genuinely unsafe across library versions. They
protect different operations and neither can substitute for the other.

---

## 6. The linear/logistic-only restriction, and the deferred joblib path

v1 promotes exactly three families: `sklearn.ridge`, `sklearn.elastic_net`,
`sklearn.logistic`. A promotion attempt for a tree family (XGBoost, LightGBM,
CatBoost) or a neural family (torch feedforward/LSTM/GRU) is a **refusal
with a clear message** naming the family and stating the deferral
(`PromotedFamilyUnsupportedError`) — never a silent no-op and never a TODO
left in running code.

**Why:** the pure-NumPy parameter-file format only has a closed-form
expression for linear/logistic evaluation. Tree ensembles and neural
networks need a different, version-pinned serialization path (most likely a
pinned joblib/ONNX-style blob), which would put scikit-learn (or XGBoost, or
torch) into the dry-run/live runtime image — exactly what this format was
chosen to avoid. That is deferred, not rejected: **TD-029** tracks it as
owned technical debt with a concrete repayment trigger (see
`docs/planning/TECHNICAL_DEBT.md`).

---

## 7. The last-fold policy and its one-fold staleness

Promotion always selects the run's **last walk-forward fold** — the highest
`fold_id` the run persisted a model blob for. One promotion produces exactly
one artifact: one `(run_id, fold_id)` pair, one fingerprint, one directory.
The chosen `fold_id` is recorded in the manifest, never implicit.

**Honest limitation:** the last fold's TRAIN window ends *before* the last
TEST window, so the promoted artifact is already stale by one fold at
promotion time. This was chosen deliberately over a final refit on all rows,
whose out-of-sample performance would be *by construction unmeasured* — the
exact drift ADR-0024 warns "is not sufficient for promotion."

---

## 8. The two parity comparisons — only one carries a tolerance

"Exact match" names two structurally different comparisons in this
mechanism. Conflating them is, per ADR-0029 §6, "the single most likely way
this mechanism gets misread later."

```text
COMPARISON 1 — OFFLINE vs ONLINE. The RELEASE GATE. Sprint 050 (Phase 14B), not built yet.
    NumPy evaluator (batch research path) == NumPy evaluator (dry-run runtime path)
    Same code, same artifact, same float64 inputs.
    BAR: EXACT, unconditionally. No tolerance, ever.

COMPARISON 2 — NUMPY vs SKLEARN. THE CROSS-CHECK. Sprint 049 (Phase 14A), Path A. DONE.
    NumPy evaluator == predictions.parquet, which scikit-learn produced.
    Two different implementations of the same mathematics.
    BAR: exact for linear; ulp-bounded for the logistic probability ONLY.
```

Comparison 1 is what ADR-0024 condition 4 actually gates on, and it is not
weakened by anything in this sprint — it has not been built yet at all.
Comparison 2 is a quality check on the framework's own arithmetic against
the library's, run this sprint (T010b), where a tiny disagreement is
structurally possible: `sklearn.LogisticRegression.predict_proba` uses
`scipy.special.expit`, which is not required to agree bit-for-bit with a
NumPy `1 / (1 + exp(-z))`.

The tolerance table, from `predictions.parquet`'s separate `y_pred` /
`y_proba` columns:

| Compared value | Family | Bar |
|---|---|---|
| `y_pred` | ridge, elastic_net | **exact** (`==` on float64) |
| `y_pred` (class label) | logistic | **exact** |
| decision function `z = Xw + b` | logistic | **exact** — asserted separately from the sigmoid |
| `y_proba` | logistic | **`rtol=0, atol=1e-15`** — and only here |

**Measured result (T010b, this sprint):** the observed maximum `y_proba`
deviation was **`0.0`** — well under the `atol=1e-15` ceiling. Comparison 2
Path A held exactly, with no measurable drift, even in the one place a
tolerance was permitted. See `docs/planning/sprints/SPRINT_049.md` §6
(S049-T010b row) and its Sprint Review for the full record.

**The tolerance is not inherited by Sprint 050.** If Comparison 1 is ever
non-exact, that is a failure of the release gate, full stop — regardless of
what Comparison 2 measured here.

---

## 9. What this sprint does not build

Promotion (this document) is **all** that Sprint 049 / Phase 14A ships. It
deliberately does **not** ship:

- any Market Analysis component, `ComponentId`, or registry entry,
- any executor, planner, or assembler change,
- inference-time `available_at` enforcement (ADR-0024 condition 2 — the
  S049-T001 spike found the executor mechanism this condition presupposes
  does not exist today; ADR-0030 is needed and sizes Sprint 050),
- a State reachable from any Signal Model or strategy,
- the online half of the parity release gate (Comparison 1 above),
- any dry-run session.

Phase 14 (both increments) is **not** complete after this sprint. See
`docs/planning/CURRENT_STATUS.md` and ROADMAP §13F.

---

## 10. Operator usage

```powershell
uv run trading-cli research promote --config <path>
```

```yaml
research:
  promote:
    run_id: 0123456789abcdef
```

Prints `artifact_fingerprint` and the absolute `directory` on success.
Promotion needs the `ml` extra (`uv sync --extra ml`) — it reads a joblib
blob once. **Loading an already-promoted artifact needs no extra at all.**
See `docs/reference/modules/OPERATOR_CLI.md` for the full command reference and
refusal list.

---

## 11. Related documents

- `docs/adr/ADR-0029-promoted-predictive-artifact.md` — the binding design
  record: alternatives considered, the exact ADR-0023 §7 amendment, and the
  maintainer's answers to every open question.
- `docs/adr/ADR-0024-machine-learned-state-promotion.md` — the five
  promotion conditions this mechanism partially closes (1 and 5, plus
  condition 4's offline half).
- `docs/planning/sprints/SPRINT_049.md`, `S049_AVAILABILITY_FINDING.md` —
  the sprint plan and the condition-2 spike.
- `docs/reference/modules/OPERATOR_CLI.md` — the `research promote` command
  reference.
- `docs/reference/system/MODULE_MAP.md` — package responsibilities and workflow
  diagram.
- `docs/planning/TECHNICAL_DEBT.md` — TD-021 (no model registry), TD-022
  (fitted-artifact portability), TD-029 (deferred tree/neural joblib path).
- `src/trading_framework/research/predictive/CLAUDE.md`,
  `src/trading_framework/infrastructure/ml/CLAUDE.md` — module-level
  conventions for contributors working in these packages.
