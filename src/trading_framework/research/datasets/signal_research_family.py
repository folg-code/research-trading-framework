"""Persisted manifest for bounded Signal Research model-family experiments."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.paths import signal_research_family_experiment_dir


@dataclass(frozen=True, slots=True)
class SignalResearchFamilyExperimentManifest:
    """Candidate accounting and variant run references for one family study."""

    experiment_id: str
    research_id: str
    family_id: str
    definition_hash: str | None
    created_at_utc: datetime
    candidates_generated: int
    candidates_evaluated: int
    candidates_skipped: int
    skipped_variant_ids: tuple[str, ...]
    variant_runs: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "research_id": self.research_id,
            "family_id": self.family_id,
            "definition_hash": self.definition_hash,
            "created_at_utc": self.created_at_utc.isoformat(),
            "candidates_generated": self.candidates_generated,
            "candidates_evaluated": self.candidates_evaluated,
            "candidates_skipped": self.candidates_skipped,
            "skipped_variant_ids": list(self.skipped_variant_ids),
            "variant_runs": [
                {"variant_id": variant_id, "run_id": run_id}
                for variant_id, run_id in self.variant_runs
            ],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> SignalResearchFamilyExperimentManifest:
        variant_runs_raw = payload.get("variant_runs", [])
        variant_runs = tuple(
            (str(item["variant_id"]), str(item["run_id"]))
            for item in variant_runs_raw
            if isinstance(item, dict)
        )
        return cls(
            experiment_id=str(payload["experiment_id"]),
            research_id=str(payload["research_id"]),
            family_id=str(payload["family_id"]),
            definition_hash=(
                str(payload["definition_hash"])
                if payload.get("definition_hash") is not None
                else None
            ),
            created_at_utc=datetime.fromisoformat(str(payload["created_at_utc"])),
            candidates_generated=int(payload["candidates_generated"]),
            candidates_evaluated=int(payload["candidates_evaluated"]),
            candidates_skipped=int(payload["candidates_skipped"]),
            skipped_variant_ids=tuple(
                str(value) for value in payload.get("skipped_variant_ids", [])
            ),
            variant_runs=variant_runs,
        )


class SignalResearchFamilyExperimentRepository:
    """Persist and load model-family experiment manifests."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def write_manifest(self, manifest: SignalResearchFamilyExperimentManifest) -> Path:
        """Persist one family experiment manifest."""
        experiment_dir = signal_research_family_experiment_dir(
            self._root,
            manifest.experiment_id,
        )
        if experiment_dir.exists():
            msg = f"family experiment directory already exists: {experiment_dir}"
            raise FileExistsError(msg)
        experiment_dir.mkdir(parents=True, exist_ok=False)
        manifest_path = experiment_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest.to_dict(), indent=2),
            encoding="utf-8",
        )
        return manifest_path

    def read_manifest(self, experiment_id: str) -> SignalResearchFamilyExperimentManifest:
        """Load one family experiment manifest."""
        manifest_path = (
            signal_research_family_experiment_dir(self._root, experiment_id) / "manifest.json"
        )
        if not manifest_path.exists():
            msg = f"missing family experiment manifest: {manifest_path}"
            raise FileNotFoundError(msg)
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            msg = f"family experiment manifest must be a mapping: {manifest_path}"
            raise ValidationError(msg)
        return SignalResearchFamilyExperimentManifest.from_dict(payload)

    def manifest_exists(self, experiment_id: str) -> bool:
        """Return whether a family experiment manifest exists."""
        manifest_path = (
            signal_research_family_experiment_dir(self._root, experiment_id) / "manifest.json"
        )
        return manifest_path.exists()
