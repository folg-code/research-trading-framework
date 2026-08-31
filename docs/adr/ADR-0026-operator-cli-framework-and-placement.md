# ADR-0026 — Operator CLI: Framework, Placement and Config Contract

## Status

ACCEPTED (Sprint 046)

Approved-by: Filip Folga (project maintainer), given directly in conversation
with the orchestrating Claude Code session on 2026-08-28, in response to a
summary of this ADR's key decisions (stdlib argparse + existing pyyaml, zero
new dependencies; `apps/cli` as a new workspace member with a relaxed-but-
tested import boundary; wrapping the application layer rather than script
`main()` functions, per the thin-wrapper feasibility audit). Answer: "Tak,
zatwierdzam wszystko" (approving this ADR, ADR-0025, the roadmap increment,
and opening both sprints together, in one confirmation), with an explicit
follow-up decision that Sprint 046 runs sequentially after Sprint 045
completes rather than in parallel — recorded here rather than left to point
at an external artifact, per the precedent set on ADR-0024/PR #345 in
Sprint 044.

## Context

`docs/product/PRD.md` records the second confirmed gap: 45 scripts under
`scripts/` each expose their own `argparse` entry point with their own flag
set. Running the research loop (fetch → build dataset → run research → render
report) means chaining several `uv run python scripts/.../foo.py --flag value`
invocations in the right order, from memory.

The PRD asks for one entry point, `trading-cli`, driven by a YAML config,
covering four command groups: `data fetch`, `research run`, `dry-run start`,
`report render`. It also names the **riskiest assumption**: that those scripts
can be unified as *thin wrappers* without touching their internals.

### Feasibility audit (performed for this ADR)

Every script in the four target groups was inspected:

```text
signature      def main(argv: list[str] | None = None) -> int      45 / 45
               (2 exceptions outside scope: run_aws_btc_futures_worker.py,
                backfill_dashboard_analytics_parquet.py take no argv)
body shape     _build_parser().parse_args(argv) → call an application
               workflow → print → return 0 | 1
sys.argv       never read directly outside parse_args(argv)
import-time    no import-time side effects; no global mutable state
```

So `main()` **is** callable programmatically. Two real limitations surfaced:

1. **Results are printed, not returned.** `main()` returns an `int` exit code;
   `dataset_id` / `run_id` / `output_path` only reach stdout. Chaining
   build → run → render through `main()` would require parsing stdout.
2. **Some choices are hardcoded inside `main()`.** `run_strategy_research.py`
   hardcodes `build_canonical_strategy_model()`, `SimulationAssumptions()` and
   `CmeEsRthSessionResolver()`; `build_predictive_dataset.py` hardcodes the
   session resolver. YAML cannot express what the script never exposed.

Both scripts, though, are already three-line adapters over an
**application-layer workflow** that *does* return a typed result object
(`RunPredictiveResearchRequest` → result with `run_id`/`fingerprint`,
`BuildStrategyDashboardRequest`, `ImportExternalDatasetRequest`, …).

The audit's conclusion is therefore: the assumption holds, but the correct
seam is the **application layer**, not `main()`.

## Decision

### 1. CLI framework: stdlib `argparse` subparsers

No new dependency. `argparse` is already the project-wide CLI style in all 45
scripts, and `pyyaml>=6.0.0` is already a runtime dependency, so the config
loader needs nothing new either.

```text
Rejected: click / typer (see Alternatives)
Flags:    only --config, --dry-run (print the resolved plan), --json, --verbose
          long per-command flag lists stay out; YAML is the input contract
```

### 2. Placement: `apps/cli`, a uv workspace member

`trading-cli` is a genuine deployable consumer, like `apps/dashboard`
(ADR-0022). It gets `apps/cli/pyproject.toml` with a
`[project.scripts] trading-cli = "trading_cli.__main__:main"` entry point and
joins `[tool.uv.workspace] members`.

**But it does not inherit the dashboard's import ban.** ADR-0022 rule 2 exists
because the dashboard reads *persisted artifacts* and must not recompute
research. A CLI's entire purpose is to invoke workflows, so:

```text
apps/dashboard   must NOT import trading_framework            (unchanged)
apps/cli         MAY import trading_framework.application.*   (allowed)
apps/cli         MUST NOT import trading_framework.research.*,
                 .market_analysis.*, .strategy.*, .execution.*,
                 or infrastructure adapters directly
apps/cli         MUST NOT contain research, simulation, or execution logic
apps/cli         MUST NOT reimplement anything that exists in application/
```

This is the same "no engine internals reimplemented" boundary ADR-0022 applies
to `apps/dashboard`, stated in the terms that fit a CLI. It is enforced by an
import-boundary test in the CLI's own test suite.

