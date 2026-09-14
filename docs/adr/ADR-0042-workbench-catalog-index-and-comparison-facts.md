# ADR-0042 — Workbench Catalog Index, Artifact Support Classification, and Comparison Compatibility Facts

## Status

ACCEPTED

Drafted during architecture triage of `docs/product/PRD-research-workbench-mvp.md`
(open questions "Catalog rebuild" and "Comparison compatibility"). Approved by
the maintainer in conversation, 2026-09-14.

## Context

The PRD requires the workbench to discover datasets and Signal Research runs
produced by the CLI or scripts — not only its own — to keep unsupported
artifacts visible and never rewrite them, and to compare arbitrary runs showing
material differences without the UI "recreating run-identity logic" or declaring
a winner.

Current facts:

- Canonical truth already exists in `user_data/`: the file-backed dataset
  registry (`market_data/metadata/`) and per-run `manifest.json` envelopes under
  `research/market_research/` (ADR-0011).
- Run identity is already framework-owned and deterministic:
  `derive_run_id` / `derive_run_id_v2` consume exactly the material inputs, and
  `SignalResearchRunManifest` persists them.
- `SignalResearchDefinitionSpec.compute_definition_hash` gives a second,
  configuration-level fingerprint (ADR-0038).
- ADR-0013 already draws the Signal Research analytics boundary: metrics and
  interpretation belong to the research domain, not to a consumer.
- `apps/dashboard` solved a *different* problem (a sanitized public projection,
  ADR-0034/0035) and its catalog code is not reusable here — the workbench reads
  the private workspace directly.

## Decision

### 1. The index is a cache; manifests are the truth

```text
canonical   user_data/market_data/metadata/**   dataset registry + ADR-0040 validation facts
            user_data/research/**/manifest.json run envelopes (ADR-0011)

cache       user_data/workbench/index/          derived, deletable, rebuildable
```

Binding rules:

- The index is fully derivable by rescanning. Deleting it loses nothing.
- No process other than the workbench writes it. The workbench never writes to a
  canonical manifest.
- Where the index and a manifest disagree, the **manifest wins** and the index
  entry is re-read. A displayed research number is always read from the
  artifact, never from the index (the index may cache identity and material
  inputs; it must not cache metrics).
- Index schema changes require no migration — drop and rebuild.

### 2. Rescan is explicit and incremental

- A full rescan runs on control-API start and on an explicit operator action
  ("Rescan workspace"), satisfying the PRD metric about discovering a run created
  outside the application.
- Staleness is detected per artifact by a cheap fingerprint (path, size, mtime).
  A matching fingerprint skips re-parsing.
- Rescan is a read-only operation. It never creates, moves, repairs, or deletes
  an artifact.

### 3. Support classification — visible, never mutating

Every discovered artifact gets exactly one classification and a human-readable
reason:

| Class | Meaning | Shown | Selectable |
|---|---|---|---|
| `SUPPORTED` | manifest readable, `schema_version` known | yes | yes |
| `UNSUPPORTED` | readable identity, unknown or newer `schema_version` | yes, badged, with reason | no |
| `INCOMPLETE` | directory exists, manifest missing/unreadable (e.g. a cancelled or interrupted job — ADR-0041 §6) | yes, badged | no |
| `UNREADABLE` | present but cannot be opened (permissions, corruption) | yes, badged, with the error | no |

Nothing in any class is rewritten, migrated, repaired, or deleted by the
application. An `UNSUPPORTED` artifact can never be confused with a supported
run because it is never offered as an input to a study or a comparison.

### 4. Comparison compatibility facts are framework-owned

A new **application-layer** use case owns the comparison:

```text
trading_framework.application.signal_research.compare_signal_research_runs
    request : tuple[RunDatasetRef, ...]
    result  : SignalResearchComparison
```

The material-input set is exactly the inputs that already determine run
identity — it is derived from the same tuple `derive_run_id_v2` consumes, so the
two can never drift:

```text
source_dataset_ref
research_scope
market_model_ids
signal_model_ids
evaluation_timeframe
requested_range (start, end)
horizon_bars_requested
outcome_definition_fingerprint
occurrence_policy
framework_version
component_lineage_hashes            (includes operator model content, ADR-0039 §6)
```

