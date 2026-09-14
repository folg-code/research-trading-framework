# Sprint 064 — Wave 0 Decisions

Binding decisions for the Research Application MVP (Phase 17, increments 17A
and 17B). Date: 2026-09-14.

```text
Status: APPROVED — all D-S064-08 checklist items confirmed by the maintainer
        in conversation, 2026-09-14 (see Approved-by below for the two
        deviations from the original proposal). `engineer` may start
        S064-T001 on `feat/signal-definition-schema-version`, cut from
        `sprint/research-application-mvp`.

Basis:  docs/planning/roadmap/PHASE_17_RESEARCH_APPLICATION.md — ACCEPTED
                (maintainer 2026-09-14)
        docs/product/PRD-research-workbench-mvp.md — ACCEPTED
                (maintainer 2026-09-14)
        docs/adr/ADR-0037, ADR-0038, ADR-0039, ADR-0040, ADR-0041, ADR-0042 —
                all ACCEPTED (maintainer 2026-09-14)
        docs/adr/ADR-0026 (+ Amendment 1), ADR-0027, ADR-0007, ADR-0011,
                ADR-0013, ADR-0022 — consumed as constraints, not reopened
        docs/planning/sprints/SPRINT_064.md (Status: Draft)
        docs/archive/planning/PROJECT_MANAGEMENT.md §14 Definition of Ready
        src/ and apps/ as on `main` @ 1bd662a (2026-09-14)
```

---

## Inherited locks (do not reopen)

```text
ADR-0037 §2  workbench_core MAY import trading_framework.application.* and the
             ADR-0026 Amendment 1 allow-list; MUST NOT import research.*,
             market_analysis.*, strategy.*, execution.* or other infrastructure
             adapters. workbench_ui MUST NOT import trading_framework at all.
             Enforced by tests/unit/test_apps_boundaries.py.
ADR-0037 §4  workbench-api and the runner bind to LOOPBACK ONLY. No auth, no
             roles, no TLS. Public exposure is unsupported and documented so.
ADR-0037 §5  Link out to the existing report/dashboard. No iframe, no reverse
             proxy, no dashboard_app import.
ADR-0037 §6  Nothing in apps/workbench publishes anything.
ADR-0038 §1  SignalResearchDefinitionSpec is the single source of truth. No
             second study schema, no presentation-side mirror dataclass, no
             reimplemented validation. UI shows the framework's own error text.
ADR-0038 §2  Unknown/newer schema_version is REFUSED and classified
             UNSUPPORTED. Never migrated, never rewritten. schema_version is
             INCLUDED in compute_definition_hash for v1 — the resulting
             mismatch with historical run manifests is documented, not patched.
ADR-0038 §5  One submission = one explicitly specified study. No UI field
             expands into a grid. No multi-variant model_family template.
ADR-0040 §1  ERROR is fatal and not acknowledgeable by any UI escape. WARNING
             is acknowledgeable and never auto-corrected. The workbench does
             not classify, re-rank, downgrade or filter findings.
ADR-0041 §2  One job = one OS subprocess invoking trading-cli. workbench_core
             MUST NOT call run_signal_research or import_external_dataset
             in-process for a job.
ADR-0041 §6  A cancelled or interrupted job never advances an artifact to
             FINALIZED or PUBLISHED and never produces a readable run manifest.
             The application never deletes an artifact.
ADR-0041 §7  The runner parses ONLY structured events. Deriving a percentage,
             ETA, row count or any other number from human-readable stdout,
             log text or file size is FORBIDDEN.
ADR-0042 §1  The index is a deletable cache; manifests are the truth. A
             displayed research number is read from the artifact, never the
             index.
ADR-0042 §4  Comparison compatibility facts are framework-owned and derived
             from derive_run_id_v2's material-input tuple. The workbench never
             reimplements the field list and never ranks or picks a winner.
PRD          No grid search, sweep, hyperopt or automated candidate generation.
             No metric computation in the presentation layer. No editing,
             repairing, deleting or silently migrating any artifact. No
             automatic retry or resume after restart.
ADR-0026 A1  apps/cli's 17-module import allow-list. Widening it is a fresh ADR
             amendment with maintainer approval — never a test-file edit.
             apps/workbench inherits this list AS-IS (ADR-0037 §2).
ADR-0027 §2  Operator-authored Python: no sandbox, no import restriction, no
             AST inspection. Not weakened here.
```

