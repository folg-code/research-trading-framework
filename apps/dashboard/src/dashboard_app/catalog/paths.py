"""Research storage path helpers used by the dashboard (read-only).

Mirrors the workspace layout from the trading framework without importing it.
"""

from __future__ import annotations

from pathlib import Path


def research_root(storage_root: Path) -> Path:
    """Return ``<storage_root>/research``."""
    return storage_root / "research"


def market_research_runs_dir(storage_root: Path) -> Path:
    """Return Signal / Market Research run envelopes directory."""
    return research_root(storage_root) / "market_research" / "runs"


def strategy_research_runs_dir(storage_root: Path) -> Path:
    """Return Strategy Research run envelopes directory."""
    return research_root(storage_root) / "strategy_research" / "runs"


def robustness_experiments_dir(storage_root: Path) -> Path:
    """Return Strategy Robustness experiment directories."""
    return research_root(storage_root) / "strategy_robustness" / "experiments"


def run_manifest_path(run_dir: Path) -> Path:
    """Return ``manifest.json`` under a run or experiment directory."""
    return run_dir / "manifest.json"
