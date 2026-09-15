# ADR-0040 — Import Validation Findings: Fatal, Acknowledgeable, and Where Acknowledgement Lives

## Status

ACCEPTED

Drafted during architecture triage of `docs/product/PRD-research-workbench-mvp.md`
(open question "Import warning contract"). Approved by the maintainer in
conversation, 2026-09-14.

## Context

The PRD requires that structurally fatal errors cannot be bypassed, that
nonfatal warnings may be acknowledged, and that an acknowledgement "must remain
visible in the resulting dataset's validation facts" — without "inventing a
second dataset lifecycle in the application".

Current facts:

- `src/trading_framework/market/validation/protocols.py` already defines
  `ValidationSeverity = ERROR | WARNING`, `ValidationIssue`, and
  `ValidationResult.is_valid` (true when no `ERROR` is present), plus
  `to_dict()`.
- `application/market_data/import_external_dataset.py` computes a
  `ValidationResult`, writes bars **only if** `is_valid`, and registers
  `DatasetMetadata` with `validation_status = PASSED | FAILED`.
- `application/market_data/finalize_dataset.py` refuses to finalize unless
  `validation_status is PASSED`.
- **The `ValidationResult` itself is never persisted.** Only the two-valued
  enum survives. A `WARNING` is therefore invisible the moment the import
  function returns — there is nowhere for an acknowledgement to remain visible,
  because there are no persisted validation facts to attach it to.

## Decision

### 1. Severity classification is framework-owned

```text
ValidationSeverity.ERROR    fatal. Blocks bar writes and blocks FINALIZED.
                            Not acknowledgeable, not overridable, no UI escape.
ValidationSeverity.WARNING  nonfatal. Acknowledgeable. Never auto-corrected.
```

`apps/workbench` does not classify, re-rank, downgrade, or filter findings. It
renders `ValidationResult.to_dict()` and offers acknowledgement only for
`WARNING` entries. A validator that produces a new finding is the single place
where its severity is decided.

### 2. Validation facts are persisted with the dataset

`ImportExternalDatasetResult` already returns the `ValidationResult`; it must
also be stored so it survives the workflow. The serialized
`ValidationResult.to_dict()` is written as a **dataset validation facts
sidecar** alongside the existing dataset metadata, keyed by `DatasetRef`, and
exposed through the existing registry read path.

```text
user_data/market_data/metadata/<dataset ref>/validation.json
    { "schema_version": "market_data.validation_facts.v1",
      "is_valid": bool,
      "issues": [ {message, severity, row_number, field}, ... ],
      "acknowledged": [ {finding_key, acknowledged_at_utc, note?}, ... ] }
```

Rationale for a sidecar rather than new `DatasetMetadata` fields: findings are
an unbounded list (a 1.3M-row import can produce many), and `DatasetMetadata` is
a small identity/lifecycle record read on every catalog scan. Keeping it small
matters for ADR-0042's index.

`DatasetMetadata` keeps only the existing `validation_status`, plus one
additional boolean-ish summary derived at write time (`warning_count`), so a
catalog listing can show "has warnings" without opening the sidecar.

### 3. Acknowledgement gates FINALIZE, not IMPORT

No second lifecycle is introduced. The existing `WORKING → FINALIZED →
PUBLISHED` transitions (ADR-0007) carry the whole contract:

```text
import   → always records findings. ERROR ⇒ no bars written, status FAILED.
finalize → refuses while any WARNING is unacknowledged.
           finalize_dataset gains an explicit `acknowledged_findings` argument.
publish  → unchanged. A published dataset carries its findings and
           acknowledgements immutably (ADR-0007: no mutation after publication).
```

Placing the gate at finalize (not import) means: an import always produces a
complete, inspectable record of what is wrong; nothing becomes a consumable
research input until a human has explicitly seen and accepted every nonfatal
finding; and a cancelled or abandoned import leaves a `WORKING` dataset, which
ADR-0007 already excludes from consumer queries.

### 4. Acknowledgement identity

An acknowledgement targets a **finding key**, not an index into a list:

```text
finding_key = sha256(severity | field | message-template | row_number-bucket)
```

Re-running validation must not silently carry an acknowledgement across to a
different finding. If the recomputed finding set does not contain a key that was
acknowledged, the acknowledgement is retained in the record as
`stale: true` rather than deleted — the PRD forbids rewriting evidence.

### 5. Acknowledgement is one-way and attributed

An acknowledgement records `acknowledged_at_utc` and an optional free-text note.
It cannot be revoked once the dataset is FINALIZED or PUBLISHED (immutability).
Before finalization, removing an acknowledgement is allowed and is itself
recorded (append-only list). The UI never acknowledges implicitly — no
"acknowledge all" default, no acknowledgement as a side effect of navigation.

## Alternatives Considered

1. **Acknowledgement stored in a workbench-owned database.** Rejected: the
   acknowledgement is a fact *about the dataset*, and a dataset produced through
   the CLI must carry the same facts. Storing it application-side would make the
   dataset's meaning depend on which front door created it — exactly the "second
   dataset lifecycle" the PRD forbids.
2. **Gate at import (refuse to import until warnings are acknowledged).**
   Rejected: the operator cannot meaningfully acknowledge a finding that does not
   exist yet, and it would force a two-pass import of a 42 MB file.
3. **A new lifecycle state (e.g. `NEEDS_REVIEW`).** Rejected: it duplicates what
   `WORKING` already means and would require migrating existing datasets and
   every lifecycle transition test.
4. **Add all findings to `DatasetMetadata`.** Rejected: unbounded growth in a
   record read on every catalog scan (§2).
5. **Let the UI decide which warnings are important.** Rejected: it puts a
   data-quality judgement in the presentation layer, contradicting the PRD's
   "no compatibility facts computed in the presentation layer".

## Consequences

### Positive

- Warnings stop being invisible after import — a real gap today, independent of
  the workbench.
- Fatal-vs-acknowledgeable is a single framework-owned rule usable by the CLI,
  the workbench, and any future consumer.
- No new lifecycle, no new dataset states, no migration of published datasets.

### Negative

- A new persisted artifact (`validation.json`) and therefore a new
  schema version to maintain and to classify in ADR-0042's support model.
- `finalize_dataset` gains a required-in-practice argument; existing callers
  (scripts, `trading-cli data fetch`) must pass an explicit empty
  acknowledgement set, and any dataset with warnings that finalized silently
  before will now refuse. That is a deliberate behaviour change and must be
  called out in the sprint's acceptance criteria.
- Pre-existing published datasets have no validation facts sidecar. They are
  displayed as `facts unavailable (imported before v1)`, never as "no warnings".

## Follow-up

- Sprint Wave 0 must bind the `finding_key` formula (specifically the
  `row_number` bucketing, so a per-row warning does not produce a million keys)
  and the maximum number of findings retained verbatim before truncation with a
  count.
- The Binance acquisition path (ADR-0025) must be checked for whether it
  produces `ValidationResult` findings at all, or only provider-level errors.

## Related

- `docs/adr/ADR-0007-dataset-lifecycle-and-publication.md`
- `docs/adr/ADR-0025-binance-usdm-historical-klines-import.md`
- `docs/adr/ADR-0042-workbench-catalog-index-and-comparison-facts.md`
- `src/trading_framework/market/validation/protocols.py`
- `src/trading_framework/application/market_data/import_external_dataset.py`
- `src/trading_framework/application/market_data/finalize_dataset.py`
