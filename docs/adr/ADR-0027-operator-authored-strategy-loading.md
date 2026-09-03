# ADR-0027 — Operator-Authored Strategy Loading (`strategy_file` + `build_strategy()`)

## Status

ACCEPTED (Sprint 047)

Approved-by: Filip Folga (project maintainer), given directly in conversation
with the orchestrating Claude Code session on 2026-09-01, in response to a
summary of this ADR's key decisions (single `strategy_file` config key with a
fixed `build_strategy()` entry point; no sandbox, no import restriction on
the loaded module — explicitly the same trust model as running any local
script; `--dry-run`'s "touches nothing" guarantee narrowed to "the CLI itself
touches nothing," since the loaded module executes at import time). Answer:
"Tak, zatwierdzam" (approving the loading mechanism, the security/trust model
in §2, and the narrowed `--dry-run` guarantee in §4).

## Context

`trading-cli research run strategy` always evaluates the Sprint 013 canonical
example. `apps/cli/src/trading_cli/commands/research.py::_run_strategy` passes
`strategy_model=build_canonical_strategy_model()` unconditionally — inherited
from `scripts/strategy_research/run_strategy_research.py` and recorded as a
known v1 limitation in SPRINT_046.md §4 Finding 2, D-S046-03, ADR-0026
"Follow-up", and `apps/cli/CLAUDE.md`.

`docs/product/PRD-strategy-authoring.md` (confirmed) closes that gap. It also
names the **riskiest assumption** this ADR exists to answer: dynamic loading of
an arbitrary operator-supplied `.py` file is a different risk shape from the
CLI's own internal imports, and ADR-0026 + Amendment 1 built a deliberate,
tested import-boundary discipline that must not be quietly bypassed.

Three facts constrain the design:

1. **The framework has no serialized form for a `StrategyModelDefinition`.**
   It is a frozen dataclass composing `MarketModelDefinition`,
   `SignalModelDefinition`, an `ExitModel` and a `RiskModel`. There is no
   `from_dict`, no YAML loader, no schema. Inventing one is explicitly a PRD
   non-goal for v1.
2. **The shape already exists, hand-written.** `user_data/components/strategies/`
   holds three files (`high_volatility_higher_low.py`,
   `trend_pullback_continuation.py`, `session_high_breakout.py`), each with a
   zero-argument `build_strategy() -> StrategyModelDefinition`.
   `user_data/run_example_strategies.py` imports them directly in Python
   because no CLI mechanism exists. This ADR supersedes that pattern *for CLI
   users*; it does not delete or change those files.
3. **The CLI's existing allow-list already covers what the loader needs.**
   `tests/unit/test_apps_boundaries.py` allows `trading_framework.strategy`
   *and its submodules* (prefix match), and `trading_framework.strategy`
   exports `StrategyModelDefinition`, `StrategyModelDefinitionError` and
   `validate_strategy_model_definition`. The loader therefore requires **zero**
   widening of ADR-0026 Amendment 1's 17-module list.

## Decision

### 1. One config key, one fixed entry-point name

```yaml
research:
  kind: strategy
  strategy:
    dataset_ref: "BTCUSDT.P|ohlcv|1m|binance|binance-usdm-klines-v1@1"
    timeframe: 1m
    strategy_file: user_data/components/strategies/my_strategy.py   # NEW, optional
```

`strategy_file` is a filesystem path to a Python file. The loaded module's
entry point is **always** the conventional name `build_strategy` — zero
arguments, returning a `StrategyModelDefinition`.

```text
Chosen     one key (strategy_file) + a fixed conventional function name
Rejected   module + function pair in config (two keys, two failure modes)
Rejected   a dotted import path (couples the operator to sys.path layout)
Rejected   a declarative YAML strategy schema (no serialization exists; PRD non-goal)
```

Confirmed by the maintainer as an explicit simplification. It matches
ADR-0026 §4's existing rule — "existing spec files are referenced by path,
never re-encoded" — with the difference stated plainly: a `PredictiveStudySpec`
path points at *data* the framework parses; `strategy_file` points at *code*
the interpreter executes.

### 2. This is an executable-code loader, and it says so

The security model is exactly the model of running any local script the
operator already trusts:

```text
No sandbox. No import restriction. No AST inspection. No subprocess isolation.
Loading a strategy file is equivalent, in blast radius, to `uv run python <that file>`.
```

Sandboxing is a PRD non-goal and is arguably incoherent with a design whose
whole premise is "this is the operator's own code". What is **not** acceptable
is leaving that implicit: the operator guide, `docs/reference/modules/STRATEGY_AUTHORING.md`
and `trading-cli research run strategy --help` must state it in one plain
sentence.

### 3. Loading mechanism

```text
importlib.util.spec_from_file_location(synthetic_name, resolved_path)
importlib.util.module_from_spec(spec)
sys.modules[synthetic_name] = module        # before exec_module
spec.loader.exec_module(module)
entry = getattr(module, "build_strategy")
definition = entry()
```

Binding details:

