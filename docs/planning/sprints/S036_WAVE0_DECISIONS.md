# Sprint 036 — Wave 0 Decisions

Binding decisions for Research Infra Audit. Date: 2026-07-18.

Basis: maintainer track (infra audit → DSL/components → AI/ML), `SPRINT_036.md`,
prior S026/S027 performance work, and a path inventory of authoring → research code.

---

## D-S036-01 — Problem statement

Before expanding component libraries or simplifying `model_authoring/`, we need a **measured**
map of where wall time and memory go on the authoring → analysis → research path.

S026 repaid Signal/Robustness post-evaluation hot paths. S027 repaid import / continuous-build
paths. This sprint audits what those did **not** cover: compile cost, Market Analysis DAG/
frame assembly at authoring scale, shared `evaluate_models`, and research/storage read patterns
that will grow with a larger component catalog.

---

## D-S036-02 — Path inventory (authoring → research)

| ID | Path | Key modules | Entrypoints | Prior perf | Audit priority |
|----|------|-------------|-------------|------------|----------------|
| P1 | DSL compile → IR | `model_authoring/` (`market_model`, `signal_model`, `compile`, `conditions`); `model_expression/validation` | Unit: `tests/unit/model_authoring/`; spikes under `tests/spike/run_inspect_declarative_models.py` | None dedicated | MEDIUM — expect cheap; measure so S037 does not guess |
| P2 | Market Analysis DAG / execute / frame | `application/market_analysis/run_analysis.py`, `load_data_view.py`; `market_analysis/planning/`, `execution/executor.py`, `assembly/frame.py`, `registry/` | App: `run_analysis`; spike: `tests/spike/run_market_analysis_backend_benchmark.py` | MA backend spike exists; not S026 | **HIGH** — catalog growth multiplies DAG work |
| P3 | Shared model evaluation | `application/model_evaluation/evaluate_models.py`; `model_expression/evaluation/`; market/signal evaluators | Used by signal + strategy research | S026 shares this path; do not regress | **HIGH** — shared by most research |
| P4 | Signal / Market research | `application/signal_research/run_signal_research.py` (+ family, analyze, persist); occurrence / forward outcomes | CLI: `scripts/signal_research/run_signal_research.py`, `run_model_family.py` | **S026 Wave A repaid** | LOW for re-optimize; verify still healthy |
| P5 | Strategy research loop | `application/strategy_research/run_strategy_research.py`; simulation compile | CLI: `scripts/strategy_research/run_strategy_research.py` | ~6 s NQ baseline documented in S026 | LOW — reference only |
| P6 | Robustness loops | `application/robustness_research/run_robustness_experiment.py` | CLI: `scripts/robustness_research/*` | **S026 Wave B repaid** | LOW; skip unless audit finds regression |
| P7 | Storage / Parquet reads | market dataset repos; research parquet writers/readers; dashboard DuckDB queries | Research CLIs; `apps/dashboard` query layer | S027 ingest; dashboard separate | MEDIUM — only if authoring benches show I/O |

**Hypothesis (pre-measurement):** P2 + P3 dominate when component graphs grow; P1 stays small;
P4–P6 should not be the first optimization targets unless benches contradict S026.

---

## D-S036-03 — Existing harnesses to reuse

| Asset | Role in S036 |
|-------|----------------|
| `tests/spike/run_market_analysis_backend_benchmark.py` | Starting point for P2 wall/memory timings (synthetic bars) |
| `scripts/ops/bench_contract_chunk_columns.py` | S027 import microbench — **out of primary scope**; cite only if P7 needs ingest context |
| S026 fixture equivalence tests | Correctness gate pattern for any optimization PR |

**Decision:** Wave 1 adds a **fixture-first** authoring→analysis→evaluate microbench (documented
command), extending or wrapping the MA spike rather than inventing a second unrelated harness
family. Optional local NQ scale remains operator-only (no proprietary data in repo).

---

## D-S036-04 — Correctness gate

Same rule as S026:

- Optimizations must preserve research facts on fixtures (identical outputs; no silent schema drift).
- Public contracts (`run_analysis`, `evaluate_models`, research envelopes) unchanged unless ADR.
- Prefer measurement + small PR over speculative rewrite.

---

## D-S036-05 — Sprint branch and PR base

```text
Integration branch: sprint/research-infra-audit
Working branches:   docs/ | bench/ | feat/ | fix/  (not nested under sprint/)
PR base:            sprint/research-infra-audit  (never main until sprint integration)
```

---

## D-S036-06 — Out of scope (Wave 0 / this sprint)

- DSL API redesign or new language features (→ S037)
- Large new catalog components (→ S037)
- AI/ML / IDEA-014 promotion
- Phase 4B / 6B / Replay
- Re-running S026 Signal or Robustness rewrites without regression evidence
- Distributed / multi-machine infra
- TD-003 full `market_analysis/` reorg unless a HIGH finding requires a minimal layout change

---

## D-S036-07 — Success metrics for the audit

The audit write-up (S036-T003) must answer:

1. Ranked bottlenecks with measured wall time (and memory when relevant) on the fixture harness.
2. Explicit **non-goals** (paths we will not touch).
3. Top 1–2 optimization candidates for Waves 3–4 (or “none — proceed to S037”).
4. Gate criteria draft for S037 (what “DSL simple enough” / “library ready” mean) — finalized in T006.

---

## D-S036-08 — Follow-on ownership

| Sprint | Owns |
|--------|------|
| **036** | Inventory, benches, audit doc, ≤2 justified optimizations, S037 gate doc |
| **037** | Component libraries + maximal DSL simplification |
| Later | AI/ML research (IDEA-014) |

---

## Wave 0 checklist status

- [x] Confirm sprint branch: `sprint/research-infra-audit`
- [x] List entrypoint scripts / modules for inventoried paths (D-S036-02)
- [x] Agree fixture dataset(s) for benches: synthetic / repo fixtures first; optional local NQ
- [x] Agree identical-facts rule (D-S036-04)
- [x] Confirm S037 owns DSL + component libraries (D-S036-08)
- [x] Confirm AI/ML deferred (D-S036-06)
