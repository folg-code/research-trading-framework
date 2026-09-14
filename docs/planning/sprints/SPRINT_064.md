# Sprint 064: Signal Research Entry Point, Job Runner and First Workbench Run

Status: **Approved** — maintainer sign-off recorded 2026-09-14 in
`S064_WAVE0_DECISIONS.md` (D-S064-08 checklist, all items confirmed, two
deviations from the original proposal: D-S064-03's graceful window raised to
20s, D-S064-05 extended with a summary-report/session-awareness requirement
for 17C). `engineer` may start T001 on `sprint/research-application-mvp`.
Goal: Make one Signal Research study runnable end to end from
`apps/workbench` — chosen from a maintained template, previewed and saved as a
canonical versioned YAML, validated before side effects, executed as a
cancellable background `trading-cli` job with honest terminal states, and
opened as a result — without the operator touching a terminal.
Sources:

- `docs/planning/roadmap/PHASE_17_RESEARCH_APPLICATION.md` (ACCEPTED 2026-09-14) — increments 17A, 17B
- `docs/product/PRD-research-workbench-mvp.md` (ACCEPTED 2026-09-14)
- `docs/adr/ADR-0037-research-workbench-application-boundary.md`
- `docs/adr/ADR-0038-canonical-signal-research-configuration-and-templates.md`
- `docs/adr/ADR-0039-trusted-local-model-discovery.md`
- `docs/adr/ADR-0040-import-validation-findings-and-acknowledgement.md`
- `docs/adr/ADR-0041-workbench-local-job-runner.md`
- `docs/adr/ADR-0042-workbench-catalog-index-and-comparison-facts.md`
- `docs/adr/ADR-0026-operator-cli-framework-and-placement.md` (+ Amendment 1)
- `docs/adr/ADR-0027-operator-authored-strategy-loading.md`
- `src/trading_framework/research/signal_research/definition.py`, `loader.py`
- `src/trading_framework/application/signal_research/` (`map_definition.py`, `run_signal_research.py`)
- `apps/cli/src/trading_cli/` (`cli.py`, `config.py`, `plan.py`, `commands/research.py`) + `apps/cli/CLAUDE.md`
- `tests/unit/test_apps_boundaries.py`
- `docs/archive/planning/PROJECT_MANAGEMENT.md` §14 (Definition of Ready), §15 (Definition of Done)

Architecture triage: **complete and accepted**. ADR-0037 through ADR-0042 were
accepted by the maintainer on 2026-09-14. This sprint does not re-derive
architecture; it turns those decisions into code. Any finding that would change
an accepted ADR is a STOP-AND-REPORT, not an in-sprint amendment.

## Scope

In scope (17A + 17B only):

- `schema_version` on `SignalResearchDefinitionSpec`, with absent-means-v1
  compatibility and explicit refusal of unknown/newer versions (ADR-0038 §2).
- `trading-cli research run signal` as the canonical non-UI entry point,
  including `--dry-run` resolved-plan output (ADR-0038 §3).
- Two to three framework-owned Signal Research templates plus a listing API
  covering both template roots with a collision rule (ADR-0038 §4).
- `apps/workbench` as a new uv workspace member: `workbench_core` /
  `workbench_ui` split, per-app import rights enforced by
  `tests/unit/test_apps_boundaries.py`, loopback `workbench.api.v1`.
- One minimal read-only catalog endpoint over **already-published** datasets,
  sufficient to pick a study input.
- Structured newline-delimited phase events emitted by `trading-cli`
  (ADR-0041 §7 Tier 1) and parsed by the runner.
- A local job runner: one job = one `trading-cli` subprocess, `job.json` state
  store, the ADR-0041 §4 state machine, verbatim logs, cancellation
  (Windows-tested), and interrupted-on-restart reconciliation.
- One end-to-end operator slice in the UI: template -> editable YAML preview ->
  preflight validate -> run -> live status/phase/logs -> cancel -> open result.
- A measurement spike producing real numbers for the ~1.3M-row / 42.5 MB
  preview + import envelope, so D-S064-01 can be bound with evidence.

Out of scope:

