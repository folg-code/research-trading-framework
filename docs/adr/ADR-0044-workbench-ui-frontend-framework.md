# ADR-0044 — Workbench UI Frontend: React + Next.js, Static Export

## Status

ACCEPTED

Approved by the user in conversation, 2026-09-15: "Jeśli chodzi to
technologię frontendową to preferuję React + Next.js", followed by two
scoping choices made in the same conversation (App Router; static export
over a long-lived Next.js server).

## Context

ADR-0037 §2 created `workbench_ui` as a package that **must not import
`trading_framework` at all** and talks to `workbench_core` only over the
loopback `workbench.api.v1` JSON API. ADR-0037's own Follow-up section
deferred the actual framework choice explicitly: *"The UI framework choice
is a separate decision, gated on this ADR."* `apps/workbench/CLAUDE.md`
restates this as a hard rule: *"do not add a UI dependency or framework
import here without a separate decision."*

`docs/product/PRD-research-workbench-mvp.md` names "selecting a final
frontend framework" a non-goal **of the PRD** — i.e. the product
requirements do not prescribe one. That non-goal does not mean the choice is
avoided forever; Sprint 064 T008 (the first end-to-end operator slice) is
the point a real, renderable UI is needed, so the choice has to be made now,
deliberately, as its own decision — which is exactly what this ADR is.

Two things ADR-0037 already fixed, which this ADR must not relitigate:

- `workbench_ui` MUST NOT import `trading_framework` (ADR-0037 §2).
- Everything `workbench_ui` needs comes over `workbench.api.v1` — a
  versioned, JSON-only, loopback HTTP contract (ADR-0037 §4). *"That
  versioned boundary is what keeps the deferred frontend-framework choice
  reversible: any UI that can call HTTP satisfies it."*

## Decision

### 1. React + Next.js, App Router

`workbench_ui` is a Next.js application (App Router, TypeScript) using React
as its component model. No other frontend framework was seriously
considered once the user expressed this preference directly — see
Alternatives Considered for why a from-scratch SPA or a non-React framework
were not pursued instead.

### 2. Static export — no Next.js server process, ever

`next.config` sets `output: 'export'`. The build produces a static
`out/` directory (HTML/JS/CSS only); there is no Next.js server, no API
routes, no server components that fetch data server-side, and no
middleware. Every data access happens client-side, in the browser, against
`workbench-api`'s JSON endpoints — the same contract a `curl` script or a
future non-React UI would use.

This is chosen over running `next dev`/`next start` as a second long-lived
process for one reason ADR-0037 already cares about: **it makes "`workbench_ui`
MUST NOT import `trading_framework`" true at the language level, not just by
convention.** There is no Node process at runtime that could ever be handed
a Python import to begin with — the boundary ADR-0037 §2 wrote as a rule
becomes, for this framework choice, physically impossible to violate through
`workbench_ui`'s own runtime, rather than something a test has to keep
policing. A dynamic Next.js server (API routes, `getServerSideProps`) would
reopen exactly the failure mode ADR-0037 §2 was written to close: a
server-side code path someone could, by habit or convenience, point at
`trading_framework` directly instead of through `workbench-api`.

### 3. Packaging: `workbench-api` serves the static build

`workbench-api` (aiohttp, ADR-0037 §4) gains a static-file route serving
`out/` at `/`, alongside its existing `/api/v1/*` routes, on the same
loopback origin and port. An operator runs one process (`workbench-api`)
and opens one URL; there is no second port, no CORS configuration, and no
process-lifecycle question for a UI server, because there is no UI server.
This directly answers part of `RESEARCH_APPLICATION_PRODUCT_VISION.md` §9's
open "packaging/startup for local forks" question for the UI half of that
question — one process, one port, a static directory.

`next dev` (a real, if different, Next.js dev server) is still the
development-time workflow for iterating on `workbench_ui` itself, run
against a live `workbench-api` on its own port with CORS enabled for that
case only; it is never how an operator runs the finished tool, and no
production code path depends on it being available.

### 4. Directory layout: `apps/workbench/ui/`

The Python stub package `apps/workbench/src/workbench_ui/` (T004's
deliberately near-empty placeholder, predating this decision) is removed.
The real frontend lives at `apps/workbench/ui/` — a sibling to `src/`, with
its own `package.json`, `next.config`, and `app/` directory. It is not a uv
workspace member (uv workspaces are a Python packaging mechanism); it is
built with its own toolchain (`npm`/`pnpm`, whichever the implementing PR
picks and documents) and its output is what `workbench-api` serves per
decision 3.

`tests/unit/test_apps_boundaries.py`'s `workbench_ui` boundary scan
(currently an AST walk for `import trading_framework`, per ADR-0037 §2)
is retargeted or removed for this new location: a TypeScript/JavaScript file
cannot import a Python module, so the rule it was enforcing is now
structurally true rather than something to scan for. The implementing PR
keeps *some* automated proof this boundary holds (at minimum, that
`apps/workbench/ui/` contains no Python files and that `workbench-api`'s
static route serves only pre-built assets, never proxies or re-exports
anything from `trading_framework`) rather than deleting the scan with
nothing in its place.

