# ADR-0034 — Public Portfolio Publication Boundary: Projection, Study Identity, Content and Routing (16D)

## Status

ACCEPTED

Date: 2026-09-09
Owners: architecture triage (Claude Code session), for Phase 16 increment
16D, `docs/planning/sprints/SPRINT_059.md` (T001).

This document records decisions D059-01 through D059-04 as stated in
`SPRINT_059.md`.

Approved-by: Filip Folga (folga33@gmail.com), 2026-09-09 — "Akceptuję
ADR-0034 jak napisany", accepting the document as drafted, unblocking
Sprint 059 T002–T006.

## Context

Phase 16 increment 16D (`docs/planning/DASHBOARD_DEVELOPMENT_DIRECTION.md`,
ACCEPTED 2026-09-09) turns `apps/dashboard` from an artifact browser into a
public portfolio surface. `docs/product/PRD-portfolio-dashboard-mvp.md`
scopes the first slice: a refreshed overview plus the BTC Signal Quality
evidence path built on real Phase 16A–16C artifacts
(`docs/reference/BTC_SIGNAL_QUALITY_STUDY.md`).

Four facts constrain how that can be built:

- **The current publication path infers safety from filesystem discovery.**
  `dashboard_app.catalog.scanner` walks the mounted workspace and every
  catalog contract carries an internal path:
  `RunSummary.storage_path`, `PredictiveDatasetSummary.storage_path`,
  `PredictiveRunSummary.storage_path` (`dashboard_app/contracts.py`), which
  `views/catalog_table.py` and `views/picker.py` render, and which
  `views/research.py`, `views/strategy.py`, `views/robustness.py` and
  `views/predictive.py` use as a read root. Direction §8 and the PRD forbid
  exactly this for the public path: "automatic discovery does not mean
  exposing the mounted workspace directly". A field is public today because
  a scanner found it, not because anyone decided it was safe.

- **ADR-0022 rule 2 is the standing app boundary.** `apps/*` must not import
  research engines, execution, or infrastructure providers/importers; apps
  "read mounted storage and may keep local presentation contracts". ADR-0022
  rule 6 defers `packages/` for shared cross-app DTOs until a second consumer
  needs them. Any 16D publication mechanism must fit inside that rule rather
  than amend it. `tests/unit/test_apps_boundaries.py` enforces the boundary
  over `apps/dashboard/src` only — `apps/dashboard/pages/*.py` is unscanned
  (PRB-022).

- **There is no persisted study identity.** The BTC Signal Quality study is
  four separately-persisted things (a `SIGNAL_QUALITY` predictive dataset, a
  fitted run plus its `verdict.json`, a promoted artifact fingerprint, and
  two Strategy Research runs) connected only by a human-written reference
  document. Nothing in `user_data/` says they form one study, and ADR-0024
  condition 5 forbids the index/registry shape that would say so.

- **Sprint 060 is the first real consumer.** `SPRINT_060.md` T001 must freeze
  an artifact-to-public-field inventory for four study questions and three
  charts (model vs. random-permutation ROC AUC per fold; threshold
  sensitivity; baseline vs. scored trade disposition), plus the persisted
  `INCONCLUSIVE` verdict. Whatever 16D publishes now must absorb that
  inventory additively, without a schema break.

## Decision

Introduce one dashboard-owned publication boundary with four parts. The new
public portfolio path reads **only** a pre-generated sanitized projection;
nothing on that path scans the private workspace.

### 1. Public projection (D059-01)

1. **Artifact.** A versioned, sanitized **public projection bundle** is the
   single input to the public portfolio path. It carries an explicit
   `schema_version` (`dashboard.public.v1`), a generator version and a
   `generated_at_utc` timestamp. Its schema and sanitizer are dashboard-owned
   presentation contracts under `apps/dashboard` (ADR-0022 rule 2's
   "local presentation contracts"), not a framework artifact type, and not a
   `packages/` shared DTO (ADR-0022 rule 6 stays deferred).

2. **Producer — build/deploy time, never Streamlit runtime.** A generator
   step reads the private workspace and writes the projection bundle *before*
   the app is deployed or started. It is the only code permitted to touch
   raw research artifacts on the public path. The generator is library-free
   in the same sense as the rest of `apps/dashboard`: no `trading_framework`
   research/execution/provider import, no ML library (`sklearn`, `xgboost`,
   `torch`). Its exact module path and invocation surface are a Sprint 059
   T002 task-level decision; that it runs *before* deployment and not inside
   a Streamlit page render is fixed here.

