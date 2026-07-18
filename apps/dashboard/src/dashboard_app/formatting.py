"""Human-readable formatting helpers for the public dashboard."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any


def humanize_dataset_ref(ref: str | None) -> str:
    """Turn a DatasetRef-like string into a short public label."""
    if ref is None or not str(ref).strip():
        return "—"
    text = str(ref).strip()
    instrument = instrument_from_dataset_ref(text)
    lower = text.lower()
    if instrument and (".c.0" in lower or "c.0|" in lower):
        return f"{instrument} continuous · volume-based roll"
    if instrument and "continuous" in lower:
        return f"{instrument} continuous"
    parts = text.split("|")
    kind = parts[1] if len(parts) > 1 else ""
    if instrument and kind:
        return f"{instrument} · {kind}"
    if instrument:
        return instrument
    return text if len(text) <= 48 else text[:45] + "…"


def instrument_from_dataset_ref(ref: str | None) -> str | None:
    """Extract a short instrument id (e.g. NQ) from a dataset ref."""
    if ref is None or not str(ref).strip():
        return None
    head = str(ref).strip().split("|", 1)[0]
    token = head.split(".", 1)[0].split("@", 1)[0]
    return token or None


def humanize_model_id(model_id: str | None) -> str:
    """Convert snake_case / dotted ids into Title Case words."""
    if model_id is None or not str(model_id).strip():
        return "—"
    text = str(model_id).strip().replace(".", " ").replace("-", " ").replace("_", " ")
    return " ".join(part.capitalize() for part in text.split() if part)


def format_created_at(value: datetime | None) -> str:
    """Format UTC timestamps for catalog tables."""
    if value is None:
        return "—"
    return value.strftime("%d %b %Y, %H:%M UTC")


def format_kpi(key: str, value: Any, *, unit: str = "pts") -> str:
    """Format a known KPI key for Streamlit metric display."""
    if value is None:
        return "—"
    numeric = _as_float(value)
    if key in {"win_rate"} and numeric is not None:
        pct = numeric * 100.0 if abs(numeric) <= 1.0 else numeric
        return f"{pct:.1f}%"
    if key in {"total_return"} and numeric is not None:
        pct = numeric * 100.0 if abs(numeric) <= 1.0 else numeric
        sign = "+" if pct > 0 else ""
        return f"{sign}{pct:.2f}%"
    if (
        key
        in {
            "net_pnl",
            "max_drawdown",
            "total_costs",
            "oos_net_pnl",
            "train_net_pnl",
            "delta_net_pnl",
            "baseline_net_pnl",
            "paper_equity",
            "realized_pnl",
            "unrealized_pnl",
            "last_price",
            "pnl",
        }
        and numeric is not None
    ):
        if key == "max_drawdown" and numeric > 0:
            numeric = -abs(numeric)
        sign = "+" if numeric > 0 and key in {"net_pnl", "pnl", "delta_net_pnl"} else ""
        return f"{sign}{numeric:,.2f} {unit}"
    if key in {"sharpe_ratio", "profit_factor"} and numeric is not None:
        return f"{numeric:.2f}"
    if key in {"trade_count", "trades", "path_count", "bars_held"} and numeric is not None:
        return f"{int(numeric):,}"
    if isinstance(value, float):
        return f"{value:,.2f}"
    return str(value)


def format_probability(value: Any) -> str:
    """Format a probability as a percentage string."""
    numeric = _as_float(value)
    if numeric is None:
        return "—"
    pct = numeric * 100.0 if abs(numeric) <= 1.0 else numeric
    return f"{pct:.1f}%"


def _as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(Decimal(text))
        except (InvalidOperation, ValueError):
            return None
    return None
