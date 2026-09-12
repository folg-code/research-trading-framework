# Repository Workflow & Documentation Audit

**Status:** Audit complete, no repository changes applied. Recommendations only.
**Scope:** Git/worktree state, agent configuration, and documentation architecture as of `main@8e68acc` (2026-09-03).
**Non-goals:** This is not a rewrite. No files were moved, renamed, deleted, or substantially edited to produce this report — see [Safety constraints honored](#safety-constraints-honored).

## Executive summary

This repository is **already well-governed** relative to its size (~40k LOC, 52+ completed sprints). It has a working documentation taxonomy (`vision/` vs `reference/` vs `planning/` vs `adr/`), a docs index (`docs/README.md`), an ADR index that tracks amendments and declines, and a root `AGENTS.md` with an explicit required-reading order. The findings below are refinements to an already-functioning system, not a "no structure exists" situation:

| # | Finding | Impact |
|---|---|---|
| 1 | `.claude/worktrees/` is excluded from search only via local (uncommitted) `.git/info/exclude` | High |
| 2 | 97 sprint docs live flat with no archival tier | High |
| 3 | `.cursor/rules/project-architecture.mdc` duplicates `AGENTS.md` near-verbatim | Medium |
| 4 | 7 files carry a stale, unnecessary `_UPDATED` suffix (one with a `(1)` download-collision artifact) | Medium |
| 5 | `docs/adr/README.md` has a stale status for ADR-0020 | Low (data-integrity, not workflow) |
| 6 | One broken cross-reference (`DATA_MODULE.md` doesn't exist) | Low |
| 7 | One stale worktree + 5 orphaned branches from past agent sessions | Low (housekeeping) |
| 8 | 220 total branches, unclear which are safe to prune under a squash-merge workflow | Low |
| 9 | `docs/reference/` is flat and mixes system/workflow/module/operational content at one depth | Medium (navigation) |
| 10 | 3 of 7 `docs/vision/` files mix already-built content with genuinely future content, unflagged | Medium (trust — "is it built?" answered wrong) |
| 11 | ≥31 sprints carry two overlapping documents (`SPRINT_XXX.md` + `SXXX_WAVE0_DECISIONS.md`) with confirmed duplicated content, not just duplicated naming | Medium |
| 12 | `docs/planning/CURRENT_STATUS.md` is 1,172 lines and mixes current state, full sprint history back to Sprint 006, and independent copies of the ADR index and problem registry — directly contradicting its own §13 rule ("keep it concise") | High |

Findings 9–11 were added after a follow-up review requesting a more detailed target model for `docs/reference/` (system → workflows → modules → contracts → code), a vision-file reclassification pass, and verification of whether sprint document pairs actually duplicate content before recommending consolidation — see [Phase 6a](#phase-6a--layered-navigation-model-for-docsreference), [Phase 6b](#phase-6b--vision-reclassification-framework), and [Phase E](#phase-e--migration-sprint-doc-archival--consolidation). Finding 12 was added after a second follow-up specifically flagging `CURRENT_STATUS.md` as overloaded — confirmed by direct read, see [Phase 4c](#phase-4c--current_statusmd-audit).

---

## Phase 1 — Repository and Git state audit

### Worktree table

| Path | Branch | Commit | Clean/Dirty | Purpose | Active? | Recommended action |
|---|---|---|---|---|---|---|
| `C:/Users/Folga/research-trading-framework` | `main` | `8e68acc` | clean | Canonical checkout | Yes | None |
| `.claude/worktrees/ml-ai-workflow-strategy-b92927` | `sprint/momentum-and-regime-catalog` | `f92a06a` | clean | Sprint 051 (Phase 15A) integration branch | **No** — content already squash-merged into `main` via PR #408/#409 (`f92a06a` is not an ancestor of `main`, confirming squash-merge rather than fast-forward) | **Remove** worktree + branch once a human confirms no further use is planned |
| `.claude/worktrees/repo-workflow-docs-audit-dfbfe3` | `claude/repo-workflow-docs-audit-dfbfe3` | `8e68acc` | this session | This audit | Yes | Remove after this work is merged/closed |

No detached HEADs were found. `git worktree prune -n` reported nothing prunable — the worktree admin metadata is consistent with the filesystem.

### Worktree location and pollution risk

Both non-canonical worktrees live **inside** the repo tree, under `.claude/worktrees/`. This directory is excluded from `git status`/`git add` only via a **local, uncommitted** `.git/info/exclude` entry:

```
.git/info/exclude:7:.claude/worktrees/	.claude/worktrees
```

This is a repository-local file, not shared via `.gitignore` — every new clone or fresh checkout must re-add this exclusion manually, or `.claude/worktrees/**` will be tracked and will pollute `git status`, and, more importantly, will be walked by any repo-wide `grep`/`glob`/file-search tool that doesn't already know to skip it (broad AI-agent searches, `rg` without `--no-ignore`, editor-wide search). This is the single highest-leverage fix in this audit — see [Phase A](#phase-a--safety-and-git-cleanup).

`.codex/` and `.agents/` also live at the repo root, both fully covered by `.gitignore`:
```
.idea/
.agents/
.codex/
```
Both are currently empty of tracked content and pose no discovery risk today.

### Branches

- 220 total branches (167 local, ~53 `origin/*` remote-tracking refs).
- 68 local branches are literal ancestors of `main` (`git branch --merged main`), i.e. trivially safe to delete.
- **99 are not ancestors of `main` despite the repo's squash-merge workflow** (`AGENTS.md`: "squash merge → delete branch" per PR, but locally the source branch is often kept). This means `--merged`/`--no-merged` is unreliable here — a squash-merged branch's tip commit is never an ancestor of `main` even though its content landed. Concretely: `sprint/momentum-and-regime-catalog` (the stale worktree's branch, confirmed merged via PR #408/#409) shows as **not merged** by this check, yet is fully redundant.
- **5 orphaned `worktree-agent-<hash>` branches** (`worktree-agent-a06c7616a343fa47d`, `-a35c5e0fd0d7cfb47`, `-a3eba6b46daa59ddd`, `-a99f4e2add57ea678`, `-aa69a8826b72e9643`) all point at the **same** commit `b59662b` ("docs: plan Phase 12 (Custom Strategy Authoring) sprint (#362)"), which is a confirmed ancestor of `main`. No corresponding worktree directories exist for any of them. These are clearly leftover branch pointers auto-created by past agent-worktree sessions whose worktrees were later removed without deleting the branch. Safe-to-delete candidates.
- **Recommendation:** do not bulk-delete branches based on `--merged` alone under this squash-merge model. A safe sweep needs per-branch confirmation that its content landed via a merged/closed PR (e.g. cross-referencing `gh pr list --state merged --head <branch>`), which is out of scope for this audit pass.

### `.cursor/` and other agent-adjacent config

- `.cursor/` is gitignored except `.cursor/rules/**` and `.cursor/BUGBOT.md` — this is the correct pattern (share the rules, not local Cursor state) and needs no change.
- No `.claude/settings.json`, custom commands, hooks, or MCP config are tracked in this repo; whatever exists locally under `.claude/` (outside `worktrees/`) is untracked and out of scope for a shared-repo audit.

---

## Phase 2 — Agent configuration audit

### Instruction sources found

| File | Scope | Role |
|---|---|---|
| `AGENTS.md` (root) | Global | Canonical: required reading order, architecture rules, quality commands, sprint git workflow, boundaries |
| `apps/cli/CLAUDE.md` | Module (`apps/cli`) | Module-specific conventions and gotchas only |
| `src/trading_framework/infrastructure/ml/CLAUDE.md` | Module | Same pattern |
| `src/trading_framework/infrastructure/providers/binance/CLAUDE.md` | Module | Same pattern |
| `src/trading_framework/research/predictive/CLAUDE.md` | Module | Same pattern |
| `.cursor/rules/ARCHITECTURE_CONTROL.md` | Global (Cursor) | Genuinely additive — dependency-direction/ownership matrix, PR architecture-review checklist not present elsewhere; `AGENTS.md:87` correctly points to it instead of inlining it |
| `.cursor/rules/documentation.mdc` | Global (Cursor) | Doc-taxonomy detail, low overlap with `AGENTS.md` |
| `.cursor/rules/sprint-git-workflow.mdc` | Global (Cursor) | Git branch-naming detail, low overlap |
| `.cursor/rules/python.mdc` | `.py`-scoped (Cursor) | Terse restatement of some `AGENTS.md` items (naive datetimes, composition over inheritance, dependency additions) — acceptable given it's a different consumption mechanism (Cursor's glob-scoped rule engine vs. Claude's full-file read) |
| `.cursor/rules/project-architecture.mdc` (`alwaysApply: true`) | Global (Cursor) | **Problem** — see below |

### Findings

1. **Nested `CLAUDE.md` files are a good example of the target pattern already in use.** All 4 are short, module-scoped, and do not restate global rules (no repeated quality-command list, no repeated `src`/`user_data` boundary text). No root `CLAUDE.md` exists, and that appears intentional — this repo consistently uses `AGENTS.md` for global agent instructions and reserves `CLAUDE.md` for module-local supplements.

2. **`.cursor/rules/project-architecture.mdc` is the one real duplication risk.** Its ~15 numbered rules substantially restate `AGENTS.md`'s "Architecture Rules," "Before Modifying Code," and "Quality Commands" sections near-verbatim (e.g. the `src`/`user_data` boundary and the "no speculative abstractions" rule appear in both; the exact same 4-command quality-check list appears in both). Because it's `alwaysApply: true` and independently maintained, a future edit to one side (e.g. changing a lint command) can silently drift out of sync with the other — this is the one place where "instructions contradict each other" could actually happen, not just "instructions overlap."

3. **No unnecessary repository-wide exploration or subagent-spawning instructions were found** in any agent-config file — `AGENTS.md`'s required reading order is targeted (5 specific docs + "relevant" reference/ADRs + existing contracts/tests), not "read everything."

4. **No MCP config, hooks, or custom slash-commands are committed** in this repo, so there's nothing tool-specific to reconcile across Claude Code / Codex / Cursor beyond the rules files already discussed.

---

## Phase 3 — Documentation inventory

| Folder | Tracked files | Category | Canonical for |
|---|---|---|---|
| `docs/adr/` | 41 (incl. `README.md` index) | ADR | Why a durable decision was made |
| `docs/vision/` | 7 | Architecture (target/binding) | Assumptions, target design, binding decisions — **may include unbuilt work** |
| `docs/reference/` | 12 + `docs/reference/modules/` 3 | Reference / Architecture (as-built) | What exists in code today, trusted "is it built" source |
| `docs/planning/` | 105 (incl. `docs/planning/sprints/` 97, `docs/planning/retrospectives/` 1) | Sprint / Work State | What's being built now, roadmap, problem/idea/debt registries |
| `docs/agents/` | 2 | Agent Instructions (module-specific, deep) | Market Data and Market-Analysis/multitimeframe agent contracts |
| `docs/onboarding/` | 1 | Agent Instructions (human-facing) | Developer setup guide |
| `docs/README.md` | 1 | Navigation | Single index — "folder READMEs are catalogs only" |
| `AGENTS.md` (root) | 1 | Agent Instructions | Global instruction entry point |
| `README.md` (root) | 1 | Navigation | Human entry point, role-based reading paths, top-level-map tiering (already references ADR-0022 for binding layout rules) |

Two nested doc systems already exist and are healthy:
- `docs/vision/README.md` cross-links overlapping vision files and states precedence rules between them.
- `docs/adr/README.md` tracks not just ADR list but amendment/decline history (e.g. "ADR-0023 amended by ADR-0029," "ADR-0028 declined-then-resumed").

**No `docs/historical/` (or equivalent) category existed before this report** — the closest analog, `docs/planning/retrospectives/`, is sprint-scoped (currently 1 file, for Sprints 002–003 only) rather than repo-architecture-scoped. This report is the first occupant of a new `docs/historical/` folder (see [Phase 6](#phase-6--target-documentation-architecture)).

---

## Phase 4 — Source-of-truth analysis

### Duplicate / contradiction map

| Item | Classification | Detail |
|---|---|---|
| `docs/adr/README.md` lists **ADR-0020 as `PROPOSED`** | **Contradiction** | The ADR file itself, `docs/adr/ADR-0020-model-research-methodology-mvp.md`, states `Status: ACCEPTED (Sprint 017)`. Index is stale relative to the source of truth (the ADR file). |
| `docs/agents/AGENTS_UPDATED.md` references `DATA_MODULE.md` | **Broken reference** | No file named `DATA_MODULE.md` exists; the actual file is `docs/reference/modules/DATA_MODULE_UPDATED.md`. |
| `docs/agents/AGENTS_MULTITIMEFRAME_MARKET_MODEL_UPDATED (1).md` | **Unclear ownership / fragile naming** | Literal `(1)` and a space in the filename — the classic signature of a browser download collision, not an intentional name. However it is **not orphaned clutter**: root `AGENTS.md:62` directly references this exact path as required module-specific reading. It is load-bearing despite its accidental-looking origin; needs a rename + one-line reference fix, not deletion. |
| 6 other `_UPDATED`-suffixed files (`ARCHITECTURE_FOUNDATIONS_UPDATED.md`, `ARCHITECTURE_TECHNICAL_UPDATED.md`, `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE_UPDATED.md`, `WORKFLOWS_AI_ADR_UPDATED.md`, `AGENTS_UPDATED.md`, `PROJECT_MANAGEMENT_UPDATED.md`) | **Historical information (naming only)** | Each is confirmed to be a **renamed original**, not a duplicate pair — no plain-named counterpart exists alongside any of them, and each file's internal H1 heading still reads the plain (non-suffixed) name, confirming a rename-in-place at some point rather than a fork. No content is at risk of drift, but the suffix misleads a new reader/agent into searching for a "more current" version that doesn't exist. |
| `.cursor/rules/project-architecture.mdc` vs `AGENTS.md` | **Dangerous duplication** | See [Phase 2](#phase-2--agent-configuration-audit) finding 2 — two independently maintained copies of the same rule text. |
| Module `CLAUDE.md` files vs `AGENTS.md` | **Harmless (working as intended)** | No overlapping rule text found — good separation. |
| Sprint docs vs `AGENTS.md`/vision | **Harmless (working as intended)** | Sampled sprint docs (SPRINT_049, SPRINT_051) reference architecture rules by pointer ("the architecture boundary test's allow-list — NOT widened") rather than restating them. |
| `docs/vision/ARCHITECTURE_FOUNDATIONS_UPDATED.md` §4.14 vs ADR-0001 | **Unclear ownership (minor)** | §4.14 restates the Modular-Monolith decision as current-state fact without citing ADR-0001. Not a contradiction (both agree), but a traceability gap — a reader has no link from "what" back to "why." `ARCHITECTURE_TECHNICAL_UPDATED.md` cites ADRs only 3 times total across the document. |
| Storage/engine ADRs (ADR-0008, ADR-0014, ADR-0015, ADR-MA-014) | **Needs maintainer judgment, not flagged as contradiction** | All touch storage/engine evolution and are topically adjacent; ADR-MA-014 documents its own supersession scope in-body ("Supersedes: ... Does not supersede: ...") but the ADRs it touches aren't retro-flagged. No explicit conflict found in headers skimmed — a full-text diff was out of scope for this pass. |

### Target ownership model (formalizing what already works)

```
AGENTS.md          → how to work (agents + humans); .cursor/rules/*.mdc become
                      thin pointers into it, not independent restatements
docs/vision/        → target/binding architecture (may describe unbuilt work)
docs/reference/     → as-implemented current architecture (trust for "is it built")
docs/adr/           → why a durable decision was made; immutable history,
                      Accepted → Superseded/Deprecated lifecycle
docs/planning/       → what's being built right now (sprints, roadmap, status,
                      problem/idea/debt registries)
docs/historical/    → (new) completed audits, closed investigations, and
                      superseded-but-worth-keeping context
```

This is not a new model — it is the model the repo's own `docs/README.md` already states ("Two Layers," Vision vs Reference, "Trust for 'is it built?'"). The only addition is naming `docs/historical/` as the explicit fifth tier for content that is neither current-state, current-decision, nor current-work.

### Phase 4c — `CURRENT_STATUS.md` audit

A follow-up review flagged `docs/planning/CURRENT_STATUS.md` directly: "it mixes what's current with what's been done, with ideas, etc." A full read confirms this precisely — the file is **1,172 lines** and its own closing rule (§13, "Status Update Rules") says "Keep it concise enough to understand project state quickly," which the file itself no longer satisfies.

**Section-by-section audit:**

| Section | What it actually contains | Should be in `CURRENT_STATUS.md`? |
|---|---|---|
| §1 Purpose | States the file is "a status summary... not the operational task board" | Yes — keep |
| §2 Status Metadata | Dense current-phase/milestone/branch snapshot (lines 26–128) — genuinely current-state | Yes — this is the file's real job, but the prose is one giant unbroken paragraph per field and could be tightened |
| §2.1 Current Phase 8A Update | A historical narrative (Sprints 019–024) framed as "current" | **No** — historical; belongs in the relevant sprint docs (already there) or nowhere new (redundant) |
| §3 Current Objective | Despite the name, a **chronological history of Sprints 011–044** with delivered-flow diagrams, PR numbers, ADR citations — 237 lines | **No** — this is the single largest offender. It is not "current" by any definition; it duplicates what each `SPRINT_XXX.md` already states in full, and duplicates §4 |
| §4 Completed Capabilities | Another historical listing, by Phase, overlapping §3 for several of the same sprints (e.g. Sprint 002, 003, 011–016 appear in both) | **No** — pick one owner: either `docs/reference/MODULE_MAP.md` (what's built, organized by module) or leave it solely to sprint docs; do not keep two independent historical narratives in the same file |
| §5 Documentation Baseline | A static hand-copy of `docs/README.md`'s folder-layout tree | **No** — link to `docs/README.md` instead of re-typing its content; a second copy is exactly the "dangerous duplication" pattern already flagged for `.cursor/rules/project-architecture.mdc` |
| §6 Work in Progress | Starts with 2 genuinely active items (Sprint 051, 049 pending integration — **this is current**), then continues into **~20 full "Closed" sprint write-ups going back to Sprint 006**, each restating Plan/Wave 0/ADR/Tasks/PRs/Scope already in that sprint's own `SPRINT_XXX.md` | **Partially** — keep only the active/pending-merge items at the top; the historical "Closed" entries are a duplicate archive that has no size limit and grows by one full entry per sprint forever |
| §7 Blocked Work | Short, genuinely current | Yes — keep |
| §8 Open Critical Problems | A partial copy of `docs/planning/PROBLEM_REGISTRY.md`'s content, with its own prioritized list | **No** — link to `PROBLEM_REGISTRY.md`, don't restate its rows; two independently-maintained problem lists is the same drift risk as the ADR case below |
| §9 Open Architectural Decisions | A **full, independent copy of the entire ADR status index**, all the way back to ADR-0001 | **No — confirmed dangerous duplication, not hypothetical.** This table lists `ADR-0020 ... ACCEPTED (Sprint 017)` correctly, while `docs/adr/README.md` (the doc that's supposed to be the canonical ADR index, per [Phase 4](#phase-4--source-of-truth-analysis)) has the **same ADR marked `PROPOSED`** — i.e. this repo currently maintains two independent ADR status lists and they have already drifted apart on at least one entry. This is the single clearest piece of evidence in this whole audit for why `docs/adr/README.md` must stay the *only* ADR index, and `CURRENT_STATUS.md` must link to it, not copy it. |
| §10 Known Risks | Overlaps `docs/planning/TECHNICAL_DEBT.md` | **No** — link, don't restate |
| §11 Next Planned Capability | A mini-roadmap: a chronological log of "Sprint NN CLOSED / COMPLETED on main" going back many sprints, functionally a third copy of sprint-completion history (after §3 and §6) | **No** — this belongs in `ROADMAP.md`, and appears to already exist there in some form (not fully verified this pass) |
| §12 Sprint Progress | A compact one-row-per-sprint table (all 52 sprints, goal/status/progress) | **Maybe** — this is the *least* bloated of the historical sections (one line per sprint, not a full write-up) and could reasonably stay as a lightweight index, or move to `docs/planning/README.md`/`ROADMAP.md` as a sprint index; a maintainer call, not resolved here |
| §13 Status Update Rules | The file's own maintenance rule, self-contradicted by everything above | Yes — keep, and it should actually describe the *narrower* file once trimmed |

**Root cause:** the file has no enforced boundary against accretion — every sprint closure appends a new "Closed" entry (§6) rather than replacing/superseding the previous state, so the file has grown roughly linearly with the number of sprints (52 sprints → ~20 duplicated closure write-ups, plus three separate historical narratives of the same sprints in §3/§6/§11, plus two fully independent copies of the ADR index and problem registry). This is the same accretion pattern already identified for `docs/planning/sprints/` in [Phase E](#phase-e--migration-sprint-doc-archival--consolidation), but inside the one file every agent is told to read *first* (`AGENTS.md`'s required reading order, step 2) — making it the highest-cost instance of the pattern in the repo.

| Finding | Impact | Why |
|---|---|---|
| `.claude/worktrees/` excluded only via local `.git/info/exclude`, not committed `.gitignore` | **High** | Any agent or tool whose search doesn't already know to skip this path will walk 1–2 full extra copies of the ~40k-LOC source tree per active worktree. This is the single largest avoidable context cost identified. |
| 97 flat sprint docs, no archival tier | **High** | An agent asked to "check sprint history" or "how did we handle X before" has no signal about which of 97 files are still load-bearing vs. long-closed. Later sprint docs are also growing (SPRINT_001.md: 753 lines; SPRINT_049.md: 695 lines; SPRINT_051.md: 601 lines vs. SPRINT_017.md: 297 lines), compounding the cost of reading the wrong one in full. |
| `.cursor/rules/project-architecture.mdc` duplicating `AGENTS.md` | **Medium** | Not a direct per-task cost (Claude Code doesn't read Cursor rules), but a correctness/consistency cost: a Cursor-driven change and a Claude-driven change can be governed by silently-diverging rule text. |
| Stale `_UPDATED` filenames | **Medium** | Costs one extra lookup per occurrence when an agent or human searches for what looks like a superseded name pattern and has to confirm there's no newer file. |
| 220 branches, unreliable `--merged` signal under squash-merge workflow | **Low** | Branches aren't read unless explicitly listed, so this isn't a per-task token cost, but a `git branch -a` during repo discovery returns a wide, low-signal blob any agent doing Git-state discovery will trip over once. |
| Only 1 retrospective for 52 sprints | **Low (missed opportunity, not a cost)** | Not a context tax today, but a missed chance to compress "why we did things this way across many sprints" into short reusable documents instead of requiring ADR/sprint-doc archaeology each time the question comes up. |

Correctness and architectural understanding remain more important than raw token count — none of the above findings propose removing content, only relocating/excluding/renaming it so the right content is found faster.

---

## Phase 6 — Target documentation architecture

The existing structure already answers most of the target questions well. Only one addition is proposed:

```text
AGENTS.md

docs/
├── README.md                 (existing — single index, no change needed)
├── onboarding/                (existing)
│   └── DEVELOPER_GUIDE.md
├── vision/                    (existing — target/binding architecture)
├── reference/                 (existing — as-implemented architecture)
│   └── modules/
├── planning/                  (existing — roadmap, status, sprints)
│   ├── sprints/
│   └── retrospectives/
├── adr/                       (existing — decision history)
├── agents/                    (existing — module-specific agent contracts)
└── historical/                (NEW — completed audits, closed investigations)
```

| Question | Answered by |
|---|---|
| Where's the current architecture? | `docs/reference/` |
| Where's a domain contract? | `docs/reference/modules/` or `docs/vision/` (per `docs/README.md`'s existing "Reference Trio" table) |
| Where's the reason behind a decision? | `docs/adr/` |
| Where's the current sprint? | `docs/planning/CURRENT_STATUS.md` → `docs/planning/sprints/` |
| Where are agent/dev rules? | `AGENTS.md` (global), `docs/agents/` (module-deep), nested `CLAUDE.md` (module-local) |
| Which document wins if two disagree? | `docs/adr/` for *why*; `docs/reference/` for *current state*; `docs/vision/` only binds *future* work — this precedence is already stated in `docs/README.md`'s "Two Layers" table and needs no change |

No wholesale restructuring is proposed — the candidate structure in the task prompt is adapted, not imposed, because this repo's existing structure already satisfies it apart from the missing `historical/` tier.

### Phase 6a — Layered navigation model for `docs/reference/`

A follow-up review of this report added a sharper requirement: `docs/reference/` should read as one descending hierarchy, from system-level orientation down to code, so an agent's lookup path is a strict narrowing rather than a flat list of 12 files it has to guess between:

```text
SYSTEM
  ↓
HIGH-LEVEL MAP        (docs/reference/system/)
  ↓
WORKFLOWS             (docs/reference/workflows/)
  ↓
MODULES               (docs/reference/modules/)
  ↓
CONTRACTS / APIs / TYPES   (module docs' own "Contracts" sections, or dedicated files if a module's contract surface is large)
  ↓
CODE                  (src/, tests/)
```

Today `docs/reference/` is flat (12 files: `ARCHITECTURE_AND_WORKFLOWS.md`, `MODULE_MAP.md`, `RESEARCH_METHODOLOGIES.md`, `DATA_WORKFLOWS.md`, `STRATEGY_AUTHORING.md`, `PREDICTIVE_PROMOTION.md`, `OPERATOR_CLI.md`, `DASHBOARD_APPLICATION.md`, and three AWS/BTC/dry-run operational docs, plus `README.md`), with a separate `modules/` subfolder holding only 3 files. This mixes system-level, workflow-level, and operational-runbook-level content at the same directory depth — an agent scanning `docs/reference/` for "how does strategy execution work" has to read filenames and guess rather than descend a hierarchy. Proposed target layout (adapts the existing files, does not discard them):

```text
docs/reference/
├── README.md
├── system/
│   ├── SYSTEM_OVERVIEW.md        ← new: 1-page map, links down into workflows/ and modules/
│   ├── MODULE_MAP.md             ← existing file, moved as-is
│   ├── DOMAIN_MODEL.md           ← new, or promoted from vision/ once confirmed as-built (see Phase 6b)
│   └── DEPENDENCY_RULES.md       ← existing dependency-direction content, currently split between AGENTS.md, ARCHITECTURE_CONTROL.md and ARCHITECTURE_AND_WORKFLOWS.md; consolidate pointers here, don't fork the content
├── workflows/
│   ├── SIGNAL_RESEARCH.md        ← extracted from RESEARCH_METHODOLOGIES.md
│   ├── STRATEGY_RESEARCH.md      ← extracted from RESEARCH_METHODOLOGIES.md / STRATEGY_AUTHORING.md
│   ├── STRATEGY_EXECUTION.md     ← extracted from OPERATOR_CLI.md / dry-run docs
│   └── MARKET_DATA.md            ← existing DATA_WORKFLOWS.md, renamed/moved
└── modules/
    ├── DATA.md                   ← rename of DATA_MODULE_UPDATED.md (Phase B)
    ├── MARKET_ANALYSIS.md        ← existing MARKET_ANALYSIS_MODULE.md, moved
    ├── SIGNALS.md                ← new or split out of MODEL_AUTHORING.md
    ├── STRATEGY.md                ← new
    └── EXECUTION.md               ← new
```

This is a **larger change than anything else in this report** — it reorganizes 12+ existing files, not just renames 7 — so it is intentionally kept out of Phase A–F's near-term scope and listed separately in [Phase 10a](#phase-10a--reference-restructuring-follow-up-not-scheduled). Before touching a single file, each of the 12 current `docs/reference/` files needs a content audit (which sections are system-level vs workflow-level vs module-level — most existing files already mix these, e.g. `ARCHITECTURE_AND_WORKFLOWS.md`'s name alone suggests it currently spans both the `system/` and `workflows/` tiers proposed above) to decide split points, which this pass did not perform.

**Module view vs. workflow view.** The two are complementary cuts through the same system and should both exist rather than be collapsed into one:

| Module view — *who owns what* | Workflow view — *how data/objects move* |
|---|---|
| Data | Signal Research |
| Market Analysis | Strategy Research |
| Signals | Strategy Execution |
| Strategy | Market Data |
| Execution | |

A module doc answers "what does this package do, what's its contract, who calls it." A workflow doc answers "starting from a Binance tick / a research question, what sequence of modules does it pass through, and what does each hand off." `docs/reference/RESEARCH_METHODOLOGIES.md` and `DATA_WORKFLOWS.md` are already workflow-shaped documents in substance — the proposed `workflows/` folder mostly just gives that existing content an explicit home and finishes the split for `STRATEGY_EXECUTION.md`, which today is scattered across `OPERATOR_CLI.md` and the AWS/dry-run operational docs.

### Phase 6b — Vision reclassification framework

`docs/vision/` should contain only genuinely future/target architecture — content already built belongs in `docs/reference/` instead. Applying the requested four-way classification to the 7 existing vision files (based on the vision `README.md`'s own stated purpose per file, plus spot-checks of each file's framing language — a full line-by-line audit of these files, the largest in the repo at 1,100–2,580 lines each, was out of scope for this pass and is called out below where the classification is not yet certain):

| File | Self-described purpose | Preliminary classification | Basis |
|---|---|---|---|
| `ARCHITECTURE_FOUNDATIONS_UPDATED.md` | "Domain principles, module boundaries, long-term model" | **Partially implemented — needs split** | §4.14 (Modular Monolith) restates a decision already accepted and built per ADR-0001, with zero ADR citations anywhere in the file (see [Phase 4](#phase-4--source-of-truth-analysis)); the rest of the file is explicitly "long-term model." A section-by-section pass is needed to separate the already-built principles (→ `reference/system/`) from the still-aspirational "long-term model" (→ stays in `vision/`). |
| `ARCHITECTURE_TECHNICAL_UPDATED.md` | "Cross-cutting target technical architecture" | **Likely still planned**, needs confirmation | Only 3 ADR citations across 2,459 lines; title itself says "target," suggesting it's meant to stay in `vision/` as-is, but its size means some sections may already be built and stale-labeled "target." Not verified line-by-line. |
| `MARKET_ANALYSIS_WITH_DECISIONS.md` | "Market Analysis decisions D-001–D-036" | **Intentional reference, not duplication — keep, but clarify scope note** | 12 of the 14 `ADR-MA-0xx` files cite this doc's `D-0xx` decision IDs directly (confirmed via grep). This is a deliberate two-tier decision system: `ADR-MA-*` are the formal, ADR-lifecycle-governed architectural decisions; `D-0xx` in this vision file is a finer-grained decision catalog they draw on. This is healthy as designed, but its location in `vision/` (implying "not necessarily built") sits oddly next to `docs/README.md`'s promise that ADRs are the authoritative decision record — worth a one-line clarifying note in `vision/README.md`, not a move. |
| `ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md` | "authoritative on derived data" | **Likely implemented — candidate to move to `reference/`** | The vision folder's own tagline says these docs are "not necessarily what is implemented today," yet this file's index entry calls it "authoritative," which reads as as-built, not target. Strongest single candidate in this folder for promotion to `docs/reference/`, pending confirmation against `MODULE_MAP.md` / tests. |
| `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE_UPDATED.md` | Explicitly labeled "(future)" in the vision index | **Partially implemented — needs split** | Correctly filed as future in the index, but line 1308 states "Multitimeframe support **is implemented** through timeframe-aware analytical requests..." — at least one section describes shipped behavior inside a file the index calls entirely future. Needs a current-vs-future split, not a wholesale move either direction. |
| `WORKFLOWS_AI_ADR_UPDATED.md` | "Workflow, AI usage and ADR process" | **Unclear ownership — process doc, not architecture vision** | This describes *how the team/agents work* (ADR process, AI usage), which is process/workflow documentation, not target system architecture. It arguably belongs closer to `AGENTS.md`/`docs/README.md`'s process layer than to `vision/`'s "target architecture" definition — flagged for a maintainer decision, not reclassified unilaterally here. |
| `README.md` | Vision folder index | **N/A — navigation, not content** | No reclassification needed. |

None of these moves are made in this pass — each requires either a full read (for the three "needs split" files) or a one-line maintainer confirmation (for the two "keep as-is" cases) before any content relocation, per the task's "do not assume the newest/current doc is right without verifying" constraint.

---

## Phase 7 — Target agent workflow

```text
task
  ↓
AGENTS.md (global rules, required reading order)
  ↓
docs/planning/CURRENT_STATUS.md + relevant docs/planning/sprints/SPRINT_XXX.md
  ↓
docs/README.md (navigation index, only if the task's doc area is unfamiliar)
  ↓
relevant docs/reference/* and docs/vision/* (targeted by module, not read wholesale)
  ↓
relevant docs/adr/* (only ADRs touching the module in scope)
  ↓
targeted rg/grep within src/<module>/ and tests/<module>/ — never repo-wide by default
  ↓
implementation
  ↓
uv run ruff check . / ruff format --check . / mypy / pytest
  ↓
update docs/reference/MODULE_MAP.md + docs/reference/DATA_WORKFLOWS.md if paths changed
(already mandated by AGENTS.md — no new rule needed)
  ↓
commit / PR per docs/README.md's sprint-git-workflow
```

This is already close to what `AGENTS.md`'s "Required Reading Order" describes — the explicit rules below make the *exclusions* first-class, which today are implicit:

- **Repository exploration:** default to the module directory named by the task; only widen to repo-wide search if the module-scoped search fails to answer the question.
- **Grep/glob scope:** exclude `.claude/worktrees/`, `.codex/`, `.venv/`, `dist/`, `.uv-cache/`, caches — all already gitignored, but tools invoked with `--no-ignore` or outside Git-aware search must apply the same exclusion explicitly.
- **Worktree exclusion:** never treat a sibling worktree under `.claude/worktrees/**` as part of the canonical source tree for architecture reconstruction or repo-wide search (see [Phase 8](#phase-8--worktree-lifecycle-policy)).
- **Subagent usage:** reserve for genuinely parallel, independent lookups (e.g. auditing 3 unrelated doc areas at once, as done for this report) — not for simple single-file discovery a direct `Read`/`Grep` already answers.
- **Architecture discovery:** consult `docs/reference/MODULE_MAP.md` before reading source to locate the right module; do not reconstruct architecture from source when `docs/reference/` already documents it.
- **Reading ADRs:** read only ADRs that touch the module/decision in scope, found via `docs/adr/README.md`'s index — not all 41.
- **Documentation updates:** update in the same PR as the code change that invalidates them (already `AGENTS.md`'s rule).
- **Test execution:** run the 4 quality commands already listed in `AGENTS.md`; report failures, don't hide them.
- **Task completion / handoff:** leave `docs/planning/CURRENT_STATUS.md` and the active `SPRINT_XXX.md` in a state a fresh agent/session can resume from without re-deriving intent from commit history.

---

## Phase 8 — Worktree lifecycle policy

**Principle (already true in practice, now made explicit):** `.claude/worktrees/**` and `.codex/worktrees/**` (or any equivalent temporary working copy) must never be considered part of the canonical source tree during architecture analysis or repository-wide search, regardless of whether they are currently gitignored correctly.

| Concern | Policy |
|---|---|
| When agents may create worktrees | For any task expected to span multiple sessions or require isolation from the main checkout (matches current practice: this audit itself runs from such a worktree). |
| Naming convention | `<slug>-<short-hash>` (already in use, e.g. `repo-workflow-docs-audit-dfbfe3`) — keep it. |
| Where worktrees live | Currently `.claude/worktrees/` **inside** the repo tree. This works only because tooling is expected to skip it; it is the root cause of Finding 1. No change to location is proposed here (moving worktrees outside the repo tree is a bigger workflow change than this audit's scope) — instead, harden the exclusion (see Phase A). |
| Cleanup after merge/completion | Remove the worktree directory (`git worktree remove`) and, once confirmed merged, its branch, after the corresponding PR lands — not before. |
| Stale-worktree detection | A worktree is stale when its branch tip is either an ancestor of `main` or confirmed merged via a closed/merged PR referencing that branch, **and** the worktree is clean (no uncommitted changes). Both conditions were checked for `ml-ai-workflow-strategy-b92927` in this audit before recommending removal. |
| Protection against deleting uncommitted work | Never remove a worktree without first running `git -C <worktree> status --short` and confirming it is clean; never delete a branch without confirming `git merge-base --is-ancestor` or PR-merge evidence, exactly as done in this report. |
| How agents should treat sibling worktrees during repo search | As out-of-scope for code search/architecture reconstruction; inspect a sibling worktree's Git state directly (`git -C <path> status/log`) only when the task is specifically about worktree/branch hygiene, as this one is. |

---

## Phase 9 — ADR lifecycle policy

Current state: all 40 ADR files use `Status: ACCEPTED` (some qualified, e.g. "ACCEPTED (Sprint 049)," "ACCEPTED — resumed for Sprint 048," "ACCEPTED (§7 amended by ADR-0029)"). None are marked `Superseded`/`Deprecated`/`Rejected`, and the index already tracks amendment/decline history in prose (e.g. "ADR-0023 amended by ADR-0029"; "ADR-0028 declined-then-resumed") even though no ADR's `Status` field itself says `Superseded`.

**Policy (confirms and extends the existing implicit practice):**
- Statuses: `Proposed → Accepted → {Superseded | Deprecated}`, or `Proposed → Rejected`.
- A newer decision on the same topic **supersedes** the older ADR by updating the older ADR's own `Status` field (e.g. `Superseded by ADR-00xx`) — it does not edit the older ADR's historical Context/Consequences text. History stays immutable; only the `Status` line changes.
- `docs/architecture` / `docs/reference` describes **current state**; ADRs preserve **decision history**. When both exist for the same topic, `docs/reference/` wins for "is it built," the ADR wins for "why."
- The one hygiene gap found (ADR-0020 index/file status mismatch) should be fixed as a one-line factual correction in `docs/adr/README.md`, not treated as evidence the model itself is broken — the model is sound; the index just drifted once.

---

## Phase 10 — Ordered reconstruction plan

All items below are **proposed, not executed**. Each is a separate, small, reviewable change.

### Phase A — Safety and Git cleanup

| Problem | Evidence | Proposed change | Benefit | Risk | Migration steps |
|---|---|---|---|---|---|
| `.claude/worktrees/` only excluded locally | `.git/info/exclude:7`, not in committed `.gitignore` | Add `.claude/worktrees/` (and `.codex/worktrees/` preemptively) to the committed `.gitignore` | Every clone/session gets the exclusion automatically; closes the highest-impact context-cost finding | Very low — purely additive ignore rule | Add the two lines, confirm `git status` unaffected, commit |
| Stale worktree | `ml-ai-workflow-strategy-b92927`, confirmed clean + squash-merged via PR #408/#409 | `git worktree remove` then `git branch -d sprint/momentum-and-regime-catalog` | Removes a full stale checkout from disk and repo discovery | Low — content is confirmed landed on `main`; still confirm with the user before deleting, since they may want the branch kept a while longer | Re-run `git status --short` and `git merge-base --is-ancestor` immediately before deleting to catch any new work |
| 5 orphaned `worktree-agent-*` branches | All 5 identical, pointing at merged commit `b59662b`, no worktree dirs | `git branch -d` each | Removes dead pointers from `git branch -a` output | Very low — verified identical and merged | None beyond the verification already done |
| 220 branches, unclear staleness under squash-merge | `--merged`/`--no-merged` unreliable per findings above | Do **not** bulk-delete; instead, script a check against `gh pr list --state merged --head <branch>` per branch, review with the user before any deletion | Prevents accidental loss of an unmerged branch that looks stale | Medium if done carelessly — explicitly deferred, not part of this pass | Separate follow-up task, not bundled with A |

### Phase B — Documentation ownership

| Problem | Evidence | Proposed change | Benefit | Risk | Migration steps |
|---|---|---|---|---|---|
| ADR-0020 status mismatch | Index says `PROPOSED`, file says `ACCEPTED (Sprint 017)` | Update `docs/adr/README.md`'s row for ADR-0020 to `ACCEPTED (Sprint 017)` | Removes a factual contradiction | Trivial | One-line edit |
| Broken `DATA_MODULE.md` reference | `docs/agents/AGENTS_UPDATED.md` | Update the reference to `docs/reference/modules/DATA_MODULE_UPDATED.md` (or fix after Phase B's rename, to the final plain name) | Removes a dead link | Trivial | One-line edit, sequence after the rename below |
| `(1)`-suffixed, space-containing filename is load-bearing | `docs/agents/AGENTS_MULTITIMEFRAME_MARKET_MODEL_UPDATED (1).md`, referenced from `AGENTS.md:62` | Rename to `docs/agents/AGENTS_MULTITIMEFRAME_MARKET_MODEL.md`; update the one reference in `AGENTS.md` | Removes a fragile path (space + parens break some tooling/URLs) | Low — single inbound reference, already located | `git mv`, then update `AGENTS.md:62`, verify no other references via repo-wide grep for the old filename |
| 6 other stale `_UPDATED` suffixes | See Phase 4 table | Rename each to drop `_UPDATED` (content unchanged); update the small number of inbound references (`docs/README.md`, `AGENTS.md`, `docs/vision/README.md`, `docs/reference/README.md` as applicable) | Removes the "is there a newer version?" false signal | Low — rename only, verified no content fork exists for any of the 7 | `git mv` each, grep repo-wide for old filename, update references, verify `docs/README.md`/`docs/vision/README.md` still resolve |
| `CURRENT_STATUS.md` mixes current state, full sprint history, and independent copies of the ADR/problem registries (1,172 lines) | See [Phase 4c](#phase-4c--current_statusmd-audit) — confirmed two drifted ADR-0020 status copies, three overlapping historical narratives (§3/§6/§11), duplicated `PROBLEM_REGISTRY.md` and `TECHNICAL_DEBT.md` content | Trim `CURRENT_STATUS.md` to §1 Purpose, §2 Status Metadata (tightened), §7 Blocked Work, the *active-only* portion of §6 Work in Progress, and §13 Rules; replace §5 (doc tree), §8 (problems), §9 (ADR index) with one-line links to their canonical owners (`docs/README.md`, `PROBLEM_REGISTRY.md`, `docs/adr/README.md`); move or retire §3, §4, §11's historical narratives (their content already exists in each sprint's own doc); leave §12's compact sprint-index table for a maintainer to decide (keep as a lightweight index, or move to `docs/planning/README.md`) | Restores the file to what its own §13 rule already promises ("concise... understand project state quickly"); removes the ADR-index drift risk at its source, since agents currently reading `CURRENT_STATUS.md` first (per `AGENTS.md` reading order step 2) get a *different* ADR-0020 status than agents who go straight to `docs/adr/README.md` | Medium — this is a real content restructuring, not a rename; every removed section's information must be confirmed to already exist at its target owner (or be moved there) before deletion, so it needs a careful pass, not a bulk cut | 1) Confirm each of §3/§4/§8/§9/§10/§11's content is fully represented in its target owner doc (`SPRINT_XXX.md` files, `PROBLEM_REGISTRY.md`, `docs/adr/README.md`, `TECHNICAL_DEBT.md`, `ROADMAP.md`) — fix any gap found there first. 2) Replace each section with a one-line pointer. 3) Decide §12's fate with the maintainer. 4) Re-verify §2's "Status Metadata" block still stands alone as a correct current-state snapshot after the surrounding narrative sections are gone. |

### Phase C — Navigation and context architecture

| Problem | Evidence | Proposed change | Benefit | Risk | Migration steps |
|---|---|---|---|---|---|
| No `docs/historical/` entry point | New folder created by this report | Add one row to `docs/README.md`'s folder-layout table pointing at `docs/historical/`; add a short `docs/historical/README.md` once it holds more than this one file | Keeps `docs/README.md` as the single accurate index | Trivial | One row + one small README, once a second historical doc exists |

### Phase D — Agent rules

| Problem | Evidence | Proposed change | Benefit | Risk | Migration steps |
|---|---|---|---|---|---|
| `.cursor/rules/project-architecture.mdc` duplicates `AGENTS.md` | Near-verbatim rule text in both, independently maintained | Trim `project-architecture.mdc` to a short pointer ("see root `AGENTS.md` — Architecture Rules / Before Modifying Code / Quality Commands") plus only genuinely Cursor-specific content (glob scoping, `alwaysApply` rationale) | Removes the one real drift risk found in this audit | Low-medium — must confirm Cursor's rule engine still gets what it needs from a pointer file (Cursor rules are meant to be self-contained context, so this needs a quick verification pass with Cursor itself, not just a read-through) | Draft trimmed version, diff against current behavior, confirm with the user/Cursor before replacing |

### Phase E — Migration (sprint doc archival + consolidation)

| Problem | Evidence | Proposed change | Benefit | Risk | Migration steps |
|---|---|---|---|---|---|
| 97 flat sprint docs, no archival tier, growing | Sampled sprint docs 297–753 lines each, no folder distinguishes closed from active | Document (not yet execute) a rule in `docs/planning/README.md`: sprint docs older than N sprints **and** fully superseded by a later sprint on the same topic move to `docs/historical/sprints/` | Gives future agents a size/recency signal without reading all 97 | Medium — moving any of the 97 existing files needs per-file confirmation of "still referenced?" before touching it; explicitly **not done in this pass** | Do not migrate existing files yet; define the rule, apply it going forward, revisit the backlog as a separate reviewed task once the rule has been used a few times |
| Two documents per sprint (`SPRINT_XXX.md` + `SXXX_WAVE0_DECISIONS.md`) | **Confirmed real overlap, not just a naming pattern**: at least 31 sprints have this pair (S006–S018, S026–S032, S036–S049, S051–S052). Direct comparison of `SPRINT_051.md` §2 "In scope" against `S051_WAVE0_DECISIONS.md`'s `D-S051-03` shows the same six components (RSI, MACD, stochastic, relative-volatility, autocorrelation, return-distribution) listed twice — once as a scope checklist, once with full parameters and rationale. `SPRINT_051.md` §6 even has a subsection literally titled "Wave 0 — Decisions" that summarizes what the companion file states in full. This is genuine content duplication between two co-maintained files, not two documents serving cleanly separate purposes. | Adopt **1 sprint = 1 document** going forward, using a single lifecycle template that keeps the Wave-0 decision content as sections within the sprint doc rather than a separate file: `Goal → Scope → Decisions → Tasks → Progress → Outcome → Follow-ups`. The `Decisions` section absorbs what `SXXX_WAVE0_DECISIONS.md` currently holds (including its per-decision rationale — don't compress that away, it's the part with the most reuse value). | One canonical file per sprint; no risk of a scope checklist and a decisions doc drifting apart mid-sprint (they're now the same headings in the same file); a future agent reading "what did Sprint 051 decide" doesn't need to open two files. | Low for **future** sprints (template-only change). **Do not retroactively merge the 31 existing pairs** — each merge risks silently dropping content if done mechanically, and several pairs (`S037`/`S044` also have a third `_GATE.md` file, and `S049`/`S051` each have an additional one-off artifact — `S049_AVAILABILITY_FINDING.md`, `S051_BTC_DATA_INVENTORY.md` — that are NOT part of this duplication pattern and must not be merged away) | 1) Confirm the template with the user/team before the next sprint opens. 2) Apply only to newly-opened sprints. 3) Leave all 97 existing files untouched — a retroactive merge, if ever wanted, is a separate reviewed task per sprint, not a bulk rewrite. |

### Phase F — Validation

Once Phases A–E land (in future, separate sessions), validate with representative tasks run by a fresh agent session with no prior context:
1. "What's the current architecture for market data ingestion?" — should resolve via `docs/reference/MODULE_MAP.md` → `docs/reference/DATA_WORKFLOWS.md` in 1–2 lookups, not a `src/` scan.
2. "Why does `apps/*` not import research/execution engines directly?" — should resolve to ADR-0022 directly from `AGENTS.md:30`.
3. "What's the current sprint?" — should resolve via `docs/planning/CURRENT_STATUS.md` alone.
4. A repo-wide `rg` run from a fresh worktree should not surface matches from any other sibling worktree once Phase A's `.gitignore` change lands.

### Phase 10a — Reference restructuring follow-up (not scheduled in A–F)

The `docs/reference/` → `system/` / `workflows/` / `modules/` reorganization from [Phase 6a](#phase-6a--layered-navigation-model-for-docsreference) and the vision reclassification from [Phase 6b](#phase-6b--vision-reclassification-framework) are both larger than a single reviewable change and depend on content audits this pass didn't do (full reads of 12 reference files and 3 large vision files). They are deliberately **not** folded into Phase A–F. Recommended sequencing for a later, separate effort:

1. Full read of the 3 vision files flagged "needs split" (`ARCHITECTURE_FOUNDATIONS_UPDATED.md`, `ARCHITECTURE_TECHNICAL_UPDATED.md`, `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE_UPDATED.md`) to mark each section current-vs-future; move confirmed-current sections to `docs/reference/system/`, leave the rest in `vision/`.
2. Confirm with the maintainer whether `ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md` should move to `reference/` wholesale (it self-describes as "authoritative," which is a reference-tier claim already).
3. Decide `WORKFLOWS_AI_ADR_UPDATED.md`'s home (vision, or fold into `docs/README.md`/`AGENTS.md`'s process material) — a maintainer call, not inferred here.
4. Only after 1–3 settle the *content*, split `docs/reference/`'s 12 files into the proposed `system/`/`workflows/`/`modules/` layout — splitting file organization before content ownership is settled would just move the ambiguity around rather than resolve it.
5. Validate per [Phase F](#phase-f--validation) after each step, not only at the end.

---

## File action list (Phase 10 deliverable #12)

**No action taken in this session.** All items below are recommendations for separate, reviewed follow-up changes.

| Action | File(s) | Notes |
|---|---|---|
| Add to `.gitignore` | `.gitignore` (root) | Add `.claude/worktrees/` and `.codex/worktrees/` |
| Remove worktree + branch | `.claude/worktrees/ml-ai-workflow-strategy-b92927`, branch `sprint/momentum-and-regime-catalog` | Confirmed clean + squash-merged; confirm with user first |
| Delete branches | `worktree-agent-a06c7616a343fa47d`, `-a35c5e0fd0d7cfb47`, `-a3eba6b46daa59ddd`, `-a99f4e2add57ea678`, `-aa69a8826b72e9643` | Confirmed identical + merged |
| Fix content | `docs/adr/README.md` (ADR-0020 status row) | One-line factual correction |
| Fix reference | `docs/agents/AGENTS_UPDATED.md` (`DATA_MODULE.md` link) | Sequence after the rename below |
| Rename + update reference | `docs/agents/AGENTS_MULTITIMEFRAME_MARKET_MODEL_UPDATED (1).md` → `AGENTS_MULTITIMEFRAME_MARKET_MODEL.md`; update `AGENTS.md:62` | Highest-fragility filename found |
| Rename (content unchanged) | `docs/vision/ARCHITECTURE_FOUNDATIONS_UPDATED.md`, `docs/vision/ARCHITECTURE_TECHNICAL_UPDATED.md`, `docs/vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE_UPDATED.md`, `docs/vision/WORKFLOWS_AI_ADR_UPDATED.md`, `docs/agents/AGENTS_UPDATED.md`, `docs/planning/PROJECT_MANAGEMENT_UPDATED.md`, `docs/reference/modules/DATA_MODULE_UPDATED.md` | Drop `_UPDATED` suffix; update inbound references in `docs/README.md`, `AGENTS.md`, `docs/vision/README.md` |
| Trim | `.cursor/rules/project-architecture.mdc` | Replace duplicated rule text with a pointer to `AGENTS.md`; verify with Cursor before replacing |
| Trim (separate future effort — content restructuring, not a rename) | `docs/planning/CURRENT_STATUS.md` | See [Phase 4c](#phase-4c--current_statusmd-audit) — confirm content is preserved at its canonical owner before deleting each section; reduces file from 1,172 lines to roughly §1/§2/§7/§13 plus active-only §6 |
| Add navigation row | `docs/README.md` | One row for `docs/historical/` |
| Document policy (no file migration yet) | `docs/planning/README.md` | Add the sprint-doc archival rule and the new 1-sprint-1-doc template from Phase E |
| Adopt template (new sprints only) | `docs/planning/sprints/` | `Goal / Scope / Decisions / Tasks / Progress / Outcome / Follow-ups` in one file; retire the `SXXX_WAVE0_DECISIONS.md` companion pattern going forward — 97 existing files untouched |
| Content audit, then split (separate future effort) | `docs/reference/*` (12 files) → `docs/reference/system/`, `workflows/`, `modules/` | See [Phase 10a](#phase-10a--reference-restructuring-follow-up-not-scheduled) — larger than this pass's scope, needs full reads first |
| Section-level current/future split (separate future effort) | `docs/vision/ARCHITECTURE_FOUNDATIONS_UPDATED.md`, `ARCHITECTURE_TECHNICAL_UPDATED.md`, `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE_UPDATED.md` | See [Phase 6b](#phase-6b--vision-reclassification-framework) — needs full reads, not inferred from headers |
| Maintainer decision, then move-or-keep (separate future effort) | `docs/vision/ANALYSIS_WORKSPACE_AND_DERIVED_DATA.md` (candidate move to `reference/`), `docs/vision/WORKFLOWS_AI_ADR_UPDATED.md` (candidate move out of `vision/` entirely) | See [Phase 6b](#phase-6b--vision-reclassification-framework) |
| Created this session | `docs/historical/REPO_WORKFLOW_DOCS_AUDIT.md` | This report |

---

## Safety constraints honored

- No files were deleted, moved, renamed, merged, overwritten, or substantially rewritten.
- No Git worktrees, branches, untracked files, or local changes were removed.
- No application code was changed.
- No architectural contracts were changed, even where documentation looked inconsistent (e.g. ADR-0020's status mismatch is reported, not silently fixed).
- No document was assumed authoritative merely for being newest (`_UPDATED`-suffixed files were verified as renamed originals, not assumed to be current drafts superseding a hidden original).
- No duplicate documentation was created for a concept that already has a canonical source — this report itself fills the one genuinely missing category (`historical/`) rather than duplicating `planning/retrospectives/` or `adr/`.
