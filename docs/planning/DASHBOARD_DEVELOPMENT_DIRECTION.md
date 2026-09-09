# Portfolio Dashboard Development Direction

```text
Status: DRAFT
Discovery: maintainer Q&A completed 2026-09-09
Owner: Planning
Scope: public portfolio dashboard direction, not an approved sprint scope
```

## 1. Purpose

This note defines the product direction for the public portfolio dashboard.
It supersedes the earlier dashboard note's narrower emphasis on ranking and
run-detail improvements while preserving its read-only boundary.

The dashboard should present the project as:

```text
Portfolio-grade software product
+ research methodology
+ persisted evidence
```

The primary audience is a software engineer or developer who is not expected
to have specialist quant knowledge. The project should nevertheless provide
credible evidence of software engineering, data science, quant engineering,
development and research capability.

The core story is:

```text
What was built and why
  -> how the architecture and workflows operate
  -> which persisted artifacts demonstrate the result
```

The project should speak for itself. A prominent author biography or personal
sales narrative is not part of the direction.

## 2. Product Boundary

The portfolio dashboard is a public, English-language, desktop-first,
read-only presentation surface. It is independent of the local Research
Workbench product direction and PRD.

The dashboard does not:

- acquire or edit market data;
- configure, start, cancel or manage research work;
- edit framework configuration or artifacts;
- control a paper or live strategy;
- calculate research metrics, classifications or verdicts;
- make market forecasts or publish trade ideas;
- present simulation results as evidence of a live trading edge;
- sell strategies or foreground profitability;
- replace the repository's reference documentation, ADRs or source code.

Metrics and PnL may be shown when they are necessary experiment or simulation
diagnostics. They must remain framed by their persisted assumptions and must
not become a marketing claim.

## 3. Architecture Narrative

The dashboard must not imply one mandatory end-to-end pipeline. Market Data,
Signal Research, Strategy Research, Robustness Research, Predictive Research
and Strategy Execution are separate workflows. Market Analysis is a shared
domain capability rather than a seventh workflow.

A principal architecture advantage to communicate is that independent
workflows share stable domain objects and contracts without sharing mandatory
workflow state.

The overview should show this at a deliberately small conceptual scale. Each
workflow page may then explain:

```text
inputs
shared domain objects and contracts
workflow-specific processing
persisted outputs
```

Do not turn the overview into a class diagram. Only show shared objects when
the relationship remains readable. A methodology page may describe how
knowledge can move between independent processes, but the public site must not
invent an end-to-end worked example until a real artifact has passed through
that path.

## 4. Information Architecture

### 4.1 Home

The recommended home-page sequence is:

1. concise product thesis;
2. shared-domain and architecture map;
3. entry points to the six workflows;
4. two or three manually featured studies;
5. two or three recent Research & Engineering Notes;
6. entry to the complete research catalog.

The home page is a map of the product, not a forced wizard and not a dump of
run metrics.

### 4.2 Workflow pages

Each workflow should use a recognizable structure:

1. Purpose — what problem it addresses and why it exists;
2. Architecture — how it uses shared objects and boundaries;
3. Pipeline — how this workflow operates;
4. Methodology — the current research or operational method;
5. Engineering evidence — the important contracts, tests and failure modes;
6. Representative results — simplified views of selected persisted evidence;
7. Explore Evidence — the full technical artifact view.

The structure is a consistency aid, not a requirement for every page to have
the same visual layout.

### 4.3 Supporting sections

- **Research Catalog** groups results by study before exposing experiments and
  individual runs.
- **Engineering** presents cross-cutting case studies such as domain
  boundaries, reproducibility, data lineage, read-only publication and
  dry-run reliability. Workflow pages retain shorter contextual engineering
  evidence blocks.
- **Future Direction** develops the ideas that are only summarized by status
  markers elsewhere.
- **Research & Engineering Notes** is a chronological journal for meaningful
  methodology changes, architecture decisions, negative results and changes
  of direction. It is not an automatic sprint changelog.

## 5. Progressive Disclosure

Content should have three levels:

```text
accessible explanation
  -> full workflow and methodology narrative
  -> technical evidence and provenance
```

The default narrative should be understandable by a general software
developer. Diagrams and concrete examples may appear immediately. Equations,
pseudocode, configuration fragments and detailed schemas should be available
as optional technical detail. The repository remains the destination for the
deepest contracts, ADRs and implementation detail.

## 6. Methodology and Publications

Methodology publications and result artifacts have different responsibilities:

```text
Publications explain the current methodology.
The dashboard presents persisted artifacts read-only.
```

A publication must not become a hand-written interpretation of a particular
artifact. A result or study page links to the relevant current methodology.
The methodology is maintained as living content rather than frozen separately
for every historical run.

Workflow methodology pages form an evolving handbook. Research & Engineering
Notes preserve the chronological story of meaningful changes and link back to
the current canonical workflow or methodology page. Replaced content is marked
`ARCHIVED` rather than silently presented as current.

Public content uses four explicit maturity labels:

```text
AS BUILT
IN DEVELOPMENT
FUTURE IDEAS
ARCHIVED
```

