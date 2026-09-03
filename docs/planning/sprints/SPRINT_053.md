# Sprint 053 — Repository Workflow & Documentation Hygiene (Phase A–D)

## Metadata

```text
Sprint: 053
Phase: Cross-cutting infra/docs hygiene — not part of the Phase 15 predictive
       research track (Sprint 052 / Phase 15B remains the next research-track
       sprint and is unaffected by this one).
Status: PLANNED — requires maintainer approval before opening.
Planned Start: TBD
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: docs/historical/REPO_WORKFLOW_DOCS_AUDIT.md landing on `main`
            (currently only on branch `claude/repo-workflow-docs-audit-dfbfe3`,
            produced by a separate agent session on 2026-09-03) — that audit
            is this sprint's source of truth and evidence base; merge it
            before or as this sprint's first task.
Depended On By: None known. Phase 10a (docs/reference/ restructuring, vision
            file reclassification) is an explicit follow-up sprint, not this
            one — see §7 Follow-ups.
Sprint Branch: sprint/repo-workflow-docs-hygiene
Task branch convention: feat/ | fix/ | docs/ | test/ | refactor/
PR base: sprint/repo-workflow-docs-hygiene (never main until sprint integration)
Architecture Sources:
  - docs/historical/REPO_WORKFLOW_DOCS_AUDIT.md — AUTHORITATIVE for this
    sprint's findings and evidence; every task below cites its Phase/section
  - docs/README.md — folder-layout table this sprint adds one row to
  - docs/adr/README.md — ADR index this sprint corrects one row in
  - AGENTS.md — required-reading order; unaffected except one path fix
Quality Commands (per AGENTS.md — this sprint touches docs/config only, but
  run them anyway since renames can break references picked up by tooling):
  uv run ruff check . / uv run ruff format --check . / uv run mypy / uv run pytest
```

## 1. Goal

Close the near-term, low-to-medium-risk findings from the repo workflow/docs
audit (Phases A–D) without touching application code or making any of the
larger, not-yet-content-audited restructuring calls the audit deliberately
deferred (Phase 6a/6b/10a). This is a hygiene sprint: every task is either a
rename, a one-line factual correction, a trim with a preservation check, or a
policy note for future sprints — nothing here changes runtime behavior.

## 2. Scope

**In scope** (audit Phases A–D, "File action list" rows):

