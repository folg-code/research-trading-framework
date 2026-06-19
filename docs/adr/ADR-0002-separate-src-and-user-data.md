# ADR-0002 — Separate `src` and `user_data`

## Status

ACCEPTED

## Context

The framework must support proprietary user-owned components, models, datasets and research outputs without mixing them into framework source code.
A clear public/private boundary is required for maintainability, security and licensing.

## Decision

Separate repository areas:

```text
src/trading_framework/   # framework code (versioned)
user_data/               # user-owned content (gitignored except README)
```

Rules:

- `src/trading_framework/` must not import concrete `user_data/` modules,
- proprietary logic stays in `user_data/`,
- framework exposes contracts and discovery mechanisms for user content.

## Consequences

### Positive

- framework code remains reusable and auditable,
- proprietary strategies and datasets stay outside version control,
- boundary can be enforced with architecture tests.

### Negative

- discovery and loading contracts must be designed explicitly,
- users must manage their own `user_data/` layout.

## References

- `user_data/README.md`
- `tests/unit/test_architecture_boundaries.py`
- `docs/architecture/ARCHITECTURE_FOUNDATIONS_UPDATED.md`
