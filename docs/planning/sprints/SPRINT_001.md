# Sprint 001 — Repository Foundation

## Metadata

```text
Sprint: 001
Phase: Phase 1 — Repository Foundation
Status: COMPLETED
Planned Start: 2026-06-19
Planned End: 2026-06-26
Completed: 2026-06-19
Sprint Goal Owner: Project Maintainer
```

---

## Sprint Goal

```text
Create a repository foundation that installs,
passes CI and enforces the primary architectural boundaries.
```

Success means a new contributor can clone the repository, install dependencies, run quality checks and tests locally, and find a validated core layer with UTC time primitives, identifiers, configuration and logging — without any domain implementation beyond package skeletons.

---

## Phase Alignment

This sprint implements the first vertical slice of **Phase 1 — Repository Foundation** from `ROADMAP.md`.

It must complete before **Phase 2 — Market Data MVP** begins.

---

## Scope

In scope:

- repository and package structure,
- quality toolchain (Ruff, mypy, pytest, CI, pre-commit),
- `src/` and `user_data/` separation,
- domain package skeletons without speculative logic,
- core identifiers and exceptions,
- UTC timestamp and `Timeframe` primitives,
- `Clock` contract with `SystemClock` and `FixedClock`,
- minimal validated configuration loading,
- logging foundation,
- architecture boundary tests,
- root `AGENTS.md` and `README.md`,
- initial ADR materialization for decisions already accepted in architecture documents.

Out of scope:

- provider integrations,
- Parquet repository,
- Market Analysis Engine,
- model or research workflows,
- broker or execution logic,
- trading calendar implementation,
- numeric types for price, volume and quantity (deferred to Phase 2; see PRB-010),
- full ADR set (only sprint-critical ADRs in this sprint).

---

## Dependencies

```text
Phase 0 planning documents (complete)
Vision docs in docs/vision/; reference in docs/reference/
```

No external services are required.

---

## Risks

| Risk | Mitigation |
|------|------------|
| Over-building `core/` before first domain slice | Limit identifiers to a small validated base pattern; defer domain-specific IDs to Phase 2 |
| Adding Pydantic everywhere | Use Pydantic only at configuration boundaries per architecture |
| Empty package directories become permanent taxonomy | Create skeletons only; no speculative subpackages beyond architecture baseline |
| `CURRENT_STATUS.md` diverges from repository state | Update status at sprint start and end |

---

## Task Summary

| ID | Task | Status | Depends On |
|----|------|--------|------------|
| S001-T001 | Installable package and `uv` project setup | DONE | — |
| S001-T002 | pytest configuration and smoke import test | DONE | S001-T001 |
| S001-T003 | Ruff lint and format configuration | DONE | S001-T001 |
| S001-T004 | mypy strict configuration | DONE | S001-T001 |
| S001-T005 | GitHub Actions CI pipeline | DONE | S001-T002, S001-T003, S001-T004 |
| S001-T006 | pre-commit hooks | DONE | S001-T003, S001-T004 |
| S001-T007 | Domain package skeleton | DONE | S001-T001 |
| S001-T008 | `user_data/` placeholder structure | DONE | — |
| S001-T009 | Root `AGENTS.md` entry point | DONE | — |
| S001-T010 | Root `README.md` | DONE | S001-T001 |
| S001-T011 | Test directory structure (`unit` / `integration` / `e2e`) | DONE | S001-T002 |
| S001-T012 | Architecture boundary tests | DONE | S001-T007, S001-T008 |
| S001-T013 | Core exception hierarchy | DONE | S001-T007 |
| S001-T014 | Base identifier value objects | DONE | S001-T013 |
| S001-T015 | UTC timestamp primitives and normalization | DONE | S001-T013 |
| S001-T016 | `Timeframe` value object | DONE | S001-T013 |
| S001-T017 | `Clock` protocol, `SystemClock`, `FixedClock` | DONE | S001-T015 |
| S001-T018 | Minimal framework configuration model | DONE | S001-T013 |
| S001-T019 | Configuration file loading | DONE | S001-T018 |
| S001-T020 | Logging foundation | DONE | S001-T018 |
| S001-T021 | Initial ADR files (0001–0003) | DONE | — |
| S001-T022 | Sprint review and status update | DONE | All preceding tasks |

---

## Tasks

### S001-T001 — Installable package and `uv` project setup

**Status:** DONE  
**Category:** Maintenance  
**Domain:** Core

#### Context

The repository needs a reproducible install path before any domain code is added.

#### Scope

- `pyproject.toml` with package metadata and dev dependencies
- `uv.lock` for reproducible installs
- `src/trading_framework/` package with `py.typed`
- `.python-version`

#### Acceptance Criteria

- [x] `uv sync --locked --dev` succeeds
- [x] `uv build` produces a wheel
- [x] Package imports as `trading_framework`