Future ideas may appear with clear status markers on architecture and workflow
maps and should be explained more fully on the Future Direction page.

## 7. Results and Analytical Views

The analytical layer demonstrates experiment quality and research discipline;
it does not perform market commentary or present the author as a discretionary
market analyst or trader.

Useful analytical subjects include:

- data quality;
- experiment construction;
- comparison with a declared baseline;
- stability across persisted folds, periods or assumptions;
- reproducibility and provenance.

The UI may filter, sort, group and visualize persisted facts. Any new metric,
quality classification or verdict must be produced by the owning research or
analytics layer and persisted before the dashboard displays it.

### 7.1 Simplified result view

Each workflow receives a purpose-built simplified view rather than one generic
renderer. The view should experimentally try to answer:

```text
What was studied?
Against what comparison or assumptions?
What result was persisted?
What limitations or warnings were persisted?
```

Two or three workflow-appropriate charts may remain visible because visual
evidence is valuable in a portfolio. Definitions and neutral explanations of
metrics are allowed; the dashboard must not add an artifact-specific verdict
or conclusion.

### 7.2 Explore Evidence

The existing technical views remain available as the deepest dashboard layer.
They may contain the complete charts, tables, manifests, warnings, provenance
and links to frozen reports. New simplified views are additive and may be
introduced workflow by workflow.

### 7.3 Comparisons

The dashboard should identify material compatibility differences between
runs. It may allow inspection of incompatible runs as long as it clearly
states the differences; it does not need to block the comparison or declare a
universal winner.

## 8. Catalog and Public Projection

The public catalog should automatically include every safely publishable run,
including negative, inconclusive, incomplete and unsupported results when
their identity can be established safely. Negative findings are first-class
research evidence, not material hidden outside the main catalog.

The catalog groups runs by study and then exposes experiments and individual
runs. A small set of studies may be featured manually on the home page.

Catalog filters may use persisted facts such as workflow, dataset, instrument,
date, experiment kind and an upstream verdict. If no classification artifact
exists, the dashboard presents an explicit absence such as `NO VERDICT`; it
must not infer one from displayed metrics.

Automatic discovery does not mean exposing the mounted workspace directly.
Public visibility must use an allowlisted, sanitized projection of artifacts
and fields. Internal paths, private configuration, strategy source, model
binaries, infrastructure identifiers, operational logs, credentials and other
private `user_data` content remain excluded by default.

## 9. Strategy Execution View

The public Strategy Execution surface shows only the current live-paper
status. It does not provide a public archive of completed sessions and never
provides a command surface.

The page must retain unmistakable labelling equivalent to:

```text
LIVE MARKET DATA / SIMULATED EXECUTION / NO REAL ORDERS
```

If the current status endpoint is unavailable or stale, the page shows that
state explicitly. It must not present an old snapshot as current activity.

## 10. Interaction, URLs and Presentation

The dashboard is desktop-first. The expected interaction set is deliberately
small:

- filters;
- tooltips;
- tabs;
- run selection;
- drill-down into simplified and technical evidence.

Saved workspaces, user-composed dashboards, advanced chart drawing and saved
filter state are not required.

Stable direct URLs are recommended for the home page, architecture,
workflow pages, methodology publications and study pages. Individual raw runs
may remain selections inside a study for the first version. Filters, tabs and
other transient interaction state do not need shareable URLs.

Search-engine optimization is not a requirement. A coherent theme and good
components are sufficient; the dashboard does not require a bespoke marketing
site identity. These requirements remain compatible with Streamlit for the
next increments, so a frontend migration is not part of this direction.

## 11. Delivery Direction

Whether Phase 16D requires one or several sprints should follow from the
approved work breakdown rather than be decided in this direction note.

The recommended first complete vertical slice is:

```text
Overview
  -> shared-object architecture
  -> Signal / Predictive Research context
  -> Signal Quality study
  -> simplified result
  -> Explore Evidence
```

This slice can use the artifacts produced by Phase 16A–16C and establish a
reusable content and view pattern. Other workflows may first receive improved
narrative pages leading to their current technical views; their simplified
result views can then be added iteratively.

All scope and sprint boundaries remain subject to evidence-based planning.
This document does not open or approve a sprint.

## 12. Success Test

The first portfolio release succeeds when a software developer without quant
specialization can, after a short visit:

1. explain what the project is and why it exists;
2. recognize that shared domain objects support multiple independent
   workflows;
3. describe at least two workflows at a useful high level;
4. distinguish current, in-development and future capabilities;
5. navigate from methodology to a concrete persisted research artifact;
6. move from a simplified result to its technical evidence without mistaking
   simulation for live trading performance.

## 13. Open Planning Questions

Before a sprint is approved, planning still needs to determine:

- the exact first-sprint boundary after inventorying reusable UI and content;
- the public-projection manifest or equivalent allowlist contract;
- the study identity and grouping contract used by the catalog;
- which Phase 16A–16C artifacts can support the first simplified view without
  dashboard-side derivation;
- the concrete content inventory for AS BUILT workflow pages;
- the feasibility and exact shape of stable study URLs in the retained stack;
- visual acceptance examples for the shared-object map and workflow template.
