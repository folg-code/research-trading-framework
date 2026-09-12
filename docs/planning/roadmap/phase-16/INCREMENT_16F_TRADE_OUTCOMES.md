# Increment 16F — Trade Outcome and No-Trade Models (directional)

Detailed outcome and criteria from the accepted phase plan. Return to the [Phase 16 index](../PHASE_16_QUANT_WORKBENCH.md).

## 13H.6 — Increment 16F — Trade Outcome and No-Trade Models (directional)

### Purpose

Extend the sample universe to simulated trades and to rejected/accepted
candidates, closing the loop between simulation and ML.

### Expected capabilities (directional)

- `strategy_trades` sample kind over a Strategy Research run's `trades`
  artifact, with entry-time feature/state context.
- Labels from realized outcomes: win/loss, realized R, MAE/MFE, exit reason,
  holding-time quality.
- A no-trade filter — "when should an otherwise valid setup be ignored?" —
  which is frequently more useful than an entry model.

### Completion criteria (directional)

- A trade-outcome study reproducible from a persisted strategy run ID alone.
- Entry-time context is provably entry-time: no post-entry information reaches
  a feature.
- Results feed strategy filtering only through 16C's explicit gating path —
  including its Option B family restriction, which 16F inherits and does not
  relax.

### Dependencies

16B (contract), 16C (the gating path, including its scorer-reference
contract), Phase 6A trade artifacts.

### Main risks

Label leakage from realized outcomes into features; trade counts far too small
for stable fitting; conditioning on a strategy's own simulated fills makes the
result inherit every execution assumption in that simulation.
