# Dependency Rules (As-Enforced)

> **Reference doc** — [as-implemented layer](../README.md). Consolidated
> from `AGENTS.md` and `.cursor/rules/ARCHITECTURE_CONTROL.md` §4/§8 per
> Sprint 054's deferred `system/DEPENDENCY_RULES.md` item, verified against
> actual imports rather than restated from the rule files alone.

## 1. Allowed dependency direction

```text
Market
  ↓
Market Analysis
  ↓
Strategy
  ├── Research
  └── Execution
```

Additional allowed consumption:

```text
Market          → Research
Market          → Execution
Market Analysis → Research
Market Analysis → Execution
```

Forbidden direction:

```text
Market    → Research/Execution implementation details
Strategy  → Research
Execution → Research
src/      → concrete user_data modules
Domain    → concrete infrastructure adapters
apps/*    → research/execution engines or provider/importer adapters (ADR-0022)
```

## 2. What is actually enforced by a test today

The rule file (`.cursor/rules/ARCHITECTURE_CONTROL.md` §8) describes a
`tests/architecture/` suite with one test per rule. That directory does not
exist — the real boundary tests live under `tests/unit/` instead. Verified
by reading each test's actual assertion (not just its name):

| Rule | Enforced by | Scope actually checked |
|---|---|---|
| `src` must not import concrete `user_data` modules | `tests/unit/test_architecture_boundaries.py::test_framework_does_not_import_user_data` | Whole `trading_framework` package — zero `user_data`/`user_data.*` imports anywhere |
| Execution domain must not import Research, Infrastructure, or `user_data` | `tests/unit/execution/test_execution_architecture_boundaries.py::test_execution_domain_does_not_import_research_infrastructure_or_user_data` | `trading_framework.execution` package only |
| Market Analysis must not import Infrastructure or Application | `tests/unit/market_analysis/test_market_analysis_architecture_boundaries.py::test_market_analysis_does_not_import_infrastructure_storage` | `trading_framework.market_analysis` package only |
| Databento SDK confined to its infrastructure adapter | `tests/unit/test_architecture_boundaries.py::test_databento_imports_only_in_infrastructure` | Whole package, one specific vendor SDK |
| Predictive Research must not import ML libraries/infrastructure/trading capabilities directly | `tests/unit/test_architecture_boundaries.py::test_predictive_research_does_not_import_*` (6 tests) | `trading_framework.research.predictive` and its Wave 4 packages |
| No unauthenticated `urllib` usage outside infrastructure | `tests/unit/test_architecture_boundaries.py::test_no_urllib_import_outside_infrastructure` | Whole package |

Run them together: `uv run pytest tests/unit/test_architecture_boundaries.py tests/unit/execution/test_execution_architecture_boundaries.py tests/unit/market_analysis/test_market_analysis_architecture_boundaries.py`.

## 3. Rules stated in `ARCHITECTURE_CONTROL.md` §8 with no dedicated test

These directions hold in the current codebase (spot-checked by grepping for
the forbidden import prefixes below) but are **not** independently enforced
by an automated test the way §2's rules are — a future change could violate
them without CI catching it:

- `market must not import research` — verified clean by grep, no test.
- `market must not import execution` — verified clean by grep, no test.
- `strategy must not import research` — verified clean by grep, no test.
- `research must not import execution` — verified clean by grep, no test.
- `research and execution must remain independent` — same as the two rows
  above, no dedicated test.

One known, narrow exception to "domain modules must not import
infrastructure implementations": `src/trading_framework/market/contracts/session_date.py`
imports `trading_framework.infrastructure.observability.profile_context`
(a profiling/timing helper, not a storage or provider adapter). This is not
caught by any existing test — `test_market_analysis_does_not_import_infrastructure_storage`
only covers the `market_analysis` package, not `market`. Not resolved here;
noted so the gap is documented rather than silently present.

## 4. Contract direction (not import direction)

Infrastructure implements contracts (Protocols) defined by domain or
application layers — it does not define its own contracts for domain code
to adapt to. Domain and application code must not depend directly on
provider SDKs, broker SDKs, storage drivers, or framework-specific
adapters; see `docs/reference/system/MODULE_MAP.md` for where each
concrete adapter lives.

## 5. `apps/*` boundary

`apps/dashboard` and `apps/cli` are separate deployable consumers
(ADR-0022): they must not import research/execution engines or
provider/importer adapters directly. See `AGENTS.md`'s Architecture Rules
and ADR-0022 for the full rationale.
