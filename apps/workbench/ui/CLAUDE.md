# apps/workbench/ui (`workbench_ui`)

React + Next.js (App Router, TypeScript), **static export only** — ADR-0044.
See `apps/workbench/CLAUDE.md` for how this fits into `apps/workbench` as a
whole and `docs/adr/ADR-0044-workbench-ui-frontend-framework.md` for the
full decision.

## Conventions specific to this module

- **`next.config.ts` sets `output: "export"`. Never add `next start`, an API
  route, `getServerSideProps`, or any server-side data-fetching without a
  fresh ADR amendment to ADR-0044 first** — the whole point of static
  export is that no Next.js server process exists at runtime, which is what
  makes "this app MUST NOT import `trading_framework`" (ADR-0037 §2) true at
  the language level rather than a rule a test has to keep policing. Every
  page here is a client component (`"use client"`) that fetches data from
  `workbench-api` after hydration — there is no other way for a statically
  exported page to get data.
- **`app/lib/api.ts` is the only file that knows the `workbench.api.v1`
  contract.** Every page imports typed functions from it (`listTemplates`,
  `submitJob`, `getJob`, ...) rather than calling `fetch` directly — if the
  API's JSON shape changes, this is the one file to update. It defaults to
  same-origin relative paths (`workbench-api` serves this app's own build
  at `/`, ADR-0044 decision 3); `NEXT_PUBLIC_API_BASE_URL` overrides it for
  `next dev` against a separately-started `workbench-api`.
- **A page reading `useSearchParams()` must stay wrapped in a `<Suspense>`
  boundary** (see `app/jobs/page.tsx`, `app/new/page.tsx`) — required by
  Next.js even for a fully static, no-dynamic-segment page; the build fails
  without it.
- **`<Link>` uses `prefetch={false}` everywhere in this app.** Next.js's
  default link-hover prefetch requests an RSC segment-cache path this
  simple static export + `workbench-api`'s catch-all file resolver does not
  produce, which is harmless (navigation itself always works — the
  fallback is the page's own `.html` file) but shows as noisy 404s in the
  browser console. Disabling prefetch is simpler and more honest than
  reverse-engineering Next's segment-cache file-naming to satisfy it, since
  prefetching a static shell buys nothing for a page whose actual data
  loads client-side after hydration anyway.
- **No dynamic route segments** (no `app/jobs/[jobId]/page.tsx`). A static
  export must know every possible value of a dynamic segment at build
  time, which is impossible for a `job_id` created at runtime — `app/jobs`
  is one static page that reads `?id=<job_id>` client-side instead. Follow
  the same pattern for any future per-item view.
- **`js-yaml` is a real dependency, not a dev convenience**: the study
  definition is edited as YAML text (matching what an operator would see
  opening the saved `.yaml` file directly, per T008's "generated YAML
  shown and editable"), parsed client-side with `js-yaml`, and sent to
  `workbench-api` as a plain JSON object — the API itself only ever deals
  in JSON; the `.yaml` file on disk is written server-side at save time.

## Never

- Import `trading_framework`, for any reason — there is no boundary test
  for this directory (unlike `workbench_core`'s), because a TypeScript file
  cannot import a Python module at all; do not try to route around that
  with some kind of code-generation or build-time bridge.
- Embed, iframe, or reverse-proxy the dashboard or a generated report
  (ADR-0037 §5) — link out only.
- Add a Node/npm dependency without checking whether it needs a server
  (Next API routes, `getServerSideProps`) to work — those are unusable
  under static export and would be dead weight, or worse, a temptation to
  reintroduce decision 2's exact failure mode.

## Tests

- No test suite of its own yet (Sprint 064 T008 shipped the flow itself,
  not frontend tests). `apps/workbench/tests/test_static_ui.py` covers the
  Python side of serving this build (`workbench-api`'s static-file
  resolver) against a synthetic fake export, not a real `npm run build`.
- Before relying on a change here, run `npm run build` in this directory
  and `npm run lint`, then serve the result through `workbench-api`
  (`TRADING_WORKBENCH_STORAGE_ROOT=<path> uv run --project apps/workbench
  workbench-api`) and click through the actual flow — this package has no
  automated coverage standing in for that yet.
