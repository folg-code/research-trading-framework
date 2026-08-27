"""Finished-result contract for Predictive Research HTML reporting."""

from __future__ import annotations

from dataclasses import dataclass

from trading_framework.research.datasets.predictive import PredictiveDatasetEnvelope
from trading_framework.research.datasets.predictive_run import PredictiveRunEnvelope
from trading_framework.research.predictive.importance import ImportanceTrace
from trading_framework.research.predictive.leaderboard import PredictiveLeaderboard
from trading_framework.research.predictive.learning_curves import LearningCurves
from trading_framework.research.predictive.metrics import PredictiveMetricsReport
from trading_framework.research.predictive.selection import SelectionTrace
from trading_framework.research.predictive.windows import WindowAccounting


@dataclass(frozen=True, slots=True)
class PredictiveReportSource:
    """Persisted run + metrics + dataset envelopes. Read-only report input."""

    run: PredictiveRunEnvelope
    dataset: PredictiveDatasetEnvelope
    metrics: PredictiveMetricsReport
    importance: ImportanceTrace | None = None
    selection: SelectionTrace | None = None
    leaderboard: PredictiveLeaderboard | None = None
    learning_curves: LearningCurves | None = None
    window_accounting: WindowAccounting | None = None
