# Sprint 035 - Next Increment Selection (post public demo)

## Metadata

```text
Sprint: 035
Phase: Planning / track choice
Status: COMPLETED (track choice recorded)
Planned Start: 2026-07-18
Planned End: 2026-07-18
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
| **1 (recommended)** | **Sprint 024 — Dry-run reliability wiring (re-scoped)** | Live paper is the demo crown jewel. Much of original S024 ops docs already shipped in S022; remaining work is **wiring** feed freshness / reconnect / SIGTERM / Live Paper badges onto the Streamlit+AWS stack. | ~3–4 focused PRs | Demo worker unused / always-off |
| 2 | **Docs / recruiter narrative pack** | README + overview already improved; remaining: architecture one-pager, sample-data story. | Small docs PRs | You want product capability, not narrative |
| 3 | **Phase 4B — Orderflow Market Analysis** | Unlocks trades-based research depth already imported (Sprint 011). | Large research track | Demo reliability still ambiguous on Live Paper |
| 4 | **Phase 6B — Multi-data Strategy Research** | Extends strategy beyond OHLCV. | Large | 6A + robustness already sellable |
| 5 | **Phase 8 Replay foundation** | Roadmap §12 long-term; distinct from current AWS live dry-run. | Large greenfield | Paper dry-run path already covers “execution-shaped” demo |
| 6 | **PBO / CSCV / deflated Sharpe** | Robustness science credibility. | Needs separate ADR first | Methodology without ADR |

**Explicitly not next by default:** more dashboard cosmetics (S033–S034 + follow-ups #261–#264 closed the public-demo loop).

**Do not resume original S024 checklist as-written** — it targeted the OVH portfolio UI and re-listed S022 deliverables as TODO. See re-scoped `SPRINT_024.md` (2026-07-18 audit).

---

## 3. Recommended default — Sprint 024 (re-scoped)

Resume **`SPRINT_024.md` as re-scoped on 2026-07-18** (not the original pre-dashboard draft):

```text
AWS worker + status API + Streamlit Live Paper
  -> feed freshness ≠ process heartbeat
  -> reconnect / last_error on status snapshot
  -> SIGTERM/SIGINT → STOPPED/FAILED
  -> Live Paper RuntimeHealth badges
  -> DynamoDB retention + failure-mode tests
```

Already done elsewhere (do not rebuild): CloudWatch heartbeat alarm spec, operator runbook,
cost/schedule modes (`AWS_BTC_FUTURES_DRY_RUN.md`, Sprint 022).

Suggested PR waves into `sprint/dry-run-reliability-polish`:

1. Worker feed freshness + SIGTERM/SIGINT + tests  
2. Status snapshot: reconnect / last_error / health  
3. Live Paper badges driven by those fields  
4. Retention policy + runbook addendum (+ optional architecture page)

Do **not** reopen dashboard shell work unless required by status-state UX.

---

## 4. Wave 0 decision checklist

Before coding:

- [x] Confirm track: **S024** executed; next track = **S036 research infra audit** (then S037 DSL/components; AI/ML later)  
- [x] Confirm sprint integration branch name: `sprint/dry-run-reliability-polish` (S024); next `sprint/research-infra-audit` (S036)  
- [x] Confirm AWS worker may stay running (or scheduled) during S024 — done  
- [x] Confirm out of scope for S024: real orders, multi-symbol portfolio, UI redesign  

---

## 5. Acceptance (for this planning sprint)

1. `CURRENT_STATUS.md` reflects post-S034 public demo complete and lists ranked next options.  
2. This file exists and names a default recommendation.  
3. Maintainer picks one option; implementation continues under that sprint’s file (S024 or a new sprint), not as an unbounded backlog.

**Decision (2026-07-18):** Execute S024 first (done → main #270). Next implementation track is **S036** (infra audit), then **S037** (component libraries + DSL simplification), then AI/ML — not 4B/6B/Replay by default.

---

## 6. Status

```text
S035-T001  Draft next-increment options     DONE
S035-T002  Maintainer track choice          DONE (S024 then S036→S037→AI/ML)
S035-T003  Open sprint branch for choice    DONE (S024); S036 branch at Wave 0 of SPRINT_036
```
