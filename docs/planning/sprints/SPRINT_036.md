# Sprint 036 - Research Infra Audit (gate for DSL / components)

## Metadata

```text
Sprint: 036
Phase: Research authoring foundation (pre–AI/ML)
Status: PLANNED
Planned Start: 2026-07-18
Planned End: TBD
Sprint Goal Owner: Project Maintainer
Depends On: S024 on main (#270); S026/S027 performance baselines exist
Sprint Branch: sprint/research-infra-audit
Task branch convention: feat/ | fix/ | docs/ | test/ | bench/
Architecture Sources:
  - docs/planning/sprints/SPRINT_026.md (research hot-path)
  - docs/planning/sprints/SPRINT_027.md (market-data import performance)
  - docs/planning/sprints/SPRINT_006.md (declarative models / DSL scope)
  - docs/planning/IDEA_INBOX.md (IDEA-014 ML States — deferred until after this track)
Maintainer direction (2026-07-18):
  1. Inspect research infra for optimization (this sprint)
  2. Expand component libraries + simplify DSL as far as practical (follow-on S037)
  3. AI/ML research later (not this sprint)
```

---

## 0. Why this sprint

S035 defaulted to S024 (done). The chosen **next** product direction is not 4B/6B/Replay:

```text
infra audit (measured)
  -> component libraries + maximal DSL simplicity
  -> AI/ML research (IDEA-014 and related)
```

S026/S027 already repaid known hot paths. This sprint does **not** re-run those sprints.
It audits the **authoring → analysis → research** path that will carry DSL/component growth,
and only ships optimizations justified by measurements.

---

## 1. Goal

```text
Produce a measured map of research-authoring bottlenecks
  -> repay only HIGH / justified items in small PRs
  -> leave an explicit gate document for Sprint 037 (DSL + component libraries)
```

Success: a maintainer can answer “what is slow, why, and what we will not touch yet”
before expanding the component catalog or simplifying `model_authoring/`.

---

## 2. In scope

- Inventory of critical paths (with owners and entrypoints):
  - `model_authoring` compile → IR
  - Market Analysis DAG / `run_analysis` / frame assembly
  - Signal / Market research occurrence + forward outcomes
  - Strategy research + robustness experiment loops (reference only; do not regress S026)
  - Parquet / storage read patterns used by research CLIs and dashboard queries
- Reproducible microbench or spike harnesses (fixture-first; optional larger local datasets)
- Written audit note under `docs/planning/` or `docs/reference/` (single source)
- Optimizations that:
  - have a before/after measurement,
  - preserve public contracts and research facts,
  - fit one coherent PR each (~100–400 LOC)

## 3. Out of scope

- New DSL surface area or breaking `model_authoring` API redesign (→ S037)
- Large new Market Analysis catalog components (→ S037, after audit)
- Phase 4B orderflow / 6B multi-data / Phase 8 Replay
- AI/ML training, model registry, IDEA-014 promotion
- Dashboard cosmetics, AWS dry-run worker feature work
- Speculative distributed / multi-machine infra
- Full `market_analysis/` directory reorg (TD-003) unless audit proves it blocks measurement or a justified fix

---

## 4. Relationship to prior performance work

| Prior | Keep | Do not redo |
|-------|------|-------------|
| S026 | Signal/robustness hot-path lessons + harness patterns | Blind rewrites of already-optimized loops |
| S027 | Import / continuous build notes | Re-profiling import unless authoring path depends on it |
| S006 | Declarative IR + “reduce full expression DSL” intent | Expanding DSL before simplicity goals are written |

---

## 5. Task breakdown

| Task | Outcome | Status |
|------|---------|--------|
| S036-T001 | Wave 0: path inventory + success metrics + sprint naming | TODO |
| S036-T002 | Bench/spike harness for authoring → analysis → research (fixture) | TODO |
| S036-T003 | Audit write-up: ranked bottlenecks + non-goals | TODO |
| S036-T004 | First justified optimization PR (from audit top item) | TODO |
| S036-T005 | Optional second optimization PR if still HIGH | TODO |
| S036-T006 | Gate doc for S037 (DSL simplicity criteria + component library rules) | TODO |
| S036-T007 | CURRENT_STATUS / ROADMAP closeout | TODO |

Suggested PR waves into `sprint/research-infra-audit`:

1. Wave 0 decisions + path inventory (docs)  
2. Bench harness + initial measurements  
3. Audit report (ranked findings)  
4. One optimization PR (top finding)  
5. Optional second optimization  
6. S037 gate doc + sprint closeout  

---

## 6. Wave 0 decision checklist

Before coding optimizations:

- [ ] Confirm sprint branch: `sprint/research-infra-audit`
- [ ] List entrypoint scripts / modules for each inventoried path
- [ ] Agree fixture dataset(s) for benches (no proprietary data in repo)
- [ ] Agree “identical facts” rule: optimizations must not change research outputs on fixtures
- [ ] Confirm S037 owns DSL simplification + component library expansion
- [ ] Confirm AI/ML stays deferred (IDEA-014)

---

## 7. Acceptance criteria

1. Audit document exists with ranked bottlenecks and explicit non-goals.  
2. At least one reproducible bench path is runnable via documented command.  
3. Any code change cites a measurement (before/after) in the PR.  
4. Public contracts and fixture research facts unchanged (or ADR if intentional).  
5. S037 gate criteria written (what “DSL simple enough” and “library ready” mean).  
6. Quality gates pass.

---

## 8. Follow-on (not this sprint)

### Sprint 037 (planned outline) — Component libraries + DSL simplification

```text
Expand reusable Market Analysis / signal components
  -> simplify model_authoring DSL toward maximal clarity
  -> keep IR stable; prefer libraries over new language features
```

Gate: S036 audit complete; no HIGH unpaid authoring-path bottlenecks without a documented deferral.

### Later — AI/ML research

Promote IDEA-014 only after rule-based analysis + authoring UX are stable enough for
feature lineage, leakage control, and artifact identity.

---

## 9. Risks

| Risk | Mitigation |
|------|------------|
| Re-doing S026/S027 | Inventory must cite prior baselines; skip repaid paths |
| Optimization without measurement | Reject PRs that lack before/after |
| DSL creep during audit | Keep language changes in S037 |
| Mega-sprint | Cap at two optimization PRs; rest → backlog / S037 |
