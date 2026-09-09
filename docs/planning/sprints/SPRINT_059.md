# Sprint 059: Portfolio Publication Foundation (Phase 16, increment 16D)

Status: OPEN — the maintainer approved
`docs/product/PRD-portfolio-dashboard-mvp.md` and Decisions D059-01 through
D059-04 at sprint opening (2026-09-09). T001 recorded those decisions in
ADR-0034, which the maintainer accepted as drafted on 2026-09-09; T002–T006
are Ready.
Goal: Establish the safe publication, content and navigation foundation for a
public portfolio dashboard, then ship an overview that explains the product,
shared domain architecture and six independent workflows.
Sources:

- `docs/planning/DASHBOARD_DEVELOPMENT_DIRECTION.md` — authoritative product
  direction for 16D.
- `docs/product/PRD-portfolio-dashboard-mvp.md` — feature requirements;
  ACCEPTED (maintainer, 2026-09-09).
- `docs/planning/roadmap/PHASE_16_QUANT_WORKBENCH.md` §13H.4.
- `docs/adr/ADR-0022-repository-top-level-layout.md` — dashboard application
  boundary.
- `docs/adr/ADR-0034-portfolio-publication-boundary.md` — D059-01–D059-04 as
  recorded by T001 (ACCEPTED; T002–T006 consume it).
- `docs/reference/modules/DASHBOARD_APPLICATION.md` — current contracts and
  publication path.
- `docs/vision/PRODUCT_DIRECTION.md` — workflow independence and shared-domain
  foundation.

Architecture triage: Decisions D059-01 through D059-04 below are approved and
are now recorded in ADR-0034, which extends ADR-0022 rather than amending it.
ADR-0034 carries an explicit maintainer acceptance statement (2026-09-09);
implementation tasks T002–T006 are Ready.

## Scope

In scope:

- A versioned, deny-by-default public projection for the facts needed by the
  portfolio overview and Signal Quality slice.
- A dashboard-local study manifest that links explicit persisted evidence
  without creating a framework domain object or claiming undocumented lineage.
- Version-controlled public content with a small safe Markdown and metadata
  contract.
- Stable direct routes for the overview, workflow context, methodology and
  study concepts; no persisted filter or tab state.
- A refreshed overview: concise product thesis, readable shared-domain map,
  six independent workflow entry points and visible `AS BUILT`,
  `IN DEVELOPMENT`, `FUTURE IDEAS`, `ARCHIVED` states.
- Extension of the dashboard import-boundary test to
  `apps/dashboard/pages/*.py` (PRB-022).

Out of scope:

- Signal Quality methodology prose, study charts and final evidence page
  (Sprint 060).
- A complete study-grouped catalog, full workflow redesign, Notes,
  Engineering or Future Direction sections.
- Any research computation, new metric, verdict, run control, live control,
  frontend migration, CMS, saved state or mobile-first redesign.
- Replacing or removing existing technical pages or changing current-only
  live-paper behavior.

## Decisions

| Decision | Recommendation and rationale | Status |
|---|---|---|
| D059-01 — publication boundary | Generate a separate sanitized projection before deployment and make the new public portfolio path read only that projection. The projection schema and sanitizer are dashboard-owned and library-free; unknown fields are excluded by default. This preserves ADR-0022 and prevents `storage_path` or private workspace content from becoming public merely because a scanner found it. | Accepted (maintainer, 2026-09-09); recorded in ADR-0034 §1, §5, §6 |
| D059-02 — study identity | Use a versioned dashboard-local `PortfolioStudyManifest` containing an explicit study slug, workflow references, artifact roles and public labels. It points only to projected artifacts and never infers that separate workflows form one pipeline. Do not add a shared framework study aggregate in this sprint. | Accepted (maintainer, 2026-09-09); recorded in ADR-0034 §2 |
| D059-03 — content ownership | Store public narrative as version-controlled dashboard content with required metadata (`slug`, title, status, updated date, order and links) and a restricted Markdown subset. Canonical technical contracts remain in `docs/reference/` and ADRs; methodology content links to them rather than duplicating them. | Accepted (maintainer, 2026-09-09); recorded in ADR-0034 §3 |
| D059-04 — routing | Use stable Streamlit page routes plus stable slugs for portfolio concepts. Query parameters may identify a study or evidence target but transient filters and tabs are not persisted. This follows the accepted product direction and requires no new framework contract. | Accepted implementation constraint (originally proposed); recorded in ADR-0034 §4 |

## Tasks

