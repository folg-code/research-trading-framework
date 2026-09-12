# Infrastructure and Interfaces — idea entries

Return to the [Idea Inbox index](../IDEA_INBOX.md).

# 9. Infrastructure and Interfaces

<a id="idea-024"></a>
## IDEA-024 — Web Research Dashboard

```text
Status: PARTIALLY_IMPLEMENTED
Category: Interface
Added: 2026-06-19
```

### Review (2026-09-12)

The read-only Streamlit dashboard now publishes a sanitized research catalog, workflow evidence, selected studies and reports. It does not provide a complete local data/run exploration workbench or unrestricted dataset browsing. See [Dashboard Application](../../reference/modules/DASHBOARD_APPLICATION.md) and the remaining [Research Application vision](../../vision/RESEARCH_APPLICATION_PRODUCT_VISION.md).

### Summary

Browse datasets, runs, rankings, families and reports through a web UI.

### Promotion Criteria

CLI and stored schemas become stable enough to avoid UI-driven domain design.

---

<a id="idea-025"></a>
## IDEA-025 — Notebook Helper Package

```text
Status: INBOX
Category: Developer Experience
Added: 2026-06-19
```

### Summary

Provide safe notebook helpers for querying published datasets and Research Datasets.

### Important Rule

Reusable business logic must not remain only in notebooks.

---

<a id="idea-026"></a>
## IDEA-026 — Local Research API

```text
Status: DEFERRED
Category: Interface
Added: 2026-06-19
```

### Review (2026-09-12)

The narrow read-only dry-run status HTTP endpoint is an operational view, not a general local Research API. This idea remains deferred; see [Strategy Execution](../../reference/workflows/STRATEGY_EXECUTION.md).

### Summary

Expose framework capabilities through a local REST or WebSocket API.

### Promotion Criteria

A concrete external consumer requires it.

The domain must remain independent from FastAPI or another web framework.

---
