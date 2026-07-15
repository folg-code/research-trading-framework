"""Human-readable formatting helpers for robustness HTML reports."""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from trading_framework.research.robustness.report import RobustnessReportViewModel
from trading_framework.research.robustness.verdict import VerdictGateResult, VerdictKind

_SIG_DIGITS = 4

_PARAMETER_LABELS: dict[str, str] = {
    "exit_after_bars": "exit after {value} bars",
    "volatility_threshold": "volatility threshold {value}",
    "volatility_period": "volatility lookback {value} bars",
    "pivot_range": "swing pivot range {value}",
}

_AXIS_LABELS: dict[str, str] = {
    "exit_after_bars": "Exit (bars)",
    "volatility_threshold": "Volatility threshold",
    "volatility_period": "Volatility period",
    "pivot_range": "Pivot range",
}

_STRATEGY_LABELS: dict[str, str] = {
    "high_vol_higher_low_fixed_exit": (
        "Trade higher lows after a volatility spike; exit after a fixed number of bars."
    ),
}

_KIND_LABELS: dict[str, str] = {
    "PARAMETER_SWEEP": "Parameter comparison",
    "WALK_FORWARD": "Walk-forward validation",
    "STRESS_TEST": "Stress scenarios",
    "MONTE_CARLO": "Monte Carlo simulation",
    "STATISTICAL_DIAGNOSTICS": "Statistical health checks",
}

_SCENARIO_LABELS: dict[str, str] = {
    "double_commission": "Commission costs doubled",
    "remove_top_trade": "Best single trade removed",
}

_GATE_LABELS: dict[str, str] = {
    "min_stitched_oos_net_pnl": "Out-of-sample profit (walk-forward)",
    "min_oos_beats_train_ratio": "Out-of-sample beats in-sample",
    "max_worst_stress_delta_net_pnl": "Worst stress-test drop",
    "max_mc_loss_probability": "Chance of ending in loss (Monte Carlo)",
    "max_top_trades_concentration": "Profit concentrated in few trades",
    "fail_on_isolated_optima": "No lucky isolated parameter peak",
}

_METRIC_LABELS: dict[str, str] = {
    "net_pnl": "Net profit",
    "max_drawdown": "Maximum drawdown",
    "win_rate": "Win rate",
    "final_equity": "Final equity",
}

_VERDICT_HEADLINE: dict[VerdictKind, str] = {
    VerdictKind.PASS: "Looks robust under the checks we ran.",
    VerdictKind.CONDITIONAL: "Promising, but some softer checks raised concerns.",
    VerdictKind.FAIL: "Did not pass one or more critical validation checks.",
}


def format_significant(
    value: Decimal | float | int | None,
    *,
    sig_digits: int = _SIG_DIGITS,
) -> str:
    """Format a numeric value with at most ``sig_digits`` significant figures."""
    if value is None:
        return "—"
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return str(value)
    if not decimal_value.is_finite():
        return "—"
    if decimal_value == 0:
        return "0"
    if decimal_value == decimal_value.to_integral_value():
        return f"{int(decimal_value):,}"

    float_value = float(decimal_value)
    abs_value = abs(float_value)
    if abs_value >= 1000:
        rounded = decimal_value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return f"{int(rounded):,}"
    if abs_value >= 100:
        rounded = decimal_value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        return format(rounded.normalize(), "f")
    if abs_value >= 1:
        rounded = decimal_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return format(rounded.normalize(), "f")

    exponent = decimal_value.adjusted()
    quant = Decimal(1).scaleb(exponent - sig_digits + 1)
    rounded = decimal_value.quantize(quant, rounding=ROUND_HALF_UP)
    return format(rounded.normalize(), "f")


def format_money(value: Decimal | float | int | None) -> str:
    """Format profit, loss, equity or drawdown for display."""
    return format_significant(value)


def format_probability(value: Decimal | float | int | None) -> str:
    """Format a 0-1 probability as a percentage."""
    if value is None:
        return "—"
    decimal_value = Decimal(str(value))
    percent = float(decimal_value) * 100.0
    if abs(percent) >= 10:
        return f"{percent:.1f}%"
    if abs(percent) >= 1:
        return f"{percent:.2f}%"
    return f"{percent:.3f}%"


def format_share(value: Decimal | float | int | None) -> str:
    """Format a 0-1 share as a percentage."""
    return format_probability(value)


def format_parameter_settings(overrides: dict[str, str] | None) -> str:
    """Turn parameter overrides into a short plain-language label."""
    if not overrides:
        return "Default strategy settings"
    parts: list[str] = []
    for key in sorted(overrides):
        template = _PARAMETER_LABELS.get(key, key.replace("_", " ") + " {value}")
        parts.append(template.format(value=overrides[key]))
    return "; ".join(parts).capitalize()


