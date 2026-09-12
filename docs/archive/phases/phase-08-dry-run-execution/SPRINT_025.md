# Sprint 025 - Streamlit Dashboard Polish and VPS Publish

## Metadata

```text
Sprint: 025
Phase: Phase 8A + Dashboard Application
Status: COMPLETE on main (2026-07-18)
Planned Start: 2026-07-18
Planned End: 2026-07-18
Sprint Goal Owner: Project Maintainer
Depends On: SPRINT_028, SPRINT_031, SPRINT_032 (on main); AWS dry-run already on main (#199)
Sprint Branch: sprint/dashboard-streamlit-polish
Task branch convention: feat/ | fix/ | docs/ | test/
Architecture Sources:
  - apps/dashboard/docs/RUNBOOK.md
  - docs/reference/DASHBOARD_APPLICATION.md
  - SPRINT_028.md
  - SPRINT_031.md
```

---

## 0. Slice Choice (updated 2026-07-18)

**Original S025** targeted HTML / `portfolio_live` visualization polish.

**Current direction:** presentation polish is **`apps/dashboard` (Streamlit)**, then
**publish that app to the VPS**. Legacy HTML demo artifacts and the OVH aiohttp
`portfolio_live` server are not the polish target.

```text
AWS dry-run (worker + status API)  — already on main
  → Streamlit apps/dashboard (research + Live Paper)
  → visual polish
  → VPS deploy (Compose + Caddy, read-only storage)
```

**Out of scope:** HTML report redesign, new strategy features, real trading,
authenticated start/stop of the AWS worker from the UI.

---

## 1. Sprint Goal

```text
apps/dashboard Streamlit
  -> clearer Live Paper + research pages
  -> chart / markers / timeline where data already exists
  -> VPS runbook + deploy of the Streamlit stack
```

Success: an operator can open the VPS dashboard, see research runs and live paper
status without reading the repo, and everything stays read-only.

---

## 2. MVP Scope Checklist

- [x] Polish Streamlit Live Paper page (layout, empty/stale states, refresh UX).
- [x] Polish research pages (Overview / Strategy / Robustness) for readability.
- [x] Add or improve Live Paper chart/markers from status `recent_bars` / fills when useful.
- [x] Keep all controls read-only (no worker start/stop, no orders).
- [x] Refresh `apps/dashboard/docs/RUNBOOK.md` for VPS publish (Compose, env, status URL).
- [x] Deploy / verify Streamlit dashboard on the VPS (Compose stack live; CI/CD wired).
- [x] Public HTTPS via shared VPS edge (`dashboard.filipf.online` → host `:8080`).
- [ ] Mount / sync read-only `user_data` on VPS (deferred — follow-up, not blocking S025).
- [x] Document that HTML / `portfolio_live` are legacy relative to Streamlit.
- [x] Wire GitHub Actions → VPS deploy for `apps/dashboard/**` on `main`.

---

## 3. Presentation Boundary

```text
Dashboard may visualize:
  - research artifacts under mounted storage
  - live paper status from GET status URL
  - recent bars / fills / events from that payload

Dashboard must not:
  - submit orders
  - modify strategy config
  - restart the AWS worker
  - expose credentials
```

---

## 4. Task Breakdown

| Task | Outcome | Status |
|------|---------|--------|
| S025-T001 | Live Paper Streamlit UX polish | DONE |
| S025-T002 | Research pages readability polish | DONE |
| S025-T003 | Optional Live Paper chart from `recent_bars` | DONE |
| S025-T004 | VPS runbook update for Streamlit + status URL | DONE |
| S025-T005 | VPS deploy / verify Compose stack | DONE |
| S025-T006 | Mark HTML / portfolio_live as legacy in docs | DONE |
| S025-T007 | GitHub Actions SSH deploy for dashboard on main | DONE |
| S025-T008 | Shared VPS edge TLS (`/opt/edge`) for public hostname | DONE (ops; outside this repo) |
| S025-T009 | Read-only `user_data` mount on VPS | DEFERRED |

---

## 5. Acceptance Criteria

1. Streamlit on VPS shows research catalog and Live Paper status.
2. Stale/offline AWS status is handled with a clear message (no crash).
3. No new write/control endpoint is introduced.
4. Quality checks for touched code pass.

---

## 6. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Polish expands into a product UI | Keep read-only; no auth control plane |
| Confusing HTML vs Streamlit | Explicit legacy note; VPS serves Streamlit |
| AWS status URL changes | Keep `DEFAULT_LIVE_PAPER_STATUS_URL` + env override |

---

## 7. Post-Sprint Direction

Sprint 025 is complete on main for Streamlit polish, VPS Compose, CI/CD, and public
HTTPS via a shared edge proxy.

Deferred follow-up: mount/sync read-only `user_data` for research catalog pages.

Next capability choices: Phase 8B paper-execution contracts, S024 reliability
hardening, or research-track work (e.g. Phase 4B).
