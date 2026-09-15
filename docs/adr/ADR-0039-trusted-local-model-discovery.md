# ADR-0039 — Trusted Local Model Discovery and Resolution

## Status

ACCEPTED

Drafted during architecture triage of `docs/product/PRD-research-workbench-mvp.md`
(open question "Trusted local model discovery"). Approved by the maintainer
in conversation, 2026-09-14.

## Context

The PRD requires the workbench to let a user "select compatible existing Market
and Signal Models, including trusted local user models", without "importing every
Python file during a read-only catalog scan" and without "weakening the existing
trusted-code warning".

Current facts:

- `src/trading_framework/research/signal_research/model_registry.py` resolves
  model identifiers through two **private module-level dicts** holding six
  hardcoded aliases, all pointing at Sprint 006 canonical builders. There is no
  listing API and no user-model path at all.
- `user_data/models/` is the documented home for "Market Model and Signal Model
  definitions" (`docs/reference/system/USER_WORKSPACE.md`), but nothing reads it.
- ADR-0027 already decided the trust model for operator-authored Python: a
  single `*_file` config key, a fixed zero-argument entry point, **no sandbox,
  no import restriction**, loaded at plan-resolution time, with the blast radius
  stated in one plain sentence in the docs and in `--help`.

The unsolved part is discovery: ADR-0027 assumes the operator already knows the
path. A catalog UI must *list* candidates, and listing must not execute code.

## Decision

### 1. Two resolution sources, both explicit

```text
BUILT_IN   an identifier resolved by the framework's model registry
USER_FILE  a path to an operator-authored .py file (ADR-0027 mechanism)
```

Nothing is resolved by scanning `sys.path`, by an entry-point registry, or by
any implicit global namespace.

### 2. Built-in models become listable

The private dicts in `model_registry.py` are replaced by an explicit, listable
catalog exposing, per entry: `model_id`, `kind` (`MARKET` | `SIGNAL`),
`title`, `description`, and the resolved parameter summary that
`resolve_models_from_definition` already builds. The resolution behaviour is
unchanged; only its visibility changes. Aliases remain supported.

### 3. Operator-authored models follow ADR-0027 exactly

New optional keys on `SignalResearchDefinitionSpec`, mirroring `strategy_file`:

```yaml
market_model_file: user_data/models/my_regime.py     # entry: build_market_model()
signal_model_file: user_data/models/my_signal.py     # entry: build_signal_model()
```

- Fixed, zero-argument, conventional entry-point names. No `module:function`
  pair, no dotted path.
- `market_model` / `market_model_file` are mutually exclusive; same for signal.
- Loading uses ADR-0027 §3's mechanism verbatim (synthetic collision-proof
  module name, registered in `sys.modules` before `exec_module`, `sys.path`
  never mutated, path resolved to an absolute path and echoed in the plan).
- Error taxonomy follows ADR-0027 §5, with `StrategyModelDefinition` replaced by
  `MarketModelDefinition` / `SignalModelDefinition` and their existing
  validators.
- Security model is ADR-0027 §2, unchanged and unweakened: **no sandbox, no
  import restriction, no AST inspection.** Loading a model file is equivalent in
  blast radius to `uv run python <that file>`.

### 4. Discovery never imports Python

A read-only catalog scan of `user_data/models/` reads **declarative sidecars
only**:

```text
user_data/models/<name>/model.yaml      # sidecar, read during a catalog scan
    model_id:      my_regime
    kind:          MARKET | SIGNAL
    entry_point_file: my_regime.py      # relative to the sidecar
    title:         ...
    description:   ...
    timeframe:     1m                   # optional compatibility hint
```

Classification during a scan:

| Found | Listed as | Selectable |
|---|---|---|
| sidecar + existing entry file | `DECLARED` | yes, from the catalog |
| sidecar without a readable entry file | `BROKEN` + reason | no |
| `.py` with no sidecar | `UNDECLARED — not inspected` | yes, by explicit path |
| sidecar with unknown `kind`/keys | `UNSUPPORTED` + reason, never rewritten | no |