def format_axis_name(axis_name: str) -> str:
    return _AXIS_LABELS.get(axis_name, axis_name.replace("_", " ").title())


def format_axis_value(axis_name: str, value: str) -> str:
    if axis_name == "exit_after_bars":
        return f"{value} bars"
    return value


def format_strategy_template(template_id: str) -> str:
    return _STRATEGY_LABELS.get(template_id, template_id.replace("_", " "))


def format_dataset_label(dataset_ref: str) -> str:
    lowered = dataset_ref.lower()
    if "nq" in lowered and "ohlcv" in lowered:
        return "NQ futures — 1-minute price bars (continuous contract)"
    if "es" in lowered and "ohlcv" in lowered:
        return "ES futures — 1-minute price bars"
    if "ohlcv" in lowered:
        return "Historical 1-minute price bars"
    return "Historical market data"


def format_kind_label(kind: str) -> str:
    return _KIND_LABELS.get(kind, kind.replace("_", " ").title())


def format_scenario_label(scenario_id: str) -> str:
    return _SCENARIO_LABELS.get(scenario_id, scenario_id.replace("_", " "))


def format_gate_label(gate_id: str) -> str:
    return _GATE_LABELS.get(gate_id, gate_id.replace("_", " "))


def format_metric_label(metric: str) -> str:
    return _METRIC_LABELS.get(metric, metric.replace("_", " ").title())


def format_fold_label(fold_id: str) -> str:
    match = re.search(r"(\d+)$", fold_id)
    if match is None:
        return fold_id.replace("_", " ").title()
    return f"Period {int(match.group(1)) + 1}"


def format_verdict_badge(verdict: VerdictKind) -> str:
    if verdict is VerdictKind.PASS:
        return "Pass"
    if verdict is VerdictKind.CONDITIONAL:
        return "Conditional pass"
    return "Fail"


def format_verdict_headline(verdict: VerdictKind) -> str:
    return _VERDICT_HEADLINE[verdict]


def build_config_label_lookup(view_model: RobustnessReportViewModel) -> dict[str, dict[str, str]]:
    """Map internal config ids to parameter overrides for display."""
    lookup: dict[str, dict[str, str]] = {}
    sweep = view_model.parameter_sweep
    if sweep is not None:
        for ranking in sweep.rankings:
            lookup[ranking.config_id] = dict(ranking.parameter_overrides)
        for stability in sweep.neighbor_stability:
            lookup[stability.config_id] = dict(stability.parameter_overrides)
    walk_forward = view_model.walk_forward
    if walk_forward is not None:
        for evaluation in walk_forward.fold_evaluations:
            lookup[evaluation.selection.config_id] = dict(evaluation.selection.parameter_overrides)
    return lookup


def format_config_label(
    config_id: str | None,
    *,
    lookup: dict[str, dict[str, str]],
) -> str:
    if config_id is None:
        return "—"
    overrides = lookup.get(config_id)
    if overrides is not None:
        return format_parameter_settings(overrides)
    return "Strategy variant"


def format_verdict_summary(
    summary: str,
    *,
    lookup: dict[str, dict[str, str]],
) -> str:
    """Replace internal config ids in verdict summaries with readable labels."""
    updated = summary
    for config_id, overrides in lookup.items():
        if config_id in updated:
            updated = updated.replace(config_id, format_parameter_settings(overrides))
    updated = updated.replace("ranking ≠ validation", "grid ranking is not the same as validation")
    updated = updated.replace("ranking != validation", "grid ranking is not the same as validation")
    return updated


def format_gate_message(gate: VerdictGateResult) -> str:
    """Rewrite gate messages with rounded numbers where possible."""
    message = gate.message
    if gate.observed_value is not None:
        try:
            observed = Decimal(gate.observed_value)
            message = message.replace(gate.observed_value, format_significant(observed))
        except (InvalidOperation, ValueError):
            pass
    for token in re.findall(r"-?\d+\.\d+", message):
        try:
            message = message.replace(token, format_significant(Decimal(token)), 1)
        except (InvalidOperation, ValueError):
            continue
    return message


def format_strength_or_weakness(text: str) -> str:
    """Humanize auto-generated strength lines from verdict evaluation."""
    gate_match = re.match(r"([a-z0-9_]+) gate passed \((.+)\)", text)
    if gate_match is not None:
        gate_id, observed = gate_match.groups()
        return f"{format_gate_label(gate_id)}: {observed}"
    return text