---

## D-S064-01 — Preview and import performance envelope

**Proposed:** bind this decision **after measurement**, not now. Sprint 064's
T009 produces the numbers; the envelope below is the starting hypothesis the
measurement confirms or corrects.

```text
PROPOSED STARTING POINT (subject to T009)

preview   Polars lazy scan with a head limit of 1,000 rows. The browser never
          receives more than that slice, regardless of file size. The preview
          reads the OPERATOR'S SOURCE FILE and leaves it untouched (PRD).
import    reference dataset (~1.3M rows / 42.5 MB) completes in <= 120 s
          wall time and <= 2 GB peak RSS on the maintainer's Windows machine.
scale     the envelope is stated against ONE named reference dataset, not as a
          general throughput guarantee.
```

```text
REASON    The PRD's success metric is "previewed and imported without loading
          or rendering the entire dataset in the browser". A head limit is the
          only shape that makes that structural rather than aspirational.
REASON    1,000 rows is enough to confirm a column mapping and a timestamp
          format by eye, and is a small JSON payload.

MEASURED CONCERN — this is why the decision is routed to a spike.
          application/market_data/import_external_dataset.py currently does:
              normalized_rows = list(csv_importer.iter_rows(...))
              bars = [_market_bar_from_row(row) for row in normalized_rows]
          Two FULL in-memory materializations, the second of MarketBar objects
          wrapping Price/Volume values, before validation runs. At 1.3M rows
          the 2 GB RSS figure is a hypothesis that may already be false TODAY,
          with no workbench involved.

IF THE MEASUREMENT MISSES THE ENVELOPE, the proposed response is to record the
          real numbers as the bound envelope for 17C and open a separate
          streaming-import decision — NOT to refactor the import path inside
          Sprint 064, and NOT to quietly relax the number until it passes.
```

```text
NOT DECIDED HERE   the preview's column-inference rules, the mapping-form
                   contract, and chunked/streaming import. All are 17C.
```

**Needs maintainer sign-off.** Blocks 17C, not Sprint 064.

---

## D-S064-01 amendment — T009 measurement results (2026-09-14)

