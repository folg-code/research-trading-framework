# Sprint 029 — Wave 0 Decisions

Binding decisions for Repository Layout Foundations. Date: 2026-07-18.

Source: maintainer plan “Restrukturyzacja repo — rekomendacja i plan”
(A + selective B; defer C and `packages/`).

---

## D-S029-01 — Track choice

**Decision:** Active sprint is **Repository Layout Foundations**, not Phase 4B
orderflow, not Phase 8A polish, and not a deep `src/trading_framework/` reorg.

Sprint 028 dashboard remains the product path for research inspection; this
sprint only makes the **repository shape** match that reality.

---

## D-S029-02 — Scope = A + selective B

**Decision:** Deliver:

1. Top-level layout ADR + documentation sync + artifact hygiene.
2. uv workspace linking root ↔ `apps/dashboard` + formal apps import boundary.
3. Ops path consolidation (`deploy/local_aws_runbook/`) + `scripts/` index.

**Do not** deliver:

- `packages/` (shared contracts package),
- deep domain package reshuffles under `src/trading_framework/`.

---

## D-S029-03 — Apps tier is first-class

**Decision:** `apps/*` is a documented top-level tier for deployable consumers
outside the modular monolith package. Rules generalize D-S028-06:

Forbidden imports from any `apps/*` package:

```text
trading_framework.research
trading_framework.application.strategy_research
trading_framework.application.robustness_research
trading_framework.execution
trading_framework.infrastructure.providers
trading_framework.infrastructure.importers
```

Allowed: mounted storage roots, presentation-local contracts, DuckDB/Polars/
PyArrow/Streamlit/Plotly (or other UI/query deps local to the app).

Dashboard deploy stays co-located at `apps/dashboard/deploy/` (not under root
`deploy/aws/`).

---

## D-S029-04 — Defer `packages/` and deep src reorg

**Decision:**

- Extract `packages/dashboard_contracts` (or similar) only when a **second**
  consumer needs the same presentation DTOs as `apps/dashboard`.
- Repay TD-003 (`market_analysis/` minimal structure) when Phase 4B/4C starts
  or navigation pain is demonstrated — not in Sprint 029.

---

## D-S029-05 — Generated artifacts out of docs/

**Decision:** Standalone HTML research reports must not live under
`docs/reference/`. Generate them into `artifacts/demo/output/` (or ephemeral paths) via
`scripts/demo/`. Documentation links to generation instructions, not committed
multi-MB HTML.

---

## D-S029-06 — Deploy vs scripts

**Decision:**

```text
deploy/                  containers + infra-as-code + local AWS runbook home
scripts/                 thin CLIs over application use cases
apps/<name>/deploy/      app-specific Compose/Docker (co-located)
```

Root `local_aws_runbook/` is superseded by `deploy/local_aws_runbook/` (content
remains gitignored except a tracked README).

---

## Wave map

| Wave | Outcome |
|------|---------|
| 1 | ADR-0022 + vision/MODULE_MAP/guide sync + HTML/architecture hygiene |
| 2 | uv workspace + apps boundary test + CI dashboard tests |
| 3 | deploy/local_aws_runbook README + scripts/README index |

PR policy: one coherent outcome per working PR into `sprint/repo-layout`.
