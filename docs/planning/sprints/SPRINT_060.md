# Sprint 060: Signal Quality Portfolio Evidence (Phase 16, increment 16D)

Status: OPEN — the maintainer approved Decisions D060-01 and D060-03 at
sprint opening (2026-09-09); D060-02 was already inherited from the
accepted Sprint 059 / DASHBOARD_DEVELOPMENT_DIRECTION.md direction. T001 is
Done (field inventory frozen, one STOP-and-report finding resolved); T002
is Done; T003 (study view + charts, consuming a real committed
public-projection bundle) is In review; T004 is Ready.
Goal: Deliver the first complete portfolio story from Signal/Predictive
Research context through living methodology and the BTC Signal Quality study
to simplified persisted evidence and the existing technical view.
Sources:

- `docs/planning/DASHBOARD_DEVELOPMENT_DIRECTION.md` — authoritative product
  direction for 16D.
- `docs/product/PRD-portfolio-dashboard-mvp.md` — feature requirements;
  ACCEPTED (maintainer, 2026-09-09).
- `docs/planning/sprints/SPRINT_059.md` — publication, content and routing
  contracts (Done; merged to `main` via #490).
- `docs/adr/ADR-0034-portfolio-publication-boundary.md` — the accepted
  publication boundary this sprint consumes without amending.
- `docs/reference/BTC_SIGNAL_QUALITY_STUDY.md` — as-built result and artifact
  inventory source.
- `docs/reference/PREDICTIVE_VERDICT.md` and ADR-0032 — verdict semantics and
  display restrictions.
- ADR-0033 — score delivery boundary; consumed, not changed.
- `docs/planning/sprints/SPRINT_060_T001_FIELD_INVENTORY.md` — the frozen
  artifact-to-public-field inventory T003 implements verbatim.
- `scripts/dashboard/generate_btc_signal_quality_projection.py` — the
  build-time generator; its output,
  `apps/dashboard/publication_data/projection.json`, is committed per the
  maintainer's Sprint 060 T003 decision.
- `docs/planning/sprints/SPRINT_060_T001_FIELD_INVENTORY.md` — T001's frozen
  artifact-to-public-field inventory and the STOP-and-report resolution
  below.

Architecture triage: inherits the accepted Sprint 059 publication boundary.
Any need to change a persisted research schema, verdict semantics or
cross-workflow lineage is a STOP-and-report finding, not an implementation
detail.

**T001 STOP-and-report, resolved (maintainer, 2026-09-09):** the "rejected
winners and losers" fact (D060-01 chart 3; the acceptance criterion "two
rejected occurrences (one winner, one loser)") and the Strategy Research
score-gate threshold are not persisted in any JSON/parquet artifact — only
as prose in `docs/reference/BTC_SIGNAL_QUALITY_STUDY.md` §6. These facts
are sourced as reviewed narrative content through `dashboard_app.content`
(T002), never computed by the dashboard or added as a new research-layer
artifact this sprint. See `SPRINT_060_T001_FIELD_INVENTORY.md` for the full
resolution and the three new `publication/` sanitizer roles T003 adds.

## Scope

In scope:

- Accessible Signal Research and Predictive Research context that preserves
  their independence and explains how they share stable domain objects.
- A living, public-friendly Signal Quality methodology page that links to
  canonical technical references and does not interpret an individual run.
- A stable BTC Signal Quality study page answering: what was studied, against
  what baseline/assumptions, what result was persisted, and what limitations
  or warnings were persisted.
- Two or three charts built only from allowlisted, persisted Phase 16C facts.
- Explicit presentation of the persisted `INCONCLUSIVE` verdict and the
  negative baseline-versus-score-filtered result.
- One-action links from the study to methodology and `Explore Evidence`.
- Desktop visual QA and a maintainer-observed acceptance walkthrough.

Out of scope:

- New research, changed thresholds, a new verdict, artifact interpretation or
  dashboard-side metric derivation.
- A full catalog replacement or simplified result views for other workflows.
- Notes, Engineering, Future Direction, live-session history or any control
  surface.
- PnL marketing, market commentary, forecasts, trade ideas or claims of a live
  edge.

## Decisions

| Decision | Recommendation and rationale | Status |
|---|---|---|
| D060-01 — chart set | Use: (1) model versus random-permutation ROC AUC across persisted folds, (2) threshold sensitivity emphasizing coverage collapse, and (3) baseline-versus-scored trade disposition including rejected winners and losers. PnL may appear as a neutral supporting fact, not the hero chart. This set explains stability, threshold risk and downstream usefulness without inventing analysis. | Accepted (maintainer, 2026-09-09) |
| D060-02 — workflow narrative | Present Signal Research, Predictive Research and Strategy Research as separate processes connected only by explicit persisted inputs/outputs in this study. Do not show a synthetic end-to-end artifact lineage. | Inherited from accepted direction |
| D060-03 — result language | Use the persisted verdict verbatim and neutral explanatory definitions. The study page may state that the score did not meaningfully filter this strategy because that finding is already persisted in the canonical study evidence; it must not generate a new conclusion from chart values. | Accepted (maintainer, 2026-09-09) |

## Tasks

| Task | Outcome | Dependencies | Ownership | Risk | Status | PR |
|---|---|---|---|---|---|---|
| T001 | Freeze the exact Phase 16C artifact-to-public-field inventory for the four study questions and three recommended charts; report any missing fact instead of deriving it | Sprint 059; real 16C artifacts available | dashboard publication contract + documentation | high | Done | [#491](https://github.com/folg-code/research-trading-framework/pull/491) |
| T002 | Author and review the Signal/Predictive workflow context and living Signal Quality methodology content, with links to canonical references and no run-specific interpretation | T001; Sprint 059 content contract | `apps/dashboard` content + methodology review | standard | Done | [#492](https://github.com/folg-code/research-trading-framework/pull/492) |
| T003 | Implement the simplified study view and its three persisted-fact charts with neutral metric definitions, explicit assumptions, warnings and unavailable-state behavior | T001, T002 | `apps/dashboard` study view/charts | high | In review | pending |
| T004 | Connect stable overview, workflow, methodology and study routes; add one-action `Explore Evidence` navigation to the existing Predictive and Strategy Research details without duplicating them | T003 | `apps/dashboard` navigation/evidence integration | standard | Ready | — |
| T005 | Add contract and regression tests for traceability, negative/`INCONCLUSIVE` evidence, absent optional artifacts, no dashboard-side verdict/metric logic and unchanged technical/live-paper surfaces | T003, T004 | dashboard tests | high | Gated | — |
| T006 | Run desktop visual QA and the maintainer-observed success walkthrough; reconcile dashboard/reference/planning docs and record remaining portfolio outcomes outside this PRD | T002–T005 | visual acceptance + documentation | standard | Gated | — |

## Acceptance criteria

- A visitor can reach the BTC Signal Quality study from the overview in no
  more than three navigation actions; methodology and `Explore Evidence` are
  each one action from the study.
- The page visibly answers all four study questions and shows two or three
  charts whose fields trace to the accepted public projection.
- The persisted `INCONCLUSIVE` verdict, two rejected occurrences (one winner,
  one loser) and effectively unchanged downstream result remain visible.
- No chart or component implements a new research metric, threshold,
  classification, verdict or fallback conclusion.
- Methodology explains the current method and links to technical references;
  it contains no hand-authored conclusion about this artifact.
- A general software developer can explain the project purpose, shared-domain
  advantage, at least two independent workflows and the evidence path during
  the acceptance walkthrough.
- At a representative desktop viewport, the study summary and primary charts
  are understandable without opening raw artifact tables.
- Existing technical evidence and current-only Live Paper behavior pass their
  targeted regression tests.

## Integration risks

- Dual-axis or dense charts could make the result harder to read. Prefer small
  multiples or separate panels when threshold coverage and hit rate cannot be
  shown clearly together.
- The negative result could be softened into portfolio marketing. Preserve the
  canonical evidence language and show limitations next to the charts.
- Deep links into existing pages may depend on transient widget state. The
  accepted Sprint 059 routing contract governs; do not add saved UI state.
- Real artifacts may omit a desired field. Reduce the chart set or show an
  explicit unavailable state; do not compute a substitute.

## Closeout

- Integrated checks: pending
- Documentation reconciliation: pending
- Review: pending
- Remaining work: full catalog grouping and the other workflow/content
  surfaces remain later outcomes under the accepted direction
