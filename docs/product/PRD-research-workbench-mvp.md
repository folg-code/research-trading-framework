# PRD — Data Manager + Signal Research Workbench MVP

```text
Status: DRAFT
Discovery: maintainer Q&A completed 2026-09-09
Approval gate: architecture triage required before maintainer approval
```

Feature-level PRD for the first increment of
`docs/vision/RESEARCH_APPLICATION_PRODUCT_VISION.md`. It defines one local
research vertical slice. It does not approve later Strategy Research,
Robustness Research, Predictive Research, live control, public portfolio, or
Strategy Builder increments.

## Problem

The framework already has capable Market Data and Signal Research workflows,
but operating them requires knowledge of command syntax, script entry points,
configuration files, filesystem locations, and the correct sequence of
operations. Persisted results can be inspected through reports and a read-only
dashboard, but there is no single local workflow for preparing data, starting
Signal Research, tracking the run, and comparing results.

This creates three concrete forms of friction for the primary user:

1. command and configuration syntax must be remembered or reconstructed;
2. YAML is edited without a discoverable, validated form over available
   datasets, templates, and existing models;
3. comparing saved runs requires manual navigation and does not make material
   compatibility differences prominent.

The missing product capability is a local operator experience over existing
framework contracts. The missing capability is not a new research engine.

## Goals / Non-goals

### Goals

- Provide one desktop-first, English-language local workflow from market-data
  acquisition through Signal Research result comparison.
- Accept two data entry paths:
  - a local CSV or Parquet file;
  - the framework's existing Binance USD-M historical OHLCV acquisition path.
- Leave a selected source file untouched and create a canonical, versioned
  dataset through the framework's existing import, validation, finalization,
  and publication contracts.
- Automatically propose CSV/Parquet column mappings, require the user to
  confirm timestamp, OHLCV, instrument, timeframe, and timezone semantics,
  and show a bounded data preview before import.
- Show validation findings before dataset creation. Structurally fatal errors
  cannot be bypassed. Nonfatal warnings may be acknowledged and must remain
  visible in the resulting dataset's validation facts.
- Provide a read-only dataset catalog for selecting compatible published
  datasets. The UI does not edit records or physically delete datasets.
- Start Signal Research from a maintained template rather than an empty form.
- Allow the user to select compatible existing Market and Signal Models,
  including trusted local user models supported by the framework.
- Expose one explicit value per configurable field. One submission represents
  one consciously specified study; no UI field expands into an implicit
  parameter grid.
- Generate a normal, versioned, human-readable YAML configuration that can be
  previewed, saved, loaded again, and used through a compatible non-UI entry
  point.
- Validate and resolve the study before side effects, showing the selected
  workflow, dataset, models, range, parameters, and intended output location.
- Run work independently of the browser tab, expose queued/running/terminal
  status and useful progress or logs, and allow cancellation.
- Treat an application or worker restart as interruption in this increment.
  Do not automatically retry or resume interrupted research work.
- Discover compatible persisted datasets and Signal Research runs produced by
  the existing CLI or scripts, not only runs initiated from the application.
- Show a run catalog, basic Signal Research results, and a link into the
  existing detailed report/dashboard during the transition to richer native
  views.
- Allow the user to compare arbitrary Signal Research runs. Display material
  differences and a clear not-directly-comparable warning where appropriate;
  do not block the comparison or declare a universal winner.
- Keep a comparison ephemeral in the MVP. A shareable URL may encode the
  selection, but no durable named comparison workspace is required.
- Keep unsupported historical artifact versions visible when safely
  identifiable, mark them `UNSUPPORTED`, explain the reason, and never rewrite
  or migrate them automatically.
- Preserve the `src/` / `user_data/` boundary and keep all research,
  analytical, and model-evaluation logic outside the application UI.

### Non-goals

- Strategy Research, Robustness Research, Predictive Research, model
  promotion, Strategy Execution, or live/paper control.
- Public portfolio publishing or any public endpoint.
- A structured Strategy Builder, strategy parameter editor, or declarative
  serialization format for `StrategyModelDefinition`.
- Replacing operator-authored Python for complex models or strategies.
- Grid search, family expansion from UI values, parameter sweep, hyperopt,
  Bayesian optimization, automated candidate generation, or automatic model
  selection.
- Computing new research metrics, verdicts, rankings, or compatibility facts
  in the presentation layer.
- Editing, repairing, deleting, or silently migrating market data, datasets,
  runs, reports, or model artifacts.
- Automatically retrying or resuming work after an application or worker
  restart.
- Multi-user accounts, authentication, authorization roles, collaboration,
  subscriptions, or hosted SaaS operation.
- Mobile-first research authoring.
- Selecting a final frontend framework, database, task queue, packaging model,
  or deployment topology in this PRD.
- Changing the existing Binance importer beyond what is required to expose its
  already-supported behavior. Known provider, interval, and data-contract
  limitations remain visible rather than being silently widened by the UI.

## Success metrics

- A user completes the following representative flow without opening a
  terminal: select a local OHLCV CSV/Parquet file, confirm its mapping, review
  validation, create/select the published dataset, choose a Signal Research
  template and existing models, validate the resolved plan, run the study, and
  open its results.
- The same flow works with the existing supported Binance USD-M historical
  OHLCV acquisition path.