`scripts/` stays. The CLI is an additional front door, not a replacement, so
existing scripts, tests and demos keep working (PRD non-goal: "replacing all
45 scripts").

### 3. Delegation rule: application first, `main()` only as fallback

```text
Preferred   apps/cli maps YAML → an application Request dataclass and calls
            the application workflow, using its typed result
Fallback    where no application-layer entry point exists, call the script's
            main(argv) with a constructed argv list
Never       reimplement the workflow, parse another command's stdout, or
            edit a script's internals to make wrapping easier
```

Composition (build → run → render in one `research run`) is only allowed on
the application path, because that is the only path that returns identifiers.

When the fallback is used, the CLI catches `SystemExit` from `parse_args` and
converts it into a CLI-level configuration error — an operator must never see
an argparse usage message referring to flags they never typed.

### 4. YAML config contract

One schema, three layers: a common envelope, a per-group block, and an
untouched pass-through for existing spec files.

```yaml
version: 1                 # required; unknown version → error
storage_root: user_data/workspace   # required for every group

data:                      # trading-cli data fetch
  provider: binance | databento
  binance:                 # provider-specific block
    mode: ohlcv
    symbol: BTCUSDT
    instrument_id: BTCUSDT.P
    interval: 1m
    start: 2025-01-01T00:00:00Z
    end:   2025-04-01T00:00:00Z
    publish: true

research:                  # trading-cli research run
  kind: predictive | strategy
  predictive:
    definition: configs/study.yaml     # existing PredictiveStudySpec, unchanged
    estimator:  configs/ridge.yaml     # existing EstimatorSpec, unchanged
    persist: true
  strategy:
    dataset_ref: "BTCUSDT.P|ohlcv|1m|binance|binance-usdm-klines-v1@1"
    timeframe: 1m

dry_run:                   # trading-cli dry-run start
  symbol: BTCUSDT
  duration_minutes: 60
  event_log: user_data/runtime/btc_futures_dry_run/events.jsonl

report:                    # trading-cli report render
  kind: predictive | strategy
  run_id: ...
  output: ...              # optional; defaults to the workflow's default
```

Rules:

- **`version` and `storage_root` are the only cross-group keys.** Resisting a
  large shared section is deliberate: the four groups have almost nothing in
  common, and a fat common block would invent coupling that does not exist.
- **Existing spec files are referenced by path, never inlined or re-parsed.**
  `PredictiveStudySpec` and `EstimatorSpec` keep their own loaders and remain
  the single source of truth for their schema.
- Unknown keys are an **error**, not a warning — a typo must not silently
  change nothing.
- The CLI validates and resolves the config **before** any side effect, and
  `--dry-run` prints the resolved plan (workflow, arguments, output paths)
  without executing it.
- **No credentials in the config file.** Binance credentials come from
  `TRADING_FRAMEWORK_BINANCE_API_KEY` only (ADR-0025 §5). A config file
  containing an API-key-shaped key is rejected outright.

### 5. Scope boundary

Only the four groups. `ops`, `demo`, `robustness_research` and
`signal_research` scripts are **not** wrapped in v1. Adding a group later is
additive; nothing in the design assumes eventual coverage of all 45 scripts.

## Consequences

### Positive

- Zero new dependencies; nothing new for a reviewer or an agent to learn.
- One documented input contract instead of 45 flag sets.
- Wrapping at the application layer makes composition (`build → run → render`)
  possible, which stdout-chaining never would.
- Existing scripts and their tests are untouched, so blast radius is bounded.
- `--dry-run` makes a config reviewable before a multi-hour import starts.

### Negative

- `argparse` subparsers need more boilerplate than `typer` for help text and
  type coercion.
- Two front doors (CLI and scripts) must stay behaviourally consistent; the
  CLI is the only place that can drift.
- Where a script hardcodes a choice (canonical strategy model, session
  resolver), the CLI inherits that limitation. Exposing it is a separate,
  explicitly out-of-scope change to the application layer.
- A fourth workspace member adds a CI job.

### Neutral

- `trading-cli` is invoked as `uv run trading-cli ...`; no global install is
  assumed.
- YAML, not TOML/JSON, because `pyyaml` is already a dependency and existing
  spec files are YAML.

## Alternatives Considered

1. **`typer`.** Rejected: a new runtime dependency (plus `click`,
   `rich`, `shellingham`) for ergonomics the project does not need, in a repo
   whose 45 existing CLIs are all `argparse`. Its main advantage — deriving
   commands from type hints — is worth little when the real input is a YAML
   file, not flags.
2. **`click`.** Rejected for the same reason, with a less appealing decorator
   style relative to the existing code.
3. **`scripts/cli/main.py` instead of `apps/cli`.** Rejected: ADR-0022 rule 3
   says `scripts/` stay *thin* — parse args, call an application API, write
   output. A multi-group CLI with a config schema, validation and a plan
   renderer is not thin, and it needs its own console-script entry point and
   test suite. `apps/*` is the existing home for a deployable consumer.
4. **Wrapping every script via `main(argv)` uniformly.** Rejected: results are
   printed, not returned, so any composed command would have to parse stdout —
   a contract nothing guarantees.
5. **Refactoring scripts to return result objects first.** Rejected for this
   increment: it touches 45 files to serve 8, and the application layer
   already provides the seam. Revisit only if the fallback path spreads.
6. **One flat shared YAML section for all four groups.** Rejected: it would
   force unrelated commands to share a shape and turn every new group into a
   schema migration.

## Follow-up

- Sprint 046 Wave 0 (`S046_WAVE0_DECISIONS.md`) binds the exact per-command
  key sets, the error taxonomy, and which commands take the application path
  versus the `main(argv)` fallback.
- `data fetch binance` depends on Sprint 045 (ADR-0025) being merged; until
  then the group ships `databento` only, and `binance` is wired last.
- A follow-on increment may expose the strategy model / session resolver in
  the application layer; that is not this ADR's decision to make.

## Related

- `docs/adr/ADR-0022-repository-top-level-layout.md`
- `docs/adr/ADR-0025-binance-usdm-historical-klines-import.md`
- `docs/product/PRD.md`
- `docs/planning/sprints/SPRINT_046.md`
- `docs/planning/sprints/S046_WAVE0_DECISIONS.md`
