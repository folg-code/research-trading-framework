# PRD — Portfolio Dashboard MVP: Foundation and Signal Quality Evidence

```text
Status: DRAFT
Discovery: maintainer Q&A completed 2026-09-09
Parent direction: docs/planning/DASHBOARD_DEVELOPMENT_DIRECTION.md
Approval gate: PRD scope and Sprint 059 architecture recommendations require
               maintainer approval
```

## Problem

The project already has a public, read-only Streamlit dashboard with a project
overview, a run catalog and technical pages for Market and Signal Research,
Strategy Research, Robustness Research, Predictive Research and current
live-paper status. These pages prove that persisted artifacts exist, but the
product experience is still organized primarily as an artifact browser.

A software engineer or developer without specialist quant knowledge cannot yet
move through one coherent portfolio story:

```text
what the project is and why it exists
  -> how shared domain objects support independent workflows
  -> how a selected workflow and methodology operate
  -> which persisted artifacts demonstrate the result
```

The current overview provides simplified diagrams and module cards, while the
next click commonly leads directly to run selectors, tables and specialist
charts. Methodology and engineering context live mostly in repository
documentation. There is no public-friendly layer between the overview and the
technical evidence.

Phase 16A–16C provides a suitable first real evidence slice: persisted
predictive verdicts, signal-occurrence sampling and the BTC Signal Quality
study with a baseline-versus-score-filtered Strategy Research comparison. The
missing capability is an accessible, portfolio-grade path through that real
evidence. It is not another research engine, an operator workbench or a market
analysis service.

## Goals / Non-goals

### Goals

- Present an English-language, desktop-first public portfolio whose primary
  audience is a general software engineer or developer.
- Refresh the overview so that it communicates the product thesis before
  presenting specialist metrics.
- Show a small, readable map of shared domain objects and contracts supporting
  six independent workflows: Market Data, Signal Research, Strategy Research,
  Robustness Research, Predictive Research and Strategy Execution.
- Present Market Analysis as a shared domain capability, not as another
  mandatory workflow stage.
- Provide entry points from the overview to all six existing workflow
  surfaces, without requiring every workflow to receive a new simplified
  result view in this increment.
- Use explicit `AS BUILT`, `IN DEVELOPMENT`, `FUTURE IDEAS` and `ARCHIVED`
  labels where capabilities of different maturity appear together.
- Establish the first reusable portfolio pattern across the Signal and
  Predictive Research context:

  ```text
  accessible workflow context
    -> current methodology
    -> Signal Quality study
    -> simplified result
    -> Explore Evidence
  ```

- Make clear that Signal Research, Predictive Research and Strategy Research
  remain independent workflows even though the Phase 16C study deliberately
  connects persisted outputs between them.
- Publish a living, public-friendly Signal Quality methodology page from
  version-controlled content. It explains the current method and never becomes
  a hand-written interpretation of a particular run.
- Provide a simplified BTC Signal Quality study view that uses only allowlisted
  persisted Phase 16A–16C facts and answers experimentally:
  - what was studied;
  - against which baseline and assumptions;
  - what result was persisted;
  - which limitations or warnings were persisted.
- Show two or three workflow-appropriate charts on the simplified study view
  and provide neutral definitions for unfamiliar metrics without adding a
  dashboard-authored conclusion or verdict.
- Present the persisted `INCONCLUSIVE` verdict and negative downstream result
  as complete research evidence, without language implying failure of the
  product, a live edge or trading approval.
- Keep the existing technical result surfaces available as `Explore Evidence`,
  including detailed metrics, folds, verdict facts, provenance and frozen
  reports where present.
- Provide a minimal allowlisted public projection for every artifact and field
  required by this slice. Direct filesystem discovery is not proof that a
  field is safe to publish.
- Exclude internal paths, private configuration, strategy source, model
  binaries, infrastructure identifiers, operational logs, credentials and
  other private workspace content from the new public path.
- Provide stable direct URLs for the overview, workflow context, Signal Quality
  methodology and Signal Quality study. Transient filters, tabs and raw run
  selections do not need shareable state.
- Preserve the existing read-only dashboard boundary: presentation may filter,
  sort, group and visualize persisted facts, but every new metric,
  classification or verdict is produced and persisted by its owning layer.
- Preserve the current technical pages and current-only live-paper behavior
  while the new portfolio path is introduced additively.

### Non-goals

- The full target state of Phase 16D or
  `DASHBOARD_DEVELOPMENT_DIRECTION.md` in one increment.
