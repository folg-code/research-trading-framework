# Sprint 047 — Wave 0 Decisions

Binding decisions for Custom Strategy Authoring (Phase 12).
Date: 2026-09-01.

```text
Status: Accepted — Wave 0 Checklist (D-S047-14) approved 2026-09-01. Wave 2
        (Exit/Risk models, ADR-0028) is DECLINED and dropped from this
        sprint's scope; Waves 1/3/4 are approved to start.
Basis:  docs/product/PRD-strategy-authoring.md (confirmed)
        docs/adr/ADR-0027 (ACCEPTED) — strategy loading
        docs/adr/ADR-0028 (PROPOSED, declined for Sprint 047) — bracket exit / equity sizing
        docs/adr/ADR-0026 + Amendment 1 (ACCEPTED) — the CLI boundary
        docs/adr/ADR-0016 (ACCEPTED) — the MVP gates (unchanged this sprint)
        docs/planning/sprints/SPRINT_047.md
        apps/cli/ and src/trading_framework/ as on main (Sprint 046 merged via #361)
```

Unlike Sprints 045/046, this is **one sprint with dependent waves**, not two
tracks. The PRD's three pieces (loader, catalog, Exit/Risk) are gated on each
other for a working demonstration; the open question "one sprint or two?" is
answered here as **one**, with the descope order pre-agreed in D-S047-13.

---

## Inherited locks (do not reopen)

```text
ADR-0022: apps/* are deployable consumers; scripts/ stay thin
ADR-0026 §2 + Amendment 1: apps/cli's 17-module import allow-list
ADR-0026 §4: one config schema, unknown keys are an error, spec files by path
ADR-0026 §9 / D-S046-09: exit codes 0 / 1 / 2
ADR-0016: Strategy Model = Market x Signal x Exit x Risk
ML/DL extras stay out of default installs and default CI
Standard CI stays network-free
```

---

## D-S047-01 — Problem statement

`trading-cli research run strategy` always evaluates the Sprint 013 canonical
example. `research.py::_run_strategy` passes
`strategy_model=build_canonical_strategy_model()` unconditionally. No config
field selects anything else. Behind that, the component catalog has ~7 entries
and the Exit/Risk shelves have one placeholder each.

**This sprint ships exactly:** one config key that loads an operator-authored
Python strategy file; two Market Analysis components; one Exit model and one
Risk model plus the engine dispatch that makes them runnable; and example
strategies proving the three compose end to end.

**Not this sprint:** a declarative strategy format; sandboxing; a strategy
registry; exposing the session resolver or simulation assumptions; dynamic
position sizing; any third component.

---

## D-S047-02 — Sprint branch and PR base

```text
Integration branch: sprint/strategy-authoring    (cut from main, AFTER S046 merges)
Working branches:   feat/ | fix/ | docs/ | test/ + descriptive slug
PR base:            sprint/strategy-authoring    (never main until integration)
```

Working-branch PRs squash-merge into the sprint branch; one integration PR
`sprint/strategy-authoring` -> `main` at the end. Branch names describe the
change, never the task ID.

**Blocking precondition:** Sprint 046's integration PR to `main` is still
pending (`CURRENT_STATUS.md` §6). This sprint edits `apps/cli` files that only
exist on `sprint/operator-cli`. Do not cut this branch before that merge.

---

## D-S047-03 — Config key format (CONFIRMED by the maintainer)

```yaml
research:
  kind: strategy
  strategy:
    dataset_ref: "..."
    timeframe: 1m
    strategy_file: user_data/components/strategies/my_strategy.py   # NEW
```

```text
Key name      strategy_file          exactly one key, a filesystem path
Type          string                 non-string -> ConfigError
Required      NO                     absent -> canonical example (D-S047-05)
Extension     .py                    anything else -> ConfigError naming the extension
Resolution    relative to the process CWD, then made absolute; the ABSOLUTE
              path appears in the resolved plan and in every error message
Rejected      module + function pair (two keys, two failure modes)
Rejected      a dotted import path (couples to sys.path, which we do not touch)
```

No new cross-group key. ADR-0026 §4's rule that `version` and `storage_root`
are the only cross-group keys is untouched.

---

## D-S047-04 — Entry-point convention (CONFIRMED by the maintainer)

```text
Name          build_strategy          fixed, conventional, NOT configurable
Signature     zero required arguments
Returns       StrategyModelDefinition
```

No function-name field in config. This is the exact shape already hand-written
in all three `user_data/components/strategies/*.py` files, so those files
become CLI-runnable with zero edits — which is Wave 1's acceptance demo.

