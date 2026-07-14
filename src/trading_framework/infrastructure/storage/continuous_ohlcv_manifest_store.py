"""Continuous OHLCV derivation manifest persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

from trading_framework.market.derivation.config import (
    TRADES_TO_BARS_DERIVATION_METHOD,
    TRADES_TO_BARS_VERSION,
)
from trading_framework.time.models.utc_instant import require_utc_aware

CONTINUOUS_OHLCV_MANIFEST_VERSION = "continuous-ohlcv-manifest-v1"
CONTINUOUS_OHLCV_BUILDER_VERSION = "continuous-ohlcv-builder-v1"
DEFAULT_OHLCV_REBUILD_WINDOW_SESSIONS = 10


@dataclass(frozen=True, slots=True)
class ContinuousOhlcvManifest:
    """Describe how one derived continuous OHLCV dataset version was built."""

    manifest_version: str
    source_continuous_trades_ref: str
    source_continuous_manifest_fingerprint: str
    schema_version: str
    derivation_method: str
    derivation_version: str
    builder_version: str
    target_timeframe: str
    start_session: date
    end_session: date
    rebuild_window_sessions: int
    source_fingerprint: str
    created_at_utc: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "source_continuous_trades_ref": self.source_continuous_trades_ref,
            "source_continuous_manifest_fingerprint": self.source_continuous_manifest_fingerprint,
            "schema_version": self.schema_version,
            "derivation_method": self.derivation_method,
            "derivation_version": self.derivation_version,
            "builder_version": self.builder_version,
            "target_timeframe": self.target_timeframe,
            "start_session": self.start_session.isoformat(),
            "end_session": self.end_session.isoformat(),
            "rebuild_window_sessions": self.rebuild_window_sessions,
            "source_fingerprint": self.source_fingerprint,
            "created_at_utc": require_utc_aware(self.created_at_utc).isoformat(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ContinuousOhlcvManifest:
        created_raw = payload["created_at_utc"]
        created_at = (
            datetime.fromisoformat(created_raw) if isinstance(created_raw, str) else created_raw
        )
        return cls(
            manifest_version=str(payload["manifest_version"]),
            source_continuous_trades_ref=str(payload["source_continuous_trades_ref"]),
            source_continuous_manifest_fingerprint=str(
                payload["source_continuous_manifest_fingerprint"]
            ),
            schema_version=str(payload["schema_version"]),
            derivation_method=str(
                payload.get("derivation_method", TRADES_TO_BARS_DERIVATION_METHOD)
            ),
            derivation_version=str(payload.get("derivation_version", TRADES_TO_BARS_VERSION)),
            builder_version=str(payload.get("builder_version", CONTINUOUS_OHLCV_BUILDER_VERSION)),
            target_timeframe=str(payload["target_timeframe"]),
            start_session=date.fromisoformat(str(payload["start_session"])),
            end_session=date.fromisoformat(str(payload["end_session"])),
            rebuild_window_sessions=int(
                payload.get("rebuild_window_sessions", DEFAULT_OHLCV_REBUILD_WINDOW_SESSIONS)
            ),
            source_fingerprint=str(payload["source_fingerprint"]),
            created_at_utc=require_utc_aware(created_at),
        )


def write_continuous_ohlcv_manifest(path: Path, manifest: ContinuousOhlcvManifest) -> Path:
    """Persist a continuous OHLCV manifest JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
    return path


def read_continuous_ohlcv_manifest(path: Path) -> ContinuousOhlcvManifest:
    """Load a continuous OHLCV manifest JSON file."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ContinuousOhlcvManifest.from_dict(payload)
