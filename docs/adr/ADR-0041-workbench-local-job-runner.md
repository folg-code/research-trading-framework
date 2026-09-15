# ADR-0041 — Workbench Local Job Runner: Process Boundary, Cancellation, Progress and Interruption

## Status

ACCEPTED

Drafted during architecture triage of `docs/product/PRD-research-workbench-mvp.md`
(open questions "Job boundary", "Cancellation semantics", "Progress contract").
These three are decided together because they are one mechanism. Approved by
the maintainer in conversation, 2026-09-14, including the §2
subprocess-over-`trading-cli` resolution to the execution-model fork (which
obliges `apps/cli` to emit the §7 structured phase events).

## Context

The PRD requires work to survive a browser-tab close, to expose
queued/running/terminal status with useful progress or logs, to support
cancellation, and to appear **interrupted** — never running, successful, or
auto-resumed — after an application or worker restart. It explicitly rules out a
distributed scheduler, retries, and resume.

Current facts:

- Every application workflow is **synchronous and blocking**.
  `run_signal_research` computes and then returns; there is no background
  execution anywhere in `src/trading_framework/`.
- A repository-wide search for `progress` / `on_progress` / callback / `tqdm`
  in `src/trading_framework/application/` returns **no matches**. There is no
  progress contract to consume; none exists to scrape either.
- `ADR-0026` established `trading-cli` as an application-layer front door that
  validates and resolves before any side effect and can print a resolved plan.
- `SignalResearchDatasetRepository.write(envelope)` is the single publication
  point for a run; before it, nothing durable exists under
  `research/market_research/`.

## Decision

### 1. The job runner lives in `apps/workbench`, not in the framework

`src/trading_framework/` stays synchronous and runs nothing in the background.
Job lifecycle is application-shell concern, owned by `apps/workbench`
(ADR-0037 §2, `workbench_core`).

### 2. One job = one OS subprocess invoking `trading-cli`

```text
workbench-api  ──writes──►  user_data/workbench/jobs/<job_id>/config.yaml
               ──spawn ──►  uv run trading-cli <group> --config <that file> --json
               ──reads ──►  the child's stdout/stderr and exit code
```

Rationale:

- It makes the PRD's CLI-interoperability property **structural**: every
  workbench run is, by construction, a run that the CLI could have produced from
  a file the operator can read (ADR-0038 §3).
- Cancellation is a signal to a process, not a cooperative flag threaded through
  twenty call sites.
- A crash, an OOM, or a segfault in a heavy Polars operation kills the job, not
  the control API.
- The framework needs no change to support it.

The subprocess is the **only** execution path. `workbench_core` must not call
`run_signal_research` or `import_external_dataset` in-process for a job; it may
call read-only application use cases in-process for catalogs and previews.

### 3. Job state store

```text
user_data/workbench/jobs/<job_id>/
    job.json      state, kind, timestamps, pid, exit code, config path, artifact ids
    config.yaml   the exact generated CLI config (the operator can rerun it by hand)
    stdout.log    verbatim child output
```

`job.json` is **workbench-owned lifecycle state, never research truth**.
Deleting the whole `jobs/` tree loses no research artifact and no persisted
research fact. Nothing else in the repository reads it.

### 4. State machine

```text
QUEUED ──► RUNNING ──► SUCCEEDED
                  ├──► FAILED        (non-zero exit)
                  ├──► CANCELLED     (operator action)
                  └──► INTERRUPTED   (runner restart, see §5)
```

Terminal states are terminal. No automatic retry, no resume, no requeue
(PRD non-goal). Re-running is an explicit new job with a new `job_id` — and,
because run identity is deterministic (ADR-0011), a re-run of an identical study
resolves to the same `run_id` and is refused by the repository rather than
overwriting.

### 5. Interruption after restart

On every `workbench-api` / runner start, each job in `QUEUED` or `RUNNING` is
reconciled:

```text
recorded pid alive AND matches the recorded start time  → leave RUNNING
otherwise                                               → mark INTERRUPTED
```

`INTERRUPTED` is a distinct terminal state with its own label in the UI. It is
never displayed as failed, never as cancelled, never as running. The reason
("the application or worker restarted while this job was active") is stored.

### 6. Cancellation semantics, per workflow

The binding rule, applying to every workflow:

> **A cancelled or interrupted job never advances an artifact to FINALIZED or
> PUBLISHED, and never produces a readable run manifest.**

| Workflow | Safe point | What a cancel leaves behind |
|---|---|---|
| Signal Research | any time before `SignalResearchDatasetRepository.write` | either no run directory at all, or a directory without a readable `manifest.json` |
| Local CSV/Parquet import | any time | at most a `WORKING` dataset version — ADR-0007 already excludes `WORKING` from consumer queries, and ADR-0040 blocks finalize |
| Binance acquisition (ADR-0025) | between pagination pages | same: a `WORKING` dataset with fewer rows than requested, never finalized |

Enforcement, not just intent:

- Termination is `SIGTERM` (graceful window, default 10s) then `SIGKILL`. On
  Windows the runner uses the equivalent terminate/kill pair; this must be
  tested on the maintainer's platform, which is Windows.
- A run directory that exists without a readable `manifest.json` is classified
  `INCOMPLETE` by ADR-0042 and is never listed as a run. It is **not** deleted —
  the PRD forbids the application deleting artifacts.
- The workbench never auto-calls `finalize_dataset` or `publish_dataset` as part
  of a cancelled job's cleanup.

### 7. Progress contract: two tiers, one of them deferred

**Tier 1 — runner-owned phase progress (this increment).**

Each job kind declares an ordered, static phase list (e.g. import:
`read → normalize → validate → write → register`). The CLI emits
newline-delimited structured events on stdout:

```json
{"event":"phase","name":"validate","index":3,"of":5,"at":"2026-..."}
```

The runner parses only these structured lines and stores the latest phase in
`job.json`. Everything else from stdout is surfaced verbatim as logs.

**Explicitly forbidden:** deriving a percentage, an ETA, a row count, or any
other number by parsing human-readable stdout, log text, or file sizes. If a
fact is not emitted as a structured event, the UI shows "running" and the log,
and nothing more.

**Tier 2 — a framework-owned reporting contract (deferred).** A minimal
`ProgressSink` protocol in `trading_framework/application/` accepted as an
optional keyword argument by long-running use cases. Deferred because no
application workflow reports anything today, so adding it is a cross-cutting
change across 20+ use cases serving a UI that does not exist yet. The trigger to
write it: the first time phase-level granularity is demonstrably insufficient
for a real operator task (e.g. a multi-hour Binance range where "fetching" is a
single phase for 40 minutes).

### 8. Concurrency

One job at a time by default, FIFO, with a configurable small maximum. No task
queue dependency (no Celery, Redis, RQ, Dramatiq), no broker, no scheduler — the
ADR index's "distributed processing" reconsideration trigger has not fired.

## Alternatives Considered

1. **In-process thread or `asyncio` task inside the API.** Rejected: cancelling a
   CPU-bound Polars/NumPy computation from another thread is not reliably
   possible; a crash takes the whole control surface down; and it would require
   the framework to grow cooperative cancellation checks.
2. **A real task queue (Celery/RQ + Redis).** Rejected: a broker, a daemon and
   two dependencies for a single-user local application with one concurrent job.
   The ADR backlog's distributed-processing trigger explicitly has not fired.
3. **Subprocess calling `python -c` into the application layer directly.**
   Rejected: it bypasses the canonical entry point and reintroduces two
   divergent invocation paths — the exact drift ADR-0026 §"Negative" warns about.
4. **A durable job DB (SQLite) instead of per-job JSON files.** Not rejected on
   merit; deferred. One directory per job is inspectable with a text editor,
   trivially recoverable, and needs no migration. Revisit if job listing becomes
   slow (thousands of jobs).
5. **Auto-resume interrupted work.** Rejected: PRD non-goal, and partial
   research output presented as complete is the single worst failure mode this
   design exists to prevent.
6. **Scraping stdout for progress percentages.** Rejected: §7 — it makes an
   unversioned human-readable string a contract.

## Consequences

### Positive

- Tab-close survival, cancellation and restart-interruption all fall out of the
  OS process model rather than needing new framework machinery.
- Every workbench run is reproducible by hand from the committed `config.yaml`.
- Zero new runtime dependencies.

### Negative

- Subprocess startup cost (interpreter + imports) per job — seconds, not
  milliseconds. Acceptable for jobs measured in minutes; unacceptable if the
  workbench ever needs many short jobs.
- The CLI must learn to emit structured phase events, which is a new obligation
  on `apps/cli` and a (small) new output contract to version.
- Phase-level progress is coarse. A long single phase looks stalled; the UI must
  show elapsed time and live logs to compensate.
- Windows process-termination semantics differ from POSIX and are the primary
  platform here — this needs explicit test coverage, not an assumption.
- `job.json` is a state file that can disagree with reality if edited by hand;
  reconciliation (§5) mitigates but does not eliminate this.

## Follow-up

- Sprint Wave 0 must bind: the graceful-termination window, the default
  concurrency limit, the phase lists per job kind, and the structured-event
  schema version.
- Tier 2 `ProgressSink` remains an open, triggered decision (§7).
- Whether `INCOMPLETE` run directories should ever be garbage-collected (by the
  operator, explicitly, never automatically) is deferred.

## Related

- `docs/adr/ADR-0037-research-workbench-application-boundary.md`
- `docs/adr/ADR-0026-operator-cli-framework-and-placement.md`
- `docs/adr/ADR-0038-canonical-signal-research-configuration-and-templates.md`
- `docs/adr/ADR-0007-dataset-lifecycle-and-publication.md`
- `docs/adr/ADR-0011-signal-research-outcomes-and-persistence.md`
- `docs/adr/ADR-0042-workbench-catalog-index-and-comparison-facts.md`
- `docs/adr/README.md` — "Reconsideration triggers: distributed processing"