A `build_strategy` with only optional/defaulted parameters is accepted (it is
callable with zero arguments). One with any *required* parameter is a
ConfigError naming those parameters.

---

## D-S047-05 — Fallback when `strategy_file` is absent (answers a PRD open question)

```text
LOCKED: strategy_file is OPTIONAL. Absent -> build_canonical_strategy_model(),
        exactly as on main today. This increment is purely additive.
LOCKED: the output (human and --json) states which path was taken, so a
        canonical strategy_model_id is never a silent surprise again.
```

Making it required was rejected: it would break committed Sprint 046 example
configs to enforce an explicitness the output line already provides.

---

## D-S047-06 — Loading mechanism and where it happens

```text
importlib.util.spec_from_file_location(synthetic_name, absolute_path)
synthetic_name = "trading_cli._loaded_strategy." + sha256(absolute_path)[:12]
sys.modules[synthetic_name] = module        BEFORE exec_module
exec_module(module); entry = getattr(module, "build_strategy"); definition = entry()
```

```text
LOCKED  sys.path is NEVER mutated. A strategy needing sibling imports is the
        operator's packaging problem; the guide documents PYTHONPATH.
LOCKED  the module stays in sys.modules under its synthetic name (removing it
        breaks dataclasses, pickling, and classes defined in the file)
LOCKED  the synthetic name is an implementation detail; nothing may depend on it
LOCKED  loading happens in resolve_plan(), NOT in run() -- so every failure is
        pre-flight (ADR-0026 §4: validate before any side effect) and --dry-run
        proves the file loads by printing the resolved strategy_model_id
ACCEPTED COST  --dry-run's guarantee narrows to "the CLI performs no side
        effect; the loaded module is operator code and executes at import".
        This wording goes in OPERATOR_CLI.md; it is not glossed over.
```

Two files with the same stem must load independently — asserted by a test, not
assumed.

---

## D-S047-07 — Error handling (binding table)

Dividing line: **anything wrong with the file, the convention, or the returned
object is a configuration error (exit 2). Only an exception raised inside the
operator's own `build_strategy()` body is a workflow failure (exit 1).**

| Condition | Class | Exit | The message must name |
|---|---|---|---|
| path missing / not a file / a directory | `ConfigError` | 2 | `research.strategy.strategy_file` + the resolved absolute path |
| extension is not `.py` | `ConfigError` | 2 | the actual extension |
| the module raises during import | `ConfigError` | 2 | the file; chained from the original exception |
| no `build_strategy` attribute | `ConfigError` | 2 | the convention verbatim: a zero-argument `build_strategy()` |
| `build_strategy` is not callable | `ConfigError` | 2 | the attribute's actual type |
| `build_strategy` has required parameters | `ConfigError` | 2 | those parameter names |
| `build_strategy()` raises | `WorkflowError` | 1 | the file; chained from the original exception |
| return value is not a `StrategyModelDefinition` | `ConfigError` | 2 | the actual returned type |
| the definition fails `validate_strategy_model_definition` | `ConfigError` | 2 | the framework's own validation message |

```text
LOCKED  __cause__ is preserved on every chained error, so --verbose shows the
        operator their own traceback. No exception is swallowed.
LOCKED  no message invents advice the CLI cannot verify ("did you mean...?" is
        only allowed against the actual module's dir(), not guessed).
```

---

## D-S047-08 — Import-boundary treatment (the PRD's riskiest assumption)

Two boundaries, deliberately different. Full reasoning in ADR-0027 §6.

**Boundary A — `apps/cli`'s own source: UNCHANGED, and not widened.**

```text
LOCKED  ADR-0026 Amendment 1's 17-module allow-list is not widened by this sprint.
        trading_framework.strategy is already on it and matched by prefix, and it
        exports StrategyModelDefinition, StrategyModelDefinitionError and
        validate_strategy_model_definition -- everything the loader needs.
LOCKED  S047-T004 ASSERTS the allow-list is byte-identical to main.
LOCKED  if an implementation detail turns out to need a wider import, that is a
        STOP-and-ask (a new ADR amendment with fresh maintainer approval), never
        a test-file edit. This is the exact lesson Amendment 1 exists to record.
```

**Boundary B — the loaded strategy module: UNCONSTRAINED, and not enforced.**

```text
LOCKED  a file named by strategy_file is NOT part of apps/cli's source tree, is
        NOT scanned by the boundary test, and is subject to NO import restriction.
```