3. **Deny by default.** Sanitization is an explicit per-artifact-role field
   allowlist. Any field not named in the allowlist — including a newly
   appearing field in an upstream artifact — is **omitted**, not passed
   through, not logged into the bundle. Categorically excluded, with no
   allowlist entry permitted: filesystem paths of any kind (including
   `storage_path`), private configuration, strategy source, model binaries
   or any reference to `models/fold_*.bin`, infrastructure identifiers,
   hostnames, operational logs, credentials, and any other `user_data`
   content (ADR-0002).

4. **Copy, never derive.** The generator copies persisted values verbatim.
   It computes no metric, no classification, no verdict, no threshold and no
   fallback conclusion — those belong to the owning research layer
   (Direction §7, PRD non-goals). Rounding or formatting for display happens
   in the view, not in the projection.

5. **Identity without paths.** Projected artifacts are identified by
   already-persisted identity values (run id, dataset id/fingerprint,
   promoted `artifact_fingerprint`) plus a projection-local artifact id.
   A consumer must never be able to reconstruct a workspace location from
   projected content.

6. **Consumer rule.** Only the new public portfolio modules and pages read
   the projection bundle, and they read *nothing else* from disk: no
   workspace scan, no `Path(...)` built from projected values, no
   catalog-scanner call. If the bundle is absent, stale or fails schema
   validation, the public path shows an explicit unavailable state — it
   never falls back to scanning the workspace.

### 2. Study identity (D059-02)

1. **`PortfolioStudyManifest`** is a versioned, **dashboard-local,
   version-controlled** presentation contract with its own `schema_version`.
   No framework study aggregate, no persisted framework index, no `latest`
   pointer is introduced (ADR-0024 condition 5, unchanged).

2. **Required content per study:** an explicit stable `slug`; a public
   title; a maturity label; explicit `workflow` references naming which
   independent workflows contributed; and a set of **artifact roles**, each
   mapping a named role to exactly one projected artifact id.

3. **Explicit roles only; no inferred lineage.** A role that is not declared
   is absent. The manifest never claims that separate workflow runs form one
   pipeline, and no code derives such a relationship from timestamps,
   fingerprint proximity, directory adjacency or naming. A study spanning
   Signal, Predictive and Strategy Research says only "these named,
   separately persisted artifacts are what this study reports".

4. **Fail closed on dangling references.** A manifest naming an artifact
   absent from the projection is a validation failure surfaced as an explicit
   missing-evidence state — never a silent omission and never a substituted
   artifact.

5. **Role vocabulary is additive.** Sprint 060 T001 freezes the exact roles
   and fields for the BTC Signal Quality study (expected shape: predictive
   run metrics, the `verdict.json` facts, threshold-sensitivity rows, the
   promoted artifact fingerprint as a bare identity string, and the baseline
   vs. score-filtered Strategy Research summaries). Adding a role or an
   allowlisted field later is a minor version bump, not a break — see §5.

### 3. Content ownership (D059-03)

1. **Public narrative is version-controlled dashboard content** (files in the
   repository, reviewed like code). No CMS, no database, no runtime editing
   (PRD non-goals).

2. **Required metadata per content document:** `slug` (stable), title,
   status (one of `AS BUILT`, `IN DEVELOPMENT`, `FUTURE IDEAS`, `ARCHIVED`),
   updated date, ordering key, and declared links. Missing or invalid
   metadata is a validation failure with an explicit error state; the page
   does not render partially-valid content as if it were complete.

3. **Restricted Markdown subset.** Rendering supports only an explicitly
   allowed set of constructs (headings, paragraphs, lists, links, emphasis,
   inline and fenced code, tables, and repository-local images). Raw HTML,
   scripts, iframes and remote transclusion are not rendered. Like the
   projection, the renderer is deny-by-default: an unsupported construct is
   not passed through.

4. **Content links, it does not duplicate.** `docs/reference/` and the ADRs
   remain the canonical technical contracts. Methodology and workflow content
   explains and links; it must not restate a schema, threshold or contract in
   a form that can silently diverge. Content must not hard-code a computed
   research number — every displayed number comes from the projection.

5. **Living, not frozen per run.** Methodology content describes the current
   method and carries no interpretation of an individual run (Direction §6).
   Replaced content is marked `ARCHIVED` rather than deleted or silently
   presented as current.

### 4. Routing (D059-04)

1. Stable Streamlit page routes plus stable slugs identify the overview,
   workflow context, methodology and study pages. A slug is a public
   identifier: renaming one is a compatibility break (§5), not an edit.

2. Query parameters may carry a study or evidence target slug so those pages
   reopen in a new browser session.

