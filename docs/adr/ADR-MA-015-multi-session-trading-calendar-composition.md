# ADR-MA-015 — Multi-Session Trading Calendar Composition

## Status

PROPOSED

## Context

Phase 19 Sprint 066 (Wave A) needs three `session.*` Market Analysis
components — `session.overlap_window`, `session.previous_period_extreme`,
`session.current_period_extreme` (IDEA-027) — and Wave 0's D-P19-04
decision placed their session-hour definitions in the shared
`src/trading_framework/time/sessions/` module, "extending the existing
`TradingSessionResolver` pattern."

An architecture-triage pass before implementing T001 (session-calendar
module) found that pattern does not generalize as assumed:

1. **One resolver per execution run.** `SequentialBatchExecutor.execute()`
   accepts a single optional `session_metadata`/`session_resolver` pair
   for the whole plan (`execution/executor.py`); there is no per-component
   resolver selection and no other executor variant in the repo.
2. **`TradingSessionMetadata` silently drops unknown columns.**
   `assembly/session_metadata.py` validates only that the four required
   `RESOLVER_OUTPUT_COLUMNS` (`timestamp`, `trading_day`, `session_id`,
   `is_rth`) are present, then does `frame.select(*_STORED_COLUMNS)` where
   `_STORED_COLUMNS = ("trading_day", "session_id", "is_rth")` — any extra
   resolver output column is discarded, not an error.
3. **`is_rth` is a single, CME-ES-RTH-shaped boolean**, consumed directly
   by `structure.session_range` (`(trading_day, is_rth)` grouping) and by
   two non-analysis call sites (`contract_rth_volumes.py`,
   `market/continuous/volumes.py`). Nothing in the codebase composes two
   named sessions or asks "is this bar in session A **and** session B."
4. **Wide fan-out, zero prior design.** ~20 `application/*` request types
   forward a `session_resolver` parameter down to `run_analysis.py`, the
   single place that constructs `TradingSessionMetadata`; the whole test
   suite constructs `CmeEsRthSessionResolver()` directly. ADR-MA-013 (the
   ADR that introduced this machinery) already flagged "RTH resolver is
   ES-specific; other instruments need new resolver implementations" as a
   known limitation, but neither it nor any later ADR or planning document
   designed multi-session composition.

`session.overlap_window` cannot be built against today's contract: it
needs simultaneous membership in two named sessions (e.g. London and New
York), and today's model carries exactly one boolean.

Per this project's own established convention (ADR-0028's engine-change
precedent, and this sprint's own binding rule that a Wave-0-invalidating
finding is a STOP-AND-REPORT, not a silent in-sprint fix), this ADR
proposes the extension design before T001 touches any shared code.

## Decision

### 1. Named-session resolvers stay separate from `TradingSessionResolver`

`TradingSessionResolver` (the `is_rth`/`session_id`/`trading_day` contract)
is **unchanged**. Add one new resolver,
`GlobalSessionCalendarResolver`, to `time/sessions/`, implementing the
*same* `TradingSessionResolver` protocol (still returns the four required
columns, computed identically to `CmeEsRthSessionResolver` — RTH stays
RTH) **plus** additional boolean columns, one per named intraday session:
`session_asia`, `session_london`, `session_new_york`. Exact hour windows
(against a documented reference, e.g. Asia 00:00–09:00 `Asia/Tokyo`,
London 08:00–16:30 `Europe/London`, New York 09:30–16:00
`America/New_York`) are the implementer's call in T001, following
`CmeEsRthSessionResolver`'s own UTC-in → `dt.convert_time_zone` →
weekday/hour/minute pattern — no new timezone-handling approach is
introduced. `GlobalSessionCalendarResolver` is a **superset**, not a
replacement: it may delegate to (or duplicate) `CmeEsRthSessionResolver`'s
own RTH computation so `is_rth` stays byte-identical for any consumer that
only cares about RTH.

No second resolver-protocol type is introduced, and the executor's
`session_resolver` parameter shape does not change — one resolver, one
call, more output columns.

### 2. `TradingSessionMetadata` gains dynamic named-session columns

`assembly/session_metadata.py` changes additively:

- `_STORED_COLUMNS`'s selection becomes: the four required columns, plus
  any column in the resolved frame matching the `session_<name>` naming
  convention (`session_asia`, `session_london`, `session_new_york`, and
  any future named session — no fixed allow-list to edit per new session).
- A new accessor, `TradingSessionMetadata.named_session(name: str) ->
  tuple[bool, ...]`, lazily materialized like `.is_rth` already is.
  Requesting a name absent from the resolved frame (e.g. a run configured
  with plain `CmeEsRthSessionResolver`, which carries no `session_*`
  columns) raises a clear, actionable error — never silently returns all
  `False` or `None`.
