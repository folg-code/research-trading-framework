---
slug: future-ai-research-infrastructure
title: AI Research Infrastructure
status: FUTURE_IDEAS
updated: 2026-09-10
order: 13
links: docs/planning/sprints/SPRINT_061.md, docs/vision/PRODUCT_DIRECTION.md
---

This is a proposed direction, not implemented capability or approved
architecture. Provider selection, persistence, authorization, orchestration
runtime and delivery scope remain undecided.

## The idea

An AI control plane could decide **what to investigate** while the existing
framework remains responsible for **how deterministic computation is executed**.
The model would formulate hypotheses, prepare bounded experiment proposals,
request existing research workflows, inspect persisted analytics and decide
whether to continue or stop. It would not calculate backtests inside a prompt
or replace the framework's research contracts.

## Lightweight coordination

The proposed first shape uses a local or free model as a lightweight
coordinator. Routine classification, routing and state transitions stay cheap.
Difficult statistical criticism, architecture or coding work may be escalated
on demand to officially supported subscription-agent environments. Paid API
usage remains an optional fallback rather than an MVP requirement.

No unofficial browser automation, session capture or private web endpoints are
part of this direction. Any integration would use interfaces officially
supported by its provider.

## Local agents and on-demand specialists

The always-on coordinator is intentionally small and local. It reads a shared
Research State, classifies the next action and routes a structured task. It can
run deterministic framework tools directly, assign routine work to a
local/free model, or delegate a difficult bounded task to a stronger specialist.

```text
Local Research Orchestrator
  ├─ deterministic tool → framework computation
  ├─ local agent → routing, extraction, routine analysis
  └─ subscription agent → hard statistics, architecture or coding
```

A subscription agent such as Codex, Claude Code or an equivalent supported
environment is not treated like a chat-completion endpoint. It may receive a
repository checkout, terminal, tools, permissions and a durable task context,
then return an implementation, tests, critique or decision artifact. Expensive
reasoning is a specialist escalation, not the permanent control loop.

## Roles and structured artifacts

One model could serve several roles, but the responsibilities and output
contracts remain separate:

- an **Experiment Planner** produces a bounded proposal with dataset, models,
  horizons and search space;
- a **Result Analyst** summarizes persisted effects and limitations;
- a **Research Critic** challenges sample size, multiple testing, leakage,
  stability and concentration;
- a **Coding Agent** receives an implementation task rather than deciding what
  the evidence means;
- a coordinator updates shared research state and decides the next action.

Roles exchange structured hypotheses, proposals, reports, critiques and
decisions instead of relying on a long conversation as memory.

## The research loop

```text
Research goal
  → observe existing evidence
  → formulate a hypothesis
  → design and validate a bounded experiment
  → run deterministic research
  → analyze results
  → request an independent critique
  → update persistent knowledge
  → continue, escalate or stop
  ↺
```

The loop is explicit state, not an endless prompt. Every cycle consumes a
budget, records its inputs and outcome, and ends with a typed decision. Failed,
negative and inconclusive directions enter the knowledge base so the system
does not rediscover and retest them indefinitely.

The orchestrator owns sequencing; agents do not chat peer-to-peer. Planner,
Analyst, Critic, Component Designer, Coding Agent and later Knowledge Curator
read the same Research State and return structured artifacts through the
orchestrator. Their model, tools and permissions can differ even when one local
model plays several roles in the MVP.

## Model and compute routing

A future router would consider task type, context size, required tools, cost,
latency, availability and remaining limits. The preferred cost hierarchy is:
deterministic framework first, then local model, free API, subscription agent,
and paid API only as an optional fallback. Research compute can later run on
local CPU, cloud CPU or GPU without making the AI control plane responsible for
the numerical implementation.

## Persistent knowledge and research budgets

A future knowledge base could retain tested hypotheses, rejected directions,
evidence links, robustness findings and open questions. Formal budgets would
bound experiments, candidates, agent cycles, subscription escalations and paid
API cost.

Those limits support a non-negotiable anti-data-mining policy: an agent cannot
"try everything until a high score appears." Proposals must pass explicit
sample-size, out-of-sample, multiple-testing, complexity and budget checks.

## Safety boundary

Autonomous research could never promote itself into live execution. Model
promotion, strategy selection and any operational deployment remain separate,
human-governed processes. The AI layer is a possible client of existing
research contracts, not a new source of research truth or trading authority.