- **All of 17C** — the Data Manager: CSV/Parquet import UI, column-mapping
  form, bounded preview UI, validation findings UI, acknowledgement UI, the
  Binance acquisition form, the `validation.json` sidecar and the
  `finalize_dataset(acknowledged_findings=...)` change (ADR-0040). Only the
  `finding_key` *decision* is bound here; no ADR-0040 code ships.
- **All of 17D** — the run catalog UI, the rebuildable index cache
  (`user_data/workbench/index/`), rescan, support classification, and
  `compare_signal_research_runs` (ADR-0042). Only the index-format *decision*
  is bound here; no ADR-0042 code ships.
- ADR-0039 model discovery: the `model.yaml` sidecar scan, the listable built-in
  model catalog, and `market_model_file` / `signal_model_file` spec keys. The
  first UI slice selects **built-in models by identifier only**.
- The Tier 2 framework-owned `ProgressSink` (ADR-0041 §7, deferred).
- Any frontend-framework commitment beyond "something that speaks HTTP/JSON".
- Any change to `apps/dashboard`, its import ban, or the public projection.
- Any publishing, any non-loopback bind, any authentication.
- Strategy / Robustness / Predictive workflows in the workbench.
- Grid search, sweeps, `model_family` multi-variant templates (ADR-0038 §5).
- Rewriting, migrating or deleting any existing artifact.

## Decisions

Binding detail, rationale and the maintainer checklist:
[`S064_WAVE0_DECISIONS.md`](S064_WAVE0_DECISIONS.md).

| Decision | Recommendation | Status |
|---|---|---|
| D-S064-01 — preview/import performance envelope | Bind **after** T009's measurement, not before. Proposed starting point: preview via Polars lazy scan capped at 1,000 rows, browser never receives more than that slice; import of the reference dataset <=120s and <=2GB RSS. The current `import_external_dataset` materializes two full in-memory lists, so the RSS figure is a hypothesis to be measured, not a specification. | Proposed; pending maintainer approval. Blocks nothing in this sprint; blocks 17C. |
| D-S064-02 — catalog index storage format | One JSON document per artifact kind under `user_data/workbench/index/`, drop-and-rebuild, no migrations. SQLite deferred on ADR-0041 alternative 4's reasoning. | Approved 2026-09-14 (see `S064_WAVE0_DECISIONS.md`). Blocks 17D, not this sprint. |
| D-S064-03 — job concurrency and termination window | `max_concurrent_jobs = 1`, FIFO, configurable small maximum. Graceful termination window 20s, then hard kill. | Approved 2026-09-14 (see `S064_WAVE0_DECISIONS.md`). |
| D-S064-04 — phase lists and event schema | `workbench.phase_event.v1`; static ordered phase lists declared per job kind; the runner parses only structured lines and never derives a number from prose. | Approved 2026-09-14 (see `S064_WAVE0_DECISIONS.md`). |
| D-S064-05 — `finding_key` bucketing | Bucket `row_number` so a per-row warning cannot produce a million keys; cap verbatim findings retained and record a truncation count. | Approved 2026-09-14, with an addition (session-aware gap detection + `validation.json` summary, bound for 17C) — see `S064_WAVE0_DECISIONS.md`. |
| D-S064-06 — template roots, collision and initial set | Framework template wins on `template_id` collision; the user template is still listed, badged `SHADOWED`, and is not silently dropped. Initial framework set: 3 templates. | Approved 2026-09-14 (see `S064_WAVE0_DECISIONS.md`). |
| D-S064-07 — `definition_hash` break | ADR-0038 §2 includes `schema_version` in the hash for v1, so `definition_hash` values in existing run manifests will no longer match a re-serialized spec. Past runs are immutable and are **not** rewritten; the break is documented, not patched. | Inherited from ADR-0038 (ACCEPTED); non-negotiable, must be restated in T001's acceptance. |

## Tasks

