# Status and reference review — 2026-09-12

## Evidence method

This is a documentation-first review of all 34 TD entries, 26 idea entries,
the 12 files in `docs/vision/`, an inventory and cross-check of the 50 files
in `docs/reference/`, and the 60
numbered completed sprint records under `docs/archive/phases/`. The
[sprint coverage matrix](completed-sprint-coverage.csv) maps each completed
sprint to its primary current reference or planning entry point. For disputed
implementation claims, the review checked source files, tests, ADR status and
the completed sprint record. An ADR marked accepted was not treated as proof
that its code shipped.

The matrix is a navigation and coverage audit, not a copy of 60 sprint plans.
Decision-only and documentation-only sprints are classified separately; they
do not create fictional runtime capabilities.

## Technical debt dispositions

| Disposition | IDs | Evidence and action |
|---|---|---|
| Repaid in this review | TD-001 | The indexed ADR catalog and separate architecture references now exist. Historical text is retained with a dated review note. |
| Previously repaid, reconfirmed | TD-017–021 | Sprint 026/027 hot-path changes and the promoted-artifact repository remain reflected in source and Reference. |
| Obsolete, never incurred | TD-005, TD-007 | There is no general `EventBus` and no general external Trading Calendar adapter; both are still future directions. |
| Accepted with narrowed current meaning | TD-003, TD-011 | Market Analysis has expanded package structure but not a permanent per-category component layout. The columnar historical query exists beside the list-returning API; it does not erase TD-011. |
| Accepted, reconfirmed | TD-002, TD-004, TD-006, TD-008–010, TD-012–016, TD-022–034 | No completed phase or targeted code check proved repayment of these specific remaining shortcuts. TD-023's Binance historical importer still restricts 1m; TD-031/032 remain missing loader/CLI surfaces; TD-034 still serializes one projection bundle. |

Final counts: **26 accepted, 6 repaid, 2 obsolete**. Repaid/obsolete entries
remain addressable by stable ID but no longer count as open debt.

## Idea dispositions

| Disposition | IDs | Evidence and action |
|---|---|---|
| Implemented | IDEA-005 | Databento DBN `trades` import is built; derived OHLCV is a separate workflow. The old "DBN OHLCV first" delivery sequence was superseded. |
| Implemented | IDEA-007 | Continuous-futures contract/roll/trades/derived-bar path is delivered (Sprint 015, ADR-0018). Other roll policies are separate future work. |
| Partially implemented | IDEA-024 | A read-only public research catalog and selected study/report views exist; a complete local research workbench and unrestricted dataset browsing do not. |
| Still proposed/deferred/gated | Remaining 23 IDs | No matching completed full capability. Borderline IDEA-006, 008, 015, 020 and 026 have specific review notes distinguishing existing narrower slices from the proposed whole. |

`IDEA_INBOX.md` now states delivered/partial status at the entry point rather
than presenting these IDs as unstarted work.

## Vision review

The concise future-direction files plus `README.md` describe undelivered
extensions and link to implemented Reference baselines. The
longer Research Application vision was corrected so immutable public
projection releases, selected studies and bounded Live Paper status are
explicitly current; only deployment/session publication and broader control
remain in its Public Portfolio direction. Research Space now distinguishes
implemented bounded Signal/Predictive candidate paths from the future
cross-workflow cost estimator. A Portfolio Research methodology existed only
as a plan, so it moved from Reference to
[Portfolio Research Future](../../../docs/vision/PORTFOLIO_RESEARCH_FUTURE.md).
Future workspace lifecycle, column pruning and generic derived-data
materialization were likewise removed from the as-built workspace reference
and retained in Market Analysis Future. No roadmap gate was opened by this
review.

## Reference review against completed phases

The [Reference index](../../../docs/reference/README.md) now routes the
delivered phase tracks to current contracts. The audit found and corrected:

- stale dashboard page numbers after current page renumbering;
- a Predictive Research methodology that still described an older direct
  private-catalog scan as the current public page path;
- an accepted data-representation **target** written as if `MarketFrame` and
  universal fixed-point storage were already present. `MarketFrame` code has
  not shipped; contract trades use `price_nanos`, while bars and continuous
  trades retain string prices;
- missing current hot-path detail for Sprint 026 Signal Research and Sprint
  027 Market Data import/materialization in their workflow references.
- generic deep-reference bullets in capability guides that did not link to
  the actual module, workflow or ADR pages.
- older Market Analysis workspace and time-model sections that still treated
  multitimeframe support as future while also describing proposed pruning,
  derived-data persistence and 11-field identity as current. The implemented
  MTF alignment now stays in Reference; those remaining proposals sit in
  Vision with explicit non-implementation status.

The phase-level map covers every numbered completed sprint record found in
the archive. It points to current contracts instead of duplicating historical
task prose. Future review should repeat this cross-check when a new sprint
closes, especially where an ADR authorizes a later implementation stage.

Validation: all 60 matrix rows have distinct sprint IDs and existing target
files. The local Markdown validator checked 1113 links across 338 docs with
no missing files or anchors. The repository's `.ai-toolkit` validator remains
unavailable because `.ai-toolkit/bin/devteam.mjs` is not in this checkout.
