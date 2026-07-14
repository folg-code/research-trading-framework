"""Roll schedule manifest persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from trading_framework.market.continuous.policy import ROLL_SCHEDULE_BUILDER_VERSION
from trading_framework.time.models.utc_instant import require_utc_aware

ROLL_SCHEDULE_MANIFEST_VERSION = "roll-schedule-manifest-v1"


@dataclass(frozen=True, slots=True)
class RollScheduleManifest:
    """Describe how one roll schedule version was built."""

    manifest_version: str
    product: str
    policy_slug: str
    schema_version: str
    builder_version: str
    version: int
    start_session: date
    end_session: date
    confirmation_sessions: int
    contract_dataset_refs: tuple[str, ...]
    source_fingerprint: str
    created_at_utc: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "product": self.product,
            "policy_slug": self.policy_slug,
            "schema_version": self.schema_version,
            "builder_version": self.builder_version,
            "version": self.version,
            "start_session": self.start_session.isoformat(),
            "end_session": self.end_session.isoformat(),
            "confirmation_sessions": self.confirmation_sessions,
            "contract_dataset_refs": list(self.contract_dataset_refs),
            "source_fingerprint": self.source_fingerprint,
            "created_at_utc": require_utc_aware(self.created_at_utc).isoformat(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RollScheduleManifest:
        created_raw = payload["created_at_utc"]
        created_at = (
            datetime.fromisoformat(created_raw) if isinstance(created_raw, str) else created_raw
        )
        return cls(
            manifest_version=str(payload["manifest_version"]),
            product=str(payload["product"]),
            policy_slug=str(payload["policy_slug"]),
            schema_version=str(payload["schema_version"]),
            builder_version=str(payload.get("builder_version", ROLL_SCHEDULE_BUILDER_VERSION)),
            version=int(payload["version"]),
            start_session=date.fromisoformat(str(payload["start_session"])),
            end_session=date.fromisoformat(str(payload["end_session"])),
            confirmation_sessions=int(payload["confirmation_sessions"]),
            contract_dataset_refs=tuple(str(ref) for ref in payload["contract_dataset_refs"]),
            source_fingerprint=str(payload["source_fingerprint"]),
            created_at_utc=require_utc_aware(created_at),
        )


def write_roll_schedule_manifest(path: Path, manifest: RollScheduleManifest) -> Path:
    """Persist a roll schedule manifest JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
    return path


def read_roll_schedule_manifest(path: Path) -> RollScheduleManifest:
    """Load a roll schedule manifest JSON file."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return RollScheduleManifest.from_dict(payload)
