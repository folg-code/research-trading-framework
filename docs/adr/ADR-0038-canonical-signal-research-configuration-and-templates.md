# ADR-0038 — Canonical Signal Research Configuration Schema and Templates

## Status

ACCEPTED

Drafted during architecture triage of `docs/product/PRD-research-workbench-mvp.md`
(open questions "Canonical Signal Research configuration" and "Template
ownership"). Approved by the maintainer in conversation, 2026-09-14, including
the framework-package-plus-user_data resolution to §4's template-location fork
and acceptance of the §2 `definition_hash` break on existing run manifests.

## Context

The PRD requires that a UI-generated configuration round-trips through save and
reload without a material change to the resolved study, and that the saved file
is accepted by "the canonical non-UI configuration/workflow entry point selected
during architecture triage". It correctly notes that `trading-cli` has no Signal
Research command, so ADR-0026's v1 schema cannot be that entry point as it
stands.

The triage found that the schema itself already exists and is framework-owned:

```text
src/trading_framework/research/signal_research/definition.py
    SignalResearchDefinitionSpec   frozen dataclass, YAML/JSON-shaped
    to_dict() / from_dict()        symmetric serialization
    validate_signal_research_definition()   scope/model/baseline invariants
    compute_definition_hash()      sha256 over the normalized payload
    with_resolution()              attaches resolved params + lineage hashes

src/trading_framework/research/signal_research/loader.py
    load_signal_research_definition(path)

scripts/signal_research/run_signal_research.py
    --definition <path> → resolve → map_definition_to_run_request → run
```

Three real gaps:

1. **No version field.** The spec carries no `schema_version`, so an older
   application cannot safely refuse a newer file — it would silently
   misinterpret it. The PRD requires unsupported artifacts to be identifiable.
2. **No `trading-cli` command.** The only non-UI entry point is a `scripts/`
   argparse file, which ADR-0022 rule 3 keeps deliberately thin and which
   ADR-0026 §5 explicitly left unwrapped in v1.
3. **No templates.** "Start from a maintained template rather than an empty
   form" has no artifact to start from.

## Decision

### 1. `SignalResearchDefinitionSpec` is the single source of truth

The UI forms, the generated YAML, preflight validation, and non-UI execution all
resolve to this one type. `apps/workbench` **must not** define a second study
schema, a presentation-side mirror dataclass, or its own validation rules.

```text
UI form  ──►  dict  ──►  SignalResearchDefinitionSpec.from_dict()
                              │
YAML file ◄── to_dict() ◄─────┤   same object, both directions
                              │
trading-cli research run signal ──► resolve → run_signal_research
```

Validation shown in the UI is the framework's own
`validate_signal_research_definition` error text, not a reimplementation.

### 2. Explicit schema version

Add `schema_version: str = "signal_research.definition.v1"` to the spec and its
serialized payload.

```text
absent         → treated as v1 (every existing committed file keeps working)
known          → loaded
unknown/newer  → refused with an explicit reason; the artifact is classified
                 UNSUPPORTED (ADR-0042) and is NEVER migrated or rewritten
```

`schema_version` is excluded from `compute_definition_hash` inputs only if a
later version proves payload-compatible; for v1 it is included, so a version
bump is a material change by construction.

### 3. `trading-cli research run signal` is the canonical non-UI entry point

Added to ADR-0026 §4's `research` group, following its existing
reference-by-path rule ("existing spec files are referenced by path, never
inlined or re-parsed"):

```yaml
research:
  kind: signal                 # NEW alongside predictive | strategy
  signal:
    definition: configs/my_study.yaml   # SignalResearchDefinitionSpec, unchanged
    persist: true
```

- It uses the **application path** (`resolve_signal_research_definition` →
  `map_definition_to_run_request` → `run_signal_research`), which already
  returns a typed result with `run_id` — not the `main(argv)` fallback.
- `--dry-run` prints the resolved plan (dataset, scope, models, range, horizons,
  intended output location) with no side effect, satisfying the PRD's
  "validate and resolve the study before side effects" goal for both front doors
  at once.
- `scripts/signal_research/run_signal_research.py` stays. This is additive.
- ADR-0026 §5's "signal_research scripts are not wrapped in v1" is superseded
  for this one command group by this ADR.

The PRD's round-trip success metric is met against this command, and the binding
acceptance test is:
`from_dict(to_dict(spec)) == spec` **and** `compute_definition_hash` unchanged
across a save/reload cycle.

### 4. Template ownership and versioning

A template is **data**: a valid (possibly partial) `SignalResearchDefinitionSpec`
payload plus presentation metadata. It never contains executable code, a Python
path that is executed at listing time, or an embedded model body.

```text
src/trading_framework/research/signal_research/templates/*.yaml
    framework-owned, version-controlled, ships with a fork
    required keys: template_id, template_version, title, description
    body: a partial SignalResearchDefinitionSpec payload

user_data/config/signal_research/templates/*.yaml
    operator-owned, same shape, discovered and listed as USER
```

Rules:

- `template_id` is stable; `template_version` is an integer bumped on any
  material change. A template is never edited in place across a version.
- Templates reference Market/Signal Models **by identifier or by file path
  only** (ADR-0039). A template that names an unresolvable model is listed but
  flagged at selection time, not hidden.
- Applying a template produces a normal editable payload. The resulting run
  manifest records `template_id`/`template_version` in `resolved_parameters`
  for provenance; the template is **not** part of run identity (two studies that
  resolve to the same material inputs from different templates are the same
  study).
- Field-level UI metadata (labels, help text, allowed values) is derived from
  the spec's own enums and validators wherever possible; anything extra lives
  beside the template as data, never as UI-side branching.

### 5. No implicit expansion

`candidate_bounds.max_candidates` defaults to 1 and `model_family` exists in the
spec, but the workbench MVP submits exactly one explicitly specified study per
submission (PRD goal, and PRD non-goal "no UI field expands into an implicit
parameter grid"). A template must not ship a multi-variant `model_family`
in this increment.

## Alternatives Considered

1. **Invent a workbench-owned study schema and translate into the framework
   spec.** Rejected: two schemas means two validators, two sets of defaults, and
   a guaranteed drift; it also breaks the PRD's requirement that the saved file
   works outside the UI.
2. **Use ADR-0026's `research` YAML as the canonical schema directly.**
   Rejected: that envelope is a *CLI config*, not a study definition — its own
   rule is that study specs are referenced by path. Promoting it would duplicate
   `SignalResearchDefinitionSpec`.
3. **Make `scripts/signal_research/run_signal_research.py` the canonical entry
   point.** Rejected: ADR-0022 rule 3 keeps scripts thin and they are explicitly
   not a stable contract; the PRD asks for a supported non-UI entry point.
4. **Templates as Python builders.** Rejected: it would make listing templates
   require importing code, reintroducing exactly the problem ADR-0039 solves for
   models, for no gain — a study definition is pure data.
5. **Templates only in `user_data/`.** Rejected: a fresh fork would then have no
   maintained starting point, defeating "start from a maintained template".

## Consequences

### Positive

- No new schema is invented; the PRD's interoperability claim becomes structural
  rather than aspirational.
- A versioned schema makes the "unsupported, never migrated" requirement
  implementable for study files, not just run artifacts.
- The CLI gains a Signal Research command that the CLI's own users wanted
  independently of the workbench.

### Negative

- Adding `schema_version` touches `to_dict`/`from_dict`/hash and every committed
  example definition; existing `definition_hash` values recorded in past run
  manifests will not match a re-serialized spec. Past runs are immutable and are
  not rewritten — the mismatch must be documented, not patched.
- A fifth `trading-cli` command group widens ADR-0026 §5's deliberately small
  scope.
- Two template roots (framework and user) need a precedence and collision rule
  (framework wins on `template_id` collision; the user template is listed with
  an explicit shadowing warning).

## Follow-up

- Sprint Wave 0 must bind: the initial template set (2–3), the exact required
  template keys, and the `template_id` collision rule.
- Whether `definition_hash` should exclude `schema_version` is deferred to the
  first actual v2 bump.

## Related

- `docs/adr/ADR-0026-operator-cli-framework-and-placement.md` §4, §5
- `docs/adr/ADR-0011-signal-research-outcomes-and-persistence.md`
- `docs/adr/ADR-0039-trusted-local-model-discovery.md`
- `docs/adr/ADR-0042-workbench-catalog-index-and-comparison-facts.md`
- `docs/vision/RUN_IDENTITY_AND_CONFIGURATION.md`
- `src/trading_framework/research/signal_research/definition.py`