3. **No persisted transient UI state**: filters, tabs, run selections,
   sort order and chart interactions are not stored in the URL, in session
   state across sessions, or anywhere else. This is the deliberate
   difference from `PRD-research-workbench-mvp.md`, which is a different
   product and a different trust boundary.

### 5. Compatibility rules

- Every contract above (projection bundle, `PortfolioStudyManifest`, content
  metadata) carries an explicit `schema_version`. Consumers validate it and
  refuse to render on a major-version mismatch rather than guessing.
- **Additive within a major version:** new optional fields, new artifact
  roles, new studies, new content documents and new pages. Consumers tolerate
  fields they do not render and treat absent optional fields as absent, never
  as zero or as a default.
- **Breaking (major bump + a new ADR or an explicit amendment to this one):**
  removing or renaming a field or role, changing the meaning or units of an
  existing field, changing a published slug, relaxing deny-by-default, or
  moving projection generation into runtime.
- Widening the field allowlist is a reviewed change with a fixture proving
  the new field is a persisted public fact — never an incidental edit.
- Sprint 060 and later 16D sprints are expected to extend, not break, `v1`.

### 6. Migration rules

- **Existing technical pages are grandfathered, not migrated now.**
  `pages/1_Research_Catalog.py` … `pages/6_Predictive_Research.py` and their
  view modules keep reading the mounted workspace directly through the
  existing catalog scanner. They are `Explore Evidence` depth, out of the new
  public path's scope, and the PRD forbids replacing or removing them in this
  increment.
- **`storage_path` is frozen, not deleted.** It may remain on the existing
  presentation contracts for those grandfathered readers, but it must never
  appear in the projection bundle, in any `PortfolioStudyManifest`, or on any
  new portfolio page. Its removal from the rendered catalog table and picker
  is a later increment's work, tracked as follow-up.
- **No new direct-read code.** After this ADR, any new public-path module
  that reads a raw artifact is a boundary violation, regardless of whether an
  older module nearby does the same thing.
- **Boundary enforcement extends to pages.** `tests/unit/test_apps_boundaries.py`
  is extended to `apps/dashboard/pages/*.py` (Sprint 059 T003, PRB-022) so the
  library-free claim covers the files that actually render the public path.
- Migrating the full catalog onto the projection, and reconciling it with the
  curated/immutable publication model in
  `RESEARCH_APPLICATION_PRODUCT_VISION.md`, are explicitly later work — see
  Follow-up.

## Alternatives Considered

### A — Sanitize at read time inside the running dashboard

Keep scanning the mounted workspace at request time and strip forbidden
fields in the view layer.

- Pros: no build step, no new artifact, no deploy-pipeline change; smallest
  immediate diff.
- Cons: the publication decision stays coupled to filesystem discovery, which
  is precisely what Direction §8 and the PRD reject; the public host still
  needs the private workspace mounted, so a single missed filter or a new
  page leaks private content; "unknown fields are excluded" cannot be proven
  once rather than re-proven at every call site.
- Rejected: it does not remove the class of failure, only the current
  instances of it.

### B — A framework-owned publication contract in `src/trading_framework/`

Make publication a research-layer concern with a persisted public artifact
type.

- Pros: one authoritative definition of "publishable"; reusable by a future
  second consumer.
- Cons: creates a second research schema over the same facts (the exact risk
  `SPRINT_059.md` lists first under Integration risks); puts a presentation
  concern into the modular monolith; ADR-0022 rule 6 defers shared cross-app
  DTOs until a second consumer actually exists — today there is one.
- Rejected for this increment, not forever: revisit if the Research Workbench
  or another app needs the same projection.

### C — A framework study aggregate as the study identity

Persist a first-class Study entity linking predictive, promotion and Strategy
Research evidence.

- Pros: a single canonical identity; the catalog's study grouping would be
  read, not authored.
- Cons: a durable domain object and a lifecycle/index shape that ADR-0024
  condition 5 deliberately refuses; it would encode cross-workflow lineage
  that the persisted artifacts do not evidence, contradicting Direction §3
  and the PRD's "no fictional end-to-end example"; 16D needs presentation
  grouping, not a domain concept.
- Rejected: a dashboard-local manifest gives the needed grouping with no
  claim the evidence cannot support.

### D — CMS or database-backed public content

- Rejected outright by the PRD's non-goals (no CMS, no accounts, no runtime
  editing) and unnecessary for a version-controlled portfolio.

## Consequences

### Positive

- The public path can run without the private workspace mounted at all: a
  leak requires an allowlist edit, not merely a new file appearing on disk.