- A representative local Parquet dataset at the maintainer's current scale
  (approximately 1.3 million rows and 42.5 MB) can be previewed and imported
  without loading or rendering the entire dataset in the browser.
- A UI-generated configuration round-trips through save and reload without a
  material change to the resolved study. The saved configuration is accepted
  by the canonical non-UI configuration/workflow entry point selected during
  architecture triage.
- Closing the browser tab does not stop a running study. Cancelling a queued or
  running study produces an explicit terminal status and never presents a
  partial artifact as a successful run.
- After an application or worker restart, previously active work is shown as
  interrupted rather than running, successful, or automatically resumed.
- The run catalog displays a compatible run created outside the application
  after rescanning the same `user_data/` workspace.
- A user can compare at least two arbitrary Signal Research runs. When a
  material input differs, the comparison identifies the difference and marks
  the pair as not directly comparable without preventing inspection.
- Every number presented as a research result is read from an existing
  persisted artifact or framework-owned analysis output; the application
  presentation layer contains no Signal Research metric calculation.
- A structurally invalid import is refused before dataset publication. A
  nonfatal warning can be acknowledged and remains discoverable after the
  import completes.
- An unsupported artifact is never automatically rewritten and cannot be
  mistaken for a fully supported run.
- Existing CLI/script workflows and existing read-only dashboard behavior
  remain available; adopting the application is additive.

## User stories

- As a local researcher, I can select an OHLCV CSV/Parquet file and confirm an
  automatically proposed schema mapping so that I do not need to construct an
  import command manually.
- As a local researcher, I can review fatal validation errors and acknowledge
  nonfatal warnings before creating a dataset so that data quality is explicit
  rather than silently corrected.
- As a local researcher, I can acquire a supported Binance historical range
  through a form so that I do not need to remember provider-specific syntax.
- As a local researcher, I can browse immutable published datasets and select
  one as a study input without editing or deleting its records.
- As a local researcher, I can start from a maintained Signal Research
  template and choose an existing Market or Signal Model so that the common
  path is discoverable without removing Python as an advanced escape hatch.
- As a local researcher, I can inspect and save the generated YAML before I
  run it so that the UI does not hide material configuration or lock me into
  the application.
- As a local researcher, I can validate the resolved study before execution so
  that configuration errors fail before expensive work or file writes begin.
- As a local researcher, I can close the browser while a run continues and
  later return to its status, progress, logs, and result.
- As a local researcher, I can cancel work I no longer need and see an honest
  cancelled or interrupted state rather than a misleading success.
- As a local researcher, I can browse runs created through the application,
  CLI, or existing scripts so that the same workspace has one discoverable
  history.
- As a local researcher, I can compare any selected Signal Research runs and
  see their material configuration differences so that I can interpret the
  comparison without the application choosing a winner for me.
- As a local researcher, I can open the existing detailed report from a run's
  native summary so that the first increment does not need to rewrite every
  analytical view.
- As a maintainer, I can see an unsupported artifact and the reason it cannot
  be loaded without the application rewriting historical evidence.

## Open questions

Architecture triage is required before this PRD is eligible for approval. It
must resolve or route the following questions to ADR/design work without
turning them into product decisions inside the UI:

- **Application boundary:** ADR-0022 makes the existing dashboard a read-only
  artifact consumer, while this increment must invoke Market Data and Signal
  Research workflows. Should control/API and presentation be separate
  deployable consumers, and what exact application-layer imports may the
  control side use?
- **Canonical Signal Research configuration:** what existing or new
  framework-owned schema is the one source of truth for UI forms, YAML,
  validation, and non-UI execution? `trading-cli` does not currently expose a
  Signal Research command, so interoperability cannot be claimed by pointing
  at its current v1 schema unchanged.
- **Template ownership:** where do maintained templates live, how are they
  versioned, and how do they reference existing Market/Signal Model
  definitions without embedding arbitrary executable code in configuration?
- **Trusted local model discovery:** how does the application enumerate and
  validate user models without importing every Python file during a read-only
  catalog scan or weakening the existing trusted-code warning?
- **Import warning contract:** which existing validation findings are fatal,
  which may be acknowledged, and where is acknowledgement persisted without
  inventing a second dataset lifecycle in the application?
- **Job boundary:** what minimal local worker/process contract lets work
  survive a browser-tab close, supports cancellation, and marks work
  interrupted after process restart without introducing a distributed
  scheduler?
- **Cancellation semantics:** what constitutes safe cancellation for each
  supported application workflow, and how are temporary or partially written
  outputs prevented from appearing as published/successful artifacts?
- **Progress contract:** which progress facts already exist at the application
  layer and which require a framework-owned reporting contract rather than UI
  scraping of stdout or logs?
- **Catalog rebuild:** which metadata belongs in a rebuildable application
  index versus canonical manifests under `user_data/`, and how are incomplete
  or unsupported artifacts represented without mutating them?
- **Comparison compatibility:** what is the framework-owned set of material
  Signal Research inputs used to produce compatibility differences, ensuring
  the UI does not recreate run-identity logic?
- **Existing report integration:** whether the first increment links to,
  embeds, or reverse-proxies the current read-only dashboard/report while
  preserving its import and trust boundary.
- **Representative-scale acceptance:** the bounded preview size and acceptable
  import latency/memory envelope for the approximately 1.3-million-row local
  reference scale.
