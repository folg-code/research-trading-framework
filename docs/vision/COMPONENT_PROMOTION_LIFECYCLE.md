# Trading Research Framework

# COMPONENT_PROMOTION_LIFECYCLE.md

> **Target architecture / not-yet-built content.** This file was created by
> Sprint 055 T008 out of `docs/vision/ARCHITECTURE_FOUNDATIONS.md` §4.12;
> `docs/vision/ARCHITECTURE_TECHNICAL.md` §5.12, §6.4; and
> `docs/vision/MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` §18 (all three
> source files now dissolved). These were four near-verbatim restatements
> of the same unbuilt five-stage promotion + `reproducibility_status` model
> (`Grep` for `reproducibility_status`/`EXPERIMENTAL` across
> `src/trading_framework/` returned zero matches). Content below is
> preserved verbatim from the original files; only classification headers,
> this merge header, and provenance notes are newly authored/added.

---

## Local Component Development and Promotion

*(Longest/primary copy — merged from: `ARCHITECTURE_FOUNDATIONS.md` §4.12,
now dissolved. Classified MIXED by Sprint 054 T001 — as-built status
unclear/partial. The underlying identity primitives (`component_id`,
`definition_hash`, `resolved_parameters`) are pervasively implemented
elsewhere and already documented as CURRENT in
`docs/reference/system/DOMAIN_MODEL.md`. The five-stage
promotion lifecycle and the `reproducibility_status`/`implementation_hash`
fields described below have zero code counterpart.)*

Market Analysis components may be developed locally before becoming maintained framework components.

Suggested lifecycle:

```text
Local Working Component
        ↓
Experimental Component
        ↓
Validated Candidate
        ↓
Promoted Framework Component
        ↓
Released Framework Component
```

Working components may change freely and do not require formal public versioning.

However, research using a working component must preserve an implementation fingerprint.

Suggested working identity:

```text
component_id
implementation_hash
dependency_hash
resolved_parameters
reproducibility_status = EXPERIMENTAL
```

A component may be promoted into the framework when it is:

- stable,
- reusable,
- strategy-independent,
- tested,
- documented,
- governed by an explicit contract,
- ready for compatibility maintenance.

Formal component versioning begins when the component becomes part of the maintained framework contract.

The same fingerprint rule applies to mutable local model definitions used in research, including:

- Market Models,
- Signal Models,
- Exit Models,
- Risk Models,
- Strategy Models.

Their experimental identity should include:

```text
definition_hash
resolved_parameters
dependency identities
reproducibility_status = EXPERIMENTAL
```

Not every completed component must become public.

> **Merged from: `ARCHITECTURE_TECHNICAL.md` §5.12 "Local Development and
> Promotion", now dissolved.** That section (classified FUTURE by Sprint
> 054 T002 — same `reproducibility_status`/`EXPERIMENTAL` zero-match
> evidence) restated the same lifecycle with one unique addition: concrete
> suggested filesystem locations for each stage —
>
> ```text
> user_data/development/market_analysis/       (local working components)
> user_data/candidates/market_analysis/         (validated candidates)
> src/trading_framework/market_analysis/        (promoted framework components)
> ```

---

## Local Model Fingerprints

*(Merged from: `ARCHITECTURE_TECHNICAL.md` §6.4, now dissolved. Classified
FUTURE by Sprint 054 T002 — the model-layer counterpart of the promotion
lifecycle's unbuilt fingerprint mechanism above. Same
`reproducibility_status`/`EXPERIMENTAL` search returned zero matches.)*

Mutable local model definitions used in research require identity even before formal versioning.

Store:

```text
definition_hash
resolved_parameters
dependency identities
reproducibility_status = EXPERIMENTAL
```

This applies to:

- Market Models,
- Signal Models,
- Exit Models,
- Risk Models,
- Strategy Models.

Released definitions use formal version identity.

> **Merged from: `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` §18 "User
> Data Structure" (fingerprint portion only), now dissolved.** That section
> (classified MIXED by Sprint 054 T003 — same zero-match evidence)
> restated the same two fingerprint field lists (working-component identity
> and mutable-model-definition identity) with no unique material beyond
> wording. Its `user_data/` directory-layout portion is evicted to
> `docs/historical/SUPERSEDED_LAYOUT_PROPOSALS.md` §4, since it is a
> superseded layout proposal rather than promotion-lifecycle content.

---

## Architectural Rule (fingerprint portion)

*(Merged from: `MULTITIMEFRAME_MARKET_MODEL_ARCHITECTURE.md` §19 rule 21,
now dissolved. Rules 1-16, 19, 22, 24 were classified CURRENT and moved into
the former `docs/reference/system/MULTITIMEFRAME_MARKET_MODEL.md`, which
Sprint 055 T007 merged into `docs/reference/system/TIME_AND_ALIGNMENT.md`;
rules 17/18/20 live in `RESEARCH_SPACE_AND_ANALYTICS.md`; rule 23 lives in
`EXECUTION_RUNTIME_FUTURE.md`.)*

21. Working components and models used in research require fingerprints. *(FUTURE - see the sections above.)*
