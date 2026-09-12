# Increment 16E — Strategy Families (directional)

Detailed outcome and criteria from the accepted phase plan. Return to the [Phase 16 index](../PHASE_16_QUANT_WORKBENCH.md).

## 13H.5 — Increment 16E — Strategy Families (directional)

### Purpose

Give Strategy Research the bounded-expansion machinery Signal Research already
has. **This increment is the planned closure route for `PRB-020`** (OPEN,
MEDIUM) **and for `PRB-012`** (OPEN, MEDIUM) — see `PROBLEM_REGISTRY.md`. Both
are planned, not closed; both remain OPEN until this increment ships.

The two belong together and are deliberately not split: `PRB-020` asks for
bounded candidate generation in Strategy Research, and `PRB-012` asks for the
default limits that make "bounded" mean something. Building the first without
the second would produce a planner whose only bound is the user's own YAML —
which is the situation PRB-012 already describes.

### Direction decisions already taken (maintainer, 2026-09-04)

```text
Q4 — PRB-020's direction.  DEFAULT DIRECTION SET: port
                           research/signal_research/family_planning.py's
                           pattern to a new
                           research/strategy_research/family_planning.py,
                           mirroring the Signal Research design.
                           NOT unconditional: if 16E's own design work finds
                           Strategy Research's combinatorics genuinely differ
                           (multi-model composition vs. single-model parameter
                           sweeps), that finding is SURFACED EXPLICITLY at
                           16E's Wave 0 and decided there — never decided
                           unilaterally by an architect mid-implementation.
Q8 — PRB-012 back-         NOT RETROFITTED to Signal Research's existing
     application.          planner. Deliberate, not an oversight: no runaway
                           incident has been reported, and retrofitting would
                           change existing working configs' behaviour with no
                           demonstrated trigger (§2.7). PRB-012 closes for the
                           NEW Strategy Research planner only; the asymmetry
                           is accepted explicitly and revisited if a concrete
                           incident or need arises.
```

### Expected capabilities

- Bounded candidate generation with `candidates_generated` /
  `candidates_evaluated` / `candidates_skipped` bookkeeping, mirroring
  `research/signal_research/family_planning.py`'s established pattern (Q4's
  default direction).
- Family identifiers, nested model comparison, marginal-contribution analysis,
  parameter sensitivity, cost/slippage sensitivity.
- A ranking-objective contract with eligibility filters.
- **Planner limits with conservative defaults** (`PRB-012`): a maximum
  candidate count, a maximum number of model conditions, a maximum parameter
  dimensionality, a warning/confirmation threshold below the hard maximum,
  and a preflight cost estimate. Every limit is overridable explicitly, and
  exceeding one is reported, never silently applied.

### Why it belongs in this phase

ML scoring creates families by construction:

```text
baseline signal
baseline signal + regime filter
baseline signal + volatility filter
baseline signal + ML quality score
baseline signal + ML quality score + bracket exit
```

Without family machinery, 16C's comparison is a hand-assembled pair of runs.

### Completion criteria (directional)

- A Strategy Research config declaring alternatives produces a bounded,
  observable candidate set with counts preserved — the search space is
  **observable before it is large**.
- Multiple-testing exposure is recorded, not implied.
- `PRB-020`'s resolution criteria are met along Q4's default direction, or a
  documented Wave 0 divergence from it is recorded with its rationale.
- **`PRB-012`'s resolution criteria are met** as part of this increment:
  - initial conservative default limits ship enabled, not opt-in;
  - every limit has an explicit, documented override;
  - planner tests cover both the default-limit path and the override path,
    including the refusal at the boundary;
  - **no silent pruning** — a candidate set that would exceed a limit is
    refused or reported with counts, never quietly truncated. A truncation
    that is not visible in `candidates_skipped` is a defect, not a
    performance feature.
- The Signal Research asymmetry (Q8: not retrofitted) is restated in the
  increment's closing notes, so PRB-012 does not close leaving the reader to
  discover the gap themselves.

### Dependencies

- Phase 6A.
- **PRB-020's direction** — resolved as a default (Q4); no longer a blocking
  prerequisite for planning 16E, but its confirmation-or-divergence is a
  required Wave 0 item.
- **PRB-012** — co-requisite, resolved inside this increment. Its default
  *values* remain a Wave 0 decision for 16E's sprint.
- Independent of 16B/16C in principle, though 16C is what makes it urgent.
- Sprint 052 has run (§13H.0).

### Main risks

Unbounded search dressed up as a family; a ranking objective that quietly
becomes an optimizer over noise; limits set so high on first pass that they
satisfy PRB-012's letter while bounding nothing in practice (mitigation:
defaults are chosen to be *inconvenient*, with an easy documented override,
rather than generous); the Q8 asymmetry drifting out of memory and someone
"fixing" Signal Research's planner as a side effect of 16E — which would be
exactly the unrequested behaviour change Q8 declined.

### ADR

Confirming (or departing from) Q4's default port direction is a binding
architectural decision — **ADR expected** (§13H.9). PRB-012's default limits
are a parameter choice recorded in that ADR's consequences, not a separate
ADR, and so is the Q8 non-retrofit boundary.
