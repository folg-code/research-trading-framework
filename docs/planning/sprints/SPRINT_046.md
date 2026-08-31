# Sprint 046 — Universal Operator CLI (`trading-cli`, Phase 11)

## Metadata

```text
Sprint: 046
Phase: Phase 11 — Universal Operator CLI (opening and, in scope terms, closing increment)
Status: COMPLETE — 14/14 tasks done 2026-08-31, Phase 11 closed (ROADMAP §13C)
Planned Start: 2026-08-31
Planned End: 2026-08-31
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_045 (for the `data fetch binance` command only — see §9),
            SPRINT_028/029 (apps/* workspace precedent, ADR-0022),
            SPRINT_013/014, SPRINT_020/024, SPRINT_039–041 (the workflows being wrapped)
Sprint Branch: sprint/operator-cli
Task branch convention: feat/ | fix/ | docs/ | test/
PR base: sprint/operator-cli (never main until sprint integration)
Wave 0 decisions: docs/planning/sprints/S046_WAVE0_DECISIONS.md
Architecture Sources:
  - docs/product/PRD.md (confirmed)
  - docs/adr/ADR-0026 (CLI framework, placement, config contract) — ACCEPTED
  - docs/adr/ADR-0022 (apps/* consumer boundary; scripts/ stay thin)
  - docs/adr/ADR-0025 (the Binance import this CLI will wrap) — ACCEPTED
  - docs/planning/ROADMAP.md §13C (Phase 11, applied in PR #349)
```

---

## 0. Slice choice

45 scripts, 45 flag sets, one operator. Running the actual loop means chaining
`uv run python scripts/.../foo.py --flag value` invocations in the right order,
from memory, with the identifiers copy-pasted between steps.

This sprint gives that loop one front door and one input contract. It adds **no
capability** — every command calls a workflow that already exists and is already
tested. That is the point: it is an interface sprint, and its risk is entirely
in the seam, not in the logic.

The PRD's riskiest assumption ("45 heterogeneous scripts can be unified behind
4 command groups purely as thin wrappers") was audited before this sprint was
written. The result is in §4 and it changes the design: **the seam is the
application layer, not `main()`**.

**Out of scope by design:** the Binance importer itself. It is Sprint 045, with
its own ADR and branch. This sprint only wraps whatever Sprint 045 publishes.

---

## 1. Sprint Goal

```text
one YAML config
    ↓
trading-cli <group> <command> --config <path>
    ↓
validate + resolve the plan     (--dry-run stops here, no side effects)
    ↓
call an existing application-layer workflow
    ↓
typed result → human output or --json

data fetch     binance (S045) | databento
research run   predictive | strategy
dry-run start  the existing BTC futures dry-run runtime
report render  predictive | strategy
```

Success: `trading-cli research run --config configs/my_study.yaml` replaces
remembering the `build_predictive_dataset.py` → `run_predictive_research.py` →
`render_predictive_report.py` flag sequence, and no research, simulation or
execution logic moved into the CLI to make that happen.

---

## 2. In scope

- [ ] `apps/cli` package: `pyproject.toml`, workspace member, `trading-cli` console script.
- [ ] `argparse` subparser tree for the four command groups (no new dependency).
- [ ] YAML config loader with strict validation and unknown-key rejection.
- [ ] `--dry-run` resolved-plan renderer; `--json`; a documented exit-code taxonomy.
- [ ] `report render` for predictive and strategy runs.
- [ ] `research run` for predictive (composed build → run → render) and strategy.
- [ ] `dry-run start` wrapping the existing runtime, unmodified.
- [ ] `data fetch` for databento, and for binance once S045 has merged.
- [ ] Import-boundary test: `apps/cli` reaches only `trading_framework.application.*`.
- [ ] Example configs, operator guide, CI job for the new workspace member.
- [ ] `apps/cli/CLAUDE.md` recording the boundary that differs from `apps/dashboard`.

## 3. Out of scope

- Building the Binance importer (Sprint 045).
- Wrapping `ops`, `demo`, `robustness_research`, `signal_research` scripts.
- Removing, renaming, or changing the flags of any existing script.
- Any change to execution or order-routing logic — `dry-run start` only wires.
- Exposing configuration a script never exposed (see §4 finding 2) — that is an
  application-layer change and needs its own increment.
- Interactive/TUI mode, shell completion, global install packaging.
- A scheduler, queue, or run history. The CLI is stateless.

---

## 4. Thin-wrapper feasibility audit (the PRD's riskiest assumption)

Every script in the four target groups was read before this sprint was opened.

### What holds

```text
def main(argv: list[str] | None = None) -> int      43 / 45 scripts
body: _build_parser().parse_args(argv) → application workflow → print → return
sys.argv is never read outside parse_args(argv)
no import-time side effects; no global mutable state
(the 2 exceptions take no argv and are outside this sprint's scope)
```

So `main()` **is** cleanly callable as a function. The assumption survives.

### What does not hold