A sidecar is a **convenience index, not an authority**. It is never used to
infer a model's parameters, identity, or compatibility — only to offer a name
and a path. The authoritative facts come from the definition object returned by
the entry point at resolution time.

### 5. Import happens once, at plan resolution, before side effects

Per ADR-0027 §4, the file is imported and the builder called during preflight
resolution — inside the trusted control/job process, never during a catalog
listing and never in the presentation layer. ADR-0027's narrowed guarantee
carries over verbatim and must be repeated in the workbench UI:

> The application itself performs no side effect during validation; the loaded
> model module is operator code and executes at import.

The UI shows this warning at the moment a user selects a `USER_FILE` model, and
the resolved plan names the absolute path that will be executed. The warning is
never collapsed behind a "don't show again" control in this increment.

### 6. Run identity covers operator model content

`component_lineage_hashes` (already produced by `resolve_models_from_definition`)
gains, for a `USER_FILE` model: the resolved absolute path **and** a sha256 of
the entry file's bytes. Two different edits of the same file therefore produce
different lineage, so a re-run after an edit is not silently mistaken for the
earlier run.

**Accepted residual risk:** the content hash covers only the entry file, not its
sibling imports or any data it reads. A model whose behaviour lives in an
imported helper can change without changing the lineage hash. This is accepted
for the MVP and must be logged as technical debt with a repayment trigger
(the first time a multi-file operator model exists), alongside TD-025 which
records the same structural blindness for the boundary test.

## Alternatives Considered

1. **Import every `.py` under `user_data/models/` to build the catalog.**
   Rejected outright: it executes arbitrary operator code as a side effect of
   opening a listing page — the PRD's stated prohibition, and a far worse
   surprise than an explicit selection.
2. **AST-parse each file to extract metadata without executing.** Rejected:
   fragile (a `build_signal_model()` that composes values at runtime yields
   nothing useful), and it creates a second, silently-wrong source of truth for
   model identity.
3. **A decorator-based or `importlib.metadata` entry-point registry.** Rejected
   for the same reason ADR-0027 §"Alternatives" 3 rejected it: it trades an
   explicit path for an implicit global namespace whose failure mode
   ("why did it pick that one?") is worse than "file not found".
4. **Make the sidecar mandatory.** Rejected: it would make an existing
   hand-written model file invisible until the operator writes boilerplate, and
   ADR-0027's path-based selection already works without one.
5. **Sandboxed model execution.** Rejected: PRD non-goal, trivially defeated,
   real machinery protecting nothing (ADR-0027 §2).

## Consequences

### Positive

- Listing models is a pure filesystem read: safe, fast, and safe to run on every
  page load.
- One trust model across strategies (ADR-0027) and models (this ADR) — one
  sentence for the operator to learn, one place to change it.
- User models become usable from a Signal Research definition at all, which they
  currently are not, independent of the workbench.

### Negative

- The sidecar is a second artifact the operator must maintain, and it can drift
  from the code it points at. Mitigated by never treating it as authoritative.
- `resolve_models_from_definition` grows a code-loading path, so a Signal
  Research definition can now execute arbitrary code — a genuine widening of the
  research domain's attack surface relative to today's alias-only resolution.
  Accepted deliberately, on the same grounds as ADR-0027.
- Adding `market_model_file` / `signal_model_file` changes the definition
  payload and therefore `definition_hash`; see ADR-0038 §2 on version bumps.

## Follow-up

- Sprint Wave 0 must bind the exact sidecar key set and whether `timeframe` is a
  hint or a validated compatibility fact.
- The multi-file lineage gap needs a `TECHNICAL_DEBT.md` entry (proposed
  TD-026) with a concrete repayment trigger.

## Related

- `docs/adr/ADR-0027-operator-authored-strategy-loading.md`
- `docs/adr/ADR-0006-declarative-market-and-signal-models.md`
- `docs/adr/ADR-0038-canonical-signal-research-configuration-and-templates.md`
- `docs/reference/system/USER_WORKSPACE.md`
- `docs/reference/modules/MODEL_AUTHORING.md`
- `src/trading_framework/research/signal_research/model_registry.py`
- `docs/planning/TECHNICAL_DEBT.md` TD-025
