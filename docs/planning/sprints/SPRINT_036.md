# Sprint 036 - Research Infra Audit (gate for DSL / components)



## Metadata



```text

Sprint: 036

Phase: Research authoring foundation (pre–AI/ML)

Status: IN_PROGRESS

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

| S036-T001 | Wave 0: path inventory + success metrics + branch naming | DONE (S036_WAVE0_DECISIONS.md) |

| S036-T002 | Bench/spike harness for authoring → analysis → research (fixture) | DONE |

| S036-T003 | Audit write-up: ranked bottlenecks + non-goals + canonical type policy | DONE — `docs/reference/DATA_REPRESENTATION_AUDIT.md` |

| S036-T004 | Baseline measurement (250 / 2 000 / 10 000 bars) recorded as the reference for all later PRs | DONE — audit §6.1 |

| S036-T005 | Stage 0.5 — session resolver single pass (measured M1). `session_id` stays Utf8; timezone remains its own pass | DONE — #279; audit Stage 0.5 |

| S036-T006 | Extend bench harness to cover multitimeframe and Parquet reads (prerequisite for Stage 1) | DONE — #278; audit §6.3 |

| S036-T007 | Stage 1 — table-level validators + remove `MarketBar` round-trips (D-REP-03 / D-REP-07) | DONE — H2 #281; derive table validation #282; H6 deferred; H4 unmeasured |

| S036-T008 | Stage 2 — `scan_parquet` at repository boundary, then lazy analysis frame builder (D-REP-02) | DONE — step 1 #283; step 2 lazy `build_analysis_frame` (wall time flat; see audit §6.3.2) |

| S036-T009 | ADRs for D-REP-01, D-REP-05, D-REP-10 | DONE — ADR-MA-014; MA-004/010/012 and MA-005/009 amendments |

| S036-T010 | Gate doc for S037 (DSL simplicity criteria + component library rules) | DONE — `S037_GATE.md` |

| S036-T011 | CURRENT_STATUS / ROADMAP closeout | TODO |

The data representation policy and the D-REP decision register live in
[`../../reference/DATA_REPRESENTATION_AUDIT.md`](../../reference/DATA_REPRESENTATION_AUDIT.md)
(accepted 2026-08-25). It governs the Stage 1–Stage 4 scope referenced above.

Wave 1 harness command: `uv run python scripts/ops/bench_authoring_analysis_evaluate.py` (`--json`, `--bars N`, opt-in `--mtf`, `--parquet`).


Suggested PR waves into `sprint/research-infra-audit`:



1. Wave 0 decisions + path inventory (docs)  

2. Bench harness + initial measurements  

3. Audit report (ranked findings) + data representation policy  

4. Baseline measurement committed  

5. Stage 0.5 — session resolver single pass (measured top item)  

6. Harness extension: multitimeframe + Parquet coverage  

7. Stage 1 optimization PRs (D-REP-03 / D-REP-07), scoped by the extended harness  

8. Stage 2 optimization PRs (D-REP-02)  

9. ADRs for accepted contract changes (D-REP-01 / D-REP-05 / D-REP-10)  

10. S037 gate doc + sprint closeout  

The two-PR optimization cap was lifted on 2026-08-25 (see amendment in `S036_WAVE0_DECISIONS.md`).
The binding constraint is the measurement gate, not PR count.



---



## 6. Wave 0 decision checklist



Before coding optimizations:



- [x] Confirm sprint branch: `sprint/research-infra-audit`

- [x] List entrypoint scripts / modules for each inventoried path

- [x] Agree fixture dataset(s) for benches (no proprietary data in repo)

- [x] Agree “identical facts” rule: optimizations must not change research outputs on fixtures

- [x] Confirm S037 owns DSL simplification + component library expansion

- [x] Confirm AI/ML stays deferred (IDEA-014)



See `S036_WAVE0_DECISIONS.md` for binding decisions D-S036-01 … D-S036-08.



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



Gate: [S037_GATE.md](S037_GATE.md) — audit complete; HIGH authoring items repaid or deferred;
DSL stays IR-stable; catalog grows as components + namespace functions, not new language.



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

| Mega-sprint | Measurement gate on every PR (D-S036-04); T006: H2 justified, H6 defer, H4 unmeasured |

