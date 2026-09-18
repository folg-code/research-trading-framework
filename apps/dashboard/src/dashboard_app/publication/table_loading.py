"""Shared build-time helpers for loading Parquet tables into sanitizer inputs.

Extracted from ``evidence.py`` (Sprint 070 / D-P18-03) so
``workspace.py``'s new Strategy Research discovery can reuse the same
bounded-sampling and JSON-coercion logic instead of duplicating it.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq


def bounded_row_indexes(row_count: int, max_points: int) -> list[int]:
    """Select deterministic, ordered row indexes while retaining both endpoints."""
    if row_count <= max_points:
        return list(range(row_count))
    last = row_count - 1
    return sorted({round(index * last / (max_points - 1)) for index in range(max_points)})


def json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [json_value(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


def load_table(path: Path, *, max_points: int | None = None) -> list[dict[str, Any]] | None:
    """Load one Parquet file into JSON-safe rows, or ``None`` if it doesn't exist.

    ``max_points`` bounds a per-bar dense series (e.g. an equity curve) to a
    deterministic, endpoint-preserving sample -- never used for a naturally
    small table (one row per trade/episode/label), where sampling would
    misrepresent the population.
    """
    if not path.is_file():
        return None
    table = pq.read_table(path)  # type: ignore[no-untyped-call]
    if max_points is not None:
        table = table.take(bounded_row_indexes(table.num_rows, max_points))
    return [json_value(row) for row in table.to_pylist()]


def read_json_mapping(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"expected JSON object: {path.name}")
    return payload


def required_string(payload: dict[str, Any], key: str) -> str:
    value = payload[key]
    if not isinstance(value, str) or not value:
        raise ValueError(f"missing {key}")
    return value
