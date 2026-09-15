# ADR-0045 — Layered Research Terminology and Compatibility Boundary

## Status

ACCEPTED — maintainer instructed implementation to continue on 2026-09-15
after the proposed PRD and this decision were presented for approval.

Author: Codex, based on maintainer discovery on 2026-09-15

Reviewer: Filip Folga
Affected areas: Research, Strategy, Applications, documentation

## Context

The framework's domain boundaries are explicit, but several words carry
different meanings across domain contracts, executable workflows, product
copy, persisted artifacts and presentation types.

`Research` is correctly the umbrella domain, but it also appears in most
methodology, workflow and product names. The technical Signal Research
workflow supports Market Model-only, Signal Model-only and combined scopes,
so its name does not describe every user task equally well.

`Model` is an accepted qualified term in `Market Model` and `Signal Model`,
but it is also used for exit rules, risk and sizing policies, complete
strategy composition, machine-learning estimators and presentation view
models. Bare user-facing `model` labels therefore lose material type
information.

Lifecycle language also drifts between study, definition, experiment and run.
The public dashboard's `Portfolio Study` is deliberately editorial metadata,
not cross-workflow lineage or a framework-level aggregate. Existing Signal
Research definitions, manifests, identifiers, CLI commands and workspace
paths are versioned compatibility contracts and cannot be renamed as an
editorial cleanup.

The project needs a stable language boundary before the Workbench catalog and
comparison surface expand further.

## Decision

### 1. Terminology is layered

The maintained vocabulary distinguishes:

| Term | Meaning |
|---|---|
| Research | Umbrella business domain and product area |
| Methodology | Rules for framing and evaluating a research question |
| Workflow | Executable orchestration owned by the application layer |
| Use case | One callable operation inside or alongside a workflow |
| Pipeline | A data-transformation chain; not a synonym for every workflow |
| Definition / Spec | A declaration of what a workflow should execute |
| Experiment | A workflow-local controlled comparison of variants |
| Run | One execution with its own identity |
| Artifact | Persisted evidence or output |
| Portfolio Study | Editorial presentation grouping only |

No common framework-level `Study` aggregate, `StudyId`, repository or
cross-workflow lineage is introduced.

### 2. Product language maps to stable technical contracts

`Market & Signal Study` is the product-facing name for authoring and running
the existing technical Signal Research workflow. The selected scope must
always be shown as one of:

- Market Model-only,
- Signal Model-only,
- Market Model and Signal Model.

`Signal Research` remains the technical capability, workflow, package and
compatibility name. Product and reference material must explain the mapping
where users cross from product language into CLI, configuration or API names.

`PredictiveStudySpec` remains a workflow-local existing contract. `Portfolio
Study` must remain qualified and retains the editorial meaning fixed by
ADR-0035.

### 3. Qualified model terminology is required

`Market Model` and `Signal Model` retain the meanings and ownership accepted
by ADR-0006. `Estimator` identifies a statistical or machine-learning
estimator. `View Model` remains presentation terminology.

New user-facing labels and public contract fields must not use bare `model`
when the concrete concept is known. They must use the applicable qualified
term or explicit typed fields.

Current code contracts `ExitModel`, `RiskModel` and
`StrategyModelDefinition` remain unchanged. Maintained explanatory and product
copy may describe their roles as `Exit Policy`, `Risk Policy` and `Strategy
Definition`, while naming the technical identifier when relevant. Introducing
aliases, deprecations or renamed serialized fields requires a separate
contract decision.

### 4. Compatibility identifiers remain stable

This decision does not rename or migrate:

- `SignalResearchDefinitionSpec` or `signal_research.definition.v1`,
- `research_id`, `experiment_id`, `run_id` or existing manifest fields,
- `definition_hash` or run-identity inputs,
- `trading-cli research run signal` or `research.kind: signal`,
- `signal_research` packages and workflow identifiers,
- template locations,
- `user_data/research/market_research/` or other storage paths,
- existing Python classes, protocols or imports.

Historical manifests, configurations, reports, accepted ADRs and archived
planning records are not rewritten. Any future contract or storage rename
requires separate approval, explicit versioning, compatibility readers or
aliases where needed, and preservation of historical hashes and evidence.

