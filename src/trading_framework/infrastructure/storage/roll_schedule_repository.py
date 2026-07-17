"""Roll schedule repository."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from trading_framework.infrastructure.storage.parquet.roll_schedule_writer import (
    ParquetRollScheduleWriter,
)
from trading_framework.infrastructure.storage.paths import (
    roll_schedule_manifest_path,
    roll_schedule_parquet_path,
    roll_schedule_version_dir,
    roll_schedules_base_dir,
)
from trading_framework.infrastructure.storage.roll_schedule_manifest_store import (
    RollScheduleManifest,
    read_roll_schedule_manifest,
    write_roll_schedule_manifest,
)
from trading_framework.market.continuous.policy import (
    VolumeRthCloseRollPolicy,
)
from trading_framework.market.continuous.schedule import (
    RollSchedule,
)


def allocate_roll_schedule_version(root: Path, *, product: str, policy_slug: str) -> int:
    """Allocate the next roll schedule version for one product and policy."""
    latest = latest_roll_schedule_version(root, product=product, policy_slug=policy_slug)
    return 1 if latest is None else latest + 1


def latest_roll_schedule_version(root: Path, *, product: str, policy_slug: str) -> int | None:
    """Return the latest persisted roll schedule version when present."""
    base = roll_schedules_base_dir(root, product=product, policy_slug=policy_slug)
    if not base.exists():
        return None
    versions = [
        int(path.name.removeprefix("v"))
        for path in base.iterdir()
        if path.is_dir() and path.name.startswith("v") and path.name.removeprefix("v").isdigit()
    ]
    return None if not versions else max(versions)


def compute_roll_schedule_source_fingerprint(
    *,
    contract_dataset_refs: Sequence[str],
    start_session: date,
    end_session: date,
    policy: VolumeRthCloseRollPolicy,
) -> str:
    """Compute a stable fingerprint for roll schedule rebuild decisions."""
    payload = "|".join(
        [
            policy.product,
            policy.slug,
            str(policy.confirmation_sessions),
            start_session.isoformat(),
            end_session.isoformat(),
            *sorted(contract_dataset_refs),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class RollScheduleRepository:
    """Persist and load versioned roll schedules."""

    def __init__(self, root: Path, writer: ParquetRollScheduleWriter | None = None) -> None:
        self._root = root
        self._writer = writer or ParquetRollScheduleWriter()

    def write(
        self,
        schedule: RollSchedule,
        *,
        manifest: RollScheduleManifest,
    ) -> Path:
        """Persist schedule Parquet and manifest for one version."""
        version_dir = roll_schedule_version_dir(
            self._root,
            product=schedule.product,
            policy_slug=schedule.policy.slug,
            version=schedule.version,
        )
        version_dir.mkdir(parents=True, exist_ok=True)
        parquet_path = roll_schedule_parquet_path(
            self._root,
            product=schedule.product,
            policy_slug=schedule.policy.slug,
            version=schedule.version,
        )
        self._writer.write(parquet_path, schedule.entries)
        write_roll_schedule_manifest(
            roll_schedule_manifest_path(
                self._root,
                product=schedule.product,
                policy_slug=schedule.policy.slug,
                version=schedule.version,
            ),
            manifest,
        )
        return version_dir

    def read(
        self,
        *,
        product: str,
        policy_slug: str,
        version: int,
        policy: VolumeRthCloseRollPolicy,
    ) -> tuple[RollSchedule, RollScheduleManifest]:
        """Load one roll schedule version and its manifest."""
        parquet_path = roll_schedule_parquet_path(
            self._root,
            product=product,
            policy_slug=policy_slug,
            version=version,
        )
        manifest_path = roll_schedule_manifest_path(
            self._root,
            product=product,
            policy_slug=policy_slug,
            version=version,
        )
        entries = tuple(self._writer.read(parquet_path))
        schedule = RollSchedule(
            product=product,
            policy=policy,
            version=version,
            entries=entries,
        )
        return schedule, read_roll_schedule_manifest(manifest_path)