| Task | Outcome | Dependencies | Ownership | Risk | Status | PR |
|---|---|---|---|---|---|---|
| T001 | `SignalResearchDefinitionSpec` carries `schema_version`; a file without one still loads as v1, a file with an unknown/newer one is refused with a message naming the version and the supported set, and the `definition_hash` break is documented in `docs/reference/` and `TECHNICAL_DEBT.md` rather than patched | Approved sprint + D-S064-07 | `research/signal_research` + docs | standard | Done | PR TBD |
| T002 | `uv run trading-cli research run signal --config <f> --dry-run` prints a resolved plan (dataset, scope, models, range, horizons, intended output location) with zero side effects; without `--dry-run` it produces a persisted run and prints its `run_id`; `from_dict(to_dict(spec)) == spec` and `compute_definition_hash` are stable across a save/reload cycle | T001 | `apps/cli` + `application/signal_research` | high | Done | PR TBD |
| T003 | Three framework-owned templates ship in the package and a listing API returns framework + user templates with `template_id`, `template_version`, title, description, source (`FRAMEWORK`/`USER`) and shadowing status; applying one yields an editable payload that validates and runs through T002 | T001; D-S064-06 | `research/signal_research/templates` | standard | Done | PR TBD |
| T004 | `apps/workbench` exists as a uv workspace member; `workbench-api` starts on loopback, serves `workbench.api.v1`, and answers one read-only endpoint listing already-published datasets; `tests/unit/test_apps_boundaries.py` scans `workbench_core` and `workbench_ui` as two scopes with two rule sets and fails on a forbidden import | Approved sprint (parallel with T001) | `apps/workbench` + boundary tests | high | Done | PR TBD |
| T005 | `trading-cli` emits newline-delimited `workbench.phase_event.v1` events on stdout for `research run signal`, following the phase list bound in D-S064-04; human-readable output is unchanged for an operator reading the terminal | T002; D-S064-04 | `apps/cli` | standard | Done | PR TBD |
| T006 | Submitting a job through the API spawns one `trading-cli` subprocess against a written `config.yaml`, records `QUEUED -> RUNNING -> SUCCEEDED/FAILED` in `job.json`, surfaces the latest parsed phase and verbatim logs, and survives the client disconnecting; the operator can rerun the same study by hand from the written `config.yaml` | T004, T005; D-S064-03 | `apps/workbench` (`workbench_core`) | high | Blocked by T004/T005 | — |
| T007 | Cancelling a queued or running job yields terminal `CANCELLED` on Windows (graceful signal then hard kill) and leaves no readable run manifest and nothing FINALIZED/PUBLISHED; restarting `workbench-api` marks a previously active job `INTERRUPTED` with its stored reason — never running, failed, cancelled, or auto-resumed | T006; D-S064-03 | `apps/workbench` (`workbench_core`) + Windows tests | high | Blocked by T006 | — |
| T008 | A human opens the workbench, picks a template, sees and edits the generated YAML, runs preflight validation and sees the framework's own error text on a bad value, starts the study, watches phase/elapsed/logs update, cancels or lets it finish, and opens the result — all without a terminal | T003, T004, T007 | `apps/workbench` (`workbench_ui`) + `workbench_core` API | high | Blocked by T003/T007 | — |
| T009 | A recorded measurement of the reference ~1.3M-row / 42.5 MB dataset on the maintainer's machine: wall time, peak RSS and the bounded-preview cost for the current import path, written up as a proposed amendment to D-S064-01 with a named recommendation | Approved sprint (parallel with T001/T004) | measurement + docs | standard | Done — see `S064_WAVE0_DECISIONS.md` D-S064-01 amendment. Import: 54s / 2.10GB peak (misses the 2GB target by ~5%); preview: <10ms, no risk; new finding: import path is CSV-only today, no Parquet support | PR TBD |

Task detail (goal, explicit scope/out-of-scope, acceptance criteria, expected
tests, referenced documents) is in the per-task sections below. Operational
task status lives in the tracker; this table is a lightweight overview.

### T001 — Versioned Signal Research definition schema

- **Goal:** make a study definition file self-describing so an older
  application refuses a newer file instead of misreading it (ADR-0038 §2).