```text
REFERENCE DATASET
    user_data/workspace/market_data/normalized/BTCUSDT.P/ohlcv/1m/binance/
    binance-usdm-klines-v1/v1/bars.parquet -- 1,311,840 rows, 41.6 MB as
    Parquet on disk. This IS the dataset the PRD's "~1.3M rows / 42.5 MB"
    success metric names (row count matches almost exactly; the "42.5 MB"
    figure is the Parquet form's size, not any CSV re-encoding of it -- see
    the CSV-only finding below).

ENVIRONMENT
    Windows, Python 3.12, uv 0.11.14, polars 1.42.1, maintainer's machine.
    Peak memory measured via GetProcessMemoryInfo (PeakWorkingSetSize) --
    the Windows analogue of POSIX peak RSS -- through a small ctypes helper,
    NOT a new dependency (psutil was considered and deliberately not added
    for a one-off spike). Each number below is from a fresh process running
    exactly one operation, so it is not inflated by unrelated prior work in
    the same process.

REPRODUCE
    scratch/s064_t009/prepare_csv.py     -- builds the CSV fixture once
    scratch/s064_t009/measure_preview.py -- preview cost at 3 head limits
    scratch/s064_t009/measure_import.py  -- the real, unmodified
                                             import_external_dataset() call
    (scratch/ is gitignored; these files are not committed -- paste them
    back from this repo's working tree, or from this PR's diff before merge,
    to reproduce. Run each with `uv run python scratch/s064_t009/<file>.py`
    from the repo root.)

RESULTS -- import_external_dataset (2 runs, both against the same 88.3 MB
           CSV re-encoding of the reference dataset -- see finding below for
           why CSV, not the smaller Parquet form)
    wall time         53.4 s / 54.4 s   -- <= 120 s target: MET, ~2.2x margin
    peak working set   2100 MB / 2099 MB -- <= 2 GB target: MISSED by ~5%
    validation         0 issues, all 1,311,840 rows valid, both runs

RESULTS -- preview (pl.scan_csv(path).head(N).collect(), fresh process,
           3 head limits against the same 88.3 MB CSV)
    head=100      9.8 ms  (cold-start dominated)
    head=1,000    1.7 ms
    head=5,000    2.5 ms
    peak working set for the whole preview process: 80.6 MB
    verdict: the proposed <=1,000-row lazy-scan preview is met with a huge
    margin -- single-digit milliseconds regardless of file size, because
    Polars' lazy CSV scan genuinely only reads the requested head, not the
    file. NOT a source of memory or latency risk at any measured scale.

NEW FINDING, not anticipated at Wave 0 -- CSV-only import path
    import_external_dataset() / CsvOhlcvImporter only accept CSV today:
    CsvFileInspector.inspect() raises ValidationError for any other detected
    format, and iter_rows() re-raises before reading a single row. A Parquet
    source file is REFUSED outright, not merely slower. This means:
      - the reference dataset's own natural form (Parquet, 41.6 MB) could
        not be measured through this path at all; it had to be re-encoded to
        CSV first, which is 88.3 MB -- roughly 2.1x larger as uncompressed
        text than the Parquet source the PRD's "42.5 MB" figure describes.
      - 17C's PRD requirement ("a local CSV or Parquet file") is NOT
        currently satisfied by any existing code path -- a Parquet importer
        is new work for 17C, not a wire-up of something that already exists.
      - the measured numbers above are for the CSV path only. A Parquet
        import path may have a materially different profile (Parquet is
        already columnar and compressed; polars can stream it), but that is
        unmeasured and out of this spike's scope.

RECOMMENDATION TO THE MAINTAINER
    1. Preview design: CONFIRM as proposed, no change. Head-limit lazy scan
       has essentially unmeasurable cost against this reference scale.
    2. Import wall-time envelope: CONFIRM <= 120 s, no change (met at 54 s,
       plenty of margin even accounting for a slower operator machine).
    3. Import peak-RSS envelope: the current, UNMODIFIED CSV import path
       misses the proposed <= 2 GB target by roughly 100 MB (~5%) for the
       reference dataset. Per this decision's own "if the measurement
       misses the envelope" clause: recorded here as a finding, NOT acted on
       by refactoring inside Sprint 064. Two honest options for 17C, not
       decided here:
           (a) raise the accepted MVP envelope to ~2.5 GB and treat the two
               full in-memory materializations in import_external_dataset()
               (list(iter_rows(...)) then a second list[MarketBar]) as a
               named, logged technical-debt item with 17C as its repayment
               trigger, or
           (b) require a bounded/streaming rewrite of those two
               materializations before 17C ships, which is real scope, not
               a formatting fix.
       This spike takes no position between (a) and (b) -- that trade-off
       belongs to the maintainer, not to the person who ran the measurement.
    4. NEW decision needed for 17C, not previously identified: whether to
       build a Parquet import path (a real new capability, not a config
       flag) or explicitly narrow the MVP's "CSV or Parquet" PRD language to
       CSV-only for the first 17C increment, with Parquet as a stated
       follow-up. Recorded here so 17C's own Wave 0 inherits this rather
       than rediscovering it.

STATUS: measurement complete. Points 1 and 2 confirmed as proposed (numbers
        already clear the bar). Points 3 and 4 decided by the maintainer in
        conversation, 2026-09-14 -- see the bound 17C technical direction
        immediately below. This amendment is now CLOSED; further refinement
        of the streaming design belongs to 17C's own Wave 0, not here.
```

---

## D-S064-01 amendment, part 2 — bound 17C technical direction (2026-09-14)

The maintainer chose **option (b)** from the recommendation above: the
bounded/streaming rewrite is **required before 17C ships an import feature**,
not deferred as accepted technical debt. The maintainer also confirmed 17C
must build a **real Parquet import path**, not narrow the PRD's "CSV or
Parquet" language to CSV-only.

Discussed and refined in conversation into a concrete design, recorded here
so 17C's own Wave 0 inherits it rather than re-deriving it from scratch:

```text
REJECTED APPROACH   manual batch-loop chunking exposed as business logic
                     inside import_external_dataset() (e.g. "read 50k rows,
                     validate, write, repeat"). Correct in spirit but pushes
                     an implementation detail into use-case code.

CHOSEN APPROACH      single forward pass + writer-internal batching +
                     temp-file/atomic-rename publish. Concretely:

  1. iter_rows() is already a lazy generator -- unchanged.
  2. Normalize NormalizedBarRow -> MarketBar lazily (a generator expression,
     not a list comprehension) -- replaces
     `bars = [_market_bar_from_row(row) for row in normalized_rows]`.
  3. OhlcvBarValidator gains a streaming-compatible entry point that
     consumes an Iterable[MarketBar] instead of requiring a materialized
     Sequence. Low risk: the existing algorithm (ohlcv_validator.py) is
     ALREADY single-pass -- one `seen_observed_at` set for duplicate
     detection anywhere in the file, one `previous_observed_at` scalar for
     ordering. No algorithmic change, only the input type and iteration
     style change.
  4. ParquetBarWriter gains a NEW incremental write method that batches
     internally (pyarrow row groups every N rows -- Parquet's own columnar
     format makes some internal batching unavoidable; this is an
     implementation detail of the writer, never exposed as chunking logic
     to callers). ADDITIVE: the existing `write()` / `write_table()` API is
     UNCHANGED, so the two other current callers
     (import_binance_futures_ohlcv.py, derive_ohlcv_from_trades.py) are not
     touched and need no re-testing.
  5. The incremental write targets a TEMPORARY path. Only if validation is
     clean at the end of the single pass does the temp path get atomically
     renamed into place; otherwise it is discarded. This preserves today's
     invariant (never write invalid/partial data as the published artifact)
     WITHOUT a second read pass over the source file -- validate and write
     happen in the same forward pass, not two separate passes.
  6. start_at/end_at (today read from bars[0]/bars[-1]) become "first bar
     seen" (trivial) and "last bar seen so far" (an O(1) running variable),
     available identically at the end of a single forward pass.

MEMORY FLOOR AFTER THIS REFACTOR   not zero. `seen_observed_at` remains
     O(n) -- a set of timestamps, needed because a duplicate can appear
     anywhere in an operator-supplied file, not just adjacently. This is
     far cheaper per row than today's full MarketBar list (a timestamp vs.
     four Price(Decimal)-wrapped fields plus two datetimes), but 17C must
     MEASURE the actual peak after implementing, not assume a number --
     this decision does not pre-commit to a new RSS target.

BLAST RADIUS   import_external_dataset.py (rewritten), OhlcvBarValidator
     (new streaming-compatible method added), ParquetBarWriter (new
     incremental method added). NOT touched: the existing bulk write()
     path or its two other current callers.

PARQUET IMPORT PATH   a genuinely new component for 17C, not a wire-up of
     existing code -- CsvFileInspector today refuses any non-CSV format
     outright (confirmed by T009). The streaming design above should be
     written provider-agnostically where practical (e.g., the incremental
     writer and validator changes benefit both a future Parquet importer
     and the existing CSV one), but the actual Parquet reader/importer
     itself is unstarted, separate work.

NOT DECIDED HERE   the exact row-group / batch size for the incremental
     writer, the temp-file naming/location convention, and whether the
     Parquet importer reuses polars' own streaming CSV/Parquet engine or a
     hand-rolled reader. All are 17C implementation decisions, not bound by
     this conversation.
```

**Binding scope for 17C**, not Sprint 064. No code changes in this sprint;
`docs/planning/roadmap/PHASE_17_RESEARCH_APPLICATION.md`'s 17C increment
description is updated to reference this direction.

---

---

## D-S064-02 — Catalog index storage format (ADR-0042 §1)

**Proposed:** JSON files, not SQLite.

```text
PROPOSED   user_data/workbench/index/datasets.json
           user_data/workbench/index/signal_research_runs.json
           one document per artifact kind; each entry carries the artifact's
           identity, its (path, size, mtime) staleness fingerprint, its
           ADR-0042 §3 support classification and its reason string.
           Schema change => delete and rebuild. No migration path, ever.

REASON     ADR-0042 §1 requires "deleting it loses nothing". A text file a
           maintainer can open, read and delete makes that property obvious
           rather than asserted.
REASON     Consistent with ADR-0041 alternative 4, which deferred SQLite for
           job state on the same "inspectable, no migration" grounds. Two
           storage technologies for two caches in the same directory tree would
           be an odd split.
REASON     Index entries never hold metrics (ADR-0042 §1), so the record is
           small; the scale driver is artifact COUNT, not payload size.

REVISIT TRIGGER  a full index load becomes visible in the UI, or the workspace
                 exceeds roughly a few thousand runs. At that point SQLite is
                 a drop-in replacement precisely because nothing depends on the
                 format.
REJECTED   SQLite now. It buys query capability the MVP has no use for and
           costs the "open it in a text editor" property while the index is
           still small enough that no query planner matters.
```

