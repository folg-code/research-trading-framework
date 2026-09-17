# Sprint 065: Market Analysis Component Registration Tooling

Status: **Open** — maintainer authorized opening this sprint 2026-09-17.
Goal: Remove the fully-manual component-registration step before Phase 19's
Wave A (21 components) starts, by building a scaffolding CLI and a
promotion-readiness report, then proving both are actually usable by
scaffolding and shipping one real component with them.

Sources:

- `docs/product/PRD-market-analysis-catalog-expansion-2026-09.md` (APPROVED 2026-09-17)
- `docs/planning/roadmap/PHASE_19_MARKET_ANALYSIS_CATALOG_EXPANSION.md` (APPROVED 2026-09-17)
- `docs/planning/roadmap/PHASE_19_WAVE0_DECISIONS.md` — D-P19-01 (ACCEPTED 2026-09-17), the binding design for this sprint's two tools; D-P19-06 (ACCEPTED), which named this as Sprint N and recommended `structure.opening_gap` as the pilot component
- `docs/planning/registries/idea-market-analysis.md#idea-010` (Component Scaffolding CLI), `#idea-011` (Automatic Candidate Promotion Report), `#idea-027` (source of the pilot component, `structure.opening_gap`)
- `src/trading_framework/market_analysis/registry/builtins.py` (the manual pattern being scripted)
- `src/trading_framework/market_analysis/components/structure/level_distance.py` (closest existing component precedent for a single-bar, ATR-adjacent `structure.*` feature)
- `docs/reference/modules/ANALYSIS_COMPONENT_CATALOG.md` (catalog entry format)
- `docs/AGENTS.md` (ADR-0022: scripts stay thin — parse args, call an application API, write output)

Architecture triage: **complete and accepted.** D-P19-01 through D-P19-06
were accepted by the maintainer on 2026-09-17 (`PHASE_19_WAVE0_DECISIONS.md`).
This sprint does not re-derive the tooling design; it implements D-P19-01
as specified. Any finding that would change an accepted Wave 0 decision is
a STOP-AND-REPORT, not an in-sprint amendment.

## Scope

In scope:

- `scripts/market_analysis/scaffold_component.py` — a thin CLI
  (`--component-id`, `--pack`, `--kind`, `--causal`, `--depends-on`) that
  generates, per D-P19-01: a component/implementation file skeleton under
  `src/trading_framework/market_analysis/components/<pack>/<name>.py`
  (constants pre-filled, `compute`/`data_dependencies`/`component_dependencies`
  stubbed with `raise NotImplementedError`), a component-contract test
  stub under `tests/market_analysis/components/<pack>/test_<name>.py`, a
  registration patch applied directly to `registry/builtins.py` (import
  line, `register_<name>_component` function, its call inside
  `register_mvp_components`, `__all__` entry — alphabetical text-anchor
  insertion, not an AST rewrite), and a stub `ANALYSIS_COMPONENT_CATALOG.md`
  entry marked `<!-- TODO: fill in before promotion -->` under a "Phase 19
  additions" heading.
- `scripts/market_analysis/check_promotion_readiness.py` — a read-only CLI
  reporting, per component ID, the six mechanical checks D-P19-01 lists
  (registered, tested, output schema non-empty, dependency methods
  implemented, catalog entry present without the TODO marker, causal-only
  gate for `session.*` components) as PASS/FAIL/NEEDS-REVIEW. Never writes
  to the registry, the catalog doc, or any component file.
- **Pilot run**: use `scaffold_component.py` to scaffold
  `structure.opening_gap` (IDEA-027 — the gap between a bar's open and the
  prior bar's close; the simplest proposed Wave A component, no component
  dependencies), then implement its real formula/output by hand, fill in
  its catalog entry, and confirm `check_promotion_readiness.py` reports it
  PASS. This is the proof, per the PRD's success metric 1, that the
  tooling is actually used, not built and left idle.

Out of scope:

- Any other Wave A component (`structure.range_discontinuity`,
  `volatility.*`, `candle.*`, etc.) — those are Sprint N+1 (Wave A),
  opened separately once this sprint closes.
- Any Wave B component or design work (IDEA-029, IDEA-032, IDEA-031's
  VWAP variant).
- Signal Research / Strategy Research validation of `structure.opening_gap`
  or any component — out of scope for the whole PRD (see PRD non-goals),
  not just this sprint.
- Making `check_promotion_readiness.py` a CI gate or a blocking check —
  D-P19-01 is explicit that it is a recommendation surface only.
- Any registry structural change — D-P19's Wave 0 already confirmed none
  is needed.
- An AST-based rewrite of `builtins.py` — the text-anchor insertion
  approach is the accepted design; a more robust rewrite is not this
  sprint's job unless the text-anchor approach is found to be unworkable
  in practice, which would be a STOP-AND-REPORT finding.

## Decisions

Binding detail and rationale: [`PHASE_19_WAVE0_DECISIONS.md`](../roadmap/PHASE_19_WAVE0_DECISIONS.md),
D-P19-01 (tooling design) and D-P19-06 (this sprint's scope and the
`structure.opening_gap` pilot choice). No new Wave 0 decisions are opened
in this sprint; both are already ACCEPTED (maintainer, 2026-09-17).

