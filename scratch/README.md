# scratch/

Local-only workspace for ephemeral logs, bench dumps, and one-off experiments.

```text
scratch/
  *.log
  *.py          # throwaway probes (not framework code)
```

## Rules

- Everything under this directory is **gitignored** except this README.
- Prefer `scratch/` over root `.tmp_*` filenames (deprecated).
- Do not put credentials, `user_data/` datasets, or durable research results here.
- Durable CLIs belong in `scripts/`; durable docs in `docs/`.