Because: the boundary governs what this repository ships and CI can enforce (a
typical strategy file is gitignored and CI never sees it); the file is the
operator's own trusted code running with their own privileges, so a restriction
buys no security while an unrestricted interpreter is one line away; and
enforcing it would need import hooks or AST rewriting — real machinery
protecting nothing.

**Advisory convention (documented, NOT enforced, NO runtime check):** an
authored strategy should need only `trading_framework.model_authoring`,
`trading_framework.strategy.*`, and `trading_framework.time.models.timeframe`.
Reaching deeper is legal, works, and is a smell.

**TD-025 (log in `TECHNICAL_DEBT.md`):** the boundary test is a static AST scan
and is therefore structurally blind to dynamically loaded code. Recorded so a
green test is never read as proof that nothing outside the allow-list was
imported at runtime. Repayment trigger: if the loader is ever extended to run
untrusted or third-party strategies, this becomes a real gap requiring a real
mechanism.

---

## D-S047-09 — Security and trust model

```text
No sandbox. No import restriction. No AST inspection. No subprocess isolation.
Blast radius == `uv run python <that file>`.
```

A PRD non-goal, and coherent with a design premised on "this is the operator's
own code". What is **not** acceptable is leaving it implicit:

```text
LOCKED  one plain sentence in each of:
          trading-cli research run strategy --help
          docs/reference/OPERATOR_CLI.md
          docs/reference/STRATEGY_AUTHORING.md
LOCKED  no credential handling changes; D-S046-08 stands unmodified. A strategy
        file reading an environment variable is the operator's business, and the
        CLI neither helps nor blocks it.
```

---

## D-S047-10 — Component catalog additions (exactly two)