- **In scope:** `schema_version: str = "signal_research.definition.v1"` on the
  spec and its payload; `from_dict` treating an absent value as v1; an explicit
  refusal (named version + supported set) for anything else; `to_dict`,
  `from_dict` and `compute_definition_hash` updated consistently; a
  `docs/reference/` note and a `TECHNICAL_DEBT.md` entry recording the
  `definition_hash` break.
- **Out of scope:** rewriting any existing run manifest; a migration path; a v2;
  `market_model_file` / `signal_model_file` (ADR-0039, not this sprint).
- **Acceptance:** an existing definition file with no `schema_version` loads and
  resolves exactly as before; a file with `signal_research.definition.v2` is
  refused with a message naming both versions; the break is documented in the
  repository, not silently absorbed.
- **Tests:** round-trip equality, absent-version default, unknown-version
  refusal, hash stability within v1, hash change across a version bump.
- **Note for the implementer:** a repository scan found **no committed
  `SignalResearchDefinitionSpec` YAML files** under `apps/cli/examples/` or
  `configs/`. The affected surface is test fixtures, documentation examples and
  the maintainer's uncommitted `user_data/` files. Confirm this before assuming
  a wider migration is needed.

### T002 — `trading-cli research run signal`

- **Goal:** give the PRD's round-trip claim a real non-UI entry point, and give
  ADR-0041's subprocess model something to invoke.
- **In scope:** a `kind: signal` branch in `research.kind` with a
  `research.signal` block (`definition:` path, `persist:`); resolution through
  `resolve_signal_research_definition` -> `map_definition_to_run_request` ->
  `run_signal_research`; `--dry-run` printing the resolved plan; `--json`
  output carrying `run_id`.
- **Out of scope:** wrapping `scripts/signal_research/run_signal_research.py`
  (it stays); family/sweep execution; report rendering composition; changing the
  locked cross-group config schema.
- **Acceptance:** `--dry-run` performs no write anywhere under `storage_root`;
  a real run produces the same `run_id` the script path would for identical
  inputs; a YAML saved from a spec and reloaded produces an unchanged
  `compute_definition_hash`.
- **Tests:** `apps/cli/tests/` seam tests (config -> typed request -> typed
  result), dry-run no-side-effect assertion, config validation errors naming the
  offending key.
- **Boundary note:** check `tests/unit/test_apps_boundaries.py`'s allow-list
  **before** writing imports (`apps/cli/CLAUDE.md`). Any import outside
  `trading_framework.application.*` that is not already on ADR-0026 Amendment
  1's 17-module list is a STOP: it needs a fresh ADR amendment, not a test edit.

### T003 — Framework-owned templates and the template lister

- **Goal:** "start from a maintained template rather than an empty form" has an
  artifact to start from, in a fresh fork with an empty `user_data/`.
- **In scope:** three YAML templates under
  `src/trading_framework/research/signal_research/templates/`; discovery of
  `user_data/config/signal_research/templates/`; a listing function returning
  the required keys plus source and shadowing status; applying a template to
  produce an editable payload.
- **Out of scope:** a template editor; template creation from the UI; UI field
  metadata beyond what the spec's own enums and validators provide; any
  multi-variant `model_family` template (ADR-0038 §5).
- **Acceptance:** listing executes no Python from `user_data/` and opens no
  model file; a template naming an unresolvable model is **listed and flagged**,
  not hidden; a framework/user `template_id` collision resolves per D-S064-06
  with both entries visible; an applied template validates and runs through
  T002 unmodified.
- **Tests:** listing with an empty user root, with a collision, with a malformed
  user template (listed with a reason, never crashing the listing), applied
  template validates.

### T004 — `apps/workbench` skeleton, boundary test and dataset endpoint

- **Goal:** create the fourth workspace member with its import rights named and
  **tested** on day one, before there is any code that wants to cheat.
- **In scope:** `apps/workbench/pyproject.toml` as a uv workspace member; the
  `workbench_core` / `workbench_ui` package split; `workbench-api` binding to
  loopback only; `workbench.api.v1` version string; one GET endpoint listing
  published datasets (identity, instrument, timeframe, range, row count); an
  extension of `tests/unit/test_apps_boundaries.py` with two scan scopes and two
  rule sets; a CI job for the new suite; `apps/workbench/CLAUDE.md` recording
  the per-package import rights.
