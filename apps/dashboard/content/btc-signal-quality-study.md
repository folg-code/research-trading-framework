---
slug: btc-signal-quality-study
title: BTC Signal Quality Study
status: AS_BUILT
updated: 2026-09-09
order: 4
links: docs/reference/BTC_SIGNAL_QUALITY_STUDY.md
---

This study asks whether a signal quality classifier improves an existing
BTC strategy. The strategy is a real, already-committed composition (an
RSI-oversold entry gated by a relative-volatility regime filter); the
classifier is trained on the same strategy's occurrences to predict which
ones are worth taking, and evaluated against a random-permutation baseline
at a fixed decision threshold and a fixed random seed, chosen before any
result was seen.

The persisted verdict and its supporting charts appear above: they come
directly from the projected evidence, never restated or reinterpreted here.

Strategy Research then ran the same strategy twice on the same real
market data — once unscored, once filtered through the classifier at its
declared threshold — to see whether scoring changed the outcome. Two
occurrences were filtered out by the score (one that would have won, one
that would have lost); trade count, win rate and net PnL were otherwise
effectively unchanged between the two runs. This comparison, including the
declared threshold and the two filtered occurrences, is recorded in
[the full study write-up](https://github.com/folg-code/research-trading-framework/blob/main/docs/reference/BTC_SIGNAL_QUALITY_STUDY.md)
— it is not recomputed by this dashboard.
