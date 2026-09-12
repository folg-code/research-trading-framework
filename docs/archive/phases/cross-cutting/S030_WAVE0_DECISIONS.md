# Sprint 030 — Wave 0 Decisions

Binding decisions for Repository Navigability Hygiene. Date: 2026-07-18.

---

## D-S030-01 — Track choice

**Decision:** Next sprint is **navigability hygiene** (scratch + IDE excludes +
`artifacts/demo/`), not Phase 4B and not a full `ops/` regroup of `deploy/`.

---

## D-S030-02 — Local scratch convention

**Decision:** Ephemeral agent/bench logs and one-off scripts go under:

```text
scratch/
```

Root `.tmp_*` remains gitignored for compatibility but is **deprecated**.
`scratch/` is fully gitignored except a tracked `README.md`.

---

## D-S030-03 — Generated demos under artifacts/

**Decision:** Move `demo/` → `artifacts/demo/`.

```text
artifacts/demo/output/   # generated HTML (gitignored)
scripts/demo/            # generators stay under scripts/
```

`deploy/` stays top-level (ADR-0022). Do not nest under `ops/` in this sprint.

---

## D-S030-04 — IDE visibility

**Decision:** Default VS Code / Cursor excludes hide local noise:

`.venv`, tool caches, `scratch/`, `user_data/`, `dist/`, `.idea`, `.agents`, `.codex`

Tracked first-class and support dirs remain visible.