- `RESOLVER_OUTPUT_COLUMNS` (the *required* four) is unchanged. Existing
  consumers (`structure.session_range`, `contract_rth_volumes.py`,
  `market/continuous/volumes.py`, every test constructing plain
  `CmeEsRthSessionResolver()`) are unaffected — they never read
  `session_*` columns and never will unless they opt in.

### 3. Adoption is opt-in per request, not a default change

`run_analysis.py` and every `application/*` request type keep forwarding
`session_resolver` exactly as today — no signature change. A caller that
wants `session.overlap_window`, `session.previous_period_extreme`, or
`session.current_period_extreme` to resolve correctly passes
`GlobalSessionCalendarResolver()` instead of `CmeEsRthSessionResolver()`;
every other call site is untouched and keeps using the plain resolver.
`AnalysisWorkspace`'s internal per-resampled-timeframe re-resolution path
(`storage/workspace.py`, `_session_metadata_for`) needs no separate
change: it already re-invokes whatever resolver was configured and stores
whatever `TradingSessionMetadata` that produces, so it inherits the new
columns automatically once (2) lands.

### 4. Session.* components consume `named_session` directly

`session.overlap_window`'s implementation reads
`workspace.session_metadata.named_session("london")` and
`.named_session("new_york")` and ANDs them elementwise — no new
`ComponentDependency`/`ComponentOutputRef` machinery, since this is
workspace-level session metadata, the same access pattern
`structure.session_range` already uses for `.is_rth`.

`session.previous_period_extreme` and `session.current_period_extreme`
need **day/week period boundaries**, not named-session membership — a
different concept this ADR does not conflate with (1)-(4). Day boundaries
reuse the *already-required* `trading_day` column; week boundaries (if
needed) are derived by the component itself from `.trading_days` — no new
`TradingSessionMetadata` capability required for period grouping.

## Consequences

### Positive

- Fully additive: no existing consumer, request type, or executor
  signature changes. Every test constructing `CmeEsRthSessionResolver()`
  directly keeps working unchanged.
- One resolver call per run is preserved — no change to the "one resolver
  per execution plan" architecture, only to what that one resolver's
  output frame may carry.
- `session.overlap_window` becomes buildable against a real, named,
  simultaneous-membership contract instead of a workaround.
- Sets a real precedent for adding a fourth, fifth, ... named session
  later without touching `TradingSessionMetadata`'s stored-column logic
  again (it is already dynamic per `session_*`).

### Negative / limitations

- Any Wave A `session.*` component only resolves correctly when the run
  was configured with `GlobalSessionCalendarResolver` (or an equivalent
  future resolver carrying the needed `session_*` columns) — a caller
  using plain `CmeEsRthSessionResolver` gets a clear error, not silently
  wrong output, but this is still a caller-side configuration
  responsibility this ADR introduces.
- Exact session-hour boundaries (Asia/London/New York) are set by
  whoever implements T001 against a documented reference, not fixed by
  this ADR — a later finding that a boundary is wrong is a data-accuracy
  fix, not an architecture change.
- `GlobalSessionCalendarResolver` duplicates or wraps
  `CmeEsRthSessionResolver`'s RTH logic; if the two drift out of sync in a
  future edit, `is_rth` could disagree between the two resolvers. T001
  should delegate rather than duplicate where practical to avoid this.

### Follow-up (deferred)

- IDEA-031's deferred session-anchored VWAP variant (Wave B) will consume
  the same `named_session` mechanism once it needs session-anchored
  windows.
- A future resolver-composition mechanism accepting a list of named
  sessions from configuration (rather than one fixed
  `GlobalSessionCalendarResolver` class listing all three) if the named-
  session set keeps growing — not needed for this sprint's three fixed
  sessions.

## References

- `docs/adr/ADR-MA-013-cme-es-rth-session-and-swing-structure-mtf-projection.md`
  (introduces `TradingSessionResolver`/`CmeEsRthSessionResolver`/`is_rth` —
  unchanged by this ADR, referenced not superseded)
- `docs/planning/roadmap/PHASE_19_WAVE0_DECISIONS.md` D-P19-04 (original
  session-calendar placement decision this ADR makes concrete)
- `docs/planning/sprints/SPRINT_066.md` T001/T002
- `src/trading_framework/time/sessions/cme_es_rth.py`
- `src/trading_framework/market_analysis/assembly/session_metadata.py`
- `src/trading_framework/market_analysis/storage/workspace.py`
- `src/trading_framework/market_analysis/components/structure/session_range.py`
