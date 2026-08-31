# Sprint 046 — Wave 0 Decisions

Binding decisions for the universal operator CLI `trading-cli` (Phase 11).
Date: 2026-08-31.

```text
Status: Accepted — Wave 0 Checklist (§13) approved 2026-08-28; implementation
        queued behind Sprint 045 (sequential, not parallel)
Basis:  docs/product/PRD.md (confirmed)
        docs/adr/ADR-0026 (ACCEPTED)
        docs/adr/ADR-0022 (apps/* boundary; scripts/ stay thin)
        docs/planning/sprints/SPRINT_046.md
        scripts/ and src/trading_framework/application/ as on main
```

Sprint 045 (Binance historical ingestion) is a **separate** sprint with its own
Wave 0 and its own ADR. Only `data fetch binance` (S046-T010) depends on it.
No decision below may be reopened to accommodate the importer's design.

---

## Inherited locks (do not reopen)

```text
ADR-0022: apps/* are deployable consumers; scripts/ stay thin
ADR-0022: no app reimplements research or execution engine internals
Existing scripts, their flags and their tests remain valid
ML extras stay out of default installs and default CI
```

---

## D-S046-01 — Problem statement

45 scripts, each with its own `argparse` entry point and flag set. The working
loop — fetch data → build dataset → run research → render report — is a
remembered sequence of `uv run python scripts/.../foo.py --flag value`
invocations, with identifiers copy-pasted between steps.

**This sprint ships exactly:** one `trading-cli` entry point with four command
groups, driven by a YAML config, delegating to existing application workflows.

**Not this sprint:** any new capability; the Binance importer; wrapping the
other 37 scripts; changing any existing script.

---

## D-S046-02 — Sprint branch and PR base

```text
Integration branch: sprint/operator-cli    (cut from main)
Working branches:   feat/ | fix/ | docs/ | test/ + descriptive slug
PR base:            sprint/operator-cli    (never main until integration)
```

Working-branch PRs squash-merge into the sprint branch. When the sprint is
complete, one integration PR goes `sprint/operator-cli` → `main`.

---

## D-S046-03 — Thin-wrapper audit result (binding)

The PRD's riskiest assumption was audited before this sprint was opened. Full
table in `SPRINT_046.md` §4. The binding outcome:

```text
HOLDS       43/45 scripts expose def main(argv: list[str] | None = None) -> int
            no sys.argv reads, no import-time side effects, no global state
FAILS       main() returns only an int; identifiers reach stdout only
            → composition through main() would require parsing stdout
FAILS       run_strategy_research.py hardcodes build_canonical_strategy_model(),
            SimulationAssumptions(), CmeEsRthSessionResolver();
            build_predictive_dataset.py hardcodes the session resolver
```

**Locked delegation rule:**

```text
Preferred   YAML → application Request dataclass → workflow → typed result
Fallback    construct argv → script main(argv) → int, only where no application
            entry point exists; SystemExit from parse_args is translated into a
            CLI configuration error
Never       reimplement a workflow
Never       parse another command's stdout
Never       edit a script's internals to make wrapping easier
```

**Locked consequence:** where a script hardcodes a choice, the CLI inherits that
limitation and **documents** it. Exposing it is an application-layer change and
belongs to a later increment, not here.

---

## D-S046-04 — CLI framework: stdlib `argparse`

```text
Chosen      argparse subparsers (stdlib)
Rejected    typer, click — a new runtime dependency (plus click, rich,
            shellingham) for ergonomics that matter little when the real input
            is a YAML file, in a repo whose 45 CLIs are all argparse
Config      pyyaml — already a runtime dependency; nothing new
```

**Locked:** this sprint adds **no new runtime dependency**. If a task appears to
need one, stop and raise it — that is a governance decision, not an
implementation detail.

Global flags, and only these:

```text
--config PATH   required for every command
--dry-run       resolve and print the plan; touch nothing
--json          machine-readable output
--verbose       diagnostics
```