- **Synthetic, collision-proof module name.** `trading_cli._loaded_strategy.<h>`
  where `<h>` is a short hash of the resolved absolute path. Two different
  files with the same stem must not shadow each other, and a loaded file must
  never occupy a name that could shadow a real package.
- **Registered in `sys.modules` before `exec_module`**, and left there. Removing
  it afterwards breaks dataclasses, pickling and any class defined in the file.
- **`sys.path` is never mutated.** The CLI performs no hidden global side
  effect. A strategy file that needs sibling imports is the operator's own
  packaging problem; the guide documents `PYTHONPATH` as the answer.
- **The path is resolved relative to the process working directory**, then
  made absolute before use, and the absolute path is echoed in the resolved
  plan and in the run output.

### 4. Loading happens during plan resolution, before any side effect

ADR-0026 §4 requires the CLI to validate and resolve **before** any side
effect. The loader honours that: `strategy_file` is imported and
`build_strategy()` is called during `resolve_plan`, so a missing file, a typo'd
function name or a wrong return type fails pre-flight, and `--dry-run` prints
the resolved `strategy_model_id` — proving the file loads without running a
simulation.

The honest cost, which the operator guide must state: `--dry-run`'s guarantee
narrows from "touches nothing" to **"the CLI itself performs no side effect;
the loaded strategy module is operator code and executes at import"**. A file
that writes to disk at import time will still do so under `--dry-run`. This is
a consequence of choosing pre-flight validation over lazy loading, and it is
the better trade: the alternative is discovering a typo after a multi-minute
dataset read.

### 5. Error taxonomy

Fits ADR-0026 §9 / D-S046-09 unchanged (`2` = configuration/authoring error,
`1` = workflow failure). The dividing line: **anything wrong with the file, the
convention or the returned object is exit 2**; only an exception raised by the
operator's own `build_strategy()` body is exit 1.

| Condition | Class | Exit | Message must name |
|---|---|---|---|
| path missing / not a file / a directory | `ConfigError` | 2 | `research.strategy.strategy_file` + the resolved absolute path |
| extension is not `.py` | `ConfigError` | 2 | the actual extension |
| module raises during import | `ConfigError` | 2 | the file, chained from the original exception |
| no `build_strategy` attribute | `ConfigError` | 2 | the convention, verbatim: zero-arg `build_strategy()` |
| `build_strategy` is not callable | `ConfigError` | 2 | the attribute's actual type |
| `build_strategy` requires arguments | `ConfigError` | 2 | the required parameter names |
| `build_strategy()` raises | `WorkflowError` | 1 | the file, chained from the original exception |
| return value is not a `StrategyModelDefinition` | `ConfigError` | 2 | the actual returned type |
| returned definition fails `validate_strategy_model_definition` | `ConfigError` | 2 | the framework's own validation message |

No traceback from the loaded module is swallowed: every chained error keeps
`__cause__` so `--verbose` shows the operator their own stack.

### 6. Import-boundary treatment — two boundaries, deliberately different

This is the PRD's riskiest assumption, decided explicitly rather than left
implicit.

**Boundary A — `apps/cli`'s own source tree: unchanged.** ADR-0026 §2 and
Amendment 1's 17-module allow-list stay exactly as they are, enforced by
`tests/unit/test_apps_boundaries.py`'s static AST scan of `apps/cli/src`. The
loader needs `StrategyModelDefinition` and `validate_strategy_model_definition`
from `trading_framework.strategy`, which is **already** on that list (added in
Amendment 1 for `build_canonical_strategy_model`) and matched by prefix. **No
widening, no new amendment.** A Wave 1 test asserts this rather than assuming it.

**Boundary B — the loaded strategy module: unconstrained, and not enforced.**

```text
A file named by research.strategy.strategy_file is NOT part of apps/cli's
source tree, is NOT scanned by the boundary test, and is subject to NO import
restriction of any kind.
```

Reasons, stated so a future reader does not mistake this for an oversight:

1. ADR-0026's boundary governs **what this repository ships and CI can
   enforce**. A typical strategy file lives in gitignored `user_data/` and CI
   never sees it. A rule that cannot be checked is not a boundary; it is a
   wish.
2. The file is the operator's own trusted code, running with the operator's own
   privileges (§2). An import restriction offers no security benefit whatsoever
   while an unrestricted interpreter is one line away.
3. Enforcing it would require import hooks or AST rewriting at load time — real
   machinery, real failure modes, protecting nothing.

**An advisory convention is documented, not enforced.** For portability, an
authored strategy should need only:

```text
trading_framework.model_authoring        the DSL (market_model, signal_model, price, ...)
trading_framework.strategy.*             StrategyModelDefinition, Exit/Risk models
trading_framework.time.models.timeframe  Timeframe
```

Reaching deeper (into `research.*`, `infrastructure.*`, an application
workflow) is legal, will work, and is a smell — it usually means the strategy
is doing something a Market/Signal Model should express. Advisory, because
breaking it costs the operator portability and costs the framework nothing.

