# PRD — Custom Strategy Authoring (CLI loader, component catalog, Exit/Risk expansion)

Feature-level PRD within the existing Trading Research Framework product,
following the grill-me discovery pattern established for Phase 2F/11
(`docs/product/PRD.md`). Distinct file because that PRD is a closed historical
record of an already-delivered decision, not a place to accumulate unrelated
future features.

## Problem

`trading-cli research run strategy` always evaluates the Sprint 013 canonical
example (`build_canonical_strategy_model()`), hardcoded in
`scripts/strategy_research/run_strategy_research.py` and inherited unchanged
by the CLI (SPRINT_046.md §4 Finding 2). No config field, YAML or otherwise,
can select a different strategy. Confirmed directly: a `research.strategy`
config block with no strategy-selecting field at all still produces a run
manifest with `strategy_model_id: "high_vol_higher_low_fixed_exit"`.

Two structural causes make this more than a CLI gap:

1. The Market Analysis component catalog is thin — mainly
   `volatility.{atr,true_range,state}`, `structure.{swing,session_range}`,
   `trend.{ema,slope}`. There is not much to compose a Market/Signal Model
   from beyond the canonical example's own two components.
2. `strategy/exit_model.py` and `strategy/risk_model.py` have exactly one
   implementation each (`FixedBarsExitModel`, `FixedQuantityRiskModel`) —
   the simplest possible placeholder, not a realistic strategy-construction
   primitive (no stop-loss/take-profit, no equity-relative sizing).

## Goals (v1)

- **CLI loads a user-authored strategy from a single config key.**
  `research.strategy` gains one field — a file path
  (e.g. `strategy_file: user_data/components/strategies/my_strategy.py`) —
  not a module+function pair. The CLI imports that file dynamically and
  calls a function at a **fixed, conventional name**, `build_strategy()`
  (zero arguments, returns `StrategyModelDefinition`) — the exact shape
  already demonstrated by hand in `user_data/components/strategies/*.py`.
  No function-name field in config; the convention is fixed so the schema
  stays a single key, matching how `PredictiveStudySpec`/`EstimatorSpec`
  files are already "referenced by path, never re-encoded" elsewhere in the
  CLI's config contract (ADR-0026 §4). This is intentionally an
  executable-code loader, not a declarative spec: the framework has no YAML
  serialization for `StrategyModelDefinition` today, and building one from
  scratch is out of scope for v1. The security model is the same as running
  any local script the operator already trusts — no sandboxing, and this
  must be stated plainly in the operator guide, not left implicit.
- **Expand the Market Analysis component catalog** with a small set of new
  components through the existing `model_authoring` DSL pattern (see
  `volatility.atr`, `structure.session_range`, `trend.slope` as the
  precedent) — exact catalog left to the architect to scope, but should be
  chosen for composability into realistic example strategies, not
  arbitrarily.
- **Expand Exit/Risk models** beyond the two placeholders — realistic
  variants (candidates: stop-loss/take-profit exit, equity-percentage risk
  sizing), implementing the existing `ExitModel`/`RiskModel` protocols
  unchanged.
- **Compose the above into working example strategies** that exercise a new
  component, a new Exit or Risk model, and the CLI loader end-to-end —
  proving the three pieces actually work together, not just in isolation.

## Non-goals (v1)

- A declarative (YAML/JSON) strategy specification format — Python-module
  loading only. A future increment may revisit this if the Python-loader
  approach proves limiting.
- Any change to the simulation/backtesting engine (`BarSequentialSimulator`)
  itself.
- Sandboxing or restricting what a loaded strategy module can do — out of
  scope, and arguably contrary to the operator's own-trusted-code model this
  PRD accepts.
- A strategy registry, catalog UI, or discovery mechanism for user-authored
  strategies — the CLI loads exactly the one module/function path given in
  config, nothing more.
- Live trading or execution changes of any kind.

## Success metrics

- `trading-cli research run strategy --config <path>` runs a strategy loaded
  from a user-specified Python module, not the hardcoded canonical example,
  and the run manifest's `strategy_model_id` reflects the loaded strategy.
- At least one new Market Analysis component and at least one new Exit or
  Risk model are exercised by a real, passing example composed through the
  new loader.
- The canonical example strategy continues to work unmodified — this is
  additive, not a replacement of the existing hardcoded-default path (open
  question for the architect: does an unspecified `research.strategy` config
  still fall back to the canonical example, or does the loader become
  required once this ships? — see Open Questions).

## Riskiest assumption

That dynamic Python-module loading integrates cleanly with the CLI's
existing import-boundary discipline (ADR-0026 + Amendment 1). Importing an
arbitrary user-supplied module at runtime is a different risk shape than the
CLI's own internal imports — the architect should explicitly address whether
this needs its own boundary consideration (e.g. is a loaded strategy module
itself expected to only import from `trading_framework.model_authoring`/
`trading_framework.strategy`, or is it unconstrained since it runs as the
operator's own trusted code) rather than leaving it implicit.

## Open questions

- Exact component catalog for the Market Analysis expansion (architect
  scopes this against what composes well into example strategies).
- Exact Exit/Risk variants beyond stop-loss/take-profit and equity-percentage
  sizing, if any.
- Fallback behavior when `research.strategy` doesn't specify a custom
  strategy: keep defaulting to the canonical example, or require it
  explicitly once the loader exists?
- Whether this is one sprint or needs splitting — unlike Binance
  ingestion/CLI (two independent tracks), these three pieces (loader,
  catalog, Exit/Risk) are gated on each other for a working demonstration,
  so a single sprint with sequential waves is the default assumption unless
  the architect finds a reason to split.

## Handoff

Architect: design the CLI loader (module/function resolution, error
handling for a bad path/missing function/wrong return type, import-boundary
treatment), the specific component catalog additions, and the specific
Exit/Risk model additions as a Wave 0 decision set, per this project's
established sprint-opening conventions (`docs/planning/sprints/SPRINT_XXX.md`
+ `S0XX_WAVE0_DECISIONS.md`, ADR(s) where a new architectural pattern is
introduced — the strategy-loading mechanism likely needs one, mirroring
ADR-0026's treatment of the CLI's own design).