**Needs maintainer sign-off.** Blocks 17D, not Sprint 064.

---

## D-S064-03 — Job concurrency and termination window (ADR-0041 §8)

**Proposed:**

```text
DEFAULT    max_concurrent_jobs = 1, FIFO.
CONFIG     a single integer setting with an enforced maximum of 4. Values above
           it are refused at startup with an explicit message.
QUEUEING   submissions beyond the limit sit in QUEUED. Cancelling a QUEUED job
           is immediate and yields terminal CANCELLED with no subprocess spawned.
GRACE      SIGTERM (POSIX) / the Windows terminate equivalent, then a 20 s
           window, then hard kill. The window is configurable; the DEFAULT is
           part of this decision (raised from a 10 s starting proposal to 20 s
           at the maintainer's request, 2026-09-14).
RECORDED   job.json records which termination path was taken (graceful vs
           killed), because they are operationally different events.

REASON     One maintainer, one machine, jobs measured in minutes; a second
           concurrent Polars-heavy subprocess competes for the same RAM that
           D-S064-01 is worried about. FIFO at 1 is the honest default.
REASON     The cap of 4 exists so a configuration typo cannot spawn twenty
           subprocesses on a laptop.
REASON     20 s is long enough for a Python process to unwind and short enough
           that an operator who clicked Cancel does not think it was ignored.
           No framework workflow currently has a cleanup handler that needs
           longer, because none has a cleanup handler at all.

OPEN SUB-QUESTION for the maintainer: on Windows, terminating a `uv run`
           wrapper may leave the grandchild Python process alive. The proposed
           handling is a job object / process-tree kill, verified by an actual
           Windows test in T007 — not assumed from the POSIX behaviour. If the
           process-tree kill turns out to need a new dependency, that is a
           STOP-AND-REPORT, not an in-sprint dependency addition.
```

**Needs maintainer sign-off. Blocks S064-T006 and S064-T007.**

---

## D-S064-04 — Phase lists and structured-event schema (ADR-0041 §7)

**Proposed:** schema `workbench.phase_event.v1`.

```text
EVENT SHAPE (one JSON object per line, on stdout)

{"schema_version":"workbench.phase_event.v1",
 "event":"phase",
 "job_kind":"research.run.signal",
 "name":"resolve",
 "index":1,
 "of":5,
 "at":"2026-09-14T10:11:12.000Z"}

RULES
- index is 1-based; `of` equals the declared list length and never changes
  mid-job.
- Phases are emitted in declared order. A phase is emitted when it STARTS.
- A job that fails mid-phase emits no further phase events; the failure is the
  exit code, not an event.
- No other event type in v1. No "progress", no "row", no "eta", no "log" event
  — ordinary stdout stays ordinary stdout and is surfaced verbatim.
- The event lines are a VERSIONED CONTRACT. Renaming a phase is a version bump.
```

```text
PROPOSED PHASE LISTS (static, ordered, declared per job kind)

research.run.signal   (5)
    load-definition  ->  resolve-models  ->  load-dataset  ->  evaluate  ->
    persist
    Rationale: these are the real seams in
    resolve_signal_research_definition -> map_definition_to_run_request ->
    run_signal_research. `evaluate` is the long one and is honestly a single
    opaque phase — the UI compensates with elapsed time and logs (ADR-0041
    Consequences).

data.import.local     (5)   DECLARED NOW, EMITTED IN 17C
    read  ->  normalize  ->  validate  ->  write  ->  register
    Matches ADR-0041 §7's own worked example and the actual sequence in
    import_external_dataset.

data.fetch.binance    (4)   DECLARED NOW, EMITTED IN 17C
    plan-range  ->  fetch  ->  write  ->  finalize
    `fetch` covers all pagination; ADR-0041 §7 names exactly this case as the
    trigger for a future Tier 2 ProgressSink, which stays DEFERRED.
```

```text
LOCKED BY THIS DECISION (if approved)
- Sprint 064 implements emission for research.run.signal ONLY. The other two
  lists are declared here so 17C inherits a decision rather than reopening one.
- A phase list is not a progress bar. The UI may render "step 3 of 5"; it may
  NOT interpolate a percentage within a phase.
```

