# Trading Research Framework

# PROBLEM_REGISTRY.md

## Entry index

Open an ID to read the full entry:

- [PRB-001](registries/prb-001-004.md#prb-001) · [PRB-002](registries/prb-001-004.md#prb-002)
- [PRB-003](registries/prb-001-004.md#prb-003) · [PRB-004](registries/prb-001-004.md#prb-004)
- [PRB-005](registries/prb-005-008.md#prb-005) · [PRB-006](registries/prb-005-008.md#prb-006)
- [PRB-007](registries/prb-005-008.md#prb-007) · [PRB-008](registries/prb-005-008.md#prb-008)
- [PRB-009](registries/prb-009-012.md#prb-009) · [PRB-010](registries/prb-009-012.md#prb-010)
- [PRB-011](registries/prb-009-012.md#prb-011) · [PRB-012](registries/prb-009-012.md#prb-012)
- [PRB-013](registries/prb-013-016.md#prb-013) · [PRB-014](registries/prb-013-016.md#prb-014)
- [PRB-015](registries/prb-013-016.md#prb-015) · [PRB-016](registries/prb-013-016.md#prb-016)
- [PRB-017](registries/prb-017-020.md#prb-017) · [PRB-018](registries/prb-017-020.md#prb-018)
- [PRB-019](registries/prb-017-020.md#prb-019) · [PRB-020](registries/prb-017-020.md#prb-020)
- [PRB-021](registries/prb-021-024.md#prb-021) · [PRB-022](registries/prb-021-024.md#prb-022)
- [PRB-023](registries/prb-021-024.md#prb-023) · [PRB-024](registries/prb-021-024.md#prb-024)

## 1. Purpose

This registry records observed architectural, research, implementation and operational problems.

A problem is different from:

- an idea,
- a planned feature,
- a known implementation shortcut,
- an accepted architectural decision.

A problem represents a risk, inconsistency, unknown or demonstrated weakness that may require:

- research,
- design,
- an ADR,
- a bug fix,
- an epic,
- a technical-debt item.

Problems remain in this registry until resolved, rejected or explicitly converted into another tracked form.

---

## 2. Statuses

```text
OPEN
UNDER_INVESTIGATION
DECISION_REQUIRED
PLANNED
MITIGATED
RESOLVED
DEFERRED
REJECTED
```

---

## 3. Severity

```text
CRITICAL
HIGH
MEDIUM
LOW
```

Severity reflects impact, not implementation urgency alone.

---

## 4. Problem Entry Template

```markdown
## PRB-XXX — Title

Status:
Severity:
Domain:
Owner:
Discovered:
Last Updated:

### Description

...

### Evidence

...

### Impact

...

### Possible Directions

- ...

### Decision or Resolution Criteria

- ...

### Related Documents

- ...

### Related ADRs

- ...

### Related Tasks

- ...
```

---

Each problem title below links directly to its full entry. Stable ID headings remain here for existing links.

# 5. Active Problems

Read one item by ID. Full entries are grouped below; stable ID headings remain here for existing links.

## [PRB-001 — Dataset Identity Is Conceptually Defined but Not Yet Algorithmically Specified](registries/prb-001-004.md#prb-001)

## [PRB-002 — Component Fingerprint Algorithm Is Not Defined](registries/prb-001-004.md#prb-002)

## [PRB-003 — Local Model Definition Fingerprints Are Not Yet Specified](registries/prb-001-004.md#prb-003)

## [PRB-004 — Public Discovery of `user_data` Components Needs a Safe Contract](registries/prb-001-004.md#prb-004)

## [PRB-005 — Market Analysis Result Storage Shape Is Not Fixed](registries/prb-005-008.md#prb-005)

## [PRB-006 — Research Dataset Physical Schema Is Intentionally Undefined](registries/prb-005-008.md#prb-006)

## [PRB-007 — Trading Calendar Implementation Is Not Selected](registries/prb-005-008.md#prb-007)

## [PRB-008 — Bar Timestamp Convention Must Be Explicit](registries/prb-005-008.md#prb-008)

## [PRB-009 — Intrabar Higher-Timeframe Semantics Need a Formal Contract](registries/prb-009-012.md#prb-009)

## [PRB-010 — Initial Numeric Types Are Not Fixed](registries/prb-009-012.md#prb-010)

## [PRB-011 — MarketFieldReference May Become an Architectural Bypass](registries/prb-009-012.md#prb-011)

## [PRB-012 — Research Space Planner Limits Need Initial Defaults](registries/prb-009-012.md#prb-012)

## [PRB-013 — Research/Runtime Parity Is Not Yet Measurable](registries/prb-013-016.md#prb-013)

## [PRB-014 — Vectorized Backtest Semantics Need a Deliberately Limited MVP](registries/prb-013-016.md#prb-014)

## [PRB-015 — Architecture Documents Require a Formal Consistency Check](registries/prb-013-016.md#prb-015)

## [PRB-016 — ADR History Has Not Yet Been Materialized](registries/prb-013-016.md#prb-016)

## [PRB-017 — No Representative Integration and Research-Validation Datasets](registries/prb-017-020.md#prb-017)

## [PRB-018 — Torch Smoke Test False-Fails Without `dl` Extra Installed](registries/prb-017-020.md#prb-018)

## [PRB-019 — `plain mypy .` Fails on Duplicate `test_config` Module Name](registries/prb-017-020.md#prb-019)

## [PRB-020 — Strategy Research Lacks Signal Research's Family/Bounded-Expansion Machinery](registries/prb-017-020.md#prb-020)

## [PRB-021 — `FileDatasetRegistry`'s Default Version Allocator Silently Overwrites Published Datasets on Re-Import](registries/prb-021-024.md#prb-021)

## [PRB-022 — `apps/dashboard`'s Import-Boundary Test Does Not Scan `pages/*.py`](registries/prb-021-024.md#prb-022)

## [PRB-023 — Root `mypy`/`pytest` Never Check `apps/dashboard/` or `scripts/`](registries/prb-021-024.md#prb-023)

## [PRB-024 — `scripts/dashboard/` Is Not Covered by Any Import-Boundary Scan](registries/prb-021-024.md#prb-024)

# 6. Resolved Problems

No problems have yet been formally moved to `RESOLVED`.

When resolving a problem:

- preserve the original description,
- record the resolution date,
- link the ADR or task,
- describe remaining limitations.
