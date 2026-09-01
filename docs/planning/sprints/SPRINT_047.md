# Sprint 047 — Custom Strategy Authoring (Phase 12)

## Metadata

```text
Sprint: 047
Phase: Phase 12 — Custom Strategy Authoring (opening and, in scope terms, closing increment)
Status: COMPLETE — 10/10 tasks. ADR-0028 declined; Wave 2 dropped.
Planned Start: 2026-09-01
Planned End: 2026-09-01
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_046 (the CLI being extended; merged to main via #361),
            SPRINT_013 (Strategy Model, Exit/Risk contracts, BarSequentialSimulator),
            SPRINT_037/038 (model_authoring DSL, component reference pattern, session metadata)
Sprint Branch: sprint/strategy-authoring
Task branch convention: feat/ | fix/ | docs/ | test/
PR base: sprint/strategy-authoring (never main until sprint integration)
Wave 0 decisions: docs/planning/sprints/S047_WAVE0_DECISIONS.md
Architecture Sources:
  - docs/product/PRD-strategy-authoring.md (confirmed)
  - docs/adr/ADR-0027 (operator-authored strategy loading) — ACCEPTED
  - docs/adr/ADR-0028 (bracket exit / equity-relative sizing) — PROPOSED, declined for this sprint (Wave 2 dropped)
  - docs/adr/ADR-0026 + Amendment 1 (the CLI boundary this must not break)
  - docs/adr/ADR-0016 (the Strategy Research MVP; its MVP gates are unchanged this sprint)
  - docs/planning/ROADMAP.md §13D (Phase 12, applied directly in this sprint's planning PR)
```

---

## 0. Slice choice

Sprint 046 gave the operator one front door. Behind it,
`research run strategy` still always evaluates the Sprint 013 canonical
example — confirmed directly: a `research.strategy` block with no
strategy-selecting field still produces a manifest with
`strategy_model_id: "high_vol_higher_low_fixed_exit"`. That was documented as
a v1 limitation (SPRINT_046.md §4 Finding 2, D-S046-03, ADR-0026 "Follow-up"),
not hidden. This sprint closes it.

But "add a config key" is not the whole problem. The PRD names two structural
causes that make the CLI gap a symptom rather than the disease:

```text
1  the component catalog is thin — volatility.{atr,true_range,state},
   structure.{swing,session_range}, trend.{ema,slope}. There is barely
   anything to compose a Market/Signal Model from.
2  exit_model.py and risk_model.py have one implementation each, both the
   simplest possible placeholder — no stop-loss, no equity-relative sizing.
```

The sprint ships **one loader, two components, and the examples that prove
they compose**. The PRD's third piece — new Exit/Risk models — turned out to
require narrowing a PRD non-goal on `BarSequentialSimulator` (§4 Finding 1);
the maintainer declined that narrowing on 2026-09-01, so it is **dropped from
this sprint**, per the pre-agreed fallback, and deferred to a possible future
sprint with its own engine-focused ADR (ADR-0028 stays `PROPOSED`, its design
kept for that future conversation). Unlike Phase 2F/11 (two genuinely
independent tracks), the loader and the catalog remain gated on each other
for a working demonstration: the loader with nothing new to load proves
little. **One sprint, sequential waves.**

**Out of scope by design:** a declarative YAML strategy format. The framework
has no serialization for `StrategyModelDefinition` and building one is a phase,
not a task (ADR-0027 alternative 2).

---

## 1. Sprint Goal

```text
user_data/.../my_strategy.py
    def build_strategy() -> StrategyModelDefinition        (fixed convention)
        ↓
research.strategy.strategy_file: <that path>               (one config key)
        ↓
trading-cli research run strategy --config <path>
        ↓
resolve_plan: import file → call build_strategy() → validate
              (--dry-run stops here, printing the resolved strategy_model_id)
        ↓
run_strategy_research(strategy_model=<the loaded definition>)
        ↓
run manifest strategy_model_id == the operator's strategy, not the canonical one

new to compose with:
  candle.wick                 upper/lower wick + body ratios
  structure.level_distance    ATR-normalized distance to the session high/low
  (BracketExitModel / EquityPercentRiskModel — DEFERRED, ADR-0028 declined)
```