| Task | Outcome | Dependencies | Ownership | Risk | Status | PR |
|---|---|---|---|---|---|---|
| T001 | Record the accepted public-projection, study-identity and content boundaries in ADR-0034 or an explicitly approved ADR-0022 amendment; include producer, consumer, compatibility and migration rules | PRD approval; D059-01–03 | Architecture + dashboard application | high | Done | [#484](https://github.com/folg-code/research-trading-framework/pull/484) |
| T002 | Implement the versioned public projection and study-manifest contracts with mixed safe/private fixtures proving allowlisted fields are retained and forbidden or unknown fields are omitted | T001 | `apps/dashboard/src/dashboard_app/publication/` | high | Done | [#485](https://github.com/folg-code/research-trading-framework/pull/485) |
| T003 | Extend app-boundary enforcement to `apps/dashboard/pages/*.py`; prove the portfolio code imports no framework engines, execution, providers or ML libraries; update PRB-022 disposition | T001 | `tests/unit/test_apps_boundaries.py` | standard | Done | [#486](https://github.com/folg-code/research-trading-framework/pull/486) |
| T004 | Implement the content loader, required metadata validation, restricted rendering and stable-slug routing contract, with missing/invalid-content behavior covered by tests | T001, T002 | `apps/dashboard/src/dashboard_app/content/` | standard | Done | [#487](https://github.com/folg-code/research-trading-framework/pull/487) |
| T005 | Refresh the overview with the product thesis, shared-domain map, six independent workflow entries and maturity labels, using concise English content and existing visual components | T004 | `apps/dashboard` overview/content | standard | Done | [#488](https://github.com/folg-code/research-trading-framework/pull/488) |
| T006 | Reconcile dashboard reference docs and add a desktop acceptance fixture/render showing that the overview is readable and does not imply a mandatory pipeline | T002–T005 | dashboard docs + visual acceptance | standard | In review | pending |

## Acceptance criteria

- A test projection containing both allowed facts and private/unknown fields
  exposes every required allowed fact and none of the forbidden fields.
- No new portfolio route reads or displays an internal `storage_path` or scans
  the private workspace as its publication decision.
- `apps/dashboard/src/` and `apps/dashboard/pages/` both pass the strengthened
  import-boundary checks.
- The overview explains the product thesis before metrics, names six
  independent workflows, presents Market Analysis as shared capability and
  does not depict one mandatory pipeline.
- All four maturity labels are visually distinguishable and future capability
  cannot be mistaken for shipped capability.
- Stable overview and workflow-context URLs reopen in a new browser session;
  transient UI state is not saved.
- Existing technical evidence and Live Paper pages remain reachable and their
  targeted regression tests pass.
- Architecture and module documentation matches the accepted publication
  boundary before sprint closeout.

## Integration risks

- The sanitizer could become an implicit second research schema. Keep it a
  small presentation contract over explicitly named persisted facts.
- A study manifest could invent lineage. Require explicit artifact roles and
  test that missing links remain missing rather than inferred.
- Content could duplicate technical contracts. Keep methodology explanatory
  and link to canonical references.
- Streamlit navigation constraints could tempt saved transient state. Stable
  concept slugs are sufficient for this increment.

## Closeout

- Integrated checks: `apps/dashboard` full suite (148 tests, includes the new
  `test_overview_acceptance.py` desktop-render fixture) and
  `tests/unit/test_apps_boundaries.py` pass together on the integrated sprint
  branch; `ruff check`, `ruff format --check` and `mypy` (900+ files) clean.
- Documentation reconciliation: `docs/reference/modules/DASHBOARD_APPLICATION.md`
  documents the new `dashboard_app.publication` / `dashboard_app.content`
  packages and the refreshed overview; `docs/reference/system/MODULE_MAP.md`
  lists both new subpackages; a stale `pages/5_Live_Paper.py` filename
  reference was also corrected.
- Review: T001–T006 each went through independent review in a fresh context
  per `.claude/WORKFLOW.md`; the maintainer additionally reviewed the
  rendered overview locally (`streamlit run apps/dashboard/Project_Overview.py`)
  on 2026-09-09 and accepted it as a draft with the simplifications explicitly
  named in that review (workflow entry points reuse existing technical pages
  unchanged; Market Data shares Signal Research's page; Strategy Execution is
  a dry-run monitor only; no workflow-context/methodology/study pages yet;
  `content/routing.py`'s slug contract is unused by this sprint's one page).
- Remaining work: Sprint 060 plus later outcomes explicitly excluded by the
  Portfolio Dashboard MVP PRD.