- **Out of scope:** the index cache, rescan, support classification, dataset
  import, any write endpoint, any job endpoint, authentication, TLS, non-loopback
  binding.
- **Acceptance:** a deliberately forbidden import in `workbench_core`
  (`trading_framework.research.*`) fails the boundary test; any
  `trading_framework` import in `workbench_ui` fails it; `apps/dashboard`'s own
  boundary test is untouched and still passes; the endpoint returns only
  `PUBLISHED` datasets and no filesystem path the operator did not supply.
- **Tests:** boundary scans (both scopes, positive and negative), endpoint
  contract test with a fixture registry, loopback-bind assertion.

### T005 — Structured phase events from `trading-cli`

- **Goal:** give the runner a versioned progress contract instead of a prose
  stdout to scrape.
- **In scope:** newline-delimited JSON phase events on stdout for
  `research run signal`, matching D-S064-04's phase list and
  `workbench.phase_event.v1`; emission gated so a human-facing terminal session
  is not degraded.
- **Out of scope:** percentages, ETAs, row counts, per-fold detail, the Tier 2
  `ProgressSink`, phase events for workflows this sprint does not run.
- **Acceptance:** every emitted line parses as one JSON object carrying
  `event`, `name`, `index`, `of`, `at`; the phases emitted match the declared
  static list in order; existing CLI output tests still pass.
- **Tests:** event-sequence assertion for a full run and for a failing run;
  schema-version presence; no event emitted before validation completes.

### T006 — Job runner core: spawn, state, status, logs

- **Goal:** a study started from the API keeps running when the client goes
  away, and its state is inspectable.
- **In scope:** `user_data/workbench/jobs/<job_id>/` with `job.json`,
  `config.yaml` and `stdout.log` per ADR-0041 §3; job submit/get/list endpoints;
  `QUEUED -> RUNNING -> SUCCEEDED | FAILED`; FIFO queue at D-S064-03's
  concurrency; latest parsed phase stored in `job.json`; verbatim logs surfaced.
- **Out of scope:** cancellation and restart reconciliation (T007); retry;
  resume; requeue; a job database; any in-process call to `run_signal_research`
  (ADR-0041 §2 forbids it for a job).
- **Acceptance:** the written `config.yaml` is byte-for-byte usable by a human
  running `trading-cli` directly; closing the API client does not stop the
  child; a non-zero exit yields `FAILED` with the exit code recorded; deleting
  the whole `jobs/` tree loses no research artifact.
- **Tests:** subprocess lifecycle with a stub child, state transitions, phase
  parsing from a synthetic event stream, log passthrough, FIFO ordering at
  concurrency 1.

### T007 — Cancellation and interrupted-on-restart (Windows)

- **Goal:** make ADR-0041's binding rule observable: a cancelled or interrupted
  job never looks like a successful one.
- **In scope:** cancel endpoint; graceful-then-hard termination using the
  Windows terminate/kill pair with D-S064-03's window; terminal `CANCELLED`;
  restart reconciliation of `QUEUED`/`RUNNING` jobs via recorded pid + start
  time; terminal `INTERRUPTED` with a stored reason and its own label.
- **Out of scope:** deleting or repairing anything the cancelled job left
  behind; auto-resume; classifying the leftover directory (that is ADR-0042 /
  17D).
- **Acceptance:** run on Windows, not assumed — a cancelled Signal Research job
  leaves either no run directory or one without a readable `manifest.json`, and
  nothing is FINALIZED or PUBLISHED; `INTERRUPTED` is never displayed as
  failed, cancelled or running; no terminal state ever transitions again.
- **Tests:** cancel during run (Windows), cancel of a queued job, kill-after-
  grace path, restart reconciliation with a dead pid, restart reconciliation
  with a recycled pid whose start time differs, terminal-state immutability.

### T008 — First end-to-end operator slice

- **Goal:** the sprint's single demonstrable outcome — one study, start to
  finish, no terminal.
