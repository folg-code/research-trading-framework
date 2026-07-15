"""Local JSONL storage adapter for execution runtime events."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast, final

from trading_framework.execution.models import ExecutionEvent


@final
@dataclass(frozen=True, slots=True)
class JsonlExecutionEventSink:
    """Append execution events to a local JSONL file."""

    path: Path

    def append(self, event: ExecutionEvent) -> None:
        """Append one execution event as a single JSON line."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = execution_event_to_json_payload(event)
        line = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(f"{line}\n")


def execution_event_to_json_payload(event: ExecutionEvent) -> dict[str, Any]:
    """Serialize an execution event to a JSON-compatible mapping."""
    payload: Mapping[str, str] | None = event.payload
    return {
        "event_id": event.event_id,
        "event_type": event.event_type.value,
        "occurred_at": event.occurred_at.isoformat(),
        "mode": event.mode,
        "symbol": event.symbol,
        "payload": dict(payload) if payload is not None else None,
        "correlation_id": event.correlation_id,
    }


def read_jsonl_execution_events(path: Path) -> tuple[dict[str, Any], ...]:
    """Read JSONL execution events from a local file."""
    if not path.exists():
        return ()
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(cast("dict[str, Any]", json.loads(line)))
    return tuple(rows)
