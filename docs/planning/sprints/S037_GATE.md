# Sprint 037 Gate

Binding entry criteria and design rules for **Sprint 037 — Component libraries + DSL
simplification**. Written as S036-T010. Date: 2026-08-25.

Sprint 036 measured the authoring → analysis → evaluate path and repaid the justified
representation work (Stage 0.5–2, ADRs for Stage 3/4). This document answers two questions
S037 is not allowed to guess:

1. When is the **DSL simple enough**?
2. When is the **component library ready** to grow?

It is **not** the Sprint 037 task board. Wave 0 of S037 still writes `SPRINT_037.md` and
binding `S037_WAVE0_DECISIONS.md`.

---

## 1. Entry: S037 may start

All of the following must hold:

1. Sprint 036 audit exists: `docs/reference/DATA_REPRESENTATION_AUDIT.md`.
2. Authoring bench exists: `scripts/ops/bench_authoring_analysis_evaluate.py`.
3. Every HIGH authoring-path item is either repaid or **explicitly deferred** below.
4. This gate document is on the sprint branch (or `main` after S036 integration).

S036-T011 (CURRENT_STATUS / ROADMAP closeout) may finish in parallel. It does **not** block
opening S037 planning.

### 1.1 Authoring-path HIGH items

| Item | Status at this gate | S037 implication |
|------|---------------------|------------------|
| M1 session resolver | Partially repaid (#279). Residual timezone pass + Utf8 `session_id` | Do not block S037. Do not spend S037 on a second resolver rewrite unless a new component needs a different session model. |
| H2 resample `MarketBar` round-trip | Repaid (#281) | New MTF components use the columnar resample path. |
| H6 last-closed-bar align | Measured **not material** (~0.6 ms at 500 1m bars) | Do not optimize in S037. |
| H1 partitioned OHLCV read | Repaid (#283, ~41× on 90-session query) | Catalog work may assume `query_ohlcv_table` pushdown. |
| H1 research-envelope `read_parquet` | Deferred (full-file, no predicate) | Out of S037. |
| Lazy analysis frame | Shipped (#284); wall time **flat** | Keep `build_analysis_frame(...) -> DataFrame`. |
| H4 `query_historical` → `list[MarketBar]` | Unmeasured on the columnar path | Do not block S037. Do not add new bulk consumers of `list[MarketBar]`. |
| H3 `tuple` ↔ `ndarray` (esp. swing) | Unpaid; Stage 4 `MarketFrame` is the structural fix | New **batch** components still implement the current view + NumPy adapter. Do not wait for Stage 4 to add a component. |
| Stage 3 `available_at` column / lineage sidecar | ADRs landed (MA-009 / MA-005 amendments); **code not started** | New components must not invent a third availability or lineage story. Follow MA-009/MA-005 until Stage 3 PRs land. |
| Stage 4 `MarketFrame` | ADR-MA-014 landed; **code not started** | S037 does **not** migrate the engine to `MarketFrame`. That remains Stage 4, independently sequenced. |

**Decision:** there is no unpaid HIGH authoring bottleneck that forbids expanding the catalog
or simplifying the DSL. Compile cost is **0.2 ms and flat in bar count** (audit §6.1 M4). S037
has headroom.

---

## 2. “DSL simple enough”

The user-facing package is `model_authoring/`. It compiles to `model_expression` IR
(ADR-0006). S037 simplifies **authoring**, not the IR.

### 2.1 Must remain true

1. **IR is stable.** `CompareExpression`, `And`/`Or`/`Not`, `ComponentOutputReference`,
   `MarketFieldReference` stay the compile target. A new IR node requires an ADR-0006
   amendment and a reason a **library function cannot express the idea**.
2. **Authors never construct IR by hand** for the happy path. `market_model(...)` /
   `signal_model(...)` plus typed namespaces (`price`, `trend`, `volatility`, `structure`)
   are the surface.
3. **Operator set stays small:** comparisons and `&` / `|` / `~` on `Condition`. Do not add
   new dunder operators, statement forms, or a second language.
4. **New components appear as functions on a namespace**, not as new syntax.
   `trend.ema(period=20)` is the pattern; `ema := ...` macros are not.
5. **Helpers stay semantically neutral.** `price_above_ema` is allowed. `buy_setup` /
   `allow_entry` stay out of Market Analysis and out of DSL helpers (ADR-0006).
6. **`SignalFiringPolicy` stays explicit** on the resolved `SignalModelDefinition`. The DSL
   may default (`ON_EVENT` vs `ON_TRUE_EDGE`) but must not hide the resolved policy.
7. **String timeframes compile to `Timeframe`.** Resolved dependencies keep full temporal
   identity (`computation_timeframe` on the reference).
8. **Compile cost stays definition-sized**, not bar-sized. Re-run
   `bench_authoring_analysis_evaluate.py` if S037 changes `model_authoring/compile.py`;
   `p1_compile` must remain negligible vs `p2` on the fixture (today ~0.2 ms).

### 2.2 Simplification S037 *should* pursue

These are in scope because they reduce authoring friction **without** new language:

- One namespace function per **default** component output authors actually write
  (today: `trend.ema`, `volatility.state`, `structure.higher_low_event`; ATR/true-range
  are missing from the DSL even though they exist in the catalog).
- Shorter imports: authors should reach the common surface from
  `trading_framework.model_authoring` without digging into `references.*`.
- Fewer required kwargs where the component already has a canonical default
  (`period=20` on EMA). Defaults must still round-trip through
  `parameter_schema.canonicalize`.
- Docstrings and catalog documentation that show **one** copy-pasteable model, not IR.

### 2.3 Simplification S037 must *not* pursue

- YAML/JSON model files as a second source of truth (IR serialization already exists).
- Embedding Polars expressions or Python lambdas in models.
- Breaking `authored.expression` inspectability.
- Changing `evaluate_models` / `run_analysis` public contracts to make the DSL nicer.

**Done enough:** a maintainer can add a catalog component and a matching
`trend.foo(...)` (or `structure.` / `volatility.`) reference in one PR, and an author can
write a market + signal model using only `model_authoring` exports, without importing
`model_expression`.

---

## 3. “Library ready”

Catalog today (engine): `volatility.true_range`, `volatility.atr`, `volatility.state`,
`trend.ema`, `structure.swing`. Sprint 007 (slope, wick ratio, distance-to-level, session
range) was **skipped** — those names are candidates, not a mandate.

### 3.1 Every new component PR must include

1. Stable `ComponentId` + `ImplementationId` (ADR-MA-002).
2. Parameter schema with canonicalize + fingerprint.
3. NumPy adapter that passes existing contract tests (determinism, schema, alignment,
   warm-up, lineage — ADR-MA-010).
4. Registration as the default implementation.
5. A `model_authoring` namespace function for the outputs authors will reference
   (or an explicit “internal-only, no DSL” note in the PR).
6. Tests: component behavior + at least one authored model that compiles and evaluates
   on the fixture harness path.

### 3.2 Composition over new primitives

Prefer depending on existing components (`volatility.state` already depends on ATR) over
reimplementing windows. A new Feature that is a thin transform of `price` + one existing
Feature is in scope; a new “mini-language” of combinators is not.

### 3.3 Taxonomy and runtime

- Features / Structures / States stay in Market Analysis (ADR-0005). Strategy intent stays
  in strategy models.
- Until Stage 4, bulk execution is still `AnalysisDataView` + NumPy kernels. Live runtime
  keeps the view adapter (ADR-MA-014). New components must work on that contract.
- Do not add `list[MarketBar]` on bulk compute paths (H4).
- Do not add ML / fitted classifiers (IDEA-014 stays deferred).

### 3.4 PR shape

One coherent catalog outcome per PR (one component or one tight family, e.g. ATR+true-range
DSL references). Target 100–400 meaningful lines. PRs go to `sprint/<s037-slug>`, not `main`.

**Done enough:** S007-class research pieces can land without touching IR, without a
MarketFrame migration, and without a new DSL operator.

---

## 4. Explicit non-goals for S037

- Stage 4 `MarketFrame` migration (ADR-MA-014 authorizes it; it is not S037’s job unless a
  later maintainer decision merges the tracks).
- Stage 3 `available_at` column / lineage sidecar implementation (authorized; separate PRs).
- D-REP-04b `price_nanos` storage; D-REP-06 tz-aware Parquet.
- Re-running S026 Signal/Robustness or S027 import rewrites without a new measurement.
- AI/ML, IDEA-014, Phase 4B/6B/Replay.
- pandas anywhere; `pl.Decimal`.

---

## 5. First S037 Wave 0 questions (not decided here)

S037 Wave 0 still chooses:

1. Sprint slug and integration branch.
2. First catalog slice (S007 leftovers vs whatever the next research experiment needs).
3. Whether DSL namespace fill-in (ATR / true-range references) is Wave 1 or bundled with
   the first new component.

This gate only forbids answering those by inventing IR, waiting for MarketFrame, or treating
compile performance as unknown.

---

## 6. References

- `docs/planning/sprints/SPRINT_036.md` §8
- `docs/planning/sprints/S036_WAVE0_DECISIONS.md` — D-S036-06, D-S036-08
- `docs/reference/DATA_REPRESENTATION_AUDIT.md` §4.3, §6.1, §8
- `docs/adr/ADR-0006-declarative-market-and-signal-models.md`
- `docs/adr/ADR-MA-014-marketframe-polars-committed-bulk-engine.md`
- `docs/planning/sprints/SPRINT_007.md` — skipped catalog candidates
- `docs/planning/IDEA_INBOX.md` — IDEA-014 (deferred)