Both are the items previously named as next and deferred (D-S037-08:
"Session Range, then wick / distance"; D-S038-03: "**Not this sprint:** wick
ratio, distance-to-level"). Nothing else is added.

**C1 — `candle.wick`** (new `candle` namespace; `ComponentKind.FEATURE`)

```text
Component id   candle.wick                  version 1.0.0
Implementation numpy.candle_wick            version 1.0.0
Outputs        upper_wick_ratio, lower_wick_ratio, body_ratio   (all float64)
Parameters     none
Dependencies   OHLC data fields only; no component dependency
History        bars_before = 0    bar-local, causal, no warmup
Zero-range bar behaviour is DEFINED and documented, not left to produce a
    surprise NaN -- the exact convention is the implementer's call, stated in
    the docstring and asserted by a test.
DSL            model_authoring/references/candle.py, exported from
               model_authoring.__init__ alongside structure/trend/volatility
```

Chosen because it is the cheapest possible correct component (no dependencies,
no warmup, no MTF subtlety), and because a rejection wick at a level is exactly
what pairs with the existing swing/session structures into a real strategy.

**C2 — `structure.level_distance`** (existing `structure` namespace; FEATURE)

```text
Component id   structure.level_distance     version 1.0.0
Outputs        distance_to_session_high_atr, distance_to_session_low_atr
Parameters     period (int, default 14, min 1)  -- the ATR period
Dependencies   structure.session_range (session_high / session_low)
               volatility.atr(period)
History        inherits the ATR warmup; valid_from_index respects it
Causality      running session extremes only -- no look-ahead, asserted by a
               session-boundary regression test
DSL            structure.distance_to_session_high(period=14, timeframe=None)
               structure.distance_to_session_low(...)
```

Chosen because **the DSL has no arithmetic** (SPRINT_047.md §4 Finding 3):
`Operand` implements comparisons only, so an ATR-normalized distance cannot be
composed in the DSL and must live in a component. Extending the expression IR
with arithmetic is explicitly **not** opened by this sprint.

```text
LOCKED  exactly two components. A third is a separate increment, however cheap
        it looks mid-sprint.
LOCKED  the namespace question (candle.* as a new family) is settled: ADR-0005's
        taxonomy is Feature/Structure/State (a KIND), while volatility./structure./
        trend. are domain FAMILIES. Adding a family is not a taxonomy change.
```

---

## D-S047-11 — Exit and Risk model additions — DEFERRED, not part of Sprint 047

**ADR-0028 was declined by the maintainer for this sprint** (2026-09-01).
Wave 2 (this decision, D-S047-12, and tasks S047-T005–T008) is dropped from
Sprint 047's scope per the pre-agreed fallback. The design below is kept
verbatim as a starting point for a future, separate, engine-focused sprint —
it is deferred, not discarded.

**E1 — `BracketExitModel`**

```text
Fields         stop_loss_bps, take_profit_bps, max_bars, exit_model_id="bracket"
Offsets in BASIS POINTS, not price points, so a strategy is portable across
    instruments and price levels
max_bars is MANDATORY (>= 1) so no position can be held to the end of the dataset
Protocols      satisfies ExitModel UNCHANGED (exit_bar_index returns the max_bars
               timeout bar -- its worst case) PLUS a new additive PriceBracketExit
               protocol the simulator dispatches on
ExitReason     += STOP_LOSS, TAKE_PROFIT, MAX_BARS   (FIXED_BARS unchanged)
```

Locked semantics — the parts OHLCV genuinely cannot answer, decided
pessimistically because a silent optimistic assumption is how backtests lie:

```text
SAME-BAR AMBIGUITY   if a bar's low hits the stop AND its high hits the target,
                     THE STOP WINS. Always. No intrabar path reconstruction, no
                     open-proximity heuristic, and NO configuration flag -- a flag
                     here would be a flag for "how flattering should this be".
FILL PRICE           a stop or target fills at ITS OWN TRIGGER PRICE with the
                     existing slippage_bps applied AGAINST the trade.
                     The max_bars timeout keeps the next-bar-open convention,
                     identical to FixedBarsExitModel.
                     => one strategy can produce exits under two fill conventions.
                     Deliberate; exit_reason distinguishes them per trade.
SCAN WINDOW          from the entry fill bar INCLUSIVE. A gap through the stop on
                     the entry bar is a stop-out, not a skipped trade.
```

**R1 — `EquityPercentRiskModel`**

```text
quantity = (account_equity * risk_percent) / stop_distance   resolved in __post_init__
RiskModel protocol UNCHANGED (position_quantity() takes no arguments, so the
    quantity can only be a construction-time constant)
```

```text
LOCKED  this is STATIC, AUTHORING-TIME sizing. It is NOT compounding,
        equity-curve-following sizing, and must never be described as such --
        in the docstring, the guide, or a commit message.
LOCKED  v1 does NOT cross-validate stop_distance against BracketExitModel's
        stop_loss_bps (the risk model has no reference price to convert bps to
        points). The operator owns that consistency; the guide says so.
TD-026  dynamic sizing requires passing simulation state into position_quantity(),
        a RiskModel protocol change that also affects
        execution/runtime/strategy_orders.py and execution/broker_sim/paper_broker.py.
        Separate increment, own ADR. Logged with that trigger.
```

---

## D-S047-12 — Engine changes and their hard boundary — DEFERRED, not part of Sprint 047

**Answered: declined.** The maintainer chose not to narrow the PRD non-goal
for this sprint. This section is kept verbatim for a future sprint.

```text
Requested narrowing, from:
    "no change to BarSequentialSimulator"
to:
    "no change to the FIXED-BARS path's fill or accounting semantics;
     dispatch to an additional kernel is allowed"
```

Four bounded changes, nothing more:

```text
1  validate_strategy_model_definition: the two isinstance MVP guards become a
   supported-combination check
2  engine.py _require_fixed_quantity_risk -> structural RiskModel check
3  engine.py _require_fixed_bars_exit -> dispatch (FixedBars -> existing kernel,
   PriceBracketExit -> new kernel, anything else -> the same clear
   SimulationEngineError as today)
4  new research/simulation/kernels/bracket.py
```

```text
LOCKED  kernels/fixed_bars.py is NOT edited.
LOCKED  ExitModel and RiskModel Protocol definitions are NOT modified.
LOCKED  GOLDEN-RUN REGRESSION is a hard acceptance criterion: the canonical
        strategy on the committed fixture produces byte-identical trades, equity
        and run fingerprint before and after. If it does not, the change is
        wrong -- not the golden run.
LOCKED  every ExitReason consumer is audited (S047-T005) and each is stated safe
        with a reason; "probably fine" is not an audit.
```

**If the maintainer declines:** drop Wave 2 entirely, ship Waves 1/3/4, and open
Exit/Risk as its own sprint with an engine-focused ADR. Pre-decided so it is a
choice, not a mid-sprint discovery.

---

## D-S047-13 — Sequencing, descope order and testing

**One sprint, dependent waves** (answering the PRD's open question):

```text
Wave 1  loader                    <- delivers the headline metric alone
Wave 2  Exit/Risk + engine        <- DECLINED for Sprint 047, see D-S047-11/12
Wave 3  catalog                   <- independent of Wave 2
Wave 4  examples, docs, closure   <- needs 1 + 3 (Wave 2 dropped, not a dependency)
```

```text
LOCKED DESCOPE ORDER (if the sprint overruns): S047-T010, then S047-T009.
       WAVE 1 IS NEVER DROPPED -- without it nothing else is reachable from
       the CLI and the PRD's primary success metric is unmet. Wave 2 is
       already dropped by the maintainer's decision, not by overrun.
```

Testing:

```text
apps/cli/tests/      loader matrix: all nine D-S047-07 rows, same-stem collision,
                     no sys.path mutation (asserted), --dry-run writes nothing
                     from the CLI itself, end-to-end manifest strategy_model_id
tests/unit/          test_apps_boundaries.py allow-list byte-identical (D-S047-08)
                     component behaviour: causality, warmup, session boundaries,
                     zero-range bar
                     bracket kernel: stop / target / timeout / same-bar ambiguity,
                     each against a hand-computed fixture
                     GOLDEN-RUN regression for the fixed-bars path
Fixtures             apps/cli/tests/fixtures/strategies/ for loader fixtures;
                     the committed OHLCV fixture for runs
No network. No ML/DL extra. Wrapped workflows are not re-tested -- the CLI tests
the seam, the framework tests the models.
```

---

## D-S047-14 — Wave 0 Checklist (maintainer)

Nothing below may be checked off by an agent. `engineer` must refuse to start
while any box is unchecked.

- [x] **ADR-0027 approved** (PROPOSED -> ACCEPTED): the `strategy_file` loading mechanism, the pre-flight loading point, and the error taxonomy.
- [x] **D-S047-09 accepted explicitly:** the loaded strategy file is unsandboxed, unrestricted, arbitrary code execution named by a config path — and `--dry-run` no longer means "nothing ran", only "the CLI ran nothing".
- [x] **ADR-0028 answered: DECLINED.** The maintainer chose not to narrow the PRD non-goal on `BarSequentialSimulator`. Wave 2 (S047-T005–T008, D-S047-11, D-S047-12) is dropped from Sprint 047's scope per the pre-agreed fallback (SPRINT_047.md §4 Finding 1). The domain design is kept, deferred, for a possible future sprint with its own engine-focused ADR.
- [x] **D-S047-08 confirmed:** two different boundaries — `apps/cli`'s allow-list unchanged and unwidened; the loaded module unconstrained and unenforced; TD-025 logged for the static-scan blindness.
- [x] **D-S047-03 / D-S047-04 confirmed** (already given in the PRD conversation, restated here as a binding lock): single `strategy_file` key, fixed zero-argument `build_strategy()`, no function-name field.
- [x] **D-S047-05 confirmed:** an absent `strategy_file` still falls back to the canonical example (answers the PRD's open question; keeps Sprint 046 configs working).
- [x] **D-S047-10 confirmed:** exactly two components, `candle.wick` and `structure.level_distance` — and no arithmetic in the expression IR (Finding 3).
- [x] **D-S047-11/12 disposition confirmed:** DEFERRED, not built this sprint (see ADR-0028 answer above) — not applicable as an approval, but explicitly acknowledged rather than silently dropped.
- [x] **Sprint 047 scope approved as 10 tasks, 3 waves** (Wave 1 loader, Wave 3 catalog, Wave 4 composition/docs/closure) — Wave 2 and its 4 tasks removed per the ADR-0028 decision, not merely deferred by overrun.
- [x] **Branch `sprint/strategy-authoring` approved.** Sprint 046's integration PR (#361) has already merged to `main` — the D-S047-02 precondition is satisfied.
- [x] **ROADMAP Phase 12 approved** — apply the three splices in `docs/planning/ROADMAP_PHASE_12_PROPOSAL.md` and delete that file (S047-T014).

Approved-by: Filip Folga (project maintainer), given directly in conversation
with the orchestrating Claude Code session on 2026-09-01, across a structured
multi-question review: approved ADR-0027 in full; explicitly declined
ADR-0028's engine-narrowing request (dropping Wave 2 from this sprint, not
from the project); approved the exact catalog scope (`candle.wick` +
`structure.level_distance`), the sprint/branch structure, and the ROADMAP
Phase 12 splice.

Once every box is checked, the first task for `engineer` is **S047-T001**
(the `strategy_file` config key) on `feat/cli-strategy-file-loader`, cut from
`sprint/strategy-authoring`.
</content>
