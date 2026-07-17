# Sprint 025 - Live Dry-Run Visualization and Portfolio Polish

## Metadata

```text
Sprint: 025
Phase: Phase 8A - BTC Futures Live Dry-Run Execution Demo
Status: PLANNED (OPTIONAL)
Planned Start: TBD
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_024
Sprint Branch: sprint/btc-futures-dry-run-execution
Task branch convention: feat/ | fix/ | docs/ | test/
Architecture Sources:
  - scripts/demo/README.md
  - docs/reference/RESEARCH_METHODOLOGIES.md
  - SPRINT_023.md
  - SPRINT_024.md
```

---

## 0. Slice Choice

This optional sprint improves the presentation layer after the runtime is stable. It should not add new
execution semantics. The goal is to make the portfolio demo easier to understand at a glance.

**Out of scope:** changing the trading strategy, adding real trading, adding authenticated controls,
building a full SaaS dashboard.

---

## 1. Sprint Goal

```text
Live dry-run read model
  -> BTCUSDT chart
  -> simulated entry/exit markers
  -> event timeline
  -> compact architecture narrative
  -> portfolio-ready screenshots
```

Success: the public dashboard shows the live dry-run visually enough that a visitor can understand the
pipeline without reading the repository first.

---

## 2. MVP Scope Checklist

- [ ] Add recent candle history to the read model or API.
- [ ] Render BTCUSDT chart on the live dry-run page.
- [ ] Add simulated fill markers to the chart.
- [ ] Add event timeline for market event -> signal -> order intent -> fill -> position update.
- [ ] Add small architecture diagram linking OVH and AWS responsibilities.
- [ ] Add screenshot guidance for portfolio/recruiter use.
- [ ] Keep all controls read-only.

---

## 3. Presentation Boundary

```text
Dashboard may visualize:
  - recent market bars
  - simulated fills
  - current paper position
  - status and event timeline

Dashboard must not:
  - submit orders
  - modify strategy config
  - restart runtime
  - expose credentials
```

---

## 4. Task Breakdown

| Task | Outcome | Status |
|------|---------|--------|
| S025-T001 | Add recent candle read model/API support | TODO |
| S025-T002 | Add chart rendering on live dry-run page | TODO |
| S025-T003 | Add simulated entry/exit markers | TODO |
| S025-T004 | Add execution event timeline | TODO |
| S025-T005 | Add OVH + AWS architecture diagram/section | TODO |
| S025-T006 | Add portfolio screenshot notes | TODO |
| S025-T007 | Add UI fixture data and smoke checks | TODO |

---

## 5. Acceptance Criteria

1. Chart and markers render from read-only data only.
2. Every marker/fill is labeled simulated.
3. The page remains useful when AWS status is stale or offline.
4. No new write/control endpoint is introduced.
5. Quality checks for touched code/assets pass.

---

## 6. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| UI polish distracts from runtime reliability | Keep Sprint 025 optional and after hardening |
| Chart requires too much historical storage | Limit recent candles and retention |
| Visitors infer strategy profitability | Label strategy as unvalidated demo; show dry-run context |
| Dashboard grows into product UI | Keep read-only portfolio scope |

---

## 7. Post-Sprint Direction

After this sprint, decide whether to move toward Phase 8B Paper Execution contracts or return to
research-side roadmap items. **Sprint 026 (research hot-path performance)** is the recommended
research-track next step if Signal / Market Research or Robustness remain operator-blocking at
NQ half-year scale.
