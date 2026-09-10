# Sprint 060: Signal Quality Portfolio Evidence (Phase 16, increment 16D)

Status: COMPLETED — 6/6 tasks Done, integrated to `main` via #498
(2026-09-10). The maintainer approved Decisions D060-01 and D060-03 at
sprint opening (2026-09-09); D060-02 was already inherited from the
accepted Sprint 059 / DASHBOARD_DEVELOPMENT_DIRECTION.md direction.
T001 is Done (field inventory frozen, one STOP-and-report finding
resolved, #491); T002 is Done (#492); T003 (study view + charts, consuming
a real committed public-projection bundle) is Done (#493); T004 (routing
and `Explore Evidence` navigation) is Done (#494); T005
(contract/regression tests) is Done (#495); T006 (visual QA, maintainer
walkthrough, doc reconciliation) is Done (#496). Two post-review fixes
(#499, #500 — see §Closeout) landed on the sprint branch before the final
integration PR (#498) merged to `main`.
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
| T003 | Implement the simplified study view and its three persisted-fact charts with neutral metric definitions, explicit assumptions, warnings and unavailable-state behavior | T001, T002 | `apps/dashboard` study view/charts | high | Done | [#493](https://github.com/folg-code/research-trading-framework/pull/493) |
| T004 | Connect stable overview, workflow, methodology and study routes; add one-action `Explore Evidence` navigation to the existing Predictive and Strategy Research details without duplicating them | T003 | `apps/dashboard` navigation/evidence integration | standard | Done | [#494](https://github.com/folg-code/research-trading-framework/pull/494) |
| T005 | Add contract and regression tests for traceability, negative/`INCONCLUSIVE` evidence, absent optional artifacts, no dashboard-side verdict/metric logic and unchanged technical/live-paper surfaces | T003, T004 | dashboard tests | high | Done | [#495](https://github.com/folg-code/research-trading-framework/pull/495) |
| T006 | Run desktop visual QA and the maintainer-observed success walkthrough; reconcile dashboard/reference/planning docs and record remaining portfolio outcomes outside this PRD | T002–T005 | visual acceptance + documentation | standard | Done | [#496](https://github.com/folg-code/research-trading-framework/pull/496) |

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

- Integrated checks: `apps/dashboard` full suite (189 tests, includes
  `test_navigation_acceptance.py` and `test_study_contract.py`) and
  `tests/unit/test_apps_boundaries.py` (6 tests) pass together on the
  integrated sprint branch, including from the repo root with CI's exact
  invocation (`uv run --package trading-dashboard pytest
  apps/dashboard/tests -q`); `ruff check` and `ruff format --check` are
  clean for every file this sprint touched. `cd apps/dashboard && uv run
  mypy .` (PRB-023's own documented command) reports 42 pre-existing
  errors in 17 files — none in any file this sprint added
  (`views/study.py`, `views/portfolio_content.py`, the extended
  `publication/*.py`, `contracts.py`, `scripts/dashboard/*.py`, or any new
  test file). `charts/builders.py`, which this sprint extended with three
  new chart-builder functions, is the one touched file among the 17: its 2
  errors are `import-untyped` for the file's pre-existing top-of-file
  `plotly`/`plotly.subplots` imports (dating to Sprint 028), not anything
  this sprint added. The same `plotly` import-untyped class recurs,
  pre-existing and unrelated, in `charts/overlays.py`,
  `views/live_paper.py` and `pages/2_Market_and_Signal_Research.py`; the
  remaining ~37 errors are unrelated typing issues (untyped `pyarrow`
  calls in tests, unreachable statements, type mismatches) all logged
  under PRB-023, which this sprint leaves OPEN and unchanged.
- Documentation reconciliation: `docs/reference/modules/DASHBOARD_APPLICATION.md`
  gained a "BTC Signal Quality study and evidence path (Sprint 060)"
  section documenting the three additive sanitizer roles, the committed
  generator output, `views.study`/`views.portfolio_content`, and the
  section-by-section fail-closed behavior; `docs/reference/system/MODULE_MAP.md`
  lists the new `views/study.py`, `views/portfolio_content.py`,
  `pages/7-9_*.py` and `scripts/dashboard/` entries.
- Review: T001–T006 each went through independent review in a fresh
  context per `.claude/WORKFLOW.md`, with fix-and-re-review round-trips on
  T005 (a cross-test monkeypatch leak and a silently-ambiguous
  artifact-role resolution in a traceability test) and T006 (two factual
  inaccuracies in this Closeout's own first draft: an overclaimed "mypy
  clean" scope, and an ADR-0034 Follow-up item that ADR-0034 does not
  actually list) before each merged. A sprint-close integration review of
  the complete assembled diff (`sprint/signal-quality-portfolio-evidence`
  → `main`) additionally caught a third mypy-count inaccuracy in this same
  paragraph (corrected above to the exact PRB-023-documented command and
  count) and PRB-024 (above); it separately surfaced that CI's own
  "Dashboard tests" job -- run from the repo root, not `apps/dashboard` --
  had been failing since Sprint 059 merged (#490) due to `AppTest.from_file`
  resolving relative paths against the invocation directory; fixed by
  resolving to an absolute path in both affected acceptance-test files.
  The maintainer additionally walked the rendered path locally
  (`streamlit run apps/dashboard/Project_Overview.py`) on 2026-09-09 —
  Overview → Signal Quality Workflow → Signal Quality Methodology → BTC
  Signal Quality Study in three clicks, the persisted `INCONCLUSIVE`
  verdict and all three charts, `Explore Evidence` opening the real
  Predictive Research page, and the existing technical pages (spot-checked
  via Strategy Research) behaving exactly as before — and accepted it
  ("jest ok").
- Remaining work explicitly outside this PRD, per ADR-0034's own
  `## Follow-up` section: migrating the remaining technical pages
  (`pages/1-6_*.py`) onto the projection and removing `storage_path` from
  their rendered output ("Catalog migration"); reconciling the
  automatic-inclusion catalog model in
  `DASHBOARD_DEVELOPMENT_DIRECTION.md` §8 with the curated/immutable
  publication model in `RESEARCH_APPLICATION_PRODUCT_VISION.md`
  ("Visibility model reconciliation"); deciding and documenting where
  projection generation runs at deploy time, local pre-step vs. CI,
  before the first public deployment of this path ("Deploy wiring").
  Separately, and not an ADR-0034 Follow-up item — a sprint-scope note
  only: this sprint ships exactly one study behind one hand-authored
  manifest; a second study or a generalized multi-study catalog is future
  work this sprint did not attempt. **PRB-023** (root `mypy`/`pytest`
  never checking `apps/dashboard/` or `scripts/`) remains logged as OPEN
  in `docs/planning/PROBLEM_REGISTRY.md`, unchanged by this sprint. The
  sprint-close integration review additionally found and logged
  **PRB-024** (`scripts/dashboard/` -- the generator script ADR-0034 §1.2
  requires to be library-free -- is not covered by any automated
  import-boundary scan, only manual review); confirmed not an active
  violation today, logged OPEN for a future task.
