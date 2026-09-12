# Sprint 054 — T006 Recommendation: where does `WORKFLOWS_AI_ADR.md` belong?

```text
Status:      RECOMMENDATION — awaiting maintainer decision (per D-S054-03)
Task:        Sprint 054, T006
Author:      architect agent
Date:        2026-09-03
Scope:       Recommendation only. No file was moved, edited or rewritten.
Subject:     docs/vision/WORKFLOWS_AI_ADR.md (2,584 lines, read in full)
```

---

## 1. Headline recommendation

**Option (c) — none of the two options in the sprint doc. Split the file
three ways; do not move it wholesale, and do not leave it intact in
`vision/` either.**

Concretely:

| Part | Lines | ~% | Recommended home | Handled by |
|------|-------|-----|------------------|-----------|
| §1–§5 + §8 (workflow architecture, Signal/Strategy Research, Strategy Execution, Final Contract) | 1–1577, 2542–2584 | **~63%** | Stays in the **vision reclassification track** — add it to T001–T003's current/future classification scope, then let **T004** place the confirmed-current parts under `docs/reference/system/` (or `docs/reference/workflows/` once T008 creates it) and leave confirmed-future parts in `vision/` | **T004 track, not T006** |
| §6 (AI Agent Contract) | 1579–2167 | ~23% | Fold into the **`AGENTS.md` process layer** (root `AGENTS.md` + `.cursor/rules/ARCHITECTURE_CONTROL.md`) | T006 follow-up |
| §7.1–7.5, §7.9, §7.10 (ADR process, statuses, template, review rules, ownership) | 2170–2298, 2509–2540 | ~6% | Fold into **`docs/adr/README.md`** | T006 follow-up |
| §7.6–7.8 (Accepted / Deferred decisions + future triggers) | 2299–2506 | ~8% | **Decision content, not process.** Reconcile against `docs/adr/README.md`'s index — most entries already have ADRs; the rest belong in the vision/ADR track | T004 track / ADR backlog |

**Do not create a new `docs/process/` folder.** The genuinely-process
content (~29% of the file) is almost entirely *duplication of* — and in
two places *contradiction with* — material that already lives in
`AGENTS.md`, `.cursor/rules/ARCHITECTURE_CONTROL.md` and
`docs/adr/README.md`. A fourth home for agent instructions would make the
problem worse, not better.

---

## 2. The sprint doc's premise is wrong, and that matters

`SPRINT_054.md` line 53 describes the file as *"2,583 lines,
process/workflow content, not target architecture"*. That framing comes
from `docs/historical/REPO_WORKFLOW_DOCS_AUDIT.md` line 296, which reasoned
from the file's **title and vision-index one-liner** ("Workflow, AI usage
and ADR process"), and explicitly declined to read it in full.

