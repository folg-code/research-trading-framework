---
slug: signal-predictive-workflow-context
title: Signal Research and Predictive Research
status: AS_BUILT
updated: 2026-09-09
order: 2
links: docs/reference/workflows/SIGNAL_RESEARCH.md, docs/reference/workflows/RESEARCH_METHODOLOGIES.md, docs/vision/PRODUCT_DIRECTION.md
---

Signal Research and Predictive Research are independent workflows. Signal
Research studies how a declared market/signal model's occurrences resolve
over time. Predictive Research asks a narrower, separate question: whether
a declared label can be predicted from features available at a row's
evaluation point, evaluated against a random-permutation baseline rather
than assumed useful. Its default sampling is every evaluation bar, not
Signal Research's occurrences — a signal's occurrences are only one of two
supported sample kinds Predictive Research can optionally draw rows from.

Predictive Research does not require Signal Research to have run first,
and Signal Research does not require Predictive Research either. A
promotable model and a signal's own standalone performance are separate,
explicitly recorded facts, not stages of one pipeline.

The Signal Quality study on this dashboard is one example that happens
to touch both: a Signal Research occurrence set, evaluated separately by
Predictive Research, then consulted by Strategy Research through an
explicit, content-addressed artifact reference (a fingerprint identifying
one promoted model, not a version number). Each step reads only what the
previous step actually persisted — never an assumed or inferred link.

For the full workflow reference, see
[Signal Research](https://github.com/folg-code/research-trading-framework/blob/main/docs/reference/workflows/SIGNAL_RESEARCH.md)
and
[Predictive Research methodology](https://github.com/folg-code/research-trading-framework/blob/main/docs/reference/workflows/RESEARCH_METHODOLOGIES.md).