Long per-command flag lists stay out. YAML is the input contract.

---

## D-S046-05 — Placement: `apps/cli`

```text
apps/cli/pyproject.toml        own package, uv workspace member
[project.scripts]              trading-cli = "trading_cli.__main__:main"
invocation                     uv run trading-cli <group> <command> --config ...
```

Rejected: `scripts/cli/`. ADR-0022 rule 3 requires `scripts/` to stay thin —
parse args, call an application API, write output. A multi-group CLI with a
config schema, validation, a plan renderer and its own test suite is not thin.

`scripts/` is **not** removed or reduced. The CLI is an additional front door.

---

## D-S046-06 — Import boundary (differs from `apps/dashboard`)

```text
apps/dashboard   must NOT import trading_framework at all          (unchanged)
apps/cli         MAY import trading_framework.application.*
apps/cli         MUST NOT import trading_framework.research.*,
                 .market_analysis.*, .strategy.*, .execution.*,
                 or infrastructure adapters directly
apps/cli         MUST NOT contain research, simulation or execution logic
```

The dashboard reads persisted artifacts; the CLI invokes workflows. Same
underlying rule — no engine internals reimplemented in an app — applied to a
different consumer shape. S046-T004 makes it a test; S046-T013 records it in
`apps/cli/CLAUDE.md` so a future agent editing that directory learns it without
reading ADR-0026.

---

## D-S046-07 — YAML config schema (locked shape)

Three layers: a thin common envelope, a per-group block, and pass-through
references to existing spec files.

```yaml
version: 1
storage_root: user_data/workspace

data:
  provider: binance | databento
  binance:
    mode: ohlcv
    symbol: BTCUSDT
    instrument_id: BTCUSDT.P
    interval: 1m
    start: 2025-01-01T00:00:00Z
    end:   2025-04-01T00:00:00Z
    publish: true
  databento:
    archive: user_data/archives/....dbn.zst
    instrument_id: ...

research:
  kind: predictive | strategy
  predictive:
    definition: configs/study.yaml
    estimator:  configs/ridge.yaml
    persist: true
    render_report: true
  strategy:
    dataset_ref: "BTCUSDT.P|ohlcv|1m|binance|binance-usdm-klines-v1@1"
    timeframe: 1m

dry_run:
  symbol: BTCUSDT
  duration_minutes: 60
  event_log: user_data/runtime/btc_futures_dry_run/events.jsonl

report:
  kind: predictive | strategy
  run_id: ...
  output: ...
```

**Locked rules:**

```text
version + storage_root are the ONLY cross-group keys
unknown keys are an error, never a warning
existing spec files (PredictiveStudySpec, EstimatorSpec) are referenced by
    path and parsed by their own loaders — never inlined, never re-parsed
timestamps are ISO-8601 UTC (ADR-0003)
validation and resolution happen BEFORE any side effect
--dry-run prints the resolved plan and exits 0
NO credentials in any config file, ever
```

Resisting a fat shared section is deliberate: the four groups have almost
nothing in common, and a common block would invent coupling and turn every new
group into a schema migration.

---

## D-S046-08 — Credentials

```text
Binance API key   TRADING_FRAMEWORK_BINANCE_API_KEY only (ADR-0025 §5)
Config files      a key-shaped value (e.g. api_key, secret, token) is REJECTED
                  by the loader, not merely discouraged
Output            no command echoes an environment credential in any mode,
                  including --dry-run and --verbose
```

The CLI holds no credential logic of its own. It never reads the key; the
importer does.

---

## D-S046-09 — Error taxonomy and exit codes

```text
0   success
1   workflow failure (a wrapped workflow raised or returned non-zero)
2   configuration or usage error (bad YAML, unknown key, missing file,
    unsupported provider/kind, credential-shaped key)
```

**Locked:** an operator must never see an argparse usage message referring to
flags they did not type. Where the `main(argv)` fallback is used, `SystemExit`
from `parse_args` is caught and translated into an exit-code-2 CLI error naming
the config key that produced the bad argument.