Having read all 2,584 lines: **the majority of the file is target
architecture**, and it is the single most-cited architecture source in the
repository's sprint history. The audit's own hedge ("flagged for a
maintainer decision, not reclassified unilaterally here") was correct
caution — this document confirms why.

### Evidence 1 — eight sprint docs cite it as an *architecture source*, and every citation points at §3/§4

Grep across `docs/planning/sprints/`:

```text
SPRINT_008.md:18  docs/vision/WORKFLOWS_AI_ADR.md (SignalOccurrence, research datasets)
SPRINT_009.md:19  docs/vision/WORKFLOWS_AI_ADR.md (§3.3 Research Scope)
SPRINT_010.md:18  docs/vision/WORKFLOWS_AI_ADR.md (§3.14 Signal Research Analytics)
SPRINT_013.md:19  docs/vision/WORKFLOWS_AI_ADR.md
SPRINT_016.md:18  docs/vision/WORKFLOWS_AI_ADR.md (§4.20–4.21)
SPRINT_017.md:18  docs/vision/WORKFLOWS_AI_ADR.md (§3.12–3.14 Signal Research)
S016_WAVE0_DECISIONS.md:295  docs/vision/WORKFLOWS_AI_ADR.md §4.20–4.21
```

Not one citation references §6 (AI Agent Contract) or §7 (ADR process).
Every one references the workflow-architecture body. If this file were
"process, not architecture", the sprint record would not look like this.

### Evidence 2 — §3/§4/§5 read as architecture, section for section

Sample of what is actually in the "process" file:

- §3.3 (l. 256–302) defines the binding enum `MARKET_MODEL_ONLY /
  SIGNAL_MODEL_ONLY / MARKET_AND_SIGNAL` and the rule "the workflow must
  not infer scope from missing fields" — this is the contract ADR-0012
  (Combined Research Scopes) was written against.
- §3.9 (l. 475–511) assigns `SignalOccurrence` ownership to the Strategy
  Domain and enumerates its fields — a domain-model statement, later
  frozen as ADR-0011.
- §3.16 / §4.20 (l. 671–698, 1183–1199) specify on-disk layout under
  `user_data/research/…` and the per-run metadata manifest.
- §4.9 (l. 933–962) is the batch-backtest vs replay-execution split, the
  subject of PLANNED ADR-0009.
- §5.7 (l. 1380–1398) is a normative order-lifecycle state machine
  (`Created → Submitted → Accepted → Partially Filled → …`).
- §8 "Final Contract" (l. 2542–2584) closes with *"Every future workflow,
  implementation and architectural decision must remain consistent with
  this contract"* — an explicitly binding architecture statement.

None of this is "how the team works". Folding it into `AGENTS.md` or
`docs/README.md` would bury ~1,600 lines of binding architecture inside a
process index — the exact inverse of what Sprint 054 is trying to achieve.

### Evidence 3 — the genuinely-process parts are duplicates that have already drifted

The parts that *are* process do not need a new home; they need to be
reconciled with the homes that already exist, because they have gone stale:

| Conflict | In `WORKFLOWS_AI_ADR.md` | In the current process layer |
|---|---|---|
| Agent required reading order | §6.2 (l. 1601–1614): 7 steps, starts with `ARCHITECTURE_FOUNDATIONS.md`, includes this file itself at step 3, no mention of `CURRENT_STATUS.md` or `ROADMAP.md` | `AGENTS.md` l. 5–16: 8 steps, starts with `AGENTS.md`, then `CURRENT_STATUS.md` / `ROADMAP.md`, and **does not list `WORKFLOWS_AI_ADR.md` at all** |
| ADR status model | §7.4 (l. 2226–2242): six mixed-case statuses `Proposed / Accepted / Rejected / Deferred / Superseded / Deprecated` | `docs/adr/README.md` l. 11–18: four upper-case statuses `PROPOSED / ACCEPTED / DEPRECATED / SUPERSEDED` |
| ADR template | §7.5 (l. 2245–2295): 9 sections incl. Rationale, Alternatives Considered, Compatibility and Migration | `docs/adr/README.md` l. 73–97: 4 sections (Context, Decision, Consequences, References) |
| ADR location/naming | §7.3 (l. 2206–2222) still says *"Suggested location: `docs/adr/`"* with hypothetical filenames `0001-use-modular-monolith.md` | `docs/adr/` exists with 30+ real ADRs named `ADR-0001-modular-monolith.md` |
| Accepted decisions register | §7.6 (l. 2299–2434) lists 21 decisions "which should be represented by ADRs where not already recorded" | `docs/adr/README.md` index already records ~17 of them as ACCEPTED ADRs; 3 remain PLANNED (0004, 0009, 0010) |

Two independent, mutually-contradicting descriptions of the agent reading
order and of the ADR template are a concrete cost being paid today. §7.3's
"suggested location" language is a fossil from before `docs/adr/` existed.

---

## 3. Why not option (a) — stay in `vision/` as-is

- It is the only file in `docs/vision/` filed under a "Process" heading
  (`docs/vision/README.md` l. 31–35). `vision/README.md`'s own framing —
  *"Principles, target architecture, binding design decisions and future
  direction"* — does not describe §6 or §7 at all.
- It keeps two live contradictions (reading order, ADR template) in the
  repository indefinitely.
- Leaving §7.6's decision register in place keeps a second, staler ADR
  index next to `docs/adr/README.md`.

## 4. Why not option (b) — wholesale fold into `docs/README.md` / `AGENTS.md`

- Would relocate ~1,600 lines of binding workflow architecture (§1–§5, §8)
  into a process index, breaking 8 sprint documents' architecture-source
  citations and the "Vision vs Reference" two-layer model in
  `docs/README.md` l. 27–35.
- `AGENTS.md` is deliberately short (96 lines) and is loaded on every agent
  session. Merging 589 lines of §6 into it verbatim would make it
  unusable. §6 should be folded **selectively** — most of §6.4–§6.17
  already restates `.cursor/rules/ARCHITECTURE_CONTROL.md` §3 (domain
  ownership) and `AGENTS.md` §Architecture Rules.
- `docs/README.md` is explicitly *"Single index — folder READMEs are
  catalogs only"* (l. 3). It is not a content host.

---

## 5. Recommended execution shape (if the maintainer accepts option (c))

Sequenced so it does not violate D-S054-01 or D-S054-02:

1. **Amend T006's scope in `SPRINT_054.md`** from "decision + move" to
   "decision + three-way split", and **add §1–§5/§8 of this file to the
   T001–T003 classification scope** (call it T003b). This is a ~1,620-line
   read; it is the same size class as T001–T003 and should not be smuggled
   into T004 as an unclassified move.
2. **PR 1 (process, independent of T001–T004):** reconcile §7.1–7.5, §7.9,
   §7.10 into `docs/adr/README.md` — pick one status model, one template,
   drop the "suggested location" fossil. Removes those sections from
   `WORKFLOWS_AI_ADR.md` with a pointer.
3. **PR 2 (process, independent):** reconcile §6 into `AGENTS.md` +
   `.cursor/rules/ARCHITECTURE_CONTROL.md`. Only the deltas — §6.7 (local
   component lifecycle / promotion gate), §6.8 (fingerprint rules), §6.19
   (test-level matrix) and §6.23 (completion checklist) look like genuinely
   new material not already in the process layer; the rest is duplication
   to delete, not to copy. Fix the reading-order contradiction here.
4. **PR 3 (blocked on T003b + T004):** place §1–§5/§8 per the
   current/future classification, alongside the T004 output.
5. **§7.6–7.8:** reconcile against `docs/adr/README.md`'s index. Where a
   decision already has an ACCEPTED ADR, delete the duplicate. Where it
   does not (ADR-0004, 0009, 0010 are PLANNED; §7.7 deferred decisions and
   §7.8 triggers have no ADR home), keep in `vision/` and flag as ADR
   backlog — do **not** silently drop them.
6. **T009** picks up the inbound references. Current inbound links:
   `docs/agents/AGENTS.md` l. 9, `docs/agents/AGENTS_MULTITIMEFRAME_MARKET_MODEL.md`
   l. 22, `.cursor/rules/ARCHITECTURE_CONTROL.md` l. 11,
   `docs/vision/README.md` l. 35, `docs/vision/ARCHITECTURE_TECHNICAL.md`
   l. 30, `docs/vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` l. 30,
   `docs/reference/modules/DATA_MODULE.md` l. 33, plus 7 historical sprint
   docs (leave those — closed sprints are not rewritten).

---

## 6. Open questions for the maintainer

1. **Does §1–§5 duplicate `docs/reference/RESEARCH_METHODOLOGIES.md`?**
   That file is described in `docs/README.md` l. 70 as owning *"All
   research workflows — Signal, Model Research, Strategy, Robustness,
   Predictive"*. Whether §3/§4 are the *target* version of the same
   material or a stale parallel copy is exactly a T003b/T007 question, not
   something to guess here.
2. **Is the promotion gate in §6.7 still current?** It names
   `user_data/development/market_analysis/` → `user_data/candidates/…` →
   `src/trading_framework/market_analysis/`. ADR-0024 (Promotion
   Conditions for Machine-Learned Market Analysis States, Sprint 044) may
   supersede or narrow it. Not verified as part of T006.
3. **Which ADR template wins** — the richer §7.5 one or the leaner
   `docs/adr/README.md` one? Recent ADRs (0026–0029) should be sampled
   before choosing; T006 did not read them.
4. **Does the split need its own ADR?** Reorganizing the repository's most-
   cited architecture source is arguably a hard-to-reverse documentation
   decision. Maintainer's call.

---

## 7. Status

```text
STATUS: Proposed — requires your approval
What exactly needs confirmation: whether WORKFLOWS_AI_ADR.md is split three
  ways (architecture §1–5/§8 → T004 track; §6 → AGENTS.md; §7 process → 
  docs/adr/README.md) instead of being moved wholesale, and whether
  SPRINT_054.md T006 is rescoped accordingly with a new T003b
  classification task.
What happens once approved: SPRINT_054.md is amended (T006 rescoped, T003b
  added), and engineer picks up PR 1 first — reconciling §7.1–7.5/7.9/7.10
  into docs/adr/README.md, the smallest and most self-contained slice with
  no dependency on T001–T004.
```

T006 remains **open — awaiting maintainer decision**. Nothing has been
moved.