## Tasks

| Task | Outcome | Dependencies | Ownership | Risk | Status | PR |
|---|---|---|---|---|---|---|
| T001 | `scaffold_component.py` generates a correct file skeleton + test stub for a new component ID, matching the existing hand-written pattern exactly | Approved sprint | `scripts/market_analysis` | standard | Done — `scripts/market_analysis/scaffold_component.py` + `tests/unit/scripts/test_scaffold_component_cli.py` (9 tests), ruff/ruff-format/mypy clean on both the tool and its generated output; self-review fixed a real `--depends-on` line-length bug and CRLF output before opening the PR | [#552](https://github.com/folg-code/research-trading-framework/pull/552) |
| T002 | `scaffold_component.py`'s registration-patch step correctly inserts the import, `register_<name>_component` function, its call in `register_mvp_components`, and the `__all__` entry into `registry/builtins.py`, alphabetically, without disturbing existing entries | T001 | `scripts/market_analysis` + `market_analysis/registry` | standard | Done — patches pack `__init__.py` + `registry/builtins.py`; handles both an existing pack and a brand-new one; verified against the real repo (`structure.opening_gap`, reverted after verification — real component is T005) with a minimal correct diff, ruff/format/mypy clean, full `market_analysis` suite (278 tests) green | [#552](https://github.com/folg-code/research-trading-framework/pull/552) |
| T003 | `scaffold_component.py` appends a stub `ANALYSIS_COMPONENT_CATALOG.md` entry under a "Phase 19 additions" heading, marked with the TODO marker | T001 | `scripts/market_analysis` + docs | low | Not started | PR TBD |
| T004 | `check_promotion_readiness.py` runs all six D-P19-01 checks per named component ID and reports PASS/FAIL/NEEDS-REVIEW without mutating any file | Independent of T001-T003 | `scripts/market_analysis` | standard | Not started | PR TBD |
| T005 | `structure.opening_gap` is scaffolded via T001-T003, its real formula is implemented (gap = current bar open minus prior bar close, plus a normalized/percentage variant if the catalog convention calls for one — implementer confirms against `structure.level_distance`'s ATR-normalization precedent), its contract test passes, its catalog entry is completed (formula, warm-up, zero-denominator/first-bar convention), and `check_promotion_readiness.py` reports it PASS | T001-T004 | `market_analysis/components/structure` | standard | Not started | PR TBD |

## Branch and PR rules

Per the `git-workflow` skill defaults; no project-specific deviation.

```text
main
  └── sprint/market-analysis-catalog-tooling
        ├── feat/component-scaffold-cli          (T001, T002, T003)
        ├── feat/promotion-readiness-report       (T004)
        └── feat/opening-gap-component            (T005)
```

- Integration branch: `sprint/market-analysis-catalog-tooling`, cut from
  `main` at its then-current head after approval.
- Working branches: `<prefix>/<descriptive-slug>`, cut from the sprint
  branch.
- PR base is always the sprint branch. One final integration PR to `main`
  at sprint close, after review and CI.
- Squash merge for working PRs. `engineer` stops before merge and reports
  the PR URL.
- T005 depends on T001-T004 merging into the sprint branch first (it
  exercises the finished tooling); rebase before opening its PR.

## Acceptance criteria

- Running `scaffold_component.py --component-id structure.some_new_thing
  --pack structure --kind FEATURE` produces a component file, a test file,
  a `registry/builtins.py` patch, and a catalog stub — with zero manual
  editing needed to make the scaffold *runnable* (the author still fills
  in the real math and parameter schema by hand, per D-P19-01's explicit
  non-goal).
- The registration patch is idempotent-safe: running the CLI twice for
  different component IDs does not corrupt `builtins.py`'s existing
  entries or `__all__` list.
- `check_promotion_readiness.py` correctly reports FAIL for a
  freshly-scaffolded, unfinished component (empty `OutputSchema`, `NotImplementedError`
  stubs) and PASS once `structure.opening_gap` is fully implemented.
- `check_promotion_readiness.py` never writes to any file — verified by a
  test that scaffolds a component, runs the report, and asserts no file's
  mtime changed.
- `structure.opening_gap` is registered, passes its component-contract
  test, has a complete `ANALYSIS_COMPONENT_CATALOG.md` entry with no TODO
  marker remaining, and is exercised by at least one example Signal Model
  composition (PRD success metric 4 — runs error-free, correct output
  shape; no predictive claim made).
- No other Wave A component is touched in this sprint.

## Descope order

If the sprint must shrink, drop in this order — never the reverse:

```text
1. T003  (catalog-stub generation; fall back to a hand-written catalog entry for the pilot)
2. T004  (promotion report; T005 can still ship with a manual promotion-readiness check)
```

T001, T002 and T005 are not descopable: T001/T002 are the sprint's whole
point (removing manual registration before Wave A), and T005 is the proof
the tooling is actually used, required by the PRD's own success metric 1.

## Closeout

To be completed when this sprint closes: integrated checks, documentation
reconciliation (`PHASE_19_MARKET_ANALYSIS_CATALOG_EXPANSION.md`'s sprint
table, `CURRENT_STATUS.md`), review notes, and remaining work (opening
Sprint N+1 — Wave A).