| # | Finding | Consequence |
|---|---------|-------------|
| 1 | `main()` returns an `int` exit code. `dataset_id` / `run_id` / `output_path` reach **stdout only**. | Composing build → run → render through `main()` would require parsing stdout. Rejected. |
| 2 | `run_strategy_research.py` hardcodes `build_canonical_strategy_model()`, `SimulationAssumptions()` and `CmeEsRthSessionResolver()`; `build_predictive_dataset.py` hardcodes the session resolver. | YAML cannot express what the script never exposed. The CLI inherits the limitation and documents it; it does not patch the script. |
| 3 | `parse_args` raises `SystemExit(2)` and prints a usage message on bad argv. | The fallback path must catch `SystemExit` and translate it, or an operator sees a usage error about flags they never typed. |
| 4 | `run_btc_futures_dry_run.py` calls `asyncio.run()` inside `main()`. | The CLI must not already be inside an event loop when it invokes that command. |

### Consequence for the design

Each of those scripts is a three-line adapter over an application workflow that
**does** return a typed result (`RunPredictiveResearchRequest`,
`BuildStrategyDashboardRequest`, `RenderPredictiveReportRequest`, …).

```text
Preferred   YAML → application Request dataclass → workflow → typed result
Fallback    construct argv → script main(argv) → int      (only where no
            application entry point exists; SystemExit translated)
Never       reimplement a workflow, or parse another command's stdout
```

**Verdict: the CLI sprint is small, not large** — but only because it wraps the
application layer. Wrapping `main()` uniformly, as the PRD's phrasing suggested,
would have forced stdout parsing and made it much larger.

---

## 5. CLI boundary

ADR-0026 §2 is binding, and it deliberately differs from `apps/dashboard`.

```text
Allowed      apps/cli imports trading_framework.application.*
Allowed      CLI-local config models, plan rendering, output formatting
Forbidden    importing trading_framework.research / .market_analysis /
             .strategy / .execution / infrastructure adapters directly
Forbidden    research, simulation or execution logic inside apps/cli
Forbidden    reimplementing anything that exists in application/
Forbidden    any credential in any config file
```

`apps/dashboard`'s total ban on importing `trading_framework` is **not**
inherited: the dashboard reads persisted artifacts, the CLI invokes workflows.
Both share the same underlying rule — no engine internals reimplemented in an
app. S046-T004 makes this a test rather than a convention.

---

## 6. Task breakdown

### Wave 0 — Planning

Binding locks: `S046_WAVE0_DECISIONS.md`. No numbered task. Wave 0 is DONE when
that file is on the sprint branch and the maintainer has checked off the Wave 0
Checklist.

### Wave 1 — Skeleton and contract

| Task | Description | Acceptance | Status |
|------|-------------|-----------|--------|
| S046-T001 | `apps/cli` package: `pyproject.toml`, `[project.scripts] trading-cli`, uv workspace member, `argparse` subparser tree for the four groups with no command bodies | `uv run trading-cli --help` lists four groups; every command errors with "not implemented" rather than crashing | DONE |
| S046-T002 | YAML config loader + strict validation: required `version` and `storage_root`, per-group blocks, unknown keys rejected, credential-shaped keys rejected | a typo in a key fails with the key name and the closest valid key; a config containing an API key is refused | DONE |
| S046-T003 | Error taxonomy + exit codes (`0` success, `1` workflow failure, `2` config/usage error), `--dry-run` resolved-plan renderer, `--json` output mode | `--dry-run` prints workflow, resolved arguments and output paths and touches nothing on disk | DONE |
| S046-T004 | Import-boundary test in the CLI's own test suite: only `trading_framework.application.*` is reachable | test fails if a research/execution/infrastructure import is added | DONE |

Depends on: nothing. T002–T004 depend on T001.

### Wave 2 — Command groups over existing workflows

| Task | Description | Acceptance | Status |
|------|-------------|-----------|--------|
| S046-T005 | `report render` for predictive and strategy runs (pure application calls, smallest slice first) | both render offline HTML at the documented path; missing run → exit code 1 with a clear message | DONE |
| S046-T006 | `research run` predictive: composed build → run → render, passing typed results between steps, referencing existing `PredictiveStudySpec` / `EstimatorSpec` files by path | one config produces a dataset, a run and a report; identifiers are never round-tripped through stdout | DONE |
| S046-T007 | `research run` strategy, with the §4 finding 2 limitation documented in `--help` and the operator guide | runs on a published `DatasetRef`; the canonical-strategy-model limitation is stated, not silently implied | DONE |
| S046-T008 | `dry-run start` wrapping the existing runtime; no execution logic changed; event-loop entry handled per §4 finding 4 | a bounded dry-run starts and stops with the same behaviour as the script | DONE |
| S046-T009 | `data fetch databento` over the existing archive import path | publishes a `DatasetRef` from a local archive; naming caveat (import, not network fetch) documented | DONE |

Depends on: Wave 1. T005–T009 are independent of each other and may be
implemented in parallel on separate branches.

### Wave 3 — Binance wiring, docs, closure

