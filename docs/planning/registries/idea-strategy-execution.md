# Strategy Execution — idea entries

Return to the [Idea Inbox index](../IDEA_INBOX.md).

# 8. Strategy Execution

<a id="idea-020"></a>
## IDEA-020 — Unified Replay/Paper/Live Strategy Runtime

```text
Status: INBOX
Category: Strategy Execution
Added: 2026-06-19
```

### Summary

Use one runtime contract with mode-specific market feeds and broker adapters.

### Potential Value

Improves parity and reduces duplicated strategy logic.

### Risks

May create a god-object runtime if boundaries are not explicit.

### Promotion Criteria

Strategy Model and Execution contracts are stable.

---

<a id="idea-021"></a>
## IDEA-021 — Multi-Account Execution Coordinator

```text
Status: DEFERRED
Category: Strategy Execution
Added: 2026-06-19
```

### Summary

Coordinate one or more Strategy Models across multiple broker or prop-firm accounts.

### Dependencies

- reliable single-account execution,
- account isolation,
- reconciliation,
- allocation policies,
- operational monitoring.

### Promotion Criteria

Single-account live execution is validated.

---

<a id="idea-022"></a>
## IDEA-022 — Operational Risk Policy Engine

```text
Status: INBOX
Category: Strategy Execution
Added: 2026-06-19
```

### Summary

Configure reusable operational controls such as:

- daily loss limit,
- account drawdown,
- duplicate-order prevention,
- stale-data protection,
- connection-health rules,
- kill switch.

### Important Rule

This remains separate from the Strategy Domain Risk Model.

---

<a id="idea-023"></a>
## IDEA-023 — Execution Incident Timeline

```text
Status: INBOX
Category: Observability
Added: 2026-06-19
```

### Summary

Create an audit view combining:

- market events,
- strategy decisions,
- risk decisions,
- commands,
- broker acknowledgements,
- fills,
- reconciliation incidents.

### Promotion Criteria

Execution event and persistence contracts are stable.

---
