# ADR-0022 — Repository Top-Level Layout

## Status

ACCEPTED

## Context

Sprint 028 introduced `apps/dashboard` as a separate deployable consumer of
research artifacts. The repository also grew `deploy/` (AWS containers),
`demo/output/` (generated HTML), and local-only ops folders. Vision §10.1 and
related docs still described only `src/`, `user_data/`, `tests/`, `docs/`, and
`scripts/`, which caused conflicting guidance for contributors and agents
(PRB-015).

ADR-0001 keeps a modular monolith under `src/trading_framework/`. ADR-0002 keeps
`user_data/` outside the framework package. Neither ADR defines where UI apps,
deploy assets, or CLI scripts live relative to those boundaries.

## Decision

Adopt the following **top-level layout** and ownership rules:

```text
trading-research-framework/
├── src/trading_framework/   # modular monolith (ADR-0001)
├── apps/                    # deployable consumers (UI / ops frontends)
│   └── <app>/               # own pyproject.toml; co-located deploy/ OK
├── scripts/                 # thin CLIs over application use cases
├── deploy/                  # containers / infra-as-code / local AWS runbook
├── tests/                   # framework test suite
├── docs/                    # vision, reference, planning, adr, agents, onboarding
├── demo/output/             # generated demo artifacts (not docs/)
├── user_data/               # user-owned content (ADR-0002; gitignored)
├── pyproject.toml           # root package + uv workspace root
└── README.md
```

### Rules

1. **`src/trading_framework/`** never imports `user_data/` or `apps/`.
2. **`apps/*`** must not import research engines, strategy/robustness application
   engines, execution, or infrastructure providers/importers (see Sprint 029
   Wave 0 / D-S028-06 generalization). Apps read mounted storage and may keep
   local presentation contracts.
3. **`scripts/`** stay thin: parse args, call application APIs, write outputs.
4. **`deploy/`** owns shared/runtime packaging (AWS workers, status API, local
   AWS runbook). App-specific Compose/Docker may stay under `apps/<app>/deploy/`.
5. **Do not commit** build wheels (`dist/`), scratch `.tmp_*`, credentials, or
   multi-MB generated HTML under `docs/`. Prefer `demo/output/` or ephemeral paths.
6. **`packages/`** for shared cross-app DTOs is **deferred** until a second
   consumer needs them.
7. Deep reshuffles inside domain packages under `src/trading_framework/` are
   **out of scope** for layout hygiene; trigger separately (e.g. Phase 4B / TD-003).

## Consequences

### Positive

- one authoritative map for humans and agents,
- room for more `apps/*` without stuffing UI into the monolith,
- clearer separation of CLI vs container vs framework code,
- hygiene rules reduce repo noise and stale doc artifacts.

### Negative

- docs and CI must mention multiple packages (workspace),
- contributors must learn the apps import boundary.

## References

- `docs/adr/ADR-0001-modular-monolith.md`
- `docs/adr/ADR-0002-separate-src-and-user-data.md`
- `docs/planning/sprints/SPRINT_029.md`
- `docs/planning/sprints/S029_WAVE0_DECISIONS.md`
- `docs/reference/MODULE_MAP.md`
- `docs/vision/ARCHITECTURE_TECHNICAL_UPDATED.md` §10.1
