# Sprint 054 — T010 Phase F Validation Re-Run

```text
Task:   Sprint 054, T010
Date:   2026-09-03
Scope:  Re-run the 4 Phase F checks (defined in
        docs/historical/REPO_WORKFLOW_DOCS_AUDIT.md, "Phase F — Validation")
        plus the 5th check this sprint doc added, against the repository
        state after T001-T009 landed.
```

## Checks

**1. "What's the current architecture for market data ingestion?" — should
resolve via `docs/reference/MODULE_MAP.md` → `docs/reference/DATA_WORKFLOWS.md`
in 1–2 lookups, not a `src/` scan.**

**Result: PASS, via an updated path.** `MODULE_MAP.md` moved to
`docs/reference/system/MODULE_MAP.md` (Sprint 054 T008). `DATA_WORKFLOWS.md`
does not exist and never did during this sprint — it was already a dead
reference before Sprint 054 (the pre-T008 `docs/reference/README.md` carried
it with a "file not in tree" caveat). T008's rewritten
`docs/reference/README.md` dropped the dead row rather than moving it.
The check still resolves: `docs/reference/README.md` →
`system/MODULE_MAP.md` → §5 "Market Data Implementation Map" answers the
question directly, in 2 lookups. Recommend logging the permanently-missing
`DATA_WORKFLOWS.md` reference as a separate docs-hygiene item if not already
tracked — out of Sprint 054's scope to author.

**2. "Why does `apps/*` not import research/execution engines directly?" —
should resolve to ADR-0022 directly from `AGENTS.md:30`.**

**Result: PASS, line number shifted.** `AGENTS.md` line 37 (not line 30 —
shifted by T006b's edits, which extended the required-reading list and
added two Boundaries bullets) states: *"treat `apps/*` as separate
deployable consumers (ADR-0022); they must not import research/execution
engines or provider/importer adapters."* Resolves in 1 lookup.

**3. "What's the current sprint?" — should resolve via
`docs/planning/CURRENT_STATUS.md` alone.**

**Result: FAILED before this task, FIXED as part of T010.**
`CURRENT_STATUS.md` still named `SPRINT_053` as the Active Sprint and
`sprint/repo-workflow-docs-hygiene` as the active branch, even though
Sprint 053 was closed and merged via #418 before Sprint 054 was ever opened
— this staleness predates Sprint 054 and was not introduced by it, but it
directly fails this validation check, so it is corrected here rather than
just reported: Active Sprint is now `SPRINT_054`
(`sprint/vision-and-reference-reclassification`), with Sprint 053 recorded
as the last completed cross-cutting sprint. See the diff to
`docs/planning/CURRENT_STATUS.md` in this commit.

**4. A repo-wide `rg` run from a fresh worktree should not surface matches
from any other sibling worktree once Phase A's `.gitignore` change lands.**

**Result: PASS.** `.gitignore` (root) lines 68-69 already exclude
`.claude/worktrees/` and `.codex/worktrees/` (landed in Sprint 053 Phase A,
confirmed still present).

**5. (Added by SPRINT_054.md) "How does strategy execution work?" — should
resolve via `docs/reference/workflows/STRATEGY_EXECUTION.md` in 1-2
lookups, not a flat-file guess.**

**Result: PASS, via a different file than originally assumed.** T007's
content audit (read-only, evidence-based) rejected fabricating a
`workflows/STRATEGY_EXECUTION.md` from scratch — no existing source content
forms a standalone narrative for it without authoring new prose, which was
out of scope. Instead, Strategy Execution architecture lives in
`docs/reference/system/WORKFLOWS_ARCHITECTURE.md` (moved from
`docs/vision/WORKFLOWS_AI_ADR.md` §1-5/§8 by T006c), which has a dedicated
`## Strategy Execution` section. Path: `docs/reference/README.md` →
`system/WORKFLOWS_ARCHITECTURE.md` → "Strategy Execution" heading — 2
lookups, same navigability the check intended, via the sprint's own
audited structure rather than its original untested guess.

## Summary

4 of 5 checks passed as-is; 1 (CURRENT_STATUS.md staleness) failed and was
fixed as part of this task, since it was a one-line factual correction well
within a validation task's remit. No check required deferring to a future
sprint. Sprint 054's core deliverable — vision/reference navigability
without a full-repo scan — holds up under a fresh-agent-style walkthrough.