- "Unknown fields are excluded" becomes one testable property of one
  sanitizer, provable by the mixed safe/private fixture Sprint 059 T002 and
  the PRD's success metrics require.
- Study grouping ships without a new domain object, a registry or an implied
  pipeline — ADR-0022, ADR-0024 condition 5 and workflow independence all
  stay intact.
- Sprint 060's field inventory lands as an additive `v1` extension; later 16D
  sprints inherit a stable contract instead of renegotiating it.
- Stable slugs and routes give shareable URLs without the saved-UI-state
  surface the PRD rejects.

### Negative

- A new build/deploy step exists and can drift: if projection generation is
  skipped, the public site shows an explicit stale/unavailable state rather
  than fresh evidence. The deploy pipeline
  (`.github/workflows/deploy-dashboard.yml`, `apps/dashboard/docs/RUNBOOK.md`)
  must be updated to run it — otherwise the new pages are simply empty.
- Two publication mechanisms coexist for a while: the grandfathered scanner
  for technical pages and the projection for the portfolio path. That is
  deliberate but is real duplication until the catalog migration follow-up.
- The allowlist is manual work: every new public fact costs an allowlist
  entry, a fixture and a review. This is the intended friction, but it is
  friction.
- Study manifests are hand-authored, so a study can be described incorrectly
  by a human. The fail-closed dangling-reference rule limits, but does not
  eliminate, this.

### Neutral / Trade-offs

- No framework code changes and no new dependency: this decision is entirely
  inside `apps/dashboard` plus a deploy step.
- The read-only dashboard boundary is unchanged — presentation may filter,
  sort, group and visualize; it still produces no metric, classification or
  verdict.

## Follow-up

- **Catalog migration.** Moving `pages/1_Research_Catalog.py` and the
  remaining technical pages onto the projection, and removing `storage_path`
  from rendered output, is a later increment, not this one.
- **Visibility model reconciliation.** `RESEARCH_APPLICATION_PRODUCT_VISION.md`
  describes curated, immutable publication versions created by an explicit
  publish action, while Direction §8 requires automatic inclusion of every
  safely publishable run. The two must be reconciled before the full-catalog
  increment; this ADR intentionally decides only the safe-projection
  mechanism, not the curation policy.
- **Field inventory.** Sprint 060 T001 freezes the exact artifact-to-public-
  field mapping for the BTC Signal Quality study; a missing fact is reported,
  never derived.
- **Concrete module and file layout.** The generator's module path, the
  bundle's on-disk layout and the content directory are Sprint 059 T002/T004
  task-level decisions within the rules above.
- **Deploy wiring.** Where projection generation runs (local pre-rsync step
  vs. CI) must be decided and documented in the dashboard RUNBOOK before the
  first public deployment of the new path.
- **PRB-022 disposition** is closed or explicitly re-accepted by Sprint 059
  T003, not by this ADR.

## Related

- `docs/adr/ADR-0022-repository-top-level-layout.md` — rule 2 (apps import
  boundary) and rule 6 (`packages/` deferred), both consumed unchanged; this
  ADR adds a constraint inside them and does not amend them.
- `docs/adr/ADR-0002-separate-src-and-user-data.md` — the `user_data`
  boundary the projection must never leak.
- `docs/adr/ADR-0024-machine-learned-state-promotion.md` — condition 5 (no
  registry/index), the reason study identity stays dashboard-local.
- `docs/adr/ADR-0032-predictive-run-verdict-artifact.md` — the persisted
  verdict the public path displays verbatim and never generates.
- `docs/adr/ADR-0033-predictive-score-delivery-boundary.md` — the score path
  whose result the BTC study reports; consumed, not changed.
- `docs/planning/DASHBOARD_DEVELOPMENT_DIRECTION.md` §3, §6, §7, §8, §10 —
  the accepted direction this decision implements.
- `docs/product/PRD-portfolio-dashboard-mvp.md` — the feature scope and the
  publication/lineage non-goals.
- `docs/reference/BTC_SIGNAL_QUALITY_STUDY.md` — the real 16C evidence the
  first projection and study manifest must expose safely.
- `docs/reference/modules/DASHBOARD_APPLICATION.md` — current contracts,
  scanner and publication path being constrained.
- `docs/planning/sprints/SPRINT_059.md` — D059-01..D059-04, recorded here.
- `docs/planning/sprints/SPRINT_060.md` — the first consumer of this
  contract.
- `docs/planning/PROBLEM_REGISTRY.md` — PRB-022 (pages not covered by the
  import-boundary test).
