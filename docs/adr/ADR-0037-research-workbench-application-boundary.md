# ADR-0037 — Research Workbench Application Boundary and Control Surface

## Status

ACCEPTED

Drafted during architecture triage of `docs/product/PRD-research-workbench-mvp.md`
(open questions "Application boundary" and "Existing report integration").
Approved by the maintainer in conversation, 2026-09-14, including the
loopback-API-from-the-start resolution to §4's process-topology fork.

## Context

`docs/product/PRD-research-workbench-mvp.md` requires a local operator surface
that **invokes** Market Data and Signal Research workflows. The PRD names the
conflict explicitly: ADR-0022 rule 2 bans `apps/*` from importing research
engines, execution, and infrastructure adapters.

Three facts constrain the answer.

1. **`apps/dashboard` is no longer a generic "UI app".** Per ADR-0034/ADR-0035
   and `docs/reference/modules/DASHBOARD_APPLICATION.md`, it is a *public*
   read-only consumer of an immutable, deny-by-default projection bundle
   (`dashboard.public.v1`). It does not even accept `DASHBOARD_STORAGE_ROOT` on
   public pages, and its total ban on importing `trading_framework` is enforced
   by `tests/unit/test_apps_boundaries.py`. Adding a control surface to it would
   collapse the private-control / public-presentation trust split that
   `RESEARCH_APPLICATION_PRODUCT_VISION.md` §3.5 makes a product principle.
2. **ADR-0022 rule 2 has already been read as role-based, not folder-based.**
   ADR-0026 §2 gave `apps/cli` permission to import
   `trading_framework.application.*` precisely because a CLI's purpose is to
   invoke workflows, and Amendment 1 narrowed that to a tested module
   allow-list. The precedent exists; it just was never generalized in writing.
3. The PRD declares "selecting a final frontend framework" a **non-goal**. Any
   boundary decision must therefore survive a later UI-stack choice.

## Decision

### 1. A third deployable consumer: `apps/workbench`

The Research Workbench is a **new** uv workspace member under `apps/`, not a
page set inside `apps/dashboard`. `apps/dashboard` and its import ban are
untouched by this ADR.

```text
apps/dashboard   public, read-only, zero trading_framework imports   (unchanged)
apps/cli         operator CLI, application-layer allow-list          (ADR-0026)
apps/workbench   private local operator control surface              (this ADR)
```

### 2. Internal split: control core vs presentation

`apps/workbench` contains two packages with **different** import rights,
enforced by an extension of `tests/unit/test_apps_boundaries.py`:

```text
workbench_core   MAY import trading_framework.application.*
                 MAY import the ADR-0026 Amendment 1 allow-list modules
                     (value objects, typed identifiers, spec loaders)
                 MUST NOT import trading_framework.research.*,
                     .market_analysis.*, .strategy.*, .execution.*,
                     or infrastructure adapters beyond that allow-list
                 MUST NOT contain research, simulation, analytics or
                     execution logic, or reimplement anything in application/

workbench_ui     MUST NOT import trading_framework at all
                 Talks to workbench_core only over the local JSON API (§3)
```

This is the same "no engine internals reimplemented" rule ADR-0022 states, in
the terms that fit a control application. `apps/workbench` inherits ADR-0026
Amendment 1's allow-list **as-is**; widening it requires an amendment with
maintainer approval, exactly as it did for `apps/cli`.

### 3. `ADR-0022` rule 2 is restated as per-app, not blanket

> Each `apps/<app>` declares its import rights in its own ADR and has them
> enforced by `tests/unit/test_apps_boundaries.py`. The default for a new app
> is the dashboard's total ban; any widening is an explicit, named, tested
> decision. `apps/dashboard`'s ban is not relaxed by any other app's grant.

This records what ADR-0026 already did in practice. It is a clarification, not
a relaxation; ADR-0022 is not superseded.

### 4. Process topology

```text
workbench-ui  ──HTTP/JSON (loopback)──►  workbench-api  ──spawn──►  job runner
                                              │                     (ADR-0041)
                                              └── application layer / user_data
```

- `workbench-api` and the job runner bind to **loopback only**. No
  authentication, no authorization roles, no TLS — matching the PRD's
  single-local-user non-goals. Exposing either port publicly is out of scope
  and must be documented as unsupported.
- The API is versioned (`workbench.api.v1`) and JSON-only. That versioned
  boundary is what keeps the deferred frontend-framework choice reversible:
  any UI that can call HTTP satisfies it.