**Needs maintainer sign-off. Blocks S064-T005 and S064-T006.**

---

## D-S064-05 — `finding_key` bucketing and finding truncation (ADR-0040 §4)

**Proposed:**

```text
finding_key = sha256( severity | field | message_template | row_bucket )

message_template   the finding's message with every embedded numeric/literal
                   value removed, so "gap at row 41 (3 bars)" and "gap at row
                   9001 (7 bars)" share a template. Validators must expose the
                   template explicitly rather than the UI regex-stripping the
                   rendered string.
row_bucket         floor(row_number / 10_000), rendered as an integer.
                   A row-less finding uses the literal "none".

TRUNCATION
    at most 1,000 findings retained verbatim in validation.json, ordered
    ERROR-first then by first occurrence; beyond that the sidecar records
    {"truncated": true, "omitted_count": N} per (severity, template) group.
```

```text
REASON   ADR-0040's own worry is "a per-row warning does not produce a million
         keys". A 10,000-row bucket turns a 1.3M-row dataset's worst case into
         at most 130 keys per template — reviewable by a human, which is the
         point, since a human must acknowledge each one to finalize.
REASON   Bucketing rather than dropping row_number entirely keeps an
         acknowledgement LOCAL: acknowledging a gap cluster at rows 40k-50k
         does not silently acknowledge a new, different cluster at row 900k.
REASON   The template must come from the validator, not from string surgery in
         a consumer — otherwise the key silently changes when someone reworks a
         message string, and ADR-0040 §4's stale-acknowledgement machinery
         starts firing for cosmetic reasons.

CONSEQUENCE, stated plainly: a bucket is a coarsening. Two genuinely different
         findings of the same template within the same 10,000 rows collapse to
         one key and one acknowledgement. That is the deliberate trade for
         reviewability, and 10_000 is the number the maintainer is being asked
         to accept.

REJECTED  row_number verbatim in the key (a million keys, unacknowledgeable).
REJECTED  row_number omitted from the key (one acknowledgement silently covers
          every future occurrence anywhere in the file — exactly the carry-over
          ADR-0040 §4 forbids).
```

```text
MAINTAINER ADDITION (2026-09-14) — a summary report, not just bucketed findings

The maintainer needs an aggregate gap-quality report per import, not only the
per-finding list above: total gap count, % of expected bars missing, and the
longest single gap. validation.json's per-artifact-kind schema (17C) must
carry a `summary` section alongside `findings`, e.g. (illustrative, not final):

    "summary": {
        "gap_count": <int>,
        "missing_bar_pct": <float>,
        "longest_gap": {"start": <ts>, "end": <ts>, "bars_missing": <int>}
    }

SESSION AWARENESS — explicitly flagged, NOT resolved here. The reference
scale covers both session-bound instruments (CFD/Futures, with trading
hours — a bar missing outside the session is not a data gap) and crypto
(24/7 — any missing expected bar is a real gap). "Expected bars" therefore
means different things per `AssetClass`
(`src/trading_framework/market/models/instrument.py`). A repo scan at triage
time found NO trading-calendar/session-hours module in the framework today —
this is new scope, not an existing capability the workbench can just call.

ROUTED, NOT DECIDED: 17C's own design work must resolve (a) where
session-awareness lives (framework-owned, not the workbench — consistent
with "no metric/analysis logic in the presentation layer"), (b) whether it
needs its own ADR given it is a new domain concept (a trading calendar), and
(c) the exact `summary` schema. This maintainer requirement is binding scope
for 17C; the row-bucketing mechanics above (finding_key, 10k-row buckets,
1,000-item cap) still apply to the per-finding list and are unaffected by
adding a summary.
```

**Needs maintainer sign-off.** Decision only; no ADR-0040 code ships in Sprint
064 (17C owns it). The summary-report and session-awareness requirement above
is captured as binding scope for 17C, to be resolved by that increment's own
design work (or a small ADR if session-awareness proves to be a new domain
concept), not invented ad hoc inside the UI.

---

## D-S064-06 — Template roots, collision rule and initial set (ADR-0038 §4)

**Proposed:**

