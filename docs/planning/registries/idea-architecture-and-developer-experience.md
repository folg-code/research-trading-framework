# Architecture and Developer Experience — idea entries

Return to the [Idea Inbox index](../IDEA_INBOX.md).

# 4. Architecture and Developer Experience

<a id="idea-001"></a>
## IDEA-001 — Visual Dependency Graph Explorer

```text
Status: INBOX
Category: Developer Experience
Added: 2026-06-19
```

### Summary

Provide a visual representation of:

- Market Analysis dependencies,
- model expression trees,
- reused nodes,
- cache hits,
- execution order.

### Potential Value

Could make large analytical compositions easier to understand and debug.

### Main Questions

- Is textual graph inspection sufficient initially?
- Should this be a CLI, notebook view or web UI?
- Can visualization remain independent from engine semantics?

### Dependencies

- stable dependency graph,
- stable node identity,
- result lineage.

### Promotion Criteria

Promote only after real graphs become difficult to inspect using text output.

---

<a id="idea-002"></a>
## IDEA-002 — Remote Component Registry

```text
Status: DEFERRED
Category: Architecture
Added: 2026-06-19
```

### Summary

Distribute framework or private component packages through a remote registry.

### Potential Value

Could support multiple machines, teams and controlled component releases.

### Main Questions

- Is a Python package index sufficient?
- How would private components be authenticated?
- How are compatibility and signatures verified?

### Dependencies

- mature local component lifecycle,
- stable component manifest,
- multiple independent environments.

### Promotion Criteria

A demonstrated need to share versioned components across machines or teams.

---

<a id="idea-003"></a>
## IDEA-003 — Dedicated Feature Store

```text
Status: DEFERRED
Category: Data / Market Analysis
Added: 2026-06-19
```

### Summary

Introduce a dedicated offline/online store for Market Analysis results.

### Potential Value

Could support large-scale reuse across Research and Strategy Execution.

### Main Questions

- Are Parquet and local caches insufficient?
- Is online/offline consistency a demonstrated problem?
- What operational cost is acceptable?

### Dependencies

- significant repeated feature reuse,
- live runtime requirements,
- measured storage/query bottlenecks.

### Status Note (2026-08-25)

Phase 10 Predictive Research (ROADMAP §13A) persists a feature matrix per study rather than
introducing a shared store. If repeated studies show heavy duplicated feature computation, that
measurement becomes the first concrete evidence for this idea.

### Promotion Criteria

Local cache and Parquet architecture demonstrably fail required scale or parity.

---

<a id="idea-004"></a>
## IDEA-004 — Declarative Workflow Graph Editor

```text
Status: DEFERRED
Category: Developer Experience
Added: 2026-06-19
```

### Summary

Create a visual editor for Research or Strategy Execution workflow configuration.

### Potential Value

Could lower configuration complexity for non-code users.

### Risks

May incorrectly imply that workflows and domains are arbitrary graph nodes.

### Promotion Criteria

Stable configuration schemas and demonstrated user need.

---