## Consequences

### Positive

- ADR-0037 §2's "`workbench_ui` MUST NOT import `trading_framework`" rule
  becomes enforced by the language boundary itself, not just a test.
- One process, one port for an operator to run and open — no second server,
  no CORS setup, no extra process-lifecycle question.
- `workbench.api.v1` stays the only contract `workbench_ui` depends on;
  nothing about this decision reopens ADR-0037 §4.
- React + Next.js + App Router is a widely documented, actively maintained
  stack — low onboarding cost for future contributors, large ecosystem for
  the form-heavy, polling-heavy UI T008 needs (template editor, live job
  status, YAML preview).

### Negative

- A fourth toolchain in the repository (Node/npm alongside Python/uv) —
  another thing a contributor or CI needs installed, another lockfile
  family, another `CLAUDE.md` to keep current.
- Static export forgoes SSR, ISR, and Next.js API routes entirely; any
  future requirement that genuinely needs server-side rendering (unlikely
  for a local, single-operator control surface, per the PRD's own
  single-user non-goals) would need revisiting this ADR, not just a config
  flip, since decision 2's whole point is that no such server exists.
- Dynamic routes (e.g. a job-detail page keyed by `job_id`) need
  client-side routing/data-fetching patterns suited to static export
  (e.g. a single dynamic shell reading `job_id` from the URL client-side)
  rather than Next.js's server-rendered dynamic route data-fetching — a
  real but well-documented pattern, not a blocker.

### Neutral / Trade-offs

- `next dev`'s CORS-enabled, two-port development workflow is real but
  strictly a development-time convenience; it carries no production
  behavior and is not itself part of this ADR's committed architecture.
- The exact Node package manager and its lockfile are an implementation
  detail for the PR that scaffolds `apps/workbench/ui/`, not decided here.

## Alternatives Considered

### Option A — A different frontend framework (Vue, Svelte, a vanilla SPA)

- Pros: some of these have a smaller runtime footprint or steeper-but-faster
  learning curve for a small UI.
- Cons: the user directly expressed a React + Next.js preference; nothing
  in the PRD, ADR-0037, or the T008 requirements favors a different stack
  strongly enough to override that.
- Reason rejected: no material requirement pulls away from the stated
  preference.

### Option B — Next.js with a live server (`next start`), not static export

- Pros: full Next.js feature set available (SSR, API routes, middleware) if
  a future need arises; conventional Next.js dynamic-route ergonomics.
- Cons: reopens the exact failure mode ADR-0037 §2 closed — a server-side
  code path (an API route) that someone could point at `trading_framework`
  directly; a second long-lived process to start, stop, and reconcile with
  `workbench-api`'s own lifecycle; a second port and CORS configuration for
  what is a single local operator's tool.
- Reason rejected: nothing about T008 or the PRD needs SSR or server-side
  Next.js code, and running it anyway buys those costs for no benefit while
  weakening a boundary ADR-0037 explicitly wanted structurally enforced.

### Option C — Keep `workbench_ui` a Python stub; defer the real UI further

- Pros: defers the toolchain-addition cost past this sprint.
- Cons: T008 is explicitly "the sprint's single demonstrable outcome — one
  study, start to finish, no terminal" (`SPRINT_064.md`); without a real UI,
  T008 cannot be delivered at all.
- Reason rejected: the sprint's own committed scope requires a working UI
  now, and the user has already made the framework choice this ADR needed
  to unblock it.

## Follow-up

- The implementing PR (Sprint 064 T008) scaffolds `apps/workbench/ui/`,
  wires `workbench-api`'s static route, and updates
  `tests/unit/test_apps_boundaries.py` and both `apps/workbench/CLAUDE.md`
  and `apps/cli/CLAUDE.md` (cross-reference only) accordingly.
- `RESEARCH_APPLICATION_PRODUCT_VISION.md` §9's "packaging/startup for
  local forks" open question is now partially answered for the UI
  (decision 3); the Python-side packaging half remains open.
- If a genuine SSR/server-side requirement ever appears, that is a new ADR
  amendment, not a silent `next.config` edit — decision 2 is a structural
  choice, not a default that happens to be in place.

## Related

- `docs/adr/ADR-0037-research-workbench-application-boundary.md` (§2, §4,
  Follow-up — this ADR resolves the deferred choice)
- `docs/adr/ADR-0041-workbench-local-job-runner.md`
- `docs/product/PRD-research-workbench-mvp.md`
- `docs/vision/RESEARCH_APPLICATION_PRODUCT_VISION.md` §9
- `docs/planning/sprints/SPRINT_064.md` T008
- `apps/workbench/CLAUDE.md`
