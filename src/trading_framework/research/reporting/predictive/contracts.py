"""Finished-result contract for Predictive Research HTML reporting."""

from __future__ import annotations

from dataclasses import dataclass

from trading_framework.research.datasets.predictive import PredictiveDatasetEnvelope
from trading_framework.research.datasets.predictive_run import PredictiveRunEnvelope
from trading_framework.research.predictive.metrics import PredictiveMetricsReport


@dataclass(frozen=True, slots=True)
class PredictiveReportSource:
    """Persisted run + metrics + dataset envelopes. Read-only report input."""

    run: PredictiveRunEnvelope
    dataset: PredictiveDatasetEnvelope
    metrics: PredictiveMetricsReport
