# Sprint 035 - Next Increment Selection (post public demo)

## Metadata

```text
Sprint: 035
Phase: Planning / track choice
Status: PLANNED
Planned Start: 2026-07-18
Planned End: TBD (Wave 0 decision only, then execute chosen track)
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_034 (on main); public demo live at dashboard.filipf.online
Sprint Branch: (none until track chosen — then sprint/<slug> per workflow)
Task branch convention: feat/ | fix/ | docs/ | test/
Architecture Sources:
  - docs/planning/CURRENT_STATUS.md
  - docs/planning/ROADMAP.md §11–§12
  - docs/planning/sprints/SPRINT_024.md
```

---

## 0. Context

Sprints 028–034 delivered a public Streamlit dashboard, VPS CI/CD, presentation polish,
and recruiter-facing overview (English copy, workflow diagrams, Lightweight Charts OHLCV,
README dashboard link).

There is **no active implementation sprint**. This document records the ranked options for
the next coherent increment and a default recommendation.

---

## 1. Goal

```text
Choose one next capability track
  -> open or resume the matching sprint branch
  -> deliver one reviewable outcome stream (not a mega-sprint)
```

---

## 2. Ranked options

| Rank | Option | Why now | Effort shape | Defer if… |
|------|--------|---------|--------------|-----------|
| **1 (recommended)** | **Sprint 024 — Dry-run reliability / operating polish** | Live paper is the public demo crown jewel; recruiters see AWS status. Failures should be visible (stale feed vs heartbeat, STOPPED, alarms, runbook). | Ops + runtime + dashboard status states; ~1–2 weeks of focused PRs | Demo worker is unused / cost-sensitive and always-off |
| 2 | **Docs / recruiter narrative pack** | README + overview already improved; remaining gaps are methodology deep-links, architecture one-pager, sample-data story. | Small docs PRs only | You want product capability, not narrative |
| 3 | **Phase 4B — Orderflow Market Analysis** | Unlocks trades-based research depth already imported (Sprint 011). | Large research track; new contracts + components | Demo reliability is still fragile |
| 4 | **Phase 6B — Multi-data Strategy Research** | Extends strategy beyond OHLCV. | Large; depends on clearer multi-dataset research contracts | 6A + robustness already sellable |
| 5 | **Phase 8 Replay foundation** | Roadmap §12 long-term; distinct from current AWS live dry-run. | Large greenfield | Paper dry-run path already covers “execution-shaped” demo |
| 6 | **PBO / CSCV / deflated Sharpe** | Robustness science credibility. | Needs separate ADR first | Methodology sprint without ADR |

**Explicitly not next by default:** more dashboard cosmetics (S033–S034 + follow-ups #261–#264 closed the public-demo loop).

---

## 3. Recommended default — Sprint 024

Resume **`SPRINT_024.md`** as written:

```text
AWS dry-run worker
  -> feed freshness ≠ process heartbeat
  -> graceful STOPPED
  -> reconnect / last-error visibility
  -> CloudWatch alarm plan
  -> operator runbook
  -> dashboard status states aligned
```

Suggested PR waves (into `sprint/dry-run-reliability-polish` or revive historical sprint branch naming per current workflow):

1. Feed freshness + graceful shutdown contracts/tests  
2. Metrics / last-error surface on status API  
3. Dashboard Live Paper status vocabulary (RUNNING / DEGRADED / STALE / STOPPED / FAILED)  
4. Runbook + CloudWatch alarm docs + retention note  

Do **not** reopen dashboard shell work unless required by status-state UX.

---

## 4. Wave 0 decision checklist

Before coding:

- [ ] Confirm track: **S024** (default) / docs pack / 4B / other  
- [ ] Confirm sprint integration branch name  
- [ ] Confirm AWS worker may stay running (or scheduled) during the sprint  
- [ ] Confirm out of scope: real orders, multi-symbol portfolio, UI redesign  

---

## 5. Acceptance (for this planning sprint)

1. `CURRENT_STATUS.md` reflects post-S034 public demo complete and lists ranked next options.  
2. This file exists and names a default recommendation.  
3. Maintainer picks one option; implementation continues under that sprint’s file (S024 or a new sprint), not as an unbounded backlog.

---

## 6. Status

```text
S035-T001  Draft next-increment options     DONE (this file)
S035-T002  Maintainer track choice          TODO
S035-T003  Open sprint branch for choice    TODO
```
