# User Data

This directory is **user-owned** and excluded from version control except this README.

## Purpose

`user_data/` stores proprietary configuration, components, models, datasets and research outputs.
Framework code in `src/` must not import concrete modules from `user_data/`.

## Expected Layout

```text
user_data/
├── config/        # user configuration files
├── components/    # working Market Analysis components
├── models/        # working model definitions
├── datasets/      # local dataset working copies
└── research/      # research runs and outputs
```

## Rules

- do not commit credentials, API keys or proprietary strategies,
- do not place secrets in tracked files,
- use published framework contracts for discovery and loading,
- keep proprietary logic out of `src/trading_framework/`.

## Related Documents

- `docs/planning/ROADMAP.md`
- `docs/adr/ADR-0002-separate-src-and-user-data.md`
- `AGENTS.md`
