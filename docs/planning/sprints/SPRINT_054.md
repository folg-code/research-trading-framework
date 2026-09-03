# Sprint 054 — Vision Reclassification and Reference Layering (Phase 6b + 10a)

## Metadata

```text
Sprint: 054
Phase: Cross-cutting docs architecture — not part of the Phase 15 predictive
       research track (Sprint 052 / Phase 15B is unaffected).
Status: PLANNED — requires maintainer approval before opening.
Planned Start: TBD
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: Sprint 053 (repo workflow & docs hygiene) — closed on `main`
            (#418). This sprint picks up the two items Sprint 053
            deliberately deferred as "larger than a single reviewable
            change": Phase 6b (vision file reclassification) and Phase 10a
            (docs/reference/ layering), both from
            docs/historical/REPO_WORKFLOW_DOCS_AUDIT.md.
Depended On By: None known.
Sprint Branch: sprint/vision-and-reference-reclassification
Task branch convention: feat/ | fix/ | docs/ | test/ | refactor/
PR base: sprint/vision-and-reference-reclassification (never main until
         sprint integration)
Architecture Sources:
  - docs/historical/REPO_WORKFLOW_DOCS_AUDIT.md, Phase 6a/6b/10a — AUTHORITATIVE
    for this sprint's findings, sequencing, and evidence base
  - docs/vision/README.md — current vision-folder taxonomy and precedence rules
  - docs/reference/README.md — current reference-folder index (flat, 12 files)
```

## 1. Goal

Turn the audit's two largest, explicitly-deferred recommendations into
finished work: (a) confirm which parts of the 5 largest `docs/vision/` files
describe already-built behavior vs. genuinely future architecture, and (b)
give `docs/reference/` a layered navigation model (`system/` → `workflows/`
→ `modules/`) instead of its current flat 12-file list. Both require reading
large files in full before moving anything — this sprint is sequenced so
that reading and classifying happens before any file is split or moved.

## 2. Scope

**In scope**, sequenced per the audit's own Phase 10a recommendation (do not
reorder — step 4 depends on steps 1-3 settling content ownership first):

| # | Task | Audit ref | Size |
|---|---|---|---|
| T001 | Full read + current-vs-future section classification of `docs/vision/ARCHITECTURE_FOUNDATIONS.md` (1,557 lines). Produces a section-by-section table (current/future/mixed) as this sprint's Decisions output — no file is moved yet. | Phase 6b | Large (read-only) |
| T002 | Same for `docs/vision/ARCHITECTURE_TECHNICAL.md` (2,459 lines) | Phase 6b | Large (read-only) |
| T003 | Same for `docs/vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` (1,332 lines) — already known to contain at least one shipped-behavior section inside a file the vision index calls entirely future (line ~1308 per the audit) | Phase 6b | Large (read-only) |
| T004 | Move each file's confirmed-current sections (per T001-T003) to `docs/reference/system/` (new); leave confirmed-future sections in `docs/vision/`; leave genuinely ambiguous sections in `docs/vision/` with a one-line "as-built status unclear, see ADR-XXXX" note rather than guessing | Phase 6b | Medium — depends on T001-T003 |
| T005 | Maintainer decision: does `docs/vision/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md` (1,102 lines, self-describes as "authoritative" — a reference-tier claim) move to `docs/reference/` wholesale? | Phase 6b | Decision + move if yes |
| T006 | Maintainer decision: where does `docs/vision/WORKFLOWS_AI_ADR.md` (2,583 lines, process/workflow content, not target architecture) belong — stays in `vision/`, or folds into `docs/README.md`/`AGENTS.md`'s process layer? | Phase 6b | Decision + move if relocating |
| T007 | Content audit of all 12 current `docs/reference/` files (+ 3 in `modules/`): tag each file/section as system-level, workflow-level, module-level, or operational-runbook-level. Produces the actual split plan — not assumed from filenames. | Phase 6a | Large (read-only) |
| T008 | Execute the `docs/reference/` split into `system/` (`SYSTEM_OVERVIEW.md` new, `MODULE_MAP.md` moved, `DEPENDENCY_RULES.md` consolidated from `AGENTS.md`/`ARCHITECTURE_CONTROL.md`/`ARCHITECTURE_AND_WORKFLOWS.md` pointers), `workflows/` (`SIGNAL_RESEARCH.md`, `STRATEGY_RESEARCH.md`, `STRATEGY_EXECUTION.md`, `MARKET_DATA.md` — extracted per T007's plan, not the audit's untested guess), and `modules/` (existing 3 files plus any new ones T007 identifies as missing) | Phase 6a | Large — depends on T007 |
| T009 | Update every inbound reference to a moved/renamed file (`AGENTS.md`, `docs/README.md`, ADRs, sprint docs as applicable) | Phase 6a, 6b | Medium — mechanical once T004/T008 land |
| T010 | Phase F validation re-run (the 4 checks from Sprint 053, plus a 5th: "how does strategy execution work" should resolve via `docs/reference/workflows/STRATEGY_EXECUTION.md` in 1-2 lookups, not a flat-file guess) | Phase F | Small |