### 5. Current reference and product surfaces adopt the vocabulary

A canonical terminology page under `docs/reference/system/` owns the current
definitions and compatibility mapping. Current reference indexes, product
entry points, scoped Workbench copy and CLI help link or conform to it.

Specialist abbreviations are expanded or explained on first use in scoped
user-facing entry points. Technical reference pages may use established
abbreviations after linking to or defining them.

Terminology checks may reject explicitly retired ambiguous product labels but
must allow frozen identifiers and historical material through a documented,
bounded allowlist.

### 6. Catalog identity is a separate increment

The dashboard's inferred `model` display and filter are not corrected by
parsing titles differently. A later Typed Research Catalog increment must
carry explicit research-subject identifiers through the applicable private
and public presentation contracts.

That increment must review the public projection allowlist and ADR-0034,
ADR-0035 and ADR-0042 compatibility constraints. It is outside this decision's
implementation scope.

## Alternatives Considered

### Rename packages, schemas and storage immediately

Rejected. It would turn a language clarification into a breaking migration,
invalidate or fork existing identity semantics, and require multiple readers
to change together.

### Keep one vocabulary for every layer

Rejected. Persisted identifiers and code symbols require stronger stability
than product copy. A documented mapping is clearer and safer than either
freezing ambiguous UI language forever or renaming all contracts at once.

### Make Study a shared domain aggregate

Rejected for this increment. Current evidence supports workflow-local
definitions, experiments and runs, while ADR-0035 deliberately keeps
Portfolio Study editorial. A shared aggregate would require new identity,
ownership and persistence semantics not justified by the terminology problem.

### Treat the issue as documentation cleanup only

Rejected. Without a binding vocabulary and compatibility boundary, future UI
and API work could reintroduce the same ambiguity or accidentally expand a
copy change into a contract migration.

## Consequences

### Positive

- Product language describes what the user is doing rather than exposing
  historical package names everywhere.
- Accepted Market Model and Signal Model semantics remain stable.
- Definition, experiment, run and artifact gain distinct meanings.
- Future public contracts must carry explicit type information instead of a
  bare `model` field.
- Existing configurations, commands, hashes and artifacts remain compatible.

### Negative

- Product labels and technical identifiers intentionally differ at some
  boundaries and require a documented mapping.
- Some historical terminology remains visible in code, CLI commands and
  storage paths.
- Exit Policy, Risk Policy and Strategy Definition remain explanatory names
  until a separately approved contract increment justifies aliases or
  renames.
- The dashboard catalog ambiguity is identified but not repaired by this
  increment.

## Follow-up

- Implement the approved Terminology Foundation PRD without changing
  versioned contracts.
- Plan Typed Research Catalog before expanding the Workbench run catalog and
  comparison UI.
- Consider code aliases or schema v2 only from demonstrated user or
  integration needs, not as automatic follow-on work.

## References

- [PRD — Terminology Foundation](../product/PRD-terminology-foundation.md)
- [Domain Model](../reference/system/DOMAIN_MODEL.md)
- [Research Methodologies](../reference/workflows/RESEARCH_METHODOLOGIES.md)
- [ADR-0005 — Market Analysis Domain and Taxonomy](ADR-0005-market-analysis-domain-and-taxonomy.md)
- [ADR-0006 — Declarative Market and Signal Models](ADR-0006-declarative-market-and-signal-models.md)
- [ADR-0035 — Complete Public Catalog Publication and Immutable Releases](ADR-0035-complete-public-catalog-publication.md)
- [ADR-0037 — Research Workbench Application Boundary and Control Surface](ADR-0037-research-workbench-application-boundary.md)
- [ADR-0038 — Canonical Signal Research Configuration Schema and Templates](ADR-0038-canonical-signal-research-configuration-and-templates.md)
- [ADR-0042 — Workbench Catalog Index and Comparison Facts](ADR-0042-workbench-catalog-index-and-comparison-facts.md)
- [PRB-015 — Architecture Documents Require a Formal Consistency Check](../planning/registries/prb-013-016.md#prb-015)
- [TD-010 — Documentation Consistency Is Reviewed Manually Before Automation](../planning/registries/td-009-012.md#td-010)