Success: an operator writes a strategy file, points a config at it, and gets a
run and a dashboard for **their** strategy — and the three hand-authored files
already sitting in `user_data/components/strategies/` run through the CLI with
no edits at all.

---

## 2. In scope

- [ ] `research.strategy.strategy_file` config key, optional, strictly validated.
- [ ] `trading_cli/strategy_loader.py`: file-path import, fixed `build_strategy()` entry point, full error taxonomy, no `sys.path` mutation.
- [ ] Loading during plan resolution so every failure is pre-flight; `--dry-run` prints the resolved `strategy_model_id`.
- [ ] `candle.wick` component + NumPy implementation + `model_authoring` DSL namespace.
- [ ] `structure.level_distance` component (session_range x atr) + DSL functions.
- [ ] Two new example strategies + committed example configs (composed from the two new components; not from new Exit/Risk models — see Out of scope).
- [ ] `docs/reference/STRATEGY_AUTHORING.md`; `OPERATOR_CLI.md` and `apps/cli/CLAUDE.md` updates; TD-025.

## 3. Out of scope

- A declarative (YAML/JSON) strategy specification format.
- Sandboxing, import restriction, or static analysis of a loaded strategy file (ADR-0027 §6).
- A strategy registry, catalog UI, or discovery mechanism — exactly one path from config, nothing more.
- Exposing `SimulationAssumptions` or the session resolver through config (the other two thirds of SPRINT_046.md §4 Finding 2).
- **`BracketExitModel`, `EquityPercentRiskModel`, and any change to `BarSequentialSimulator` or its kernels.** ADR-0028's requested non-goal narrowing was declined by the maintainer on 2026-09-01 — see §4 Finding 1. Deferred to a possible future sprint with its own engine-focused ADR; not built here.
- Dynamic, equity-curve-following position sizing (TD-026, deferred with the above).
- Robustness Research stress dimensions over `stop_loss_bps` / `take_profit_bps`.
- Any change to live trading, order routing, or the dry-run runtime.
- Deleting, editing or replacing `user_data/run_example_strategies.py` or the three existing example files (gitignored, not in the framework's test suite).
- Any third catalog component. Exactly two.

---

## 4. Findings — read before Wave 0 is signed off

Three things were found by reading the code before this sprint was written.
Two change the design; one is unexpectedly good news.

### Finding 1 — "new Exit/Risk models on the unchanged protocols" is impossible as written

The PRD asks for stop-loss/take-profit and equity-percentage sizing
"implementing the existing `ExitModel`/`RiskModel` protocols unchanged", and
separately declares any change to `BarSequentialSimulator` a non-goal. Those two
sentences cannot both hold:

| # | Blocker | Where |
|---|---------|-------|
| 1 | `ExitModel`'s entire contract is `exit_bar_index(*, entry_fill_bar_index: int) -> int` — a pure function of one integer. It sees no price, no bar, no direction. **No implementation of it can be a stop-loss.** | `strategy/exit_model.py` |
| 2 | `BarSequentialSimulator` gates on the concrete classes (`isinstance(..., FixedBarsExitModel)`, `isinstance(..., FixedQuantityRiskModel)`), so even a protocol-conformant new model is refused before reaching the kernel. | `research/simulation/engine.py` |
| 3 | `validate_strategy_model_definition` repeats the same two guards one layer earlier ("MVP supports FixedBarsExitModel only"). | `strategy/strategy_model.py` |
| 4 | `simulate_fixed_bars_exit_kernel` is an `@njit` loop over `open_prices` only. It never reads `high`/`low` — exactly what a stop or a target needs. | `kernels/fixed_bars.py` |

A new Exit/Risk model added without touching the engine would be **dead code**:
constructible, never runnable, and unable to satisfy the PRD's own success
metric 2 or goal 4.

**Consequence for the design.** ADR-0028 asked the maintainer to narrow the
non-goal from "no change to `BarSequentialSimulator`" to "**no change to the
fixed-bars path's fill or accounting semantics; dispatch to an additional
kernel is allowed**", bounded by a golden-run regression. Four bounded changes,
one new kernel file, `fixed_bars.py` untouched.

**Decided: declined**, 2026-09-01 — a legitimate call, it was the maintainer's
non-goal to narrow or not. Wave 2 is dropped entirely; this sprint ships
Waves 1/3/4 with catalog-only examples. Exit/Risk expansion is deferred to a
possible future sprint with its own engine-focused ADR (ADR-0028's domain
design is kept as a starting point, not discarded). This was a decision, not
a mid-sprint discovery — see D-S047-14 checklist.

### Finding 2 — the loader needs zero import-boundary widening

`tests/unit/test_apps_boundaries.py` matches its allow-list by prefix, and
`trading_framework.strategy` is already on it (Amendment 1, for
`build_canonical_strategy_model`). That package exports
`StrategyModelDefinition`, `StrategyModelDefinitionError` and
`validate_strategy_model_definition` — everything the loader needs to
type-check and validate what `build_strategy()` returned.

```text
No new module on the allow-list. No new ADR-0026 amendment. Nothing to re-approve.
```

Wave 1 **asserts** this (the boundary test must stay green with no edit to its
allow-list) rather than assuming it. If an implementation detail turns out to
need a wider import, that is a STOP-and-ask, not a test edit — the same lesson
Amendment 1 was written to record.

The separate question — whether the *loaded* module gets a boundary — is
answered in ADR-0027 §6: **no, and the reason is that the rule would be
unenforceable and would protect nothing.** An advisory convention is documented;
TD-025 records that the static boundary test is structurally blind to
dynamically loaded imports, so a green test is never read as more than it is.

### Finding 3 — "distance to a level" needs a component, because the DSL has no arithmetic

`model_authoring.references.operand.Operand` implements `__eq__`, `__ne__`,
`__gt__`, `__ge__`, `__lt__`, `__le__` — **comparisons only**. There is no
`__sub__` or `__truediv__`. So `price.close > structure.session_high()` is
expressible (and `session_high_breakout.py` already does it), but
`(price.close - structure.session_high()) / volatility.atr() < 0.25` is not.

Two options: extend the expression IR with arithmetic (a large, separate
change touching `model_expression`, validation, evaluation and fingerprinting),
or put the normalization inside a component. **This sprint chooses the
component** (`structure.level_distance`, depending on `session_range` and
`atr`) and explicitly does **not** open the arithmetic-IR question.

---

## 5. Boundaries this sprint must not cross

```text
Unchanged     ADR-0026 §2 + Amendment 1: apps/cli's 17-module allow-list
Unchanged     apps/dashboard's total ban on importing trading_framework
Unchanged     ExitModel and RiskModel Protocol definitions
Unchanged     kernels/fixed_bars.py, and the numeric output of the fixed-bars path
Unchanged     every existing script, its flags and its tests
Unchanged     the three files in user_data/components/strategies/ and run_example_strategies.py
Not enforced  any import rule on a loaded strategy module (ADR-0027 §6, TD-025)
```

---

## 6. Task breakdown

### Wave 0 — Planning

Binding locks: `S047_WAVE0_DECISIONS.md`. No numbered task. Wave 0 is DONE when
that file is on the sprint branch, ADR-0027 and ADR-0028 are ACCEPTED, and the
maintainer has checked off the Wave 0 Checklist (D-S047-14).

### Wave 1 — The loader (the vertical slice; demonstrable on day one)

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S047-T001 | `research.strategy.strategy_file` key in `trading_cli/config.py` + `research.py::resolve_plan`: optional, must be a string path, unknown-key strictness preserved, absent key keeps the canonical example (D-S047-05) | a config with `strategy_file` resolves a plan carrying the resolved absolute path; a config without one resolves exactly as it does on `main` today; a mistyped key (`strategy_path`) is still rejected by name | Wave 0 | DONE |
| S047-T002 | `trading_cli/strategy_loader.py`: `spec_from_file_location` with a hash-derived synthetic module name, registered in `sys.modules` before `exec_module`, no `sys.path` mutation; resolve `build_strategy`, check zero required args, call it, type-check and validate the result | each of the nine rows in ADR-0027 §5 raises the specified class with the specified exit code and names the specified thing; `__cause__` is preserved on every chained error; two files with the same stem load independently | T001 | DONE |
| S047-T003 | Wire the loader into `_run_strategy`; `--dry-run` prints the resolved `strategy_model_id` and the absolute file path; `--help` and the plan renderer state the no-sandbox trust model | `--dry-run` on a valid strategy file prints the loaded id and writes nothing itself; `research run strategy` on the same config produces a manifest whose `strategy_model_id` is the loaded one | T002 | DONE |
| S047-T004 | Loader test matrix in `apps/cli/tests/` (fixture strategy files under `apps/cli/tests/fixtures/strategies/`), plus an assertion that `tests/unit/test_apps_boundaries.py`'s allow-list is unmodified (Finding 2) | all nine error rows covered; a valid fixture loads end to end; the boundary test passes with a byte-identical allow-list | T002 | DONE |

Depends on: Wave 0 only. **After Wave 1, the three existing
`user_data/components/strategies/*.py` files are runnable through the CLI with
no edits — that is the wave's demo.**

### Wave 2 — Exit and Risk models — DROPPED (ADR-0028 declined, 2026-09-01)

Not part of this sprint. S047-T005–T008 (`BracketExitModel`,
`EquityPercentRiskModel`, the MVP-gate widening, `kernels/bracket.py`, the
golden-run regression) are deferred in full to a possible future sprint with
its own engine-focused ADR, per the decision recorded in
`S047_WAVE0_DECISIONS.md` D-S047-11/12 and `ADR-0028`. The task numbers are
retired, not renumbered into Wave 3/4, so this sprint's history stays legible
against the original plan.

### Wave 3 — Component catalog (the two items past sprints named as next)

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S047-T009 | `candle.wick` FEATURE component + NumPy implementation + registry entry; outputs `upper_wick_ratio`, `lower_wick_ratio`, `body_ratio`; bar-local, causal, `bars_before=0`; DSL `model_authoring/references/candle.py` exported from `model_authoring.__init__` | zero-range bar produces a defined value (documented, not a NaN surprise); component follows the `AtrComponent` shape exactly (ComponentId, versions, parameter/output schema); DSL returns an `Operand` usable in a `Condition` | Wave 0 | DONE |
| S047-T010 | `structure.level_distance` FEATURE component depending on `structure.session_range` and `volatility.atr`; outputs `distance_to_session_high_atr`, `distance_to_session_low_atr`; DSL `structure.distance_to_session_high(...)` / `..._low(...)` | causal (running session extremes only, no look-ahead); warmup respects the ATR period; a session-boundary regression test; MTF behaviour matches `session_range`'s existing alignment | T009 | DONE |

Depends on: Wave 0. **This is the descope wave** — if the sprint overruns, drop
T010 first, then T009. Never Wave 1.

### Wave 4 — Composition, docs, closure

| Task | Description | Acceptance | Deps | Status |
|------|-------------|-----------|------|--------|
| S047-T011 | Two new example strategies under `user_data/components/strategies/` — one exercising `candle.wick`, one exercising `structure.level_distance` (both still with the existing `FixedBarsExitModel`/`FixedQuantityRiskModel`, since Wave 2 is dropped) — each with a committed example config under the Sprint 046 examples location | both run through `trading-cli research run strategy`; each file is copy-pasteable and commented in the style of the existing three | W1, W3 | DONE |
| S047-T012 | Framework-side fixture strategy + an end-to-end test in `apps/cli/tests` asserting the run manifest's `strategy_model_id` is the loaded strategy's, not the canonical one (PRD success metric 1), and that at least one new component is exercised (metric 2, component half only — Wave 2's Exit/Risk half is deferred) | the test fails if the loader silently falls back to the canonical example; committed fixture data only, no network, no ML extra | T011 | DONE |
| S047-T013 | Docs: new `docs/reference/STRATEGY_AUTHORING.md` (the convention, the trust model, the error table, the advisory import convention); `OPERATOR_CLI.md` gains `strategy_file` and the narrowed `--dry-run` wording; `apps/cli/CLAUDE.md` gains the loader gotchas; MODULE_MAP + ARCHITECTURE_OVERVIEW entries; TD-025 in `TECHNICAL_DEBT.md` (TD-026 deferred with Wave 2) | the config schema still appears exactly once; a future agent editing `apps/cli` learns the trust model without opening ADR-0027 | T012 | DONE |
| S047-T014 | ROADMAP.md §13D already applied (this sprint's planning PR, matching the #349 precedent — no separate proposal file to splice); update `CURRENT_STATUS.md` §2/§6/§11/§12, write the sprint Review section | status reflects delivered scope; `SPRINT_046.md` §4 Finding 2 is annotated as partially closed (strategy model only); §13D's Status line flips PLANNED -> COMPLETE | T013 | DONE |

**Progress:** 10 / 10 (S047-T005–T008 retired with Wave 2 — see §6 Wave 2 note)

---

## 7. Recommended PR sequence

| PR | Branch (example) | Outcome |
|----|------------------|---------|
| 0 | `docs/strategy-authoring-planning` | Wave 0 locks + ADR-0027 + ADR-0028 (declined) + roadmap proposal |
| 1 | `feat/cli-strategy-file-loader` | T001–T004: the loader, end to end, with its test matrix |
| 2 | `feat/candle-wick-component` | T009 |
| 3 | `feat/level-distance-component` | T010 |
| 4 | `feat/authored-example-strategies` | T011–T012: examples + the end-to-end metric test |
| 5 | `docs/strategy-authoring-guide` | T013–T014: guide, module context, TD entries, closure |

PR 1 lands first and alone: it delivers the PRD's headline metric against the
strategies that already exist, so the sprint has value even if everything after
it slips. PRs 2 and 3 are independent of each other. Each PR targets
`sprint/strategy-authoring`. (Wave 2's PRs from the original plan — domain
models and simulator dispatch — are dropped along with the wave.)

---

## 8. Acceptance criteria

1. `trading-cli research run strategy --config <path>` with `strategy_file` set runs the loaded strategy, and the run manifest's `strategy_model_id` is that strategy's.
2. The three existing `user_data/components/strategies/*.py` files run through the CLI **unmodified**.
3. A `research.strategy` block with no `strategy_file` still produces the canonical example, and every Sprint 046 example config still works.
4. Each of ADR-0027 §5's nine failure modes produces the specified error class and exit code, naming `research.strategy.strategy_file` and the resolved absolute path where applicable — always before any framework side effect.
5. `--dry-run` prints the resolved `strategy_model_id` and the CLI itself writes nothing; the narrowed guarantee (a loaded module executes at import) is documented.
6. `tests/unit/test_apps_boundaries.py` passes with its allow-list **byte-identical** to `main` (Finding 2).
7. The no-sandbox trust model appears in `--help`, `OPERATOR_CLI.md` and `STRATEGY_AUTHORING.md`.
8. `candle.wick` and `structure.level_distance` are registered, causal, warmup-correct, and reachable from the `model_authoring` DSL.
9. *(retired — `BracketExitModel`/`EquityPercentRiskModel` are Wave 2, dropped per ADR-0028 being declined.)*
10. *(retired — bracket semantics were Wave 2's scope.)*
11. *(retired — the golden-run regression guarded Wave 2's engine changes, which did not happen; `kernels/fixed_bars.py` is simply untouched, see #13.)*
12. At least one new component is exercised by a passing example composed through the loader (PRD success metric 2, component half — the Exit/Risk half is deferred with Wave 2), proven by a test that fails on silent canonical fallback.
13. `kernels/fixed_bars.py`, both `ExitModel`/`RiskModel` Protocol definitions, `research/simulation/engine.py`, `strategy/strategy_model.py`'s validation gates, and every existing script and its flags are unchanged — Wave 2 touched none of them because it did not happen.
14. TD-025 (boundary test blind to dynamic imports) is logged with its repayment trigger. TD-026 (static equity-percent sizing) does not apply — deferred with Wave 2, not built.
15. CI is green for all workspaces: `ruff check`, `ruff format --check`, `mypy`, `pytest`.
16. No new runtime dependency was added.

---

## 9. Dependencies

**Required:** Sprint 046 merged to `main` — this sprint edits
`apps/cli/src/trading_cli/commands/research.py` and `config.py`. **Satisfied:**
Sprint 046 merged via #361 on 2026-08-31, before this sprint's Wave 0 was
approved.

**Required:** ADR-0027 ACCEPTED. **Satisfied**, 2026-09-01. ADR-0028 was
**declined** the same day — Wave 2 is not part of this sprint's dependency
graph; Waves 1, 3 and 4 proceed on ADR-0027 alone, exactly as §4 Finding 1
anticipated.

**Required:** Sprint 038's session metadata on the component compute view, for
`structure.level_distance` (T010) only.

**Not required:** any new dependency, any ML/DL extra, any dashboard change,
any network access, any change to `scripts/`.

---

## 10. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Arbitrary code execution from a config-named path | Accepted deliberately (ADR-0027 §2); stated in `--help` and two guides, never implied. Sandboxing is a PRD non-goal. |
| `--dry-run` no longer means "nothing ran" | The guarantee is explicitly narrowed and documented (ADR-0027 §4), not quietly weakened. |
| An engineer widens the ADR-0026 allow-list to make the loader work | Finding 2 shows no widening is needed; T004 asserts the allow-list is unmodified; Amendment 1's history says widening is a maintainer decision, not an implementation detail. |
| A green boundary test read as proof nothing unexpected was imported | TD-025 records the structural blindness explicitly. |
| Catalog scope creep (a third, fourth component) | Exactly two, locked in D-S047-06; T010 is the named first descope. |
| Sprint overruns | Descope order is pre-agreed: T010, then T009. Wave 1 is never dropped. Wave 2 is already out of scope, not a descope target. |
| The loaded module shadows a real package in `sys.modules` | Hash-derived synthetic module name under a reserved private prefix (ADR-0027 §3), asserted by a same-stem collision test. |
| A future reader assumes Wave 2 was simply forgotten | ADR-0028, `S047_WAVE0_DECISIONS.md` D-S047-11/12, and this file's §0/§3/§4 all record the decline explicitly, with the domain design kept for a future sprint. |

---

## 11. Quality gates

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest

uv run --package trading-cli ruff check apps/cli
uv run --package trading-cli pytest apps/cli/tests -q

uv run pytest tests/unit/test_apps_boundaries.py -q
```

The last line is called out separately because Finding 2's claim — no
allow-list widening — is an acceptance criterion, not an incidental pass.

---

## 12. Post-sprint direction

Candidates, none scheduled by default:

- **Exit/Risk model expansion (ADR-0028, declined for this sprint).** The
  most direct candidate: `BracketExitModel`, `EquityPercentRiskModel`, and
  the four bounded engine changes ADR-0028 §2 scoped, gated behind its own
  golden-run regression. Would need a future sprint's own Wave 0 to
  re-confirm the design still holds against whatever else has changed by
  then, not a blind resurrection of this sprint's plan.
- exposing `SimulationAssumptions` and the session resolver through config,
  closing the remaining two thirds of SPRINT_046.md §4 Finding 2,
- dynamic, equity-curve-following position sizing (TD-026, only relevant once
  Exit/Risk expansion above is picked up) — needs a `RiskModel`
  protocol change with paper-broker and live-execution impact,
- Robustness Research stress dimensions over bracket parameters,
- arithmetic in the model-expression IR (Finding 3), which would make
  `structure.level_distance` expressible as DSL composition instead of a
  component,
- retiring `user_data/run_example_strategies.py`'s direct imports in favour of
  the CLI,
- symbol-granularity import-boundary enforcement (TD-024),
- revisiting a declarative strategy format, only if the Python loader proves
  limiting in practice.
</content>
