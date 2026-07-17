"""Migrate a legacy flat storage root into the canonical user_data workspace layout.

Legacy layouts mixed market facts and research runs under one directory, for example::

    user_data/storage_nq_half_year/
      metadata/
      normalized/
      continuous/
      <signal_run_id>/
      strategy_research/<run_id>/
      robustness_experiments/<experiment_id>/

Canonical workspace::

    user_data/
      market_data/
        raw/
        metadata/
        normalized/
        continuous/
      research/
        market_research/runs/
        market_research/experiments/
        strategy_research/runs/
        strategy_robustness/experiments/

This script only moves local files. It does not change git history.

Examples::

    # Dry-run: show planned moves from the half-year tree into user_data/
    uv run python scripts/ops/migrate_user_data_workspace.py \\
      --workspace user_data \\
      --from-storage user_data/storage_nq_half_year \\
      --dry-run

    # Apply migration, then optionally archive leftover legacy roots
    uv run python scripts/ops/migrate_user_data_workspace.py \\
      --workspace user_data \\
      --from-storage user_data/storage_nq_half_year

    uv run python scripts/ops/migrate_user_data_workspace.py \\
      --workspace user_data \\
      --relocate-raw-market-data
"""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

_HEX_RUN_ID = re.compile(r"^[a-f0-9]{16}$")


class _MigrationFs:
    """Filesystem facade that tracks planned paths during dry-run."""

    def __init__(self, *, dry_run: bool) -> None:
        self.dry_run = dry_run
        self._planned: set[Path] = set()

    def exists(self, path: Path) -> bool:
        return path.exists() or path.resolve() in self._planned

    def mark(self, path: Path) -> None:
        self._planned.add(path.resolve())
        current = path.resolve()
        while True:
            parent = current.parent
            if parent == current:
                break
            self._planned.add(parent)
            current = parent


def _move(src: Path, dest: Path, *, fs: _MigrationFs) -> None:
    if not src.exists():
        return
    print(f"MOVE  {src} -> {dest}")
    if fs.dry_run:
        fs.mark(dest)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        msg = f"destination already exists: {dest}"
        raise FileExistsError(msg)
    shutil.move(str(src), str(dest))


def _merge_tree(src: Path, dest: Path, *, fs: _MigrationFs) -> None:
    """Move src into dest when dest is missing; merge directories when both exist."""
    if not src.exists():
        return
    if not fs.exists(dest):
        _move(src, dest, fs=fs)
        return
    if not src.is_dir():
        msg = f"cannot merge non-directory collision: {src} -> {dest}"
        raise FileExistsError(msg)
    for child in sorted(src.iterdir()):
        _merge_tree(child, dest / child.name, fs=fs)
    if not fs.dry_run and src.exists() and not any(src.iterdir()):
        src.rmdir()


def migrate_storage_root(
    *,
    workspace: Path,
    legacy_storage: Path,
    fs: _MigrationFs,
) -> None:
    """Move one legacy storage root into the workspace layout."""
    market = workspace / "market_data"
    research = workspace / "research"

    _merge_tree(legacy_storage / "metadata", market / "metadata", fs=fs)
    _merge_tree(legacy_storage / "normalized", market / "normalized", fs=fs)
    _merge_tree(legacy_storage / "continuous", market / "continuous", fs=fs)

    strategy_src = legacy_storage / "strategy_research"
    if strategy_src.exists():
        for run_dir in sorted(strategy_src.iterdir()):
            if run_dir.is_dir():
                _move(
                    run_dir,
                    research / "strategy_research" / "runs" / run_dir.name,
                    fs=fs,
                )

    robustness_src = legacy_storage / "robustness_experiments"
    if robustness_src.exists():
        for exp_dir in sorted(robustness_src.iterdir()):
            if exp_dir.is_dir():
                _move(
                    exp_dir,
                    research / "strategy_robustness" / "experiments" / exp_dir.name,
                    fs=fs,
                )

    family_src = legacy_storage / "signal_research_experiments"
    if family_src.exists():
        for exp_dir in sorted(family_src.iterdir()):
            if exp_dir.is_dir():
                _move(
                    exp_dir,
                    research / "market_research" / "experiments" / exp_dir.name,
                    fs=fs,
                )

    for child in sorted(legacy_storage.iterdir()):
        if not child.is_dir():
            continue
        if child.name in {
            "metadata",
            "normalized",
            "continuous",
            "strategy_research",
            "robustness_experiments",
            "signal_research_experiments",
            "market_data",
            "research",
            "raw",
        }:
            continue
        if _HEX_RUN_ID.match(child.name) or (child / "manifest.json").is_file():
            _move(
                child,
                research / "market_research" / "runs" / child.name,
                fs=fs,
            )


def relocate_raw_market_data(*, workspace: Path, fs: _MigrationFs) -> None:
    """Move product/provider archives under market_data/ into market_data/raw/."""
    market = workspace / "market_data"
    raw = market / "raw"
    if not market.exists() and not fs.exists(market):
        return
    reserved = {"raw", "metadata", "normalized", "continuous"}
    children = sorted(market.iterdir()) if market.exists() else []
    for child in children:
        if not child.is_dir() or child.name in reserved:
            continue
        _move(child, raw / child.name, fs=fs)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace",
        type=Path,
        required=True,
        help="Canonical workspace root (usually user_data)",
    )
    parser.add_argument(
        "--from-storage",
        type=Path,
        action="append",
        default=[],
        help="Legacy storage root to migrate (repeatable)",
    )
    parser.add_argument(
        "--relocate-raw-market-data",
        action="store_true",
        help="Move market_data/<product>/... archives into market_data/raw/",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned moves without changing the filesystem",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    workspace = args.workspace.resolve()
    fs = _MigrationFs(dry_run=bool(args.dry_run))

    if not fs.dry_run:
        (workspace / "market_data" / "raw").mkdir(parents=True, exist_ok=True)
        (workspace / "research" / "market_research" / "runs").mkdir(parents=True, exist_ok=True)
        (workspace / "research" / "strategy_research" / "runs").mkdir(parents=True, exist_ok=True)
        (workspace / "research" / "strategy_robustness" / "experiments").mkdir(
            parents=True,
            exist_ok=True,
        )
    else:
        fs.mark(workspace / "market_data" / "raw")
        fs.mark(workspace / "research" / "market_research" / "runs")
        fs.mark(workspace / "research" / "strategy_research" / "runs")
        fs.mark(workspace / "research" / "strategy_robustness" / "experiments")

    for legacy in args.from_storage:
        legacy_path = legacy.resolve()
        if not legacy_path.exists():
            print(f"SKIP  missing legacy storage: {legacy_path}")
            continue
        print(f"MIGRATE {legacy_path} -> {workspace}")
        migrate_storage_root(
            workspace=workspace,
            legacy_storage=legacy_path,
            fs=fs,
        )

    if args.relocate_raw_market_data:
        print(f"RELOCATE raw archives under {workspace / 'market_data'}")
        relocate_raw_market_data(workspace=workspace, fs=fs)

    if fs.dry_run:
        print("Dry-run complete; no files were moved.")
    else:
        print("Migration complete.")
        print("Review empty legacy storage_* directories and delete or archive them manually.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
