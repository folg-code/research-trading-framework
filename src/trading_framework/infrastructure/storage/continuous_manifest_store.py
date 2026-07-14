"""Continuous trades manifest persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from trading_framework.market.continuous.identity import CONTINUOUS_BUILDER_VERSION
from trading_framework.market.continuous.trade_record import MARKET_TRADE_CONTINUOUS_SCHEMA_VERSION
from trading_framework.time.models.utc_instant import require_utc_aware

CONTINUOUS_MANIFEST_VERSION = "continuous-manifest-v1"
DEFAULT_REBUILD_WINDOW_SESSIONS = 10


@dataclass(frozen=True, slots=True)
class ContinuousTradesManifest:
    """Describe how one continuous trades dataset version was built."""

    manifest_version: str
    product: str
    schema: str
    schema_version: str
    roll_policy_slug: str
    price_adjustment: str
    builder_version: str
    roll_schedule_version: int
    roll_schedule_fingerprint: str
    contract_dataset_refs: tuple[str, ...]
    start_session: date
    end_session: date
    rebuild_window_sessions: int
    source_fingerprint: str
    created_at_utc: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "product": self.product,
            "schema": self.schema,
            "schema_version": self.schema_version,
            "roll_policy": {
                "type": self.roll_policy_slug,
                "price_adjustment": self.price_adjustment,
            },
            "builder_version": self.builder_version,
            "roll_schedule_version": self.roll_schedule_version,
            "roll_schedule_fingerprint": self.roll_schedule_fingerprint,
            "contract_dataset_refs": list(self.contract_dataset_refs),
            "start_session": self.start_session.isoformat(),
            "end_session": self.end_session.isoformat(),
            "rebuild_window_sessions": self.rebuild_window_sessions,
            "source_fingerprint": self.source_fingerprint,
            "created_at_utc": require_utc_aware(self.created_at_utc).isoformat(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ContinuousTradesManifest:
        created_raw = payload["created_at_utc"]
        created_at = (
            datetime.fromisoformat(created_raw) if isinstance(created_raw, str) else created_raw
        )
        roll_policy = payload.get("roll_policy", {})
        if isinstance(roll_policy, dict):
            policy_slug = str(roll_policy.get("type", payload.get("roll_policy_slug", "")))
            price_adjustment = str(
                roll_policy.get("price_adjustment", payload.get("price_adjustment", "none"))
            )
        else:
            policy_slug = str(payload.get("roll_policy_slug", ""))
            price_adjustment = str(payload.get("price_adjustment", "none"))
        return cls(
            manifest_version=str(payload["manifest_version"]),
            product=str(payload["product"]),
            schema=str(payload["schema"]),
            schema_version=str(
                payload.get("schema_version", MARKET_TRADE_CONTINUOUS_SCHEMA_VERSION)
            ),
            roll_policy_slug=policy_slug,
            price_adjustment=price_adjustment,
            builder_version=str(payload.get("builder_version", CONTINUOUS_BUILDER_VERSION)),
            roll_schedule_version=int(payload["roll_schedule_version"]),
            roll_schedule_fingerprint=str(payload["roll_schedule_fingerprint"]),
            contract_dataset_refs=tuple(str(ref) for ref in payload["contract_dataset_refs"]),
            start_session=date.fromisoformat(str(payload["start_session"])),
            end_session=date.fromisoformat(str(payload["end_session"])),
            rebuild_window_sessions=int(
                payload.get("rebuild_window_sessions", DEFAULT_REBUILD_WINDOW_SESSIONS)
            ),
            source_fingerprint=str(payload["source_fingerprint"]),
            created_at_utc=require_utc_aware(created_at),
        )


def write_continuous_trades_manifest(path: Path, manifest: ContinuousTradesManifest) -> Path:
    """Persist a continuous trades manifest JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
    return path


def read_continuous_trades_manifest(path: Path) -> ContinuousTradesManifest:
    """Load a continuous trades manifest JSON file."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ContinuousTradesManifest.from_dict(payload)