**Out of scope:**
- Rewriting the substance of any section — this sprint relocates and
  reclassifies content, it does not rewrite architecture decisions.
- Any change to `docs/adr/` — ADRs are immutable history and untouched here.
- Sprint-doc archival backlog (separate, already-deferred Sprint 053 item).

## 3. Decisions (Wave 0)

Binding decisions to confirm with the maintainer before opening task
branches — several of these cannot actually be pre-decided (that's the
point of T001-T003, T007) and are listed here as **decision gates**, not
answers:

- **D-S054-01 — Sequencing is mandatory.** T004 and T008 may not start
  before T001-T003 and T007 (respectively) are complete and reviewed. This
  mirrors the audit's own explicit warning: "splitting file organization
  before content ownership is settled would just move the ambiguity
  around."
- **D-S054-02 — Ambiguous sections stay put.** Where T001-T003 can't cleanly
  classify a section as current or future, the default is to leave it in
  `docs/vision/` with a status note, not to guess and move it. False
  negatives (future content miscategorized as current) are worse than
  leaving something in `vision/` a little longer.
- **D-S054-03 — T005/T006 are maintainer calls, not agent calls.** The
  audit explicitly declined to reclassify `ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md`
  or relocate `WORKFLOWS_AI_ADR.md` unilaterally. This sprint does the same
  — these two tasks produce a recommendation, then wait for sign-off before
  moving anything.
- **D-S054-04 — This sprint is large; expect multiple waves.** Combined
  vision-file line count is ~9,000 lines across 5 files; `docs/reference/`
  is 15 files. Task branches should follow normal PR-size discipline (one
  coherent outcome per PR) even though the reading itself is unavoidably
  large — a single read-and-classify task is not the same PR as the move it
  produces.

## 4. Tasks

| ID | Task | Depends on | Status |
|---|---|---|---|
| T001 | Classify `ARCHITECTURE_FOUNDATIONS.md` sections | — | TODO |
| T002 | Classify `ARCHITECTURE_TECHNICAL.md` sections | — | TODO |
| T003 | Classify `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` sections | — | TODO |
| T004 | Move confirmed-current sections to `docs/reference/system/` | T001, T002, T003 | TODO |
| T005 | Maintainer decision + move: `ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md` | — | TODO |
| T006 | Maintainer decision + move: `WORKFLOWS_AI_ADR.md` | — | TODO |
| T007 | Content audit of 12+3 `docs/reference/` files, produce split plan | — | TODO |
| T008 | Execute `docs/reference/` → `system/`/`workflows/`/`modules/` split | T007 | TODO |
| T009 | Update all inbound references | T004, T005, T006, T008 | TODO |
| T010 | Phase F validation re-run (5 checks) | T001-T009 | TODO |

## 5. Progress

Not started — sprint is PLANNED, pending maintainer approval to open.

## 6. Outcome

TBD.

## 7. Follow-ups (explicitly not this sprint)

- Any full ADR supersession pass triggered by findings in T001-T003 (e.g. if
  a vision section turns out to contradict an existing ADR rather than just
  predate it) — flag as a new ADR or problem-registry item, don't resolve
  inline.
- Sprint-doc archival backlog (still deferred from Sprint 053).
