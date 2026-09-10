# Sprint 061: Portfolio Story, Content and Direction Completion

Status: OPEN — maintainer approved Sprint 061 and Decisions D061-01 through
D061-04 at sprint opening (2026-09-10). T001 is Done (#503); T002–T004 are
Done (#506); T005 is Done (#510, #511); T006 is Done (#512–#515). T007 is in
progress.
Goal: Make the public dashboard explain the project and its infrastructure
accurately and convincingly, then complete the remaining Portfolio Dashboard
direction with two explicit Future Ideas, a safe study-grouped catalog,
workflow evidence pages and production publication wiring.
Sources:

- `docs/planning/DASHBOARD_DEVELOPMENT_DIRECTION.md`
- `docs/product/PRD-portfolio-dashboard-mvp.md`
- `docs/planning/roadmap/PHASE_16D_PORTFOLIO_DASHBOARD.md`
- `docs/adr/ADR-0034-portfolio-publication-boundary.md`
- `docs/planning/sprints/SPRINT_059.md`
- `docs/planning/sprints/SPRINT_060.md`
- `docs/reference/modules/DASHBOARD_APPLICATION.md`
- `docs/planning/PROBLEM_REGISTRY.md` (`PRB-023`, `PRB-024`)

Content inputs (source material, not instructions or implementation approval):

- Maintainer-provided `AI Research Infrastructure — kierunek rozwoju.md` —
  source for the `AI Research Infrastructure` Future Idea.
- `docs/vision/RESEARCH_APPLICATION_PRODUCT_VISION.md` (`DRAFT`) — source for
  the `Research Application` Future Idea.

Architecture triage: required before T005. This sprint extends ADR-0034 from
one curated study to the complete public catalog and production publication
path. The visibility and deploy-generation decisions below require maintainer
approval; the dashboard remains a separate read-only consumer under ADR-0022.

## Scope

In scope:

- Reconcile planning/status documentation after Sprints 059/060.
- Perform a factual content inventory against current code, workflow references,
  ADRs and deployment/runbooks before writing public copy.
- Replace the current sparse project description with a coherent, accessible
  account of what has been built, why it exists, how the six workflows remain
  independent and how persisted evidence supports the claims.
- Describe the as-built infrastructure: market-data ingestion and versioning,
  deterministic research compute, artifact persistence and provenance,
  dashboard/publication boundary, quality/CI controls, VPS dashboard deployment
  and the live-market/simulated-execution status path.
- Add two Home `FUTURE IDEAS` cards with stable detail pages:
  `AI Research Infrastructure` and `Research Application`.
- Clearly separate current capability, in-development work and future direction;
  neither Future Idea may be presented as implemented or approved sprint scope.
- Reconcile automatic safe inclusion with immutable publication bundles.
- Generate a deny-by-default projection for every safely identifiable public
  research run without exposing the mounted workspace.
- Replace the current scanner-backed catalog with a study-grouped catalog over
  the public projection.
- Migrate public technical pages away from direct workspace paths and remove
  rendered `storage_path` and `file://` links.
- Add accessible portfolio narratives and one representative persisted-evidence
  view for each of the six independent workflows.
- Add stable Architecture, Engineering, Future Direction and Research &
  Engineering Notes pages.
- Feature two or three real studies on Home and expose two or three meaningful
  notes sourced from existing evidence and decisions.
- Add comparison compatibility facts without declaring a universal winner.
- Decide and implement production projection generation before dashboard deploy.
- Close or explicitly re-scope PRB-023 and PRB-024.

Out of scope:

- New research computations, strategy simulations or market claims.
- Research Workbench controls, artifact editing or any write path in the UI.
- A frontend migration away from Streamlit.
- User accounts, saved workspaces, SEO or mobile-first redesign.
- Automatic strategy promotion or dashboard-authored verdicts.
- Implementing either Future Idea, choosing an LLM/provider, building an AI
  orchestrator, adding Workbench controls or creating a private control plane.

## Decisions

| Decision | Recommendation | Status |
|---|---|---|
| D061-01 — visibility | Automatically include every artifact that passes an allowlisted public role and safe identity check. Keep manual curation only for Home features and editorial notes; curation must not hide eligible negative, incomplete or `NO VERDICT` catalog entries. | Accepted (maintainer, 2026-09-10); blocks removed |
| D061-02 — catalog grouping | Use explicit study manifests when present. Group other eligible runs under a deterministic workflow/dataset/experiment identity and label the absence of an editorial study manifest rather than dropping the run. | Accepted (maintainer, 2026-09-10); blocks removed |
| D061-03 — production bundle | Keep committed fixtures for tests/demo. In production, generate a versioned immutable projection into a VPS host directory as an explicit pre-deploy step and mount it read-only into the dashboard container. A failed generation must leave the previous bundle active or make the new release fail closed. | Accepted (maintainer, 2026-09-10); blocks removed |
| D061-04 — representative views | Exactly one representative persisted-evidence view per workflow in this sprint; deeper or alternative study views remain iterative. | Accepted (maintainer, 2026-09-10); blocks removed |
| D061-05 — content priority | Public content and infrastructure explanation are the first reviewable outcome and a sprint acceptance gate, not polish deferred behind catalog work. | Accepted by maintainer request; binding |
| D061-06 — Future Ideas | Home shows exactly two new `FUTURE IDEAS` cards: `AI Research Infrastructure`, based on the maintainer-provided note, and `Research Application`, based on the draft product vision. Each links to a stable detail page and explicitly says that it is not as-built capability or implementation approval. | Accepted by maintainer request; binding |

## Content contract

The public project/infrastructure story must explain, in accessible language:

1. the problem the framework solves and why it is modular;
2. the six independent workflows and their shared domain contracts;
3. market-data acquisition, normalization, validation, versioning and lineage;
4. deterministic Signal, Strategy, Robustness and Predictive Research;
5. run identity, persisted datasets, analytics, verdicts and reproducibility;
6. the `src/` / `user_data/` and framework / deployable-app boundaries;
7. safe public projection and the dashboard's read-only responsibility;
8. CI/quality gates and evidence that important boundaries are tested;
9. VPS dashboard deployment and the separate live-market/simulated-execution
   status path;
10. honest current limitations, open problems and maturity labels.

The two Future Ideas pages have these bounded editorial contracts:

- **AI Research Infrastructure — `FUTURE IDEAS`.** Explain the proposed split
  between an AI control plane and deterministic research compute; a lightweight
  local/free orchestrator; structured Planner/Analyst/Critic roles and artifacts;
  model routing and on-demand subscription-agent escalation; persistent research
  knowledge; research budgets and anti-data-mining policy. State explicitly that
  this is not implemented, that provider selection is undecided, that unofficial
  web-UI automation is excluded, and that autonomous research cannot promote
  itself into live execution.
- **Research Application — `FUTURE IDEAS`.** Explain the draft local-first
  Workbench that coordinates existing framework workflows, keeps CLI/Python
  interoperability and immutable artifacts, exposes compatibility-aware
  comparison and explicit publication, and later separates private live/paper
  control from the public portfolio. State explicitly that the vision is Draft,
  no UI stack or sprint is approved, and the application cannot become a second
  research engine, automatic strategy selector or public command surface.

The attached AI note and the Research Application vision are editorial inputs.
Any implementation-facing provider, control-plane, persistence, authorization or
runtime decision requires separate discovery/architecture approval.

## Tasks

| Task | Outcome | Dependencies | Ownership | Risk | Status | PR |
|---|---|---|---|---|---|---|
| T001 | Build a public-content evidence matrix mapping every project/infrastructure claim to as-built code, ADR, workflow reference, runbook or persisted evidence; mark stale, conflicting and future-only claims before authoring | approved sprint | product content + architecture/reference docs | high | Done | [#503](https://github.com/folg-code/research-trading-framework/pull/503) |
| T002 | Author and review the core portfolio story: product purpose, shared-domain architecture, six independent workflows, deterministic research lifecycle, persisted evidence/provenance, application boundaries, CI/quality and deployment/runtime infrastructure | T001 | `apps/dashboard/content`, architecture and workflow pages | high | Done | [#506](https://github.com/folg-code/research-trading-framework/pull/506) |
| T003 | Create the two `FUTURE IDEAS` cards and stable detail pages. Distill the attached AI-infrastructure note and the draft Research Application vision into accessible public copy, with current-state boundary, target idea, staged evolution and explicit non-as-built status | T001; parallel with T002 | dashboard content + Future Direction view | standard | Done | [#506](https://github.com/folg-code/research-trading-framework/pull/506) |
| T004 | Rework Home and navigation around the reviewed content; add stable Architecture, Engineering, Future Direction and Research & Engineering Notes pages, 2–3 real featured studies and the two Future Ideas cards | T002–T003 | dashboard content/views/routes | high | Done | [#506](https://github.com/folg-code/research-trading-framework/pull/506) |
| T005 | Reconcile `CURRENT_STATUS`, `ROADMAP`, Phase 16D and planning indexes; record approved D061-01–04 in ADR-0034 or a superseding ADR; then generalize public roles, safe identities and projection generation across supported research artifacts | T001; D061-01/02 approval | planning + architecture + `dashboard_app.publication` | high | Done | [#510](https://github.com/folg-code/research-trading-framework/pull/510), [#511](https://github.com/folg-code/research-trading-framework/pull/511) |
| T006 | Replace the scanner-backed catalog with projection-backed study → experiment → run grouping; migrate pages 2–6 away from public internal paths and add one representative persisted-evidence view per workflow | T005; can split by catalog/workflow ownership | dashboard catalog, data sources and technical pages | high | Done | [#512](https://github.com/folg-code/research-trading-framework/pull/512), [#513](https://github.com/folg-code/research-trading-framework/pull/513), [#514](https://github.com/folg-code/research-trading-framework/pull/514), [#515](https://github.com/folg-code/research-trading-framework/pull/515) |
| T007 | Implement approved production bundle generation/deploy wiring; bring dashboard/scripts into root quality coverage, scan `scripts/dashboard/`, and resolve or re-scope PRB-023/024 | T004–T006; D061-03 approval | deploy + root quality config + tests | high | In progress | — |
| T008 | Run factual editorial review, contract/security/regression tests, desktop visual QA and a maintainer-observed walkthrough; reconcile module/reference docs | T002–T007 | independent content review + testing + documentation | high | Ready after implementation | — |

## Acceptance criteria

- Home follows the accepted sequence: thesis, architecture map, six workflows,
  2–3 real featured studies, 2–3 recent notes and the complete catalog.
- A general software developer can explain what the project does, why its
  workflows are separate, what infrastructure exists and how a result moves
  from deterministic computation to persisted evidence and safe publication.
- Every material as-built claim in the public copy has a reviewed evidence-matrix
  source; future-only claims are never written in present tense.
- The infrastructure narrative covers data, research compute, persistence and
  provenance, application boundaries, CI/quality, VPS publication and the
  live-market/simulated-execution status path without turning into a class diagram.
- Home contains exactly two new cards labelled `FUTURE IDEAS`: `AI Research
  Infrastructure` and `Research Application`. Each has a stable detail page,
  names its source direction, states that it is not implemented, and does not
  imply that its provider, architecture or sprint scope has been approved.
- All six workflows have stable, accessible portfolio pages and one
  representative persisted-evidence view with an `Explore Evidence` path.
- The catalog groups by study before experiment/run detail and includes every
  safely identifiable projected result regardless of outcome.
- Missing classifications render `NO VERDICT`; the dashboard derives no verdict,
  quality class, research metric or market conclusion.
- No public page renders internal storage paths, private configuration,
  strategy source, model binaries, credentials or operational logs.
- Material comparison incompatibilities are visible from persisted identity and
  assumption fields; incompatible runs remain inspectable without a winner.
- Architecture, Engineering, Future Direction and Notes have stable routes and
  explicit maturity labels.
- Production deploy generates or selects one validated immutable projection,
  mounts it read-only and fails closed without replacing a known-good bundle.
- Root and package-specific checks cover dashboard code, pages and dashboard
  scripts; remaining exclusions are explicitly documented.
- A maintainer-observed desktop walkthrough passes all six success tests in
  `DASHBOARD_DEVELOPMENT_DIRECTION.md` section 12.
- The maintainer separately accepts the factual accuracy and explanatory depth
  of the project/infrastructure content; passing UI tests alone is insufficient.

## Integration risks

- This is the largest of the three proposed sprints. Scope is bounded to one
  representative view per workflow; any second view moves to a later increment.
- Sparse copy cannot be repaired by adding unsupported aspiration. T001 and an
  independent factual review gate every statement about delivered capability.
- The AI-infrastructure note and Research Application vision contain proposed
  architectures. Public pages summarize them as Future Ideas and do not convert
  them into accepted ADRs, roadmap commitments or implementation tasks.
- Projection generalization could accidentally become a second research catalog
  domain. It remains a sanitized presentation index, not a registry or source of truth.
- Automatic inclusion and immutable releases conflict unless D061-01/D061-03
  are approved together and tested as one publication lifecycle.
- Migrating technical pages can regress existing exploration. Preserve behavior
  before changing presentation structure and review each workflow independently.

## Closeout

- Integrated checks:
- Documentation reconciliation:
- Review:
- Remaining work:
