# Increment 16A — Analyst Verdict Artifact

Detailed outcome and criteria from the accepted phase plan. Return to the [Phase 16 index](../../../planning/roadmap/PHASE_16_QUANT_WORKBENCH.md).

## 13H.1 — Increment 16A — Analyst Verdict Artifact

### Purpose

Make "is this result any good?" a persisted, reviewable fact rather than a
judgement re-made by each reader (and, worse, re-made inside the dashboard).

### Expected capabilities

- A standardized verdict vocabulary over research runs:
  `PASS`, `WEAK_PASS`, `INCONCLUSIVE`, `FAIL`, `REJECTED_OVERFIT`,
  `REJECTED_LEAKAGE_RISK`, `REJECTED_LOW_SAMPLE`, `REJECTED_CONCENTRATION`.
- The verdict computed from facts the pipeline **already persists** — baseline
  delta vs `RANDOM_PERMUTATION`, per-fold stability, train/test gap, sample
  size, class imbalance, period and regime concentration, feature-importance
  sanity — with each contributing input recorded alongside the verdict.
- The rule set is declared and versioned, so a verdict is reproducible and a
  changed threshold is visible as a diff, not as a silently different answer.
- Applied retrospectively to the Sprint 052 run as the worked example.

### Primary flow

```text
persisted run artifacts (metrics, folds, importances)
  -> declared verdict rule set (versioned)
  -> verdict + the facts that produced it, persisted as a sidecar
  -> dashboard displays it; dashboard never computes it
```

### Completion criteria

- A run carries a verdict and the inputs behind it, both reproducible from the
  persisted artifacts alone.
- Re-running the rule set over the same artifacts yields the same verdict.
- The dashboard reads the verdict; no verdict logic exists in `apps/dashboard`.
- Documentation states plainly that a verdict is a decision aid for what to
  study next — never evidence of a live edge, never a promotion approval
  (ADR-0024's rule, restated, not weakened).

### Dependencies

- Phase 10 (Sprints 039–044) — complete.
- **Phase 15B / Sprint 052 has run** — hard entry condition (§13H.0). The Q3
  parallel-start carve-out applies to 16B only, never to 16A.

### Main risks

- **A verdict becomes an authority.** A green `PASS` is easier to over-trust
  than a table of metrics. Mitigation: the vocabulary carries no "validated"
  or "approved" value, and `WEAK_PASS`/`INCONCLUSIVE` must be reachable and
  common outcomes, not rare ones.
- **Threshold tuning to produce nicer verdicts.** Mitigation: the rule set is
  versioned and diffable; changing a threshold after seeing a result is a
  reviewable act.
- Designing the rule set from one study is thin evidence. Mitigation: keep the
  first version deliberately conservative and few-ruled.

### Out of scope

- Any change to Sprint 052's scope, instrument, or acceptance criteria.
- Verdicts for Strategy or Robustness runs (16D onward may extend the
  vocabulary; the first version is predictive-run only).
- Any automatic consequence of a verdict — nothing is promoted, filtered or
  hidden because of one.

### Completion note (added at closure, 2026-09-08 — append-only, does not replace the text above)

**16A is DONE.** Delivered by Sprint 057
(`docs/archive/phases/phase-16-research-workbench/SPRINT_057.md`), 7/7 tasks, merged as six working
PRs into `sprint/analyst-verdict-artifact` (#464 ADR-0032, #465 vocabulary
and rule cascade, #466 fact extraction, #467 sidecar I/O, #468 retrospective
application, #469 dashboard display). ADR-0032 was accepted 2026-09-08 with
no correction attracted at review; the shipped vocabulary, rule set and
sidecar schema match it exactly. `sprint/analyst-verdict-artifact` was
merged into `main` via #471 (2026-09-08) — see
`docs/planning/CURRENT_STATUS.md` §2/§3 for the current integration state.

All four completion criteria above were assessed against the shipped
artifact:

1. **A run carries a verdict and the inputs behind it, both reproducible
   from persisted artifacts alone — MET.** `evaluate_run_verdict`
   (`application/predictive_research/evaluate_run_verdict.py`) reads only
   `metrics.json`, the dataset envelope, and the optional `importance.json`
   off disk; `verdict.json` records every extracted fact with its source
   artifact and every rule with its observed values and threshold. Proven,
   not merely asserted, against Sprint 052's three real runs
   (`f7ac893d54ae6b69`, `faa6983acd03f846`, `6d2842b647cd4097`) in T005.
2. **Re-running the rule set over the same artifacts yields the same
   verdict — MET.** `evaluate_verdict` is pure (no randomness, no clock, no
   dict-iteration-order dependence) and `verdict.json` carries no
   wall-clock field. Checked directly, not only asserted: the ridge run's
   `verdict.json` was re-evaluated a second time during T005 and its raw
   bytes compared byte-for-byte identical to the first write.
3. **The dashboard reads the verdict; no verdict logic exists in
   `apps/dashboard` — MET.** T006 (PR #469) added a read-only display in
   `apps/dashboard/pages/6_Predictive_Research.py` that renders
   `verdict.json`'s contents verbatim, with zero threshold constants and
   zero arithmetic; `apps/dashboard` still imports no `trading_framework`
   symbol (ADR-0022). One gap was found and logged, not fixed, during this
   task's QA: `PROBLEM_REGISTRY.md` PRB-022 — the dashboard's automated
   import-boundary test does not scan `apps/dashboard/pages/*.py`, so this
   criterion's enforcement for page files relied on manual review, not
   only the automated guard.
4. **Documentation states plainly a verdict is a decision aid, never
   evidence of a live edge or a promotion approval — MET.**
   `docs/reference/PREDICTIVE_VERDICT.md` states this in its own first
   section, restating ADR-0024's rule unweakened, and the same statement
   appears in ADR-0032 §6 and `research/predictive/CLAUDE.md`'s verdict
   entry.

One item of technical debt was left open: **TD-033**
(`docs/planning/TECHNICAL_DEBT.md`, ACCEPTED/LOW) — the verdict rule set's
three thresholds and its primary-metric-name convention independently
duplicate `research/reporting/predictive/quality.py`'s equivalents (a
deliberate design choice under ADR-0032 §2, not an oversight). Its
repayment trigger is a future consolidation increment touching both
modules, or an observed drift between them.

**This closure produced no study, no scorer, no promotion, and no new
market claim.** 16A remains a contract-and-artifact-only increment: it
applies the rule set to Sprint 052's already-closed study retrospectively
and changes nothing about that study's own conclusions
(`docs/reference/examples/BTC_PREDICTIVE_STUDY.md`, cited and never amended). 16C,
16D and 16G may now consume `verdict.json` as readers; none may extend the
vocabulary, sidecar schema, or module placement without a new or amending
ADR (ADR-0032 Follow-up).
