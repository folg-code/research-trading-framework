# ADR-0035 — Complete Public Catalog Publication and Immutable Releases

## Status

ACCEPTED

Date: 2026-09-10
Owner: Portfolio Dashboard, Sprint 061 T005
Approved-by: Filip Folga, 2026-09-10 — approval of Sprint 061 decisions
D061-01 through D061-04 and authorization to proceed after accepting the
content outcome.

This ADR extends ADR-0034. It does not replace its deny-by-default projection,
dashboard-local study manifest, content or routing contracts.

## Context

ADR-0034 established a safe projection for one curated Signal Quality study.
The complete portfolio catalog still read the mounted private workspace and
carried `storage_path` through its presentation contracts. Sprint 061 must
publish every safely identifiable result—including negative, incomplete and
unclassified evidence—without making filesystem discovery equivalent to
public visibility.

Two requirements pull in different directions. Catalog visibility should be
automatic, while a public release must be immutable and recoverable. Study
manifests also provide useful editorial grouping, but most historical runs do
not have one and must not disappear for that reason.

## Decision

### 1. Eligibility and public catalog role (D061-01)

Every Market, Signal, Strategy, Robustness or Predictive Research run is
eligible when the build-time scanner can establish a supported workflow and a
safe public identity. Eligibility does not depend on result quality, verdict
value, completeness or manual featuring.

The projection gains the additive `research_catalog_entry` artifact role. Its
allowlist contains only public identity and comparison context: workflow, run
id, title, creation time, DatasetRef, timeframe, framework/artifact versions,
research scope, experiment id, research time range and an optional persisted
verdict. `storage_path`, configuration, source code, binaries and unknown
fields remain excluded.

Artifact ids use the deterministic form `catalog-<workflow>-<run-id>` and must
pass a conservative non-path syntax check. Dataset, experiment and display
identity values must also be non-path values. Unsafe or corrupt runs are
counted as skipped generation diagnostics; they are never partially projected.
Duplicate artifact ids fail generation instead of overwriting evidence.

An absent verdict stays absent in the bundle. The catalog may display
`NO VERDICT`; neither generator nor UI derives a classification from metrics.

### 2. Study-first grouping with deterministic fallback (D061-02)

An explicit, validated `PortfolioStudyManifest` takes precedence and groups
only the artifact roles it names. It remains editorial presentation metadata,
not cross-workflow lineage.

Eligible catalog entries not referenced by a study manifest are grouped by a
deterministic presentation identity:

```text
study group = workflow + source_dataset_ref (or explicit missing-dataset label)
experiment  = persisted experiment_id, otherwise run_id
run         = run_id
```

The UI must label such groups as automatically grouped and lacking an
editorial study manifest. It must not omit them, invent a research relationship
or imply that workflow order is a pipeline. Stable slugs for automatic groups
may hash this canonical tuple; the unhashed public fields remain visible.

### 3. Immutable production release (D061-03)

Committed bundles remain fixtures for tests and demonstrations. Production
generation is an explicit pre-deploy operation over the private workspace. It
writes a candidate into a new versioned host directory, validates the complete
bundle and manifests, then changes the selected release atomically. The
dashboard mounts only the selected projection directory read-only.

A failed scan, sanitization, validation, transfer or selection does not mutate
the active release. Deployment either keeps the previous known-good bundle or
fails closed before the application is restarted. Streamlit never generates a
bundle at request time and never falls back to the private workspace.

The exact host commands, directory names and rollback steps belong to Sprint
061 T007 and the dashboard runbook; the lifecycle above is binding.

### 4. Representative workflow views (D061-04)

Sprint 061 adds exactly one representative persisted-evidence view for each of
the six independent workflows. Alternative views and additional editorial
studies are later iterations. This limits presentation scope and does not
reduce automatic catalog eligibility.

## Alternatives Considered

### Manual curation as the catalog allowlist

Rejected because it creates survivorship bias and permits negative or
incomplete evidence to disappear. Manual selection remains appropriate only
for Home features and editorial notes.

### Publish directly from the mounted workspace

Rejected by ADR-0034 and the accepted dashboard direction. A runtime sanitizer
cannot eliminate the risk created by mounting and navigating private storage.

### Require a study manifest for every run

Rejected because historical evidence predates the presentation contract and a
missing editorial artifact is not a valid reason to hide safe research.

### Replace the active bundle in place

Rejected because partial writes and failed generation would make rollback
ambiguous and could leave the public application with mixed-version evidence.

## Consequences

### Positive

- Public visibility is complete for safely identifiable supported research and
  independent of outcome selection.
- The generator has one tested identity gate, one additive catalog role and no
  path-bearing output.
- Curated studies and automatic historical coverage coexist without creating a
  framework-level Study aggregate.
- Immutable release selection gives deployment a clear rollback boundary.

### Negative

- Build-time discovery still understands historical workspace layouts until
  upstream workflows publish a shared presentation envelope.
- Unsafe or malformed historical runs require explicit repair before they can
  become public.
- Production now needs release-directory lifecycle and cleanup operations.

### Compatibility

The change is additive inside `dashboard.public.v1`. Existing study artifacts
and manifests remain valid. Grandfathered scanner-backed pages remain until
Sprint 061 T006 migrates their public reads; no framework artifact schema or
`user_data` layout changes.

## Follow-up

- T006 consumes `research_catalog_entry`, implements study → experiment → run
  grouping and removes public `storage_path`/`file://` rendering.
- T007 wires versioned generation, validation, read-only mount, rollback and
  quality/boundary coverage into production deployment.
- T008 performs the final security, editorial and visual acceptance pass.

## References

- `docs/adr/ADR-0034-portfolio-publication-boundary.md`
- `docs/planning/sprints/SPRINT_061.md`
- `docs/planning/DASHBOARD_DEVELOPMENT_DIRECTION.md` §8
- `docs/reference/modules/DASHBOARD_APPLICATION.md`
- `docs/adr/ADR-0022-repository-top-level-layout.md`
- `docs/adr/ADR-0002-separate-src-and-user-data.md`