`SignalResearchComparison` returns, per field: the per-run values, an equality
flag, and a `MaterialDifference` entry with a stable reason code when they
differ. It also returns one `directly_comparable: bool` plus the list of reason
codes behind it.

Binding rules:

- `directly_comparable = False` **never blocks** the comparison. Both runs stay
  fully inspectable (PRD goal).
- A `framework_version` difference alone sets `directly_comparable = False` with
  its own reason code — the computation may have changed underneath.
- The use case **does not rank, score, weight, or select a winner** (ADR-0013,
  PRD non-goal). It returns differences and persisted metrics as they are.
- `apps/workbench` renders this result verbatim. It does not compute equality
  itself, does not maintain its own list of "important" fields, and does not
  derive a verdict. The boundary test forbids the workbench from importing
  `derive_run_id*` or reimplementing the field list.

### 5. Comparison is ephemeral

No durable named comparison workspace (PRD). A selection may be encoded in a URL
query parameter; nothing is written to `user_data/`.

## Alternatives Considered

1. **Index as the source of truth (a real application database).** Rejected:
   `RESEARCH_APPLICATION_PRODUCT_VISION.md` §3.2 says an application database
   "may index [artifacts] but must not make them proprietary to the
   application". A cache that can be deleted is the only shape that satisfies it.
2. **No index; rescan on every page load.** Rejected on the PRD's own scale
   evidence — a workspace with many runs and a 42 MB dataset makes an unindexed
   scan visible in the UI. Also rejected as the *only* mode; an explicit full
   rescan remains available and is the correctness fallback.
3. **Reuse `dashboard_app.publication.catalog`.** Rejected: it is a *sanitizing*
   public projection builder (ADR-0034/0035) that deliberately strips
   `storage_path` and every private field. The workbench needs the private
   facts, and coupling the two would make a public-surface allow-list change
   break a private tool.
4. **Compute compatibility differences in the workbench UI from manifest JSON.**
   Rejected: it duplicates run-identity semantics in a consumer, which is the
   PRD's explicit prohibition and would silently drift the moment
   `derive_run_id_v2` gains a field.
5. **Auto-migrate or auto-repair `UNSUPPORTED` / `INCOMPLETE` artifacts.**
   Rejected: PRD non-goal, and it destroys the historical evidence the
   maintainer is trying to keep visible.
6. **Delete `INCOMPLETE` run directories after a cancelled job.** Rejected: the
   application does not delete artifacts. Manual cleanup only.

## Consequences

### Positive

- A run created by the CLI, a script, or the workbench is one discoverable
  history in one workspace, with no ownership marker.
- The index can be corrupted or deleted with zero research consequences.
- Comparison semantics live next to run identity, so one change updates both.

### Negative

- A second reader of the run manifest format exists (after the dashboard's
  publication generator), so a manifest schema change now has two consumers.
- Fingerprint-based staleness can miss an in-place edit that preserves size and
  mtime. Accepted; the explicit full rescan is the escape hatch.
- `compare_signal_research_runs` is new application surface that must be covered
  by tests independently of the UI that consumes it.
- Classifying an artifact `UNSUPPORTED` requires an explicit registry of known
  `schema_version` values — a list that must be maintained as schemas evolve.

## Follow-up

- Sprint Wave 0 must bind: the index storage format (JSON file vs SQLite), the
  reason-code vocabulary for `MaterialDifference`, and the known-`schema_version`
  registry location.
- Whether the same comparison contract generalizes to Strategy / Robustness /
  Predictive runs is explicitly **out of scope** here (PRD non-goals) and should
  be revisited when those workflows enter the workbench.

## Related

- `docs/adr/ADR-0011-signal-research-outcomes-and-persistence.md`
- `docs/adr/ADR-0013-signal-research-analytics-boundary.md`
- `docs/adr/ADR-0007-dataset-lifecycle-and-publication.md`
- `docs/adr/ADR-0034-portfolio-publication-boundary.md`
- `docs/adr/ADR-0037-research-workbench-application-boundary.md`
- `docs/adr/ADR-0040-import-validation-findings-and-acknowledgement.md`
- `docs/adr/ADR-0041-workbench-local-job-runner.md`
- `docs/vision/RUN_IDENTITY_AND_CONFIGURATION.md`