| Task | Description | Acceptance | Status |
|------|-------------|-----------|--------|
| S046-T010 | `data fetch binance` wired to the Sprint 045 workflow | works end to end once S045 is on `main`; until then the command exists and fails with an explicit "requires Sprint 045" message — never a stack trace | DONE |
| S046-T011 | Example configs, one per command group, under a documented location | each example runs as-is against fixture data or is marked as requiring real data | DONE |
| S046-T012 | `docs/reference/OPERATOR_CLI.md` (one schema, documented once) + CI job for the `trading-cli` workspace member | CI runs `ruff` and `pytest` for `apps/cli`; the guide has no second copy of the schema | DONE |
| S046-T013 | `apps/cli/CLAUDE.md` (boundary that differs from `apps/dashboard`), MODULE_MAP + ARCHITECTURE_OVERVIEW entries | a future agent editing `apps/cli` learns the boundary without reading ADR-0026 | DONE |
| S046-T014 | Apply the Phase 11 roadmap block, update `CURRENT_STATUS.md` §11/§12, write the sprint Review section | roadmap and status reflect the delivered scope | DONE |

**Progress:** 14 / 14 tasks

---

## 7. Recommended PR sequence

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 0 | `docs/operator-cli-planning` | Wave 0 locks + ADR-0026 |
| 1 | `feat/cli-skeleton-and-config` | T001–T004 package, config contract, boundary test |
| 2 | `feat/cli-report-render` | T005 the smallest end-to-end command |
| 3 | `feat/cli-research-run` | T006–T007 predictive composition + strategy |
| 4 | `feat/cli-dry-run-and-databento` | T008–T009 |
| 5 | `feat/cli-data-fetch-binance` | T010 (after S045 merges to `main`) |
| 6 | `docs/operator-cli-guide` | T011–T014 examples, guide, module context, closure |

PR 2 lands before 3/4 so the config contract is proven on the simplest command
first. PRs 3 and 4 are independent. PR 5 is the only one gated on Sprint 045.
Each PR targets `sprint/operator-cli`.

---

## 8. Acceptance criteria

1. `trading-cli data fetch binance --config <path>` publishes a queryable `DatasetRef` (once S045 is merged).
2. `trading-cli research run --config <path>` runs Predictive or Strategy Research, selected by config.
3. `trading-cli dry-run start --config <path>` starts the existing BTC futures dry-run runtime.
4. `trading-cli report render --config <path>` renders the corresponding offline HTML.
5. An invalid config fails **before** any side effect, naming the offending key.
6. `--dry-run` prints the resolved plan and writes nothing.
7. Exit codes follow the documented taxonomy (`0` / `1` / `2`); no raw argparse usage message ever reaches the operator from a wrapped script.
8. A config containing an API-key-shaped value is rejected.
9. An import-boundary test proves `apps/cli` reaches only the application layer.
10. No existing script, flag, or test was changed to make wrapping possible.
11. Predictive `research run` passes identifiers between steps as typed values, never via stdout.
12. The strategy-command limitation from §4 finding 2 is documented in the operator guide.
13. CI is green for all workspaces: `ruff check`, `ruff format --check`, `mypy`, `pytest`.
14. No new runtime dependency was added.

---

## 9. Dependencies

**Required:** existing application workflows for predictive research, strategy
research, reports, dry-run and Databento import; `pyyaml` (already a
dependency); the `apps/*` workspace pattern from Sprint 028/029.

**Required for one command only:** Sprint 045 / ADR-0025, for
`data fetch binance` (T010). Every other task can proceed without it. If Sprint
045 is deferred, this sprint still delivers 13 of 14 tasks and T010 ships as an
explicit unsupported-provider error.

**Not required:** any new dependency, any ML extra, any dashboard change, any
change to `scripts/`.

---

## 10. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| CLI drifts from script behaviour (two front doors) | Both call the same application workflow; the CLI adds no logic of its own |
| Wrapping via `main()` forces stdout parsing | Application-layer seam is the default; `main(argv)` is a documented fallback only |
| Scope creep toward wrapping all 45 scripts | Four groups locked in Wave 0; adding a group is a later increment |
| Config schema grows a fat shared section | Only `version` and `storage_root` are cross-group (ADR-0026 §4) |
| Existing spec schemas duplicated in the CLI | Spec files are referenced by path and parsed by their own loaders |
| Sprint 045 slips and blocks this sprint | Only T010 depends on it; the rest is independent by construction |
| `apps/cli` mistaken for `apps/dashboard`'s import rules | §5 states the difference; T004 tests it; T013 records it in `apps/cli/CLAUDE.md` |
| A credential lands in a committed example config | Credential-shaped keys are rejected by the loader (T002), not just discouraged |

---

## 11. Quality gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest

uv run --package trading-cli ruff check apps/cli
uv run --package trading-cli pytest apps/cli/tests -q
```

The CLI workspace runs its own checks, following the `apps/dashboard` pattern
from Sprints 028–034.

---

## 12. Post-sprint direction

Candidates, none scheduled by default:

- exposing the strategy model / session resolver through the application layer
  so YAML can select them (removes the §4 finding 2 limitation),
- additional command groups (`robustness`, `signal`) if the four prove out,
- shell completion and a packaged install,
- a `--resume` story, once any wrapped workflow actually supports resuming.