- **In scope:** template picker; generated YAML shown and editable; save/load;
  a published-dataset picker (T004's endpoint); built-in model selection by
  identifier; preflight validate calling `--dry-run` and rendering the
  framework's own error text; run submission; live status with phase, elapsed
  time and logs; cancel; a result view reading persisted artifacts plus a
  link-out to the existing report (ADR-0037 §5 — link, never embed).
- **Out of scope:** import/preview UI, validation-findings UI, Binance form
  (17C); run catalog and comparison (17D); `USER_FILE` model selection
  (ADR-0039); any metric computed in the presentation layer; any iframe,
  proxy or `dashboard_app` import.
- **Acceptance:** a human completes the flow and can state the `run_id`; every
  number shown is read from a persisted artifact or a framework-owned analysis
  output; closing the browser tab mid-run and reopening shows the same job still
  running; the saved YAML runs unchanged through T002 from a terminal.
- **Tests:** API contract tests per endpoint; a scripted end-to-end test through
  the API (not the browser) covering template -> validate -> run -> result; a
  boundary test proving `workbench_ui` imports no `trading_framework`.

### T009 — Preview/import performance measurement spike

- **Goal:** replace a guessed performance envelope with a measured one before
  17C commits to it.
- **In scope:** measuring the reference dataset (~1.3M rows / 42.5 MB) on the
  maintainer's Windows machine through the current
  `application/market_data/import_external_dataset` path: wall time, peak RSS,
  and the cost of a bounded lazy-scan preview at several head limits; a written
  recommendation amending D-S064-01.
- **Out of scope:** optimizing the import path, changing it, or building the
  preview feature. This task ships **numbers and a recommendation, not
  production code**.
- **Acceptance:** measurements are reproducible from the recorded command and
  environment; the write-up states plainly whether the proposed <=120s / <=2GB
  envelope is met, missed, or met only under conditions worth naming.
- **Known hazard to test, not assume:** `import_external_dataset` currently
  materializes `list(importer.iter_rows(...))` **and** a second full
  `list[MarketBar]` before validating. At 1.3M rows that is two full in-memory
  materializations of wrapped value objects; the 2GB RSS figure may already be
  exceeded today. If it is, that is a finding for the maintainer and a 17C
  input, not a licence to refactor the import path inside this sprint.

## Branch and PR rules

Per the `git-workflow` skill defaults; no project-specific deviation.

```text
main
  └── sprint/research-application-mvp
        ├── feat/signal-definition-schema-version      (T001)
        ├── feat/cli-signal-research-command           (T002)
        ├── feat/signal-research-templates             (T003)
        ├── feat/workbench-application-skeleton        (T004)
        ├── feat/cli-structured-phase-events           (T005)
        ├── feat/workbench-job-runner                  (T006)
        ├── feat/workbench-job-cancellation            (T007)
        ├── feat/workbench-signal-research-slice       (T008)
        └── docs/import-performance-measurement        (T009)
```

- Integration branch: `sprint/research-application-mvp`, cut from `main` at its
  then-current head after approval.
- Working branches: `<prefix>/<descriptive-slug>`, cut from the sprint branch.
  Never `sprint/research-application-mvp/<something>`.
- PR base is always the sprint branch. One final integration PR to `main` at
  sprint close, after review and CI.
- One PR = one coherent outcome. Branch names above are indicative; the
  engineer chooses the actual PR split by outcome and size. T006 and T008 are
  the likely candidates to need two PRs each — split them rather than shipping
  an 800-line diff.
- Squash merge for working PRs. `engineer` stops before merge and reports the
  PR URL.
- Wait for a dependency's PR to merge into the sprint branch, then rebase,
  before opening the dependent PR.

## Suggested PR waves

```text
Wave 1  T001, T004, T009          three independent branches, start together
Wave 2  T002, T003                both need T001 merged; parallel with each other
Wave 3  T005  then  T006          T006 rebases on T005 for phase parsing
Wave 4  T007                      needs T006
Wave 5  T008                      needs T003 and T007; the sprint's demo
```

## Acceptance criteria

- A Signal Research definition file without `schema_version` still loads; one
  with an unknown version is refused by name and is never migrated or rewritten.
- The `definition_hash` break against historical run manifests is documented in
  the repository; no past run manifest is edited.
- `trading-cli research run signal --dry-run` prints a resolved plan and writes
  nothing; the same config without `--dry-run` produces a persisted run.
- A YAML generated in the UI runs unchanged through `trading-cli` from a
  terminal, and `compute_definition_hash` is unchanged across save/reload.
- Three framework templates ship in the package and list correctly from a fresh
  fork with an empty `user_data/`; template listing executes no operator Python.
- `tests/unit/test_apps_boundaries.py` enforces `workbench_core` and
  `workbench_ui` as separate scopes; `apps/dashboard`'s ban is untouched and
  still passes.
- `workbench-api` binds to loopback only, serves `workbench.api.v1`, and returns
  no filesystem path the operator did not supply.
- Every phase-progress fact in the UI comes from a parsed structured event. No
  percentage, ETA or row count is derived from prose stdout, log text or file
  size.
- Closing the browser tab does not stop a run; reopening shows the same job.
- Cancel produces terminal `CANCELLED` on **Windows**, with no readable run
  manifest and nothing FINALIZED or PUBLISHED.
- Restarting `workbench-api` marks previously active jobs `INTERRUPTED`, with a
  distinct label and a stored reason; nothing is auto-retried or resumed.
- Deleting `user_data/workbench/jobs/` loses no research artifact.
- No Signal Research metric is computed in `apps/workbench`; every displayed
  number is read from a persisted artifact or a framework-owned output.
- No dataset, run, report or model artifact is edited, repaired, deleted or
  migrated by anything in this sprint.
- One human, one session, one study, no terminal: the T008 flow is demonstrated
  and its `run_id` recorded in the closeout.

## Integration risks

- **T002's import boundary.** `apps/cli`'s allow-list is a tested contract with
  a formal ADR amendment behind it (ADR-0026 Amendment 1, TD-024). A Signal
  Research command may want a value object that is not on the 17-module list.
  That is a STOP-AND-REPORT for a maintainer amendment, not a test edit. Wave 2
  of Sprint 046 widened the list first and amended second; do not repeat that.
- **T001's hash break has a blast radius nobody has measured.** The scan found
  no committed definition YAMLs, but tests, docs and the maintainer's
  `user_data/` all carry hashes. If T001 turns out to invalidate something the
  maintainer relies on, stop — ADR-0038 §2 chose this break deliberately and
  reversing it is a maintainer decision.
- **Two front doors drift.** `apps/cli` and `apps/workbench` both invoke
  workflows. ADR-0041's subprocess model is the mitigation; any temptation to
  call `run_signal_research` in-process from `workbench_core` for "just this
  one case" breaks it and must be refused.
- **Windows process termination is the primary platform and the least tested
  path** (ADR-0041 Consequences). T007's Windows coverage is not optional and
  cannot be satisfied by a POSIX-only test.
- **Subprocess startup cost** (interpreter + imports, seconds) makes the first
  phase event appear late. The UI must show elapsed time from submission so a
  starting job does not look hung.
- **Scope creep into 17C/17D.** T004's dataset endpoint is one read-only list
  over published datasets. The moment it grows import, preview, validation or
  comparison, the sprint has silently absorbed two later increments.
- **The UI slice is last and carries the demo.** If Wave 4 slips, T008 is the
  task at risk; descope its result view to a link-out before descoping
  cancellation or interruption, which are the honesty guarantees.

## Descope order

If the sprint must shrink, drop in this order — never the reverse:

```text
1. T009  (measurement spike; re-route to a standalone 17C precursor)
2. T008's native result view  (keep the link-out; ADR-0037 §5 permits it)
3. T003's third template      (two is enough to prove the lister)
4. T004's dataset endpoint    (fall back to a typed DatasetRef in the YAML)
```

`T007` (cancellation and interruption) is **not** descopable. It is the PRD
success metric that prevents partial work being presented as complete, and it
is the reason ADR-0041 exists.

## Closeout

- Integrated checks:
- Documentation reconciliation:
- Review:
- Remaining work:
