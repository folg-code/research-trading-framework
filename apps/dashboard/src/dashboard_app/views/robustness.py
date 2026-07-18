"""Helpers for Strategy Robustness dashboard pages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pyarrow as pa

from dashboard_app.catalog import list_runs
from dashboard_app.contracts import RunSummary, WorkflowKind
from dashboard_app.query import DashboardQueryService

_ROBUSTNESS_TABLES = (
    "parameter_sweep_rankings",
    "parameter_sweep_heatmap",
    "walk_forward_folds",
    "walk_forward_equity",
    "stress_comparison",
    "monte_carlo_distributions",
    "monte_carlo_tails",
)


@dataclass(frozen=True, slots=True)
class RobustnessExperimentArtifacts:
    """Loaded analytics tables for one robustness experiment."""

    summary: RunSummary
    tables: dict[str, pa.Table]
    verdict: dict[str, object] | None


@dataclass(frozen=True, slots=True)
class ParameterSweepSliceKey:
    """One (metric, x_axis, y_axis) combination in parameter_sweep_heatmap."""

    metric: str
    x_axis: str
    y_axis: str | None

    @property
    def label(self) -> str:
        if self.y_axis:
            return f"{self.metric}: {self.x_axis} x {self.y_axis}"
        return f"{self.metric}: {self.x_axis} (1D)"


def list_robustness_experiments(storage_root: Path) -> tuple[RunSummary, ...]:
    """Return ROBUSTNESS catalog rows newest-first."""
    catalog = list_runs(storage_root)
    return tuple(item for item in catalog.runs if item.workflow is WorkflowKind.ROBUSTNESS)


def load_robustness_experiment(
    service: DashboardQueryService,
    summary: RunSummary,
) -> RobustnessExperimentArtifacts:
    """Load Parquet analytics (and optional verdict.json) for one experiment."""
    experiment_dir = Path(summary.storage_path)
    tables: dict[str, pa.Table] = {}
    for name in _ROBUSTNESS_TABLES:
        path = experiment_dir / "analytics" / f"{name}.parquet"
        table = service.read_parquet_columns(path)
        if path.is_file():
            tables[name] = table

    verdict: dict[str, object] | None = None
    verdict_path = experiment_dir / "analytics" / "verdict.json"
    if verdict_path.is_file():
        import json

        payload = json.loads(verdict_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            verdict = payload
    return RobustnessExperimentArtifacts(summary=summary, tables=tables, verdict=verdict)


def list_parameter_sweep_slices(heatmap: pa.Table) -> tuple[ParameterSweepSliceKey, ...]:
    """Return distinct heatmap slices, preferring 2D axis pairs first."""
    required = {"metric", "x_axis", "x_value", "value"}
    if heatmap.num_rows == 0 or not required.issubset(heatmap.column_names):
        return ()

    has_y_axis = "y_axis" in heatmap.column_names
    keys: set[ParameterSweepSliceKey] = set()
    for index in range(heatmap.num_rows):
        metric = heatmap.column("metric")[index].as_py()
        x_axis = heatmap.column("x_axis")[index].as_py()
        if not isinstance(metric, str) or not isinstance(x_axis, str):
            continue
        y_axis_raw = heatmap.column("y_axis")[index].as_py() if has_y_axis else None
        y_axis = y_axis_raw if isinstance(y_axis_raw, str) and y_axis_raw.strip() else None
        keys.add(ParameterSweepSliceKey(metric=metric, x_axis=x_axis, y_axis=y_axis))

    return tuple(
        sorted(
            keys,
            key=lambda item: (
                0 if item.y_axis is not None else 1,
                item.metric,
                item.x_axis,
                item.y_axis or "",
            ),
        )
    )


def filter_parameter_sweep_slice(
    heatmap: pa.Table,
    slice_key: ParameterSweepSliceKey,
) -> pa.Table:
    """Return rows for one metric / axis-pair slice."""
    required = {"metric", "x_axis", "x_value", "value"}
    if heatmap.num_rows == 0 or not required.issubset(heatmap.column_names):
        return heatmap.slice(0, 0)

    has_y_axis = "y_axis" in heatmap.column_names
    keep: list[int] = []
    for index in range(heatmap.num_rows):
        metric = heatmap.column("metric")[index].as_py()
        x_axis = heatmap.column("x_axis")[index].as_py()
        if metric != slice_key.metric or x_axis != slice_key.x_axis:
            continue
        y_axis_raw = heatmap.column("y_axis")[index].as_py() if has_y_axis else None
        y_axis = y_axis_raw if isinstance(y_axis_raw, str) and y_axis_raw.strip() else None
        if y_axis != slice_key.y_axis:
            continue
        keep.append(index)
    if not keep:
        return heatmap.slice(0, 0)
    return heatmap.take(keep)


_GATE_LABELS: dict[str, str] = {
    "min_stitched_oos_net_pnl": "Out-of-sample profit (walk-forward)",
    "min_oos_beats_train_ratio": "Out-of-sample beats in-sample",
    "max_worst_stress_delta_net_pnl": "Worst stress-test drop",
    "max_mc_loss_probability": "Chance of ending in loss (Monte Carlo)",
    "max_top_trades_concentration": "Profit concentrated in few trades",
    "fail_on_isolated_optima": "No lucky isolated parameter peak",
}

_VERDICT_HEADLINES: dict[str, str] = {
    "PASS": "Looks robust under the checks we ran.",
    "CONDITIONAL": "Promising, but some softer checks raised concerns.",
    "FAIL": "Did not pass one or more critical validation checks.",
}


@dataclass(frozen=True, slots=True)
class VerdictGateView:
    """One gate row for the robustness verdict checklist."""

    gate_id: str
    label: str
    passed: bool
    severity: str
    message: str
    observed_value: str | None


@dataclass(frozen=True, slots=True)
class VerdictChecklistView:
    """Presentation model for robustness verdict.json."""

    verdict: str
    headline: str
    summary: str
    gates: tuple[VerdictGateView, ...]
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    blocking_issues: tuple[str, ...]


def build_verdict_checklist(payload: dict[str, object]) -> VerdictChecklistView:
    """Normalize verdict.json into a checklist-friendly view model."""
    verdict_raw = payload.get("verdict")
    verdict = str(verdict_raw).upper() if verdict_raw is not None else "UNKNOWN"
    summary_raw = payload.get("summary")
    summary = str(summary_raw) if summary_raw is not None else ""
    gates_raw = payload.get("gate_results")
    gates: list[VerdictGateView] = []
    if isinstance(gates_raw, list):
        for item in gates_raw:
            if not isinstance(item, dict):
                continue
            gate_id = str(item.get("gate_id", "gate"))
            observed = item.get("observed_value")
            gates.append(
                VerdictGateView(
                    gate_id=gate_id,
                    label=_GATE_LABELS.get(gate_id, gate_id.replace("_", " ")),
                    passed=bool(item.get("passed")),
                    severity=str(item.get("severity", "SOFT")),
                    message=str(item.get("message", "")),
                    observed_value=str(observed) if observed is not None else None,
                )
            )
    return VerdictChecklistView(
        verdict=verdict,
        headline=_VERDICT_HEADLINES.get(verdict, "Robustness verdict"),
        summary=summary,
        gates=tuple(gates),
        strengths=_string_tuple(payload.get("strengths")),
        weaknesses=_string_tuple(payload.get("weaknesses")),
        blocking_issues=_string_tuple(payload.get("blocking_issues")),
    )


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value if item is not None)