---

### S001-T002 — pytest configuration and smoke import test

**Status:** DONE  
**Category:** Maintenance  
**Domain:** Core  
**Depends On:** S001-T001

#### Scope

- pytest configuration in `pyproject.toml`
- `tests/unit/test_package.py` verifying package import

#### Acceptance Criteria

- [x] `uv run pytest` passes
- [x] `pythonpath` includes `src`

---

### S001-T003 — Ruff lint and format configuration

**Status:** DONE  
**Category:** Maintenance  
**Domain:** Core  
**Depends On:** S001-T001

#### Acceptance Criteria

- [x] `uv run ruff check .` passes
- [x] `uv run ruff format --check .` passes

---

### S001-T004 — mypy strict configuration

**Status:** DONE  
**Category:** Maintenance  
**Domain:** Core  
**Depends On:** S001-T001

#### Acceptance Criteria

- [x] `uv run mypy` passes on `src` and `tests`
- [x] `strict = true` is enabled

---

### S001-T005 — GitHub Actions CI pipeline

**Status:** DONE  
**Category:** Maintenance  
**Domain:** Core  
**Depends On:** S001-T002, S001-T003, S001-T004

#### Scope

- `.github/workflows/ci.yml` with quality, test and build jobs

#### Acceptance Criteria

- [x] CI runs Ruff, mypy, pytest and package build on `main` and pull requests

---

### S001-T006 — pre-commit hooks

**Status:** DONE  
**Category:** Maintenance  
**Domain:** Core  
**Depends On:** S001-T003, S001-T004

#### Acceptance Criteria

- [x] `.pre-commit-config.yaml` runs Ruff and mypy

---

### S001-T007 — Domain package skeleton

**Status:** DONE  
**Category:** Architecture  
**Domain:** Core  
**Depends On:** S001-T001

#### Context

Phase 1 requires domain packages to exist without speculative implementation. The architecture defines the baseline module layout.

#### Scope

Create empty package directories with `__init__.py` only:

```text
src/trading_framework/
├── core/
├── time/
├── market/
├── market_analysis/
├── strategy/
├── research/
├── execution/
├── events/
├── config/
├── infrastructure/
└── application/
```

`time/` already exists; extend it with the planned subpackage layout only if needed by later tasks in this sprint.

#### Out of Scope

- business logic,
- provider adapters,
- concrete services.

#### Architecture References

- `docs/vision/ARCHITECTURE_TECHNICAL_UPDATED.md` §10.2–10.3

#### Acceptance Criteria

- [x] All listed packages import without side effects
- [x] No cross-domain imports beyond allowed foundation dependencies
- [x] Public `__init__.py` files remain minimal

#### Test Cases

- import smoke test per top-level domain package

---

### S001-T008 — `user_data/` placeholder structure

**Status:** DONE  
**Category:** Documentation  
**Domain:** Core

#### Context

`user_data/` is user-owned and must remain outside framework imports. The repository still needs a documented placeholder.

#### Scope

- `user_data/README.md` explaining ownership, gitignore policy and expected subdirectories
- documented placeholder layout:

```text
user_data/
├── config/
├── components/
├── models/
├── datasets/
└── research/
```

#### Out of Scope

- committed proprietary strategies, datasets or credentials

#### Acceptance Criteria

- [x] `user_data/README.md` is tracked in git
- [x] `.gitignore` continues to exclude `user_data/**` except the README
- [x] README explains that `src/` must not import concrete `user_data/` modules

---

### S001-T009 — Root `AGENTS.md` entry point

**Status:** DONE  
**Category:** Documentation  
**Domain:** Core

#### Context

Cursor rules and architecture documents reference root `AGENTS.md`, but only module-specific agent docs exist under `docs/agents/`.

#### Scope

- create root `AGENTS.md` with:
  - required reading order,
  - `src/` / `user_data/` boundary rule,
  - quality commands,
  - links to architecture and planning documents,
  - module-specific agent doc pointers.

#### Acceptance Criteria

- [x] `AGENTS.md` exists at repository root
- [x] `.cursor/rules/project-architecture.mdc` reference resolves
- [x] Document is concise and does not duplicate full architecture text

---

### S001-T010 — Root `README.md`

**Status:** DONE  
**Category:** Documentation  
**Domain:** Core  
**Depends On:** S001-T001

#### Scope

- project purpose (one paragraph),
- prerequisites (Python 3.12, uv),
- install instructions,
- local quality commands,
- links to `docs/planning/ROADMAP.md` and `docs/planning/CURRENT_STATUS.md`.

#### Acceptance Criteria

- [x] README is non-empty and accurate
- [x] documented commands match CI and `pyproject.toml`

---

### S001-T011 — Test directory structure

**Status:** DONE  
**Category:** Maintenance  
**Domain:** Core  
**Depends On:** S001-T002