- The API returns **no filesystem paths to the browser** for artifacts it did
  not itself create, mirroring the dashboard's projection discipline, except
  where a path is itself the operator's input (a selected source file, a model
  file) — those are echoed back verbatim because the operator typed them.

### 5. Existing report / dashboard integration: link, never embed

The first increment **links out**. It does not embed, iframe, reverse-proxy, or
re-host the existing read-only dashboard or generated HTML reports.

```text
Chosen     an explicit link/"open" action to an existing report file or a
           configured dashboard URL
Rejected   iframe embedding      (merges two trust surfaces in one origin)
Rejected   reverse proxy         (workbench would become a public-content
                                  server; ADR-0034/0035 own that path)
Rejected   importing dashboard_app into workbench_ui
                                 (couples private control to the public
                                  projection contract)
```

Rendering a native Signal Research summary from persisted artifacts inside the
workbench is allowed and expected — that is reading artifacts, not embedding
another application.

### 6. No new public surface

Nothing in `apps/workbench` publishes anything. The only public path remains
ADR-0034/ADR-0035's explicit projection release. A future "publish from the
workbench" action is a separate decision and is out of this ADR's scope.

## Alternatives Considered

1. **Add control pages to `apps/dashboard`.** Rejected: it is now a public,
   deny-by-default projection consumer (ADR-0034/0035). Granting it
   `trading_framework` imports would put workflow invocation code in the same
   package as pages served to the internet, and would delete the one boundary
   test that currently makes the public surface auditable.
2. **Put the control surface in `apps/cli`.** Rejected: ADR-0026 §5 scopes the
   CLI to four YAML-driven command groups. A long-lived HTTP process with job
   state is not a CLI, and merging them would make the CLI's "no side effect
   before validation" guarantee harder to reason about.
3. **Extend `src/trading_framework/` with a web layer.** Rejected: ADR-0001 and
   ADR-0022 keep the framework free of deployable-consumer concerns; the
   framework must stay usable with no UI at all (Vision §1).
4. **Single-process app with internal layering only (no HTTP boundary).**
   Rejected as the *committed* boundary, though it is a legal implementation of
   §2: without a versioned API the frontend choice stops being reversible, and
   the job runner (ADR-0041) needs a process that outlives a UI session anyway.
   A first implementation may co-locate `workbench-api` and the runner in one
   process; it may not co-locate the UI with direct in-process calls into
   `workbench_core`.
5. **Reverse-proxy the existing dashboard under the workbench.** Rejected: §5.

## Consequences

### Positive

- The public trust surface (`apps/dashboard`) is provably unchanged; its
  boundary test still passes untouched.
- The frontend-framework decision stays genuinely deferred, as the PRD requires.
- Import rights are per-app, named and tested, matching how ADR-0026 already
  behaved — no more implicit reading of ADR-0022 rule 2.
- The job runner gets a natural home outside the framework package.

### Negative

- A fourth workspace member: another `pyproject.toml`, another CI job, another
  boundary-test scan target.
- Two front doors that invoke workflows (`apps/cli`, `apps/workbench`) must stay
  behaviourally consistent. ADR-0041 mitigates this by making the workbench
  execute *through* the CLI rather than beside it.
- A loopback HTTP hop adds latency and an extra failure mode for what is
  currently a single-process script invocation.

### Neutral

- The API version string is a contract; the port and process manager are not.
- Packaging/startup for local forks remains an open direction question in
  `RESEARCH_APPLICATION_PRODUCT_VISION.md` §9.

## Follow-up

- The UI framework choice is a separate decision, gated on this ADR.
- `tests/unit/test_apps_boundaries.py` must gain `apps/workbench/src/**` as two
  distinct scan scopes with two distinct rule sets.
- TD-024 (module- vs symbol-granularity in the allow-list) now applies to a
  second app; consider whether that raises its repayment priority.

## Related

- `docs/adr/ADR-0022-repository-top-level-layout.md`
- `docs/adr/ADR-0026-operator-cli-framework-and-placement.md` (+ Amendment 1)
- `docs/adr/ADR-0034-portfolio-publication-boundary.md`
- `docs/adr/ADR-0035-complete-public-catalog-publication.md`
- `docs/adr/ADR-0041-workbench-local-job-runner.md`
- `docs/product/PRD-research-workbench-mvp.md`
- `docs/vision/RESEARCH_APPLICATION_PRODUCT_VISION.md` §3.5, §4.1
- `docs/reference/modules/DASHBOARD_APPLICATION.md`
