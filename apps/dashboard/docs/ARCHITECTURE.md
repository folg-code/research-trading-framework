# Public architecture (one-pager)

Short map of the Trading Research Framework for dashboard visitors. Deeper contracts live in
`docs/vision/` and `docs/reference/` in the repository.

## What this system is

A modular Python platform for **market-data processing**, **declarative market/signal models**,
**strategy backtesting**, **robustness analysis**, and **live paper execution** on AWS.

This Streamlit app is a **read-only analytics surface**. It does not run research engines and does
not submit exchange orders.

## Three independent capabilities

```text
                       Shared definitions
              Market / Models / Time / Data contracts
                              │
             ┌────────────────┼────────────────┐
             │                │                │
             ▼                ▼                ▼
      Signal Research   Strategy Research   Strategy Execution
```

- Signal research can run without strategy research.
- Strategy research can run without a prior signal-research run.
- Live/paper execution does **not** depend on research rankings or dashboard analytics.

## Hard boundaries

| Boundary | Rule |
|----------|------|
| `src/` vs `user_data/` | Framework code stays in `src/`; datasets, runs, and local config stay in user space |
| Apps | `apps/dashboard` consumes persisted artifacts and a read-only status API — no research engine imports |
| Strategies | Stateless strategy contracts; runtime owns lifecycle and persistence |
| Time | UTC internally; no naive datetimes in domain logic |
| Secrets | Public demo uses public market data only — no exchange API keys for dry-run |

## Live paper path (AWS)

```text
Exchange public feed
  → ECS dry-run worker (framework runtime + paper strategy)
  → DynamoDB execution STATE (bounded read model, TTL)
  → read-only status API
  → Live Paper page (RuntimeHealth + feed fields)
```

Operators distinguish **process heartbeat** from **market-feed health** (`RUNNING` / `DEGRADED` /
`STALE` / `STOPPED` / `FAILED`). See `docs/reference/AWS_BTC_FUTURES_DRY_RUN.md`.

## Where to go next

| Need | Location |
|------|----------|
| Clone / install / modules | [GitHub README](https://github.com/folg-code/research-trading-framework) |
| Architecture foundations | `docs/vision/ARCHITECTURE_FOUNDATIONS_UPDATED.md` |
| Dashboard ops | `apps/dashboard/docs/RUNBOOK.md` |
| Live dry-run ops | `docs/reference/AWS_BTC_FUTURES_DRY_RUN.md` |