#### Scope

```text
tests/
├── unit/
├── integration/
└── e2e/
```

Add package `__init__.py` files and pytest markers documentation if needed.

#### Acceptance Criteria

- [x] All three test layers exist
- [x] pytest collects only meaningful tests (no empty failing modules)
- [x] integration and e2e directories have README or docstring explaining intended use

---

### S001-T012 — Architecture boundary tests

**Status:** DONE  
**Category:** Architecture  
**Domain:** Core  
**Depends On:** S001-T007, S001-T008

#### Scope

- test that `src/trading_framework` does not import `user_data`
- optional static import-boundary test using `importlib` or AST inspection

#### Architecture References

- `docs/vision/ARCHITECTURE_FOUNDATIONS_UPDATED.md`
- `docs/planning/ROADMAP.md` Phase 1 completion criteria

#### Acceptance Criteria

- [x] Failing test if framework code imports `user_data`
- [x] Test runs in CI without external dependencies

---

### S001-T013 — Core exception hierarchy

**Status:** DONE  
**Category:** Feature  
**Domain:** Core  
**Depends On:** S001-T007

#### Scope

Implement explicit base exceptions under `src/trading_framework/core/exceptions/`:

- `TradingFrameworkError` (base)
- `ValidationError`
- `ConfigurationError`

#### Out of Scope

- domain-specific exceptions (market, research, execution)

#### Acceptance Criteria

- [x] Exceptions are explicit and documented
- [x] No bare `except Exception: pass`
- [x] Unit tests cover inheritance and raising behaviour

---

### S001-T014 — Base identifier value objects

**Status:** DONE  
**Category:** Feature  
**Domain:** Core  
**Depends On:** S001-T013

#### Context

Identifiers must be validated, immutable and hashable. Domain-specific IDs such as `DatasetId` belong to Phase 2, but the base pattern must exist now.

#### Scope

- immutable string-based identifier base type or small helper
- validation rules: non-empty, normalized form, equality and hashing

#### Out of Scope

- `InstrumentId`, `DatasetId`, `DatasetRef` (Phase 2)

#### Architecture References

- `docs/vision/ARCHITECTURE_TECHNICAL_UPDATED.md` §10.3

#### Acceptance Criteria

- [x] Identifier objects are immutable
- [x] Invalid identifiers are rejected explicitly
- [x] Unit tests cover equality, hashing and validation

---

### S001-T015 — UTC timestamp primitives and normalization

**Status:** DONE  
**Category:** Feature  
**Domain:** Time  
**Depends On:** S001-T013

#### Scope

- timezone-aware UTC value object or validated alias pattern
- normalization helper rejecting naive `datetime`
- conversion helper from aware non-UTC datetime to UTC

#### Architecture References

- `docs/vision/ARCHITECTURE_TECHNICAL_UPDATED.md` §2.2–2.3
- ADR-0003 (to be created in S001-T021)

#### Acceptance Criteria

- [x] Naive datetimes are rejected
- [x] Canonical internal representation is UTC
- [x] Unit tests cover valid, invalid and conversion cases
- [x] No direct `datetime.now()` usage in domain modules introduced by this task

---

### S001-T016 — `Timeframe` value object

**Status:** DONE  
**Category:** Feature  
**Domain:** Time  
**Depends On:** S001-T013

#### Scope

- immutable `Timeframe` representing bar duration
- parse/validate canonical string forms (e.g. `1m`, `5m`, `1h`, `1d`)
- reject invalid or ambiguous values

#### Out of Scope

- calendar-aware bar alignment,
- session-aware timeframe semantics.

#### Architecture References

- `docs/reference/modules/DATA_MODULE_UPDATED.md` §29
- `docs/vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE_UPDATED.md` §6.2

#### Acceptance Criteria

- [x] `Timeframe` is immutable and hashable
- [x] Invalid values raise explicit validation errors
- [x] Unit tests cover parsing and equality

---

### S001-T017 — `Clock` protocol, `SystemClock`, `FixedClock`

**Status:** DONE  
**Category:** Feature  
**Domain:** Time  
**Depends On:** S001-T015

#### Scope

- `Clock` protocol with `now() -> datetime` returning UTC-aware datetime
- `SystemClock`
- `FixedClock` for deterministic tests

#### Out of Scope

- `ResearchClock`, `ReplayClock` (later phases)

#### Architecture References

- `docs/vision/ARCHITECTURE_TECHNICAL_UPDATED.md` §2.8

#### Acceptance Criteria

- [x] `FixedClock` enables deterministic tests
- [x] `SystemClock.now()` returns timezone-aware UTC
- [x] Unit tests cover both implementations

---

### S001-T018 — Minimal framework configuration model

**Status:** DONE  
**Category:** Feature  
**Domain:** Config  
**Depends On:** S001-T013