```text
PRECEDENCE   on a template_id collision, the FRAMEWORK template is the one
             applied. The USER template is still LISTED, badged `SHADOWED`,
             with the framework template_id it collides with named in the
             reason. It is never silently dropped and never silently wins.
SELECTABLE   a SHADOWED user template is NOT selectable under the colliding
             id. If the operator wants it, they rename its template_id — an
             explicit act.
REQUIRED KEYS  template_id, template_version, title, description, plus a
             `definition:` block holding a partial SignalResearchDefinitionSpec
             payload. Unknown top-level keys are a listing-time warning on the
             entry, not a hard failure of the whole listing.
VERSIONING   template_version is an integer, bumped on any material change. A
             template is never edited in place across a version.
PROVENANCE   applying a template records template_id/template_version in the
             run manifest's resolved_parameters. The template is NOT part of
             run identity (ADR-0038 §4).

MALFORMED    a user template that fails to parse is listed as UNSUPPORTED with
             its parse error. One bad file never breaks the listing.
NO EXECUTION a template is data. Listing opens no .py file, imports nothing,
             and resolves no model (ADR-0038 §4, ADR-0039 §4).
```

```text
PROPOSED INITIAL FRAMEWORK SET (3)

1. minimal-single-signal     the smallest valid definition: one built-in
                             market model, one built-in signal model, one
                             horizon. The "does my setup work at all" template.
2. multi-horizon-baseline    one signal evaluated across several horizons with
                             the baseline comparison configured. The
                             representative real study shape.
3. quality-rules-strict      the same shape with SignalResearchQualityRules
                             tightened, to make the rules discoverable as a
                             concept rather than a field nobody finds.

CONSTRAINT   none may ship a multi-variant model_family (ADR-0038 §5), and none
             may reference a USER_FILE model (ADR-0039 is not in this sprint).

REASON       Three covers: the trivial case, the realistic case, and one
             deliberately non-default configuration — enough to prove the
             lister and the collision rule without becoming a template library
             to maintain. The third is first in SPRINT_064.md's descope order.

MAINTAINER NOTE (2026-09-14): the collision rule (framework wins, user
template listed as SHADOWED) is APPROVED. The exact initial template set is
explicitly NOT decided yet — revisit before S064-T003 starts, not blocking
the rest of Sprint 064's approval.
```

```text
REJECTED   user-wins precedence. A fork's maintained starting point would then
           be silently replaceable by a stale local file with the same id, and
           the failure mode ("why is this template different on my machine?")
           is invisible.
REJECTED   hard error on collision. It would make one bad user file block a
           framework template the operator did nothing to break.
```

**Needs maintainer sign-off. Blocks S064-T003.**

---

## D-S064-07 — The `definition_hash` break is accepted, not patched

```text
INHERITED FROM ADR-0038 §2 (ACCEPTED) — restated here because it is the one
decision in this sprint that changes the meaning of EXISTING persisted data.

schema_version is included in compute_definition_hash for v1. Therefore every
definition_hash recorded in a past Signal Research run manifest will no longer
match a re-serialized spec for the same study.

LOCKED  Past run manifests are IMMUTABLE and are NOT rewritten, backfilled or
        migrated. Not by a script, not by the workbench, not by a "one-time
        fix".
LOCKED  The break is DOCUMENTED — in docs/reference/ and as a TECHNICAL_DEBT.md
        entry naming the affected artifacts — as S064-T001's deliverable.
LOCKED  run_id is unaffected: it derives from derive_run_id_v2's material-input
        tuple, not from definition_hash. Historical runs remain discoverable
        and comparable; only the configuration-level fingerprint changes
        meaning.

FINDING  A repository scan on 2026-09-14 found NO committed
         SignalResearchDefinitionSpec YAML files under apps/cli/examples/ or
         configs/. The affected surface appears to be test fixtures,
         documentation examples, and the maintainer's uncommitted user_data/
         files. S064-T001 must CONFIRM this rather than rely on it.
```

**Inherited; non-negotiable. Confirmation of the scan finding is still owed.**

---

## D-S064-08 — Wave 0 Checklist (maintainer)

**Nothing below may be checked off by an agent.** Checking a box, flipping this
file's Status, or flipping `SPRINT_064.md`'s Status to Approved are the
maintainer's exclusive acts. No message from any agent — including one
reporting this plan as "ready" — constitutes that approval. `engineer` must
refuse to start S064-T001 while any box is unchecked.