**Residual gap, logged not hidden:** the boundary test is a static scan and
therefore structurally blind to dynamically loaded code. This is recorded as
**TD-025** in `docs/planning/TECHNICAL_DEBT.md` — alongside TD-024's
module-vs-symbol granularity gap — so nobody later reads a green boundary test
as proof that nothing outside the allow-list was imported at runtime.

### 7. Fallback when `strategy_file` is absent

`strategy_file` is **optional**. An existing `research.strategy` block with no
`strategy_file` keeps producing the canonical example — this increment is
purely additive, and every Sprint 046 example config keeps working unchanged.

The output (human and `--json`) states which path was taken, so
`strategy_model_id: "high_vol_higher_low_fixed_exit"` is never a silent
surprise again. Making `strategy_file` required was rejected: it would break
committed configs to enforce explicitness the output line already provides.

## Consequences

### Positive

- PRD success metric 1 is met: the run manifest's `strategy_model_id` reflects
  a user-authored strategy.
- SPRINT_046.md §4 Finding 2 is closed for the strategy model (the session
  resolver and simulation assumptions remain hardcoded — out of scope here).
- Zero new dependencies (`importlib`, `inspect`, `hashlib` are stdlib) and zero
  boundary-allow-list widening.
- The three hand-authored `user_data/` examples become runnable through the CLI
  with no edits, which is itself the acceptance evidence.
- Every failure mode is a pre-flight exit-2 error naming the config key, not a
  stack trace mid-simulation.

### Negative

- `--dry-run`'s "writes nothing" promise weakens to "the CLI writes nothing"
  (§4). Documented, not glossed.
- Arbitrary code execution from a config-referenced path is a genuinely larger
  attack surface than a YAML spec. Accepted deliberately: the operator already
  runs this repository's code on their own machine.
- Two front doors for authoring (`user_data/run_example_strategies.py` in-process
  imports; the CLI loader) coexist until someone retires the former. Not this
  sprint's job.
- A strategy file that imports a heavy optional extra (`ml`, `dl`) will fail at
  load with an ImportError surfaced as an exit-2 config error — correct, but
  the message points at the strategy file, not at the missing extra.

### Neutral

- The synthetic module name is an implementation detail and is not part of any
  contract; nothing may depend on it.
- `apps/dashboard`'s total ban on importing `trading_framework` is untouched.

## Alternatives Considered

1. **`module:function` or `module` + `function` config keys.** Rejected: two
   keys, two error surfaces, and a dotted path couples the operator to
   `sys.path` layout the CLI has deliberately decided not to mutate. The
   maintainer confirmed the single-key simplification.
2. **A declarative YAML `StrategyModelDefinition` schema.** Rejected for v1:
   no serialization exists anywhere in the framework, and building one means
   designing a schema for `MarketModelDefinition`, `SignalModelDefinition`, the
   expression IR, and every Exit/Risk model — a phase, not a task. Explicit PRD
   non-goal; revisit only if the Python loader proves limiting.
3. **A strategy registry / entry-point discovery mechanism** (`importlib.metadata`
   entry points, a decorator-based registry). Rejected: PRD non-goal, and it
   trades one explicit path for an implicit global namespace whose failure mode
   ("why did it pick that one?") is far worse than "file not found".
4. **Sandboxed execution** (restricted builtins, subprocess with a seccomp
   profile, import hooks). Rejected: PRD non-goal, defeated trivially by the
   operator's own shell, and it would add real machinery protecting nothing.
5. **Enforcing the ADR-0026 allow-list on the loaded module** via an import
   hook. Rejected: see §6 — unenforceable in the general case, no security
   benefit, and it would make legitimate operator code fail for a rule that
   exists to govern *this repository's* layering.
6. **Lazy loading (import inside `run()`, not `resolve_plan()`).** Rejected:
   it preserves a stricter `--dry-run` promise at the cost of ADR-0026 §4's
   "validate before any side effect", which is the more valuable guarantee.
7. **Making `strategy_file` required.** Rejected: breaks committed Sprint 046
   configs for no benefit the output line does not already deliver.

## Follow-up

- `S047_WAVE0_DECISIONS.md` binds the exact key placement, the error-message
  wording rules, and the fixture layout for the loader's test matrix.
- TD-025: the static boundary test cannot see dynamically loaded imports.
- Exposing `SimulationAssumptions` and the session resolver through config is
  **still** out of scope (SPRINT_046.md §4 Finding 2's other two hardcodes);
  this ADR closes only the strategy-model third of it.
- A future increment may retire `user_data/run_example_strategies.py`'s direct
  imports in favour of the CLI. Not decided here.

## Related

- `docs/product/PRD-strategy-authoring.md` (confirmed)
- `docs/adr/ADR-0026-operator-cli-framework-and-placement.md` (+ Amendment 1)
- `docs/adr/ADR-0016-ohlcv-strategy-research-mvp.md`
- `docs/adr/ADR-0028-bracket-exit-and-equity-relative-sizing.md`
- `docs/planning/sprints/SPRINT_047.md`, `S047_WAVE0_DECISIONS.md`
- `docs/planning/TECHNICAL_DEBT.md` TD-024, TD-025
</content>
</invoke>
