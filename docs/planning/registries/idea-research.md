# Research — idea entries

Return to the [Idea Inbox index](../IDEA_INBOX.md).

# 7. Research

<a id="idea-015"></a>
## IDEA-015 — Research Preflight Cost Estimator

```text
Status: INBOX
Category: Research
Added: 2026-06-19
```

### Summary

Estimate before execution:

- candidate count,
- unique dependency count,
- reused nodes,
- expected storage,
- approximate memory and runtime class.

### Potential Value

Prevents accidental large experiment expansion.

### Dependencies

- stable planner,
- node identities,
- measured component costs.

---

<a id="idea-016"></a>
## IDEA-016 — Pareto Frontier Candidate Explorer

```text
Status: INBOX
Category: Research Analytics
Added: 2026-06-19
```

### Summary

Compare candidates across:

- expectancy,
- drawdown,
- stability,
- sample size,
- complexity,
- cross-asset consistency.

### Promotion Criteria

Strategy Research metrics and persistent datasets are stable.

### Status Note (2026-08-25)

Sprint 042 introduces a single-study leaderboard for predictive estimator families. That is a
narrower artifact than a Pareto explorer, but it establishes the comparison view model this idea
would generalize.

---

<a id="idea-017"></a>
## IDEA-017 — Automated Family Discovery

```text
Status: DEFERRED
Category: Research Analytics
Added: 2026-06-19
```

### Summary

Group nearby Market or Strategy Model variants automatically.

### Main Questions

- semantic versus parameter distance,
- stable family identifiers,
- explainability.

### Promotion Criteria

Manual family definitions become a demonstrated bottleneck.

---

<a id="idea-018"></a>
## IDEA-018 — Research Insight Generator

```text
Status: DEFERRED
Category: AI / Research
Added: 2026-06-19
```

### Summary

Generate structured summaries of:

- stable effects,
- weak samples,
- contradictory assets,
- sensitivity regions,
- potential follow-up hypotheses.

### Important Rule

Generated insights must remain interpretations of stored facts.

They must not mutate Research Datasets or declare a strategy validated automatically.

---

<a id="idea-019"></a>
## IDEA-019 — Distributed Research Workers

```text
Status: DEFERRED
Category: Infrastructure
Added: 2026-06-19
```

### Summary

Distribute independent research workloads across machines.

### Dependencies

- stable local execution,
- task identity,
- deterministic artifacts,
- measurable single-machine bottleneck.

### Promotion Criteria

One machine repeatedly fails required throughput or memory constraints.

---