---

## D-S046-10 — Command groups and their delegation path

| Command | Path | Notes |
|---------|------|-------|
| `data fetch binance` | application (S045 workflow) | Gated on Sprint 045; until then an explicit "requires Sprint 045" error, never a stack trace |
| `data fetch databento` | application (archive import) | Naming caveat: this is a local archive **import**, not a network fetch — say so in help text |
| `research run predictive` | application, composed build → run → render | The only composed command; typed results flow between steps |
| `research run strategy` | application | Inherits the hardcoded canonical strategy model (D-S046-03); documented, not patched |
| `dry-run start` | application (existing runtime) | `asyncio.run` is invoked by the wrapped path; the CLI must not already be in an event loop |
| `report render predictive` \| `strategy` | application | Smallest slice; implemented first to prove the config contract |

Scope is exactly these. `ops`, `demo`, `robustness_research` and
`signal_research` are **not** wrapped in v1. Adding a group later is additive.

---

## D-S046-11 — Testing

```text
apps/cli/tests/     CLI's own suite, own CI job (apps/dashboard pattern)
Unit                config validation: valid, unknown key, missing required,
                    credential-shaped key, wrong version
Unit                exit-code taxonomy incl. translated SystemExit
Unit                --dry-run writes nothing (asserted, not assumed)
Integration         each command against fixtures / a tmp storage_root
Boundary            import test per D-S046-06
```

No network in CI. No ML extra in the CLI environment. Wrapped workflows are not
re-tested here — they already have coverage; the CLI tests the seam.

---

## D-S046-12 — Docs this sprint touches

```text
docs/planning/sprints/S046_WAVE0_DECISIONS.md   this file (new)
docs/planning/sprints/SPRINT_046.md             status + task progress
docs/adr/ADR-0026-...md                         PROPOSED → maintainer sets ACCEPTED
docs/adr/README.md                              index row
docs/reference/OPERATOR_CLI.md                  new — the schema, documented once
docs/reference/MODULE_MAP.md                    apps/cli entry
docs/reference/ARCHITECTURE_OVERVIEW.md         apps/cli as a consumer
apps/cli/CLAUDE.md                              module context (boundary)
docs/planning/CURRENT_STATUS.md                 Active Sprint S046
docs/planning/ROADMAP.md                        Phase 11 (Wave 3)
```

**Not this sprint:** ADR-0025, any Binance import document, any change to
existing script READMEs beyond a pointer to the CLI.

---

## D-S046-13 — Wave 0 Checklist (maintainer)

- [x] ADR-0026 approved (status moved PROPOSED → ACCEPTED)
- [x] D-S046-04 confirmed: stdlib `argparse`, no new runtime dependency
- [x] D-S046-05 confirmed: `apps/cli` as a workspace member, not `scripts/cli/`
- [x] D-S046-06 confirmed: `apps/cli` may import `application.*` — a deliberate difference from `apps/dashboard`
- [x] D-S046-07 config schema shape confirmed (thin common envelope; spec files by path)
- [x] D-S046-03 accepted, including that hardcoded script choices stay hardcoded in v1
- [x] Sprint 046 scope and 14-task breakdown approved
- [x] Branch `sprint/operator-cli` approved
- [x] Decision confirmed on sequencing relative to Sprint 045: **sequential — Sprint 045 first, Sprint 046 after**, not parallel

Approved-by: Filip Folga (project maintainer), given directly in conversation
with the orchestrating Claude Code session on 2026-08-28 — "Tak, zatwierdzam
wszystko", after correcting the architect to open Sprint 045 and Sprint 046 as
two independent sprints (not one combined sprint).

Design is fully locked. **Implementation is queued behind Sprint 045**, not
started now: the maintainer chose the sequential option over running both
sprints in parallel. Do not cut `sprint/operator-cli` or pick up S046-T001
until Sprint 045 has merged to `main`.