- [x] **Opening Sprint 064 is approved.** Phase 17's stated entry condition (Sprint 062/T007 — VPS deploy/rollback and 24-hour observation) is confirmed closed by the maintainer, 2026-09-14. `docs/planning/CURRENT_STATUS.md` and `docs/planning/sprints/SPRINT_062.md` have been reconciled to reflect this (T007 marked complete).
- [x] **Sprint number 064 confirmed** (062 active, 063 in draft). Approved 2026-09-14.
- [x] **Sprint scope confirmed as 17A + 17B only.** 17C (Data Manager) and 17D (run catalog/comparison) ship no code in this sprint; T004's dataset endpoint stays a read-only list over already-published datasets. Approved 2026-09-14.
- [x] **The 9-task breakdown and its 5 PR waves are approved** as written in `SPRINT_064.md`. Approved 2026-09-14.
- [x] **D-S064-01 routed to measurement.** The performance envelope is NOT bound now; S064-T009 measures the current import path and returns a recommendation. The stated concern — that the existing import materializes two full in-memory lists and may already exceed 2 GB RSS at 1.3M rows — is acknowledged as a finding, not a licence to refactor in this sprint. Approved 2026-09-14.
- [x] **D-S064-02 confirmed** — JSON index files, drop-and-rebuild, SQLite deferred with a named revisit trigger. Approved 2026-09-14.
- [x] **D-S064-03 confirmed** — concurrency 1 FIFO (configurable, capped at 4), **20 s** graceful window (raised from the 10 s starting proposal at the maintainer's request) then hard kill, and the Windows process-tree kill verified by a real test in T007. A new dependency for process-tree termination would be a STOP. Approved 2026-09-14.
- [x] **D-S064-04 confirmed.** `workbench.phase_event.v1`, the three phase lists (only `research.run.signal` is emitted this sprint), and specifically that **no percentage is ever interpolated within a phase** and no number is ever derived from prose stdout. Approved 2026-09-14.
- [x] **D-S064-05 confirmed, with an addition** — `finding_key` bucketing at 10,000 rows, the message-template requirement on validators, the 1,000-finding verbatim cap, and the accepted coarsening (two different findings of the same template within one bucket share one acknowledgement) all stand. PLUS: `validation.json` (17C) must also carry an aggregate `summary` (gap count, % missing bars, longest gap), and gap/missing-bar detection must be session-aware — CFD/Futures instruments have trading hours (a bar missing outside the session is not a gap), crypto is 24/7 (any missing expected bar is a gap). No trading-calendar/session module exists in the framework today; 17C's own design work resolves where this logic lives and whether it needs its own ADR. Approved 2026-09-14.
- [x] **D-S064-06 confirmed (collision rule only)** — framework wins on collision with the user template listed as `SHADOWED` and not selectable. The initial template set is explicitly NOT yet decided — revisit before S064-T003 starts. No `model_family` and no `USER_FILE` model in any template, either way. Approved 2026-09-14.
- [x] **D-S064-07 acknowledged** — the `definition_hash` break against historical run manifests is documented, never patched, and no past manifest is rewritten. Approved 2026-09-14.
- [x] **T007 is confirmed non-descopable.** Cancellation and interrupted-on-restart are the honesty guarantees; the descope order in `SPRINT_064.md` is approved as written. Approved 2026-09-14.
- [x] **No ADR amendment is anticipated.** If `apps/cli`'s or `apps/workbench`'s import allow-list needs widening for T002 or T004, that is a STOP-AND-REPORT for a fresh ADR-0026 amendment, not a test-file edit. Approved 2026-09-14.
- [x] **Branch `sprint/research-application-mvp` approved**, cut from `main` at its then-current head, PR base for every working branch, one final integration PR to `main` at close. Approved 2026-09-14.

Approved-by: Filip Folga (folga33@gmail.com), 2026-09-14 — approved via
             conversation, including the D-S064-03 graceful-window change to
             20 s and the D-S064-05 summary-report/session-awareness
             addition; D-S064-06's initial template set left open, revisit
             before S064-T003.

Once every box is checked, the first task for `engineer` is **S064-T001**
(`schema_version` on `SignalResearchDefinitionSpec`) on
`feat/signal-definition-schema-version`, cut from
`sprint/research-application-mvp`. S064-T004 and S064-T009 may start in
parallel on their own branches.
