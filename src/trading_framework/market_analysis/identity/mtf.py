"""Layered cache and lineage identities for multitimeframe execution."""

import json
from dataclasses import dataclass

from trading_framework.market.datasets import DatasetRef
from trading_framework.market_analysis.models.alignment import AlignmentPolicy
from trading_framework.market_analysis.models.resample import ResampleSpec
from trading_framework.market_analysis.models.time_range import TimeRange
from trading_framework.time.models.timeframe import Timeframe


@dataclass(frozen=True, slots=True)
class ResampleIdentity:
    """Identity of one shared resampling node output."""

    dataset_ref: DatasetRef
    source_timeframe: Timeframe
    target_timeframe: Timeframe
    resample_spec: ResampleSpec
    requested_range: TimeRange

    def canonical_key(self) -> str:
        payload = {
            "kind": "resample",
            "dataset_ref": str(self.dataset_ref),
            "source_timeframe": self.source_timeframe.value,
            "target_timeframe": self.target_timeframe.value,
            "resample_spec": self.resample_spec.to_json_dict(),
            "requested_range": self.requested_range.canonical(),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def __hash__(self) -> int:
        return hash(self.canonical_key())


@dataclass(frozen=True, slots=True)
class AlignmentIdentity:
    """Identity of one aligned presentation of a component result on an evaluation grid."""

    component_computation_key: str
    output_id: str
    evaluation_timeframe: Timeframe
    evaluation_range: TimeRange
    alignment_policy: AlignmentPolicy

    def canonical_key(self) -> str:
        payload = {
            "kind": "alignment",
            "component_computation_key": self.component_computation_key,
            "output_id": self.output_id,
            "evaluation_timeframe": self.evaluation_timeframe.value,
            "evaluation_range": self.evaluation_range.canonical(),
            "alignment_policy": self.alignment_policy.value,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def __hash__(self) -> int:
        return hash(self.canonical_key())
