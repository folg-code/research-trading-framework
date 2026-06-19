# Trading Research Framework

Modular quantitative trading research platform in Python.

The framework separates market data, market analysis, strategy definition, research and execution into independent domains with explicit contracts and reproducibility requirements.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)

## Install

```bash
uv sync --locked --dev
```

## Quality Checks

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
uv run pytest
```

## Project Layout

```text
src/trading_framework/   # framework code
user_data/             # user-owned config, models and data (gitignored)
tests/                 # unit, integration and e2e tests
docs/                  # architecture, planning and ADRs
```

## Documentation

- Roadmap: `docs/planning/ROADMAP.md`
- Current status: `docs/planning/CURRENT_STATUS.md`
- Sprint 001: `docs/planning/sprints/SPRINT_001.md`
- Architecture: `docs/architecture/`
- AI agent entry point: `AGENTS.md`

## Configuration

Minimal framework configuration can be loaded from TOML:

```toml
environment = "dev"
log_level = "INFO"
```

```python
from pathlib import Path

from trading_framework.config import load_framework_config

config = load_framework_config(Path("user_data/config/framework.toml"))
```

## License

Private research project.
