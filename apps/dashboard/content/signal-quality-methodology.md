---
slug: signal-quality-methodology
title: Signal Quality Methodology
status: AS_BUILT
updated: 2026-09-09
order: 3
links: docs/reference/PREDICTIVE_VERDICT.md, docs/adr/ADR-0032-predictive-run-verdict-artifact.md, docs/reference/workflows/RESEARCH_METHODOLOGIES.md
---

A Signal Quality study asks whether a classifier trained on a signal's
features beats chance at predicting its labelled outcome. Two comparisons
make this concrete: pooled ROC AUC against a random-permutation baseline
(does the model separate outcomes better than shuffled labels would?), and
threshold sensitivity across a probability grid (does a usable decision
threshold actually exist, or does requiring confidence collapse the
number of covered occurrences to almost nothing?).

Every run is scored against a fixed, versioned rule set
(`verdict_rules.v1`) that classifies the result into one of eight
outcomes — from a clear pass to specific rejection reasons like
overfitting or an implausibly leaky effect size. The rule set and the
full vocabulary are documented once, canonically, and are not restated
per study; see
[Predictive Verdict](https://github.com/folg-code/research-trading-framework/blob/main/docs/reference/PREDICTIVE_VERDICT.md).

This page describes the method in general — it is maintained as living
content and updated when the method changes, not frozen to describe one
run. It draws no conclusion about any specific study; a study's own
persisted verdict and evidence are presented separately.
