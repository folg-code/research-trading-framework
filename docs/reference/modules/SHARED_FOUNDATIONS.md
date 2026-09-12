# Shared foundations — implementation map

This page records the existing packages and entry points for shared foundations. Start with the [module map](../system/MODULE_MAP.md) for system-wide placement and follow the links below for contracts and workflows.

## Packages and entry points

### `core/`

**Responsibility**

- shared identifiers,
- base value types,
- framework exceptions,
- profiling primitives.

**Used by**

All domain and application modules.

**Typical paths**

```text
core/
├── identifiers/
├── types/
├── exceptions.py
└── profiling.py
```

---

### `time/`

**Responsibility**

- UTC time representation,
- timeframes,
- trading sessions,
- clock contracts,
- temporal alignment primitives.

**Used by**

- `market/`,
- `market_analysis/`,
- `research/`,
- `execution/`.

---

### `config/`

**Responsibility**

- framework configuration loading,
- runtime path configuration,
- environment-driven settings.

**Used by**

Application entry points and runtime assembly.

---
