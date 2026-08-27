"""Panel registry for Predictive Research reports (D-S041-07)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from trading_framework.research.predictive.estimators import TaskType
from trading_framework.research.reporting.predictive.view_models import (
    PredictiveReportViewModel,
)

RESERVED_PANEL_IDS: frozenset[str] = frozenset()


class PanelStatus(StrEnum):
    """Whether a registered panel renders or degrades to a skip note."""

    RENDER = "RENDER"
    SKIP = "SKIP"


@dataclass(frozen=True, slots=True)
class PanelDefinition:
    """One registered panel. Assembly iterates this tuple; it does not switch on ids."""

    panel_id: str
    title: str
    intro: str
    applicability: Callable[[PredictiveReportViewModel], tuple[PanelStatus, str | None]]


@dataclass(frozen=True, slots=True)
class ResolvedPanel:
    """Registry decision for one panel on one view model."""

    panel_id: str
    title: str
    intro: str
    status: PanelStatus
    skip_reason: str | None = None


def _always_render(_view: PredictiveReportViewModel) -> tuple[PanelStatus, str | None]:
    return PanelStatus.RENDER, None


def _regression_only(view: PredictiveReportViewModel) -> tuple[PanelStatus, str | None]:
    if view.task_type is TaskType.REGRESSION:
        return PanelStatus.RENDER, None
    return PanelStatus.SKIP, "Skipped: this panel applies to regression runs only."


def _classification_only(view: PredictiveReportViewModel) -> tuple[PanelStatus, str | None]:
    if view.task_type is TaskType.CLASSIFICATION:
        return PanelStatus.RENDER, None
    return PanelStatus.SKIP, "Skipped: this panel applies to classification runs only."


def _calibration(view: PredictiveReportViewModel) -> tuple[PanelStatus, str | None]:
    if view.task_type is not TaskType.CLASSIFICATION:
        return PanelStatus.SKIP, "Skipped: calibration applies to classification runs only."
    if not view.has_probabilities:
        return (
            PanelStatus.SKIP,
            "Skipped: classification run has no predicted probabilities; "
            "calibration would be undefined.",
        )
    return PanelStatus.RENDER, None


def _feature_importance(view: PredictiveReportViewModel) -> tuple[PanelStatus, str | None]:
    if view.feature_importance:
        return PanelStatus.RENDER, None
    return (
        PanelStatus.SKIP,
        "Skipped: no importance.json sidecar for this run.",
    )


def _leaderboard(view: PredictiveReportViewModel) -> tuple[PanelStatus, str | None]:
    if view.leaderboard_rows:
        return PanelStatus.RENDER, None
    return (
        PanelStatus.SKIP,
        "Skipped: no leaderboard.json sidecar for this run.",
    )


def _selection_trace(view: PredictiveReportViewModel) -> tuple[PanelStatus, str | None]:
    if view.selection_folds:
        return PanelStatus.RENDER, None
    return (
        PanelStatus.SKIP,
        "Skipped: no selection.json sidecar for this run (single-estimator runs do not select).",
    )


def _learning_curves(view: PredictiveReportViewModel) -> tuple[PanelStatus, str | None]:
    if view.learning_curves:
        return PanelStatus.RENDER, None
    return (
        PanelStatus.SKIP,
        "Skipped: no learning_curves.json sidecar for this run.",
    )


def _window_accounting(view: PredictiveReportViewModel) -> tuple[PanelStatus, str | None]:
    if view.window_accounting:
        return PanelStatus.RENDER, None
    return (
        PanelStatus.SKIP,
        "Skipped: no window_accounting.json sidecar for this run.",
    )


PREDICTIVE_REPORT_PANELS: tuple[PanelDefinition, ...] = (
    PanelDefinition(
        panel_id="fold_timeline",
        title="Fold timeline",
        intro=(
            "A thin purge band or overlapping test windows usually means the split leaked. "
            "A large embargo/purge share is the honest cost of the guards."
        ),
        applicability=_always_render,
    ),
    PanelDefinition(
        panel_id="metric_stability",
        title="Metric stability across folds",
        intro=(
            "A pooled score built from one strong fold and several near-chance folds is not "
            "a stable result. Look at the spread, not the pooled point."
        ),
        applicability=_always_render,
    ),
    PanelDefinition(
        panel_id="model_vs_baselines",
        title="Model versus reference baselines",
        intro=(
            "If the model bar sits inside the permutation baseline, the features did not beat "
            "shuffled labels. Constant/majority is the floor a useful model must clear."
        ),
        applicability=_always_render,
    ),
    PanelDefinition(
        panel_id="prediction_quality",
        title="Prediction quality",
        intro=(
            "A cloud with no slope, or residuals that fan out, means the model is not tracking "
            "realized forward return even when rank IC looks modestly positive."
        ),
        applicability=_regression_only,
    ),
    PanelDefinition(
        panel_id="discrimination",
        title="Discrimination",
        intro=(
            "ROC/PR curves that hug the diagonal, or that collapse on one fold, mean the model "
            "is not ranking positives above chance."
        ),
        applicability=_classification_only,
    ),
    PanelDefinition(
        panel_id="calibration",
        title="Calibration",
        intro=(
            "Good AUC with a broken reliability curve is usable for ranking and dangerous for "
            "thresholding. A curve far from the diagonal should not be used as a probability."
        ),
        applicability=_calibration,
    ),
    PanelDefinition(
        panel_id="prediction_buckets",
        title="Prediction buckets",
        intro=(
            "Mean forward return should rise with the prediction decile. A spike only in the "
            "top bucket, with noise elsewhere, is usually a small-sample artefact."
        ),
        applicability=_always_render,
    ),
    PanelDefinition(
        panel_id="sample_composition",
        title="Label and sample composition",
        intro=(
            "If incomplete horizons or purge/embargo dominate the row budget, the learning "
            "problem is smaller than the study spec suggests."
        ),
        applicability=_always_render,
    ),
    PanelDefinition(
        panel_id="quality_flags",
        title="Quality flags",
        intro=(
            "Flags are warnings with the threshold that triggered them. They are not a "
            "PASS/FAIL verdict and they never block the report."
        ),
        applicability=_always_render,
    ),
    PanelDefinition(
        panel_id="feature_importance",
        title="Feature importance",
        intro=(
            "Native gain is a training-fold statistic. Permutation importance is the "
            "out-of-sample drop when each TEST column is shuffled. Trust permutation first."
        ),
        applicability=_feature_importance,
    ),
    PanelDefinition(
        panel_id="leaderboard",
        title="Study leaderboard",
        intro=(
            "Families and S040 baselines on one dataset fingerprint. A tree that cannot "
            "beat ridge on the same folds is a statement about the features."
        ),
        applicability=_leaderboard,
    ),
    PanelDefinition(
        panel_id="selection_trace",
        title="Candidate selection and train/test gap",
        intro=(
            "The inner-validation winner is refit on the full TRAIN fold. A large "
            "|train - test| gap on the primary metric is overfitting, not skill."
        ),
        applicability=_selection_trace,
    ),
    PanelDefinition(
        panel_id="learning_curves",
        title="Learning curves",
        intro=(
            "Train and inner-validation loss come from the inner early-stopping run, "
            "not a TEST-supervised refit. The marker is the epoch that was restored."
        ),
        applicability=_learning_curves,
    ),
    PanelDefinition(
        panel_id="window_accounting",
        title="Window accounting",
        intro=(
            "A long lookback on a short fold can discard most samples. Effective sample "
            "is windows built after DROP; a strong metric on a tiny remainder is not "
            "the same study."
        ),
        applicability=_window_accounting,
    ),
)


def resolve_report_panels(view: PredictiveReportViewModel) -> tuple[ResolvedPanel, ...]:
    """Resolve the registered panels for one view model, including skip notes."""
    resolved: list[ResolvedPanel] = []
    for definition in PREDICTIVE_REPORT_PANELS:
        status, skip_reason = definition.applicability(view)
        resolved.append(
            ResolvedPanel(
                panel_id=definition.panel_id,
                title=definition.title,
                intro=definition.intro,
                status=status,
                skip_reason=skip_reason,
            )
        )
    return tuple(resolved)