| # | Task | Audit ref | Risk |
|---|---|---|---|
| T001 | Add `.claude/worktrees/` and `.codex/worktrees/` to committed `.gitignore` | Phase A | Trivial |
| T002 | Fix `docs/adr/README.md` ADR-0020 status row (`PROPOSED` → `ACCEPTED (Sprint 017)`) | Phase B, Phase 9 | Trivial |
| T003 | Rename `docs/agents/AGENTS_MULTITIMEFRAME_MARKET_MODEL_UPDATED (1).md` → `AGENTS_MULTITIMEFRAME_MARKET_MODEL.md`; update the one reference at `AGENTS.md:62` | Phase B | Low |
| T004 | Rename the 6 other stale `_UPDATED`-suffixed files (content unchanged); update inbound references in `docs/README.md`, `AGENTS.md`, `docs/vision/README.md`, `docs/reference/README.md` as applicable | Phase B, Phase 4 | Low |
| T005 | Fix broken `DATA_MODULE.md` reference in `docs/agents/AGENTS_UPDATED.md` (sequence after T004's rename of `DATA_MODULE_UPDATED.md`) | Phase B | Trivial |
| T006 | Trim `docs/planning/CURRENT_STATUS.md` from 1,172 lines to §1/§2/§7/§13 plus active-only §6, replacing §5/§8/§9/§10 with one-line links to their canonical owners; §3/§4/§11 historical narratives removed only after confirming their content already exists at the target owner doc; §12's fate is a maintainer call (keep as lightweight sprint index, or move to `docs/planning/README.md`) | Phase 4c, Phase B | Medium — see §3 Decisions |
| T007 | Add one row for `docs/historical/` to `docs/README.md`'s folder-layout table (once the audit doc has landed on `main`, T007 also needs a short `docs/historical/README.md` per audit Phase C — currently optional at 1 file, required once a 2nd historical doc exists) | Phase C | Trivial |
| T008 | Trim `.cursor/rules/project-architecture.mdc` to a short pointer at `AGENTS.md` (Architecture Rules / Before Modifying Code / Quality Commands) plus only genuinely Cursor-specific content (glob scoping, `alwaysApply` rationale) | Phase D | Low-medium — verify with Cursor's rule engine before replacing, not just a read-through |
| T009 | Document (policy only, no file migration) the sprint-doc archival rule and the "1 sprint = 1 document" template (`Goal → Scope → Decisions → Tasks → Progress → Outcome → Follow-ups`) in `docs/planning/README.md`; this sprint's own doc is written in that template as a live example | Phase E | Trivial (policy text only) |
| T010 | Validation pass — re-run the 4 checks from audit Phase F against a fresh-context read after T001–T009 land | Phase F | Trivial |

**Already done, outside this sprint** (executed directly in this chat session on 2026-09-03, ahead of/broader than the audit's cautious Phase A recommendation, per explicit maintainer authorization):
- Removed the stale `ml-ai-workflow-strategy-b92927` worktree and its `sprint/momentum-and-regime-catalog` branch (confirmed clean + squash-merged via PR #408/#409).
- Deleted the 5 orphaned `worktree-agent-*` branches.
- Bulk-deleted **164 local branches** and **51 remote (`origin/*`) branches** beyond the audit's 6 confirmed-safe candidates, per explicit maintainer confirmation that `main` is current and nothing outstanding needs to land from them — this intentionally supersedes the audit's more conservative "defer bulk branch deletion, verify per-branch via `gh pr list`" recommendation (Phase A, row 4).
- One branch, `origin/sprint/btc-futures-dry-run-execution`, is GitHub branch-protected and could not be deleted — left as-is, not blocking.
- `claude/repo-workflow-docs-audit-dfbfe3` (this audit's own branch) was deliberately left alone, local and remote, because another live session was still using its worktree at cleanup time.

**Out of scope** (deferred to a separate, later sprint — see §7 Follow-ups):
- `docs/reference/` restructuring into `system/`/`workflows/`/`modules/` (Phase 6a / 10a) — needs a full content audit of 12 files first.
- Vision file current-vs-future reclassification (Phase 6b / 10a) — needs full reads of 3 files at 1,100–2,580 lines each.
- Maintainer decision on `ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md` and `WORKFLOWS_AI_ADR_UPDATED.md` homes (Phase 6b).
- Retroactive merge of the 31 existing `SPRINT_XXX.md` + `SXXX_WAVE0_DECISIONS.md` pairs (Phase E explicitly says do not do this — template applies to new sprints only).
- Retroactive migration of any of the 97 existing sprint docs into a `docs/historical/sprints/` archival tier (Phase E — rule is defined here, applied going forward only).

## 3. Decisions (Wave 0)

Binding decisions for this sprint, to be confirmed with the maintainer before task branches open:

- **D-S053-01 — Merge order.** The audit doc (`docs/historical/REPO_WORKFLOW_DOCS_AUDIT.md`) must land on `main` before or as T007, since T007 depends on the file existing at that path.
- **D-S053-02 — T006 (`CURRENT_STATUS.md` trim) is content-preservation-gated.** No section may be deleted until its content is confirmed already present at its canonical owner (`SPRINT_XXX.md` files, `PROBLEM_REGISTRY.md`, `docs/adr/README.md`, `TECHNICAL_DEBT.md`, `ROADMAP.md`) or has been moved there first. This is the one task in this sprint with real content-loss risk if done mechanically.
- **D-S053-03 — §12 of `CURRENT_STATUS.md` (compact sprint-index table).** Maintainer to decide at task time: keep in place as a lightweight index, or relocate to `docs/planning/README.md`. Not pre-decided here.
- **D-S053-04 — T008 (`.cursor/rules/project-architecture.mdc` trim) needs a Cursor-side check**, not just a text diff — confirm the trimmed pointer file still gives Cursor's rule engine what it needs (Cursor rules are meant to be self-contained), since Claude Code does not read `.cursor/rules/*`.
- **D-S053-05 — No branch/worktree deletion tasks remain in this sprint.** That work is already complete (see §2, "Already done, outside this sprint"); this sprint is docs/config only.

## 4. Tasks

| ID | Task | Depends on | Status |
|---|---|---|---|
| T001 | `.gitignore`: add `.claude/worktrees/`, `.codex/worktrees/` | — | TODO |
| T002 | Fix ADR-0020 status row in `docs/adr/README.md` | — | TODO |
| T003 | Rename `AGENTS_MULTITIMEFRAME_MARKET_MODEL_UPDATED (1).md`, fix `AGENTS.md:62` | — | TODO |
| T004 | Rename remaining 6 `_UPDATED` files, fix inbound refs | — | TODO |
| T005 | Fix `DATA_MODULE.md` broken reference | T004 | TODO |
| T006 | Trim `CURRENT_STATUS.md` (content-preservation-gated per D-S053-02) | — | TODO |
| T007 | Add `docs/historical/` row to `docs/README.md` | Audit doc merged to `main` | TODO |
| T008 | Trim `.cursor/rules/project-architecture.mdc` (Cursor-verified per D-S053-04) | — | TODO |
| T009 | Document sprint archival rule + 1-sprint-1-doc template in `docs/planning/README.md` | — | TODO |
| T010 | Phase F validation pass (4 fresh-context lookup checks) | T001–T009 | TODO |

## 5. Progress

Not started — sprint is PLANNED, pending maintainer approval to open.

## 6. Outcome

TBD.

## 7. Follow-ups (explicitly not this sprint)

- **Phase 10a — `docs/reference/` restructuring** (`system/` / `workflows/` / `modules/`): needs a full content audit of the 12 current files before any file is moved. Separate sprint.
- **Phase 6b — Vision file reclassification**: full reads of `ARCHITECTURE_FOUNDATIONS_UPDATED.md`, `ARCHITECTURE_TECHNICAL_UPDATED.md`, `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE_UPDATED.md` to mark current-vs-future sections. Separate sprint.
- **Sprint-doc backlog**: applying the archival rule defined in T009 to the existing 97 sprint docs, and any retroactive `SPRINT_XXX.md`/`SXXX_WAVE0_DECISIONS.md` merges — both explicitly deferred by the audit (Phase E) to per-file reviewed follow-ups, not a bulk pass.