- Full narrative and simplified result redesigns for all six workflows.
- A complete study-grouped replacement for the current research catalog. The
  first slice needs a discoverable Signal Quality study; the full catalog
  transformation remains a later outcome under the parent direction.
- Research & Engineering Notes, the cross-cutting Engineering section or the
  full Future Direction section. The overview may reserve clear entry points
  or maturity language without implementing those surfaces now.
- Data acquisition, data editing, research configuration, run control,
  cancellation or any other Research Workbench behavior.
- Strategy start, stop, flatten, order submission or any public command
  surface.
- Dashboard-side research computation, metric derivation, model fitting,
  compatibility inference, classification, verdict logic or promotion logic.
- New Signal Quality research, new market claims or changes to the Phase 16C
  study and its persisted conclusions.
- Replacing or removing existing technical evidence pages.
- A market commentary site, price forecasts, trade ideas, strategy sales or a
  profitability showcase.
- A prominent personal biography or self-promotional author page.
- A public archive of completed live-paper sessions or changes to the current
  Live Paper page.
- Exposing the mounted workspace or private `user_data` content directly.
- A CMS, user accounts, collaboration, comments, subscriptions or a hosted
  multi-tenant product.
- Saved workspaces, saved filters, user-composed dashboards, advanced chart
  drawing or shareable transient UI state.
- Mobile-first optimization or search-engine optimization.
- Migration away from Streamlit or selection of another frontend stack.
- Replacing canonical reference documentation, ADRs, source code or frozen
  research reports.
- A fictional end-to-end example implying that every workflow forms one
  mandatory pipeline or that an artifact followed lineage not evidenced by
  persisted facts.

## Success metrics

- In a maintainer-observed acceptance walkthrough, a software developer without
  quant specialization can explain the project's purpose, identify its shared
  domain foundation and recognize that the six workflows are independent.
- The same visitor can reach the BTC Signal Quality study from the overview in
  no more than three navigation actions.
- From the study page, the current Signal Quality methodology and `Explore
  Evidence` are each reachable in one navigation action.
- The simplified study view visibly answers the four declared study questions
  and shows two or three charts sourced from persisted Phase 16C facts.
- Every displayed number, classification and verdict in the new path can be
  traced to an allowlisted persisted artifact; the presentation layer contains
  no research metric or verdict implementation.
- Public-projection tests containing both allowed facts and forbidden private
  fields expose all required allowed facts and none of the forbidden fields.
- The persisted `INCONCLUSIVE` verdict, negative baseline-versus-filtered
  result, rejected winners and rejected losers remain visible without language
  suggesting live performance, a market forecast or trading approval.
- The methodology page explains the current method and links to deeper
  repository references without containing a hand-authored conclusion about
  the BTC study.
- `AS BUILT`, `IN DEVELOPMENT`, `FUTURE IDEAS` and `ARCHIVED` states used in
  the slice are visually distinguishable; future capability cannot be mistaken
  for shipped functionality.
- The overview and workflow map do not claim that one mandatory end-to-end
  pipeline exists and do not present a fictitious artifact that traversed all
  workflows.
- Stable direct URLs reopen the overview, workflow context, methodology and
  study pages after a new browser session or deployment.
- At a representative desktop viewport, the thesis, workflow map, study
  summary and primary charts are readable without consulting raw artifact
  tables for basic comprehension.
- Existing technical evidence pages and current live-paper behavior remain
  available and their automated tests continue to pass.
- The repository-wide app boundary prohibits dashboard imports of research
  engines, execution engines, providers and ML libraries, including imports
  from `apps/dashboard/pages/*.py`.

## User stories

- As a software developer visiting the project, I can understand its purpose
  and architecture before seeing specialist metrics so that I can evaluate the
  engineering work in context.
- As a software developer, I can see how shared domain objects support multiple
  independent workflows so that I understand the main architectural advantage
  without reading a class diagram.
- As a visitor, I can distinguish as-built, in-development, future and archived
  content so that ideas are not mistaken for implemented features.
- As a visitor without quant specialization, I can read Signal Quality workflow
  and methodology content in plain language and reveal deeper technical detail
  only when I need it.
- As a visitor, I can open the BTC Signal Quality study, understand what was
  compared and inspect a small number of meaningful charts before entering the
  full technical evidence view.
- As a technical reviewer, I can move from the simplified study to persisted
  metrics, fold evidence, verdict facts, provenance and frozen reports without
  using a terminal.
- As a visitor, I can see an inconclusive model result and a downstream result
  that did not improve the strategy so that the portfolio demonstrates honest
  research rather than survivorship-biased selection.
- As a visitor, I can navigate from the study to the current methodology while
  recognizing that the methodology is not an editorial interpretation of that
  run.
