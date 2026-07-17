"""Tests for the user_data workspace migration helper."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.ops.migrate_user_data_workspace import (
    _MigrationFs,
    migrate_storage_root,
    relocate_raw_market_data,
)


def test_migrate_storage_root_moves_market_and_research(tmp_path: Path) -> None:
    legacy = tmp_path / "storage_legacy"
    (legacy / "metadata" / "NQ.c.0").mkdir(parents=True)
    (legacy / "metadata" / "NQ.c.0" / "meta.json").write_text("{}", encoding="utf-8")
    (legacy / "normalized" / "NQ.c.0").mkdir(parents=True)
    (legacy / "normalized" / "NQ.c.0" / "bars.parquet").write_bytes(b"parquet")
    (legacy / "continuous" / "schedules").mkdir(parents=True)
    (legacy / "strategy_research" / "run-a").mkdir(parents=True)
    (legacy / "strategy_research" / "run-a" / "manifest.json").write_text(
        json.dumps({"run_id": "run-a"}),
        encoding="utf-8",
    )
    (legacy / "robustness_experiments" / "exp-1").mkdir(parents=True)
    signal_run = legacy / "abcdef0123456789"
    signal_run.mkdir()
    (signal_run / "manifest.json").write_text(
        json.dumps({"research_id": "demo"}),
        encoding="utf-8",
    )

    workspace = tmp_path / "user_data"
    migrate_storage_root(
        workspace=workspace,
        legacy_storage=legacy,
        fs=_MigrationFs(dry_run=False),
    )

    assert (workspace / "market_data" / "metadata" / "NQ.c.0" / "meta.json").is_file()
    assert (workspace / "market_data" / "normalized" / "NQ.c.0" / "bars.parquet").is_file()
    assert (workspace / "market_data" / "continuous" / "schedules").is_dir()
    assert (
        workspace / "research" / "strategy_research" / "runs" / "run-a" / "manifest.json"
    ).is_file()
    assert (workspace / "research" / "strategy_robustness" / "experiments" / "exp-1").is_dir()
    assert (
        workspace / "research" / "market_research" / "runs" / "abcdef0123456789" / "manifest.json"
    ).is_file()


def test_relocate_raw_market_data_moves_product_archives(tmp_path: Path) -> None:
    workspace = tmp_path / "user_data"
    archive = workspace / "market_data" / "NQ" / "databento" / "batch"
    archive.mkdir(parents=True)
    (archive / "file.dbn.zst").write_bytes(b"dbn")
    (workspace / "market_data" / "normalized").mkdir(parents=True)

    relocate_raw_market_data(workspace=workspace, fs=_MigrationFs(dry_run=False))

    relocated = workspace / "market_data" / "raw" / "NQ" / "databento" / "batch" / "file.dbn.zst"
    assert relocated.is_file()
    assert not (workspace / "market_data" / "NQ").exists()
    assert (workspace / "market_data" / "normalized").is_dir()