#### Scope

- add `pydantic` as a demonstrated dependency
- `FrameworkConfig` with minimal fields, e.g.:
  - `environment` (`dev` / `test` / `prod`)
  - `log_level`
- strict validation, no arbitrary code execution

#### Architecture References

- `docs/vision/ARCHITECTURE_TECHNICAL_UPDATED.md` §9.1–9.4

#### Acceptance Criteria

- [x] Invalid configuration is rejected with explicit errors
- [x] Model is serializable to and from dict/JSON
- [x] Unit tests cover valid and invalid inputs

---

### S001-T019 — Configuration file loading

**Status:** DONE  
**Category:** Feature  
**Domain:** Config  
**Depends On:** S001-T018

#### Scope

- load `FrameworkConfig` from YAML or TOML file
- clear error on missing file, malformed file or schema mismatch

#### Out of Scope

- environment-variable layering,
- run-specific override persistence.

#### Acceptance Criteria

- [x] Loading from a valid file returns `FrameworkConfig`
- [x] Invalid files raise `ConfigurationError`
- [x] Unit tests use fixture files under `tests/`

---

### S001-T020 — Logging foundation

**Status:** DONE  
**Category:** Feature  
**Domain:** Config  
**Depends On:** S001-T018

#### Scope

- `configure_logging(config: FrameworkConfig)` helper
- structured, explicit log level from configuration
- no global hidden state beyond standard `logging` module usage

#### Acceptance Criteria

- [x] Logging can be configured from `FrameworkConfig`
- [x] Default behaviour is safe for tests
- [x] Unit test verifies level configuration

---

### S001-T021 — Initial ADR files (0001–0003)

**Status:** DONE  
**Category:** Documentation  
**Domain:** Architecture

#### Context

Architectural decisions are described in foundation documents but not yet preserved as individual ADR files. PRB-016 tracks this gap.

#### Scope

Create:

```text
docs/adr/ADR-0001-modular-monolith.md
docs/adr/ADR-0002-separate-src-and-user-data.md
docs/adr/ADR-0003-utc-internal-time.md
```

Each ADR must follow the project ADR template: context, decision, consequences, status.

#### Out of Scope

- ADR-0004 through ADR-0010 (subsequent sprint or Phase 0 cleanup increment)

#### Acceptance Criteria

- [x] Three ADR files exist with accepted status
- [x] `docs/adr/README.md` index links to created ADRs
- [x] PRB-016 note updated if resolution criteria are met for these items

---

### S001-T022 — Sprint review and status update

**Status:** DONE  
**Category:** Documentation  
**Domain:** Core  
**Depends On:** All preceding tasks

#### Scope

- complete Sprint Review and Retrospective sections below
- update `docs/planning/CURRENT_STATUS.md`
- mark completed tasks in this file without rewriting historical plan text

#### Acceptance Criteria

- [x] Sprint Review section filled with actual outcomes
- [x] `CURRENT_STATUS.md` reflects Phase 1 progress
- [x] Incomplete work carried forward with explicit reason

---

## Sprint Review

### Completed

- T001–T022 (full Sprint 001 scope)

### Not Completed

- none

### Demonstrated Capabilities

- installable package with pydantic configuration boundary,
- domain package skeletons for all planned modules,
- core exceptions, identifiers, UTC time primitives, `Timeframe`, `Clock`,
- TOML configuration loading and logging setup,
- architecture boundary test preventing `user_data/` imports,
- 36 unit tests, CI-ready quality toolchain,
- root `AGENTS.md`, `README.md`, `user_data/README.md`,
- ADR-0001 through ADR-0003.

### Deviations From Plan

- Sprint document was created after partial Phase 1 implementation had already started (T001–T006).
- Configuration loading uses TOML via stdlib `tomllib` rather than YAML.

### Carry-Forward Items

- none

---

## Retrospective

### What Worked

- vertical-slice approach delivered a testable foundation quickly,
- architecture boundary test provides early enforcement of `src/` / `user_data/` separation,
- Pydantic limited to configuration boundary kept domain models lightweight.

### What Did Not Work

- initial sprint planning lagged behind the first repository bootstrap commits.

### Process Improvements

- define the next sprint before closing the current one,
- keep `CURRENT_STATUS.md` aligned when implementation starts before sprint documentation.

### Next Recommended Sprint Goal

```text
Phase 2 start: first Market Data vertical slice —
Instrument, MarketBar, DatasetId, CSV import, UTC normalization.
```

---

## Definition of Done (Sprint Level)

The sprint is complete when:

```text
[x] Sprint Goal is achieved
[x] All in-scope tasks are DONE or explicitly carried forward
[x] CI is green on main
[x] CURRENT_STATUS.md is updated
[x] Sprint Review and Retrospective sections are filled
[x] No undocumented architectural deviation was introduced
```