- As a maintainer, I can expose the artifacts required by the study through an
  explicit public allowlist without copying computed values into dashboard
  content or revealing private workspace fields.
- As a maintainer, I can add later workflow slices using the same narrative,
  methodology, simplified-result and `Explore Evidence` pattern without the
  first slice pretending to implement the entire portfolio direction.

## Open questions

Architecture triage has identified three decisions that must be accepted in
Sprint 059 before implementation: the public-projection boundary,
dashboard-local study identity and public content ownership. The PRD remains
DRAFT until those recommendations and this product scope are approved.

### Resolved during roadmap and sprint planning (2026-09-09)

- **Direction precedence:** the maintainer accepted
  `DASHBOARD_DEVELOPMENT_DIRECTION.md` as authoritative for 16D. The phase
  roadmap now states that precedence explicitly.
- **Phase 16D scope:** the former Quant Lab / dashboard-authored accept-reject
  framing was replaced with the public Portfolio Dashboard outcome. The UI
  displays an upstream persisted verdict and never creates one.

### Remaining questions and conflicts
- **Public publication conflict:**
  `RESEARCH_APPLICATION_PRODUCT_VISION.md` describes curated, immutable
  publication versions created by an explicit publish action. The parent
  direction requires automatic catalog inclusion of every safely publishable
  run through an allowlisted projection. The visibility model must be
  reconciled before the later full-catalog increment; this slice still needs a
  minimal safe projection for the Signal Quality study.
- **Live-history conflict:** `RESEARCH_APPLICATION_PRODUCT_VISION.md` includes
  permanent public pages for ended dry-run sessions. The parent direction
  limits this dashboard to current live-paper status with no public session
  archive. The older vision must be amended or scoped to a different future
  surface.
- **Workbench separation:** `PRD-research-workbench-mvp.md` concerns a local
  control product and permits shareable selection state. This public PRD has no
  control behavior and rejects persistent transient UI state. The difference
  is intentional; naming and cross-links must prevent the two products from
  being interpreted as one trust boundary.
- **Current public catalog conflict:** the existing dashboard catalog scans the
  mounted workspace and exposes fields including `storage_path`. The parent
  direction forbids exposing internal paths and requires an allowlisted public
  projection. Architecture triage must determine the safe source for the new
  slice and the later migration path for the current catalog.
- **Current overview conflict:** the existing overview includes one simplified
  `Research workflow` diagram. The new overview must ensure this cannot be read
  as a mandatory pipeline and should build from the existing independent-
  capabilities diagram instead.
- **Public-projection contract:** which owning layer declares allowed artifact
  types and fields, and where is the sanitized projection produced? The
  dashboard must not infer safety from file discovery.
- **Signal Quality artifact inventory:** which exact Phase 16A–16C artifacts
  answer the four simplified-view questions and support two or three charts
  without any dashboard-side derivation?
- **Study identity:** what canonical persisted identity represents the BTC
  Signal Quality study and connects its predictive, promotion and Strategy
  Research evidence without inventing lineage?
- **Methodology ownership:** where does the public-friendly, living Signal
  Quality methodology content live, and how does it link to as-built reference
  documentation without becoming a contradictory second technical contract?
- **Content rendering contract:** which safe Markdown subset and metadata are
  required for title, status, update date, ordering, links and archived state?
- **Discoverability boundary:** does the first slice add a minimal entry to the
  current catalog, introduce a small study index or rely on a featured link
  from the overview? The complete study-grouped catalog is explicitly outside
  this PRD.
- **Chart selection:** which two or three persisted visualizations best explain
  the Signal Quality result to a developer without quant specialization?
- **Explore Evidence boundary:** which existing Predictive and Strategy
  Research panels form the technical destination, and does the new study page
  link to them or compose them without duplicating interpretation?
- **Stable routing:** how are stable workflow, methodology and study URLs
  represented in the retained Streamlit stack while transient UI state remains
  unpersisted?
- **Boundary enforcement gap:** Phase 16A recorded that the dashboard import
  boundary test does not scan `apps/dashboard/pages/*.py` (`PRB-022`). The
  implementation plan must route repayment or explicit acceptance before
  claiming the strengthened boundary success metric.
- **Visual acceptance evidence:** which wireframes or rendered reference pages
  establish that the shared-object map and simplified study remain
  comprehensible at the representative desktop viewport?
- **Delivery size:** this PRD defines one coherent product outcome but does not
  decide whether implementation requires one or multiple sprints. Sprint
  slicing follows only after architecture triage and PRD approval.
