"""Tests for `research run signal`'s structured phase events (Sprint 064 T005, D-S064-04).

Tier 1, network-free -- same fixture/config-building helpers as
`test_research.py`'s signal-research section, imported rather than
duplicated.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from trading_framework.application.signal_research import SignalResearchError

from test_research import _write_config, _write_published_dataset, _write_signal_definition
from trading_cli.cli import main
from trading_cli.errors import EXIT_SUCCESS
from trading_cli.phase_events import PHASE_EVENT_SCHEMA_VERSION, SIGNAL_RESEARCH_RUN_PHASES


def _build_signal_config(tmp_path: Path, ohlcv_sample_1m_path: Path) -> Path:
    storage_root = tmp_path / "workspace"
    dataset_ref = _write_published_dataset(storage_root, csv_path=ohlcv_sample_1m_path)
    definition_path = tmp_path / "signal_definition.yaml"
    _write_signal_definition(definition_path, dataset_ref=dataset_ref)
    return _write_config(
        tmp_path,
        storage_root=storage_root,
        text=(
            "version: 1\n"
            "storage_root: {storage_root}\n\n"
            "research:\n"
            "  kind: signal\n"
            "  signal:\n"
            f"    definition: {definition_path.as_posix()}\n"
        ),
    )


def _phase_events(stdout: str) -> list[dict[str, object]]:
    """Extract phase-event lines from stdout, ignoring the (pretty-printed,
    multi-line) `--json` summary `dump_json` prints alongside them."""
    events = []
    for line in stdout.splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("event") == "phase":
            events.append(payload)
    return events


def test_research_run_signal_emits_phase_events_in_order(
    tmp_path: Path, ohlcv_sample_1m_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_path = _build_signal_config(tmp_path, ohlcv_sample_1m_path)

    exit_code = main(["research", "run", "--config", str(config_path), "--json"])

    assert exit_code == EXIT_SUCCESS
    events = _phase_events(capsys.readouterr().out)
    assert [event["name"] for event in events] == list(SIGNAL_RESEARCH_RUN_PHASES)
    for position, event in enumerate(events, start=1):
        assert event["schema_version"] == PHASE_EVENT_SCHEMA_VERSION
        assert event["job_kind"] == "research.run.signal"
        assert event["index"] == position
        assert event["of"] == len(SIGNAL_RESEARCH_RUN_PHASES)
        assert event["at"]


def test_research_run_signal_without_json_emits_no_phase_events(
    tmp_path: Path, ohlcv_sample_1m_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config_path = _build_signal_config(tmp_path, ohlcv_sample_1m_path)

    exit_code = main(["research", "run", "--config", str(config_path)])

    assert exit_code == EXIT_SUCCESS
    assert _phase_events(capsys.readouterr().out) == []


def test_research_run_signal_dry_run_emits_no_phase_events(
    tmp_path: Path, ohlcv_sample_1m_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """No event is emitted before validation completes: --dry-run never reaches
    the run body that emits them, in --json mode or otherwise."""
    config_path = _build_signal_config(tmp_path, ohlcv_sample_1m_path)

    exit_code = main(["research", "run", "--config", str(config_path), "--dry-run", "--json"])

    assert exit_code == EXIT_SUCCESS
    out = capsys.readouterr().out
    assert _phase_events(out) == []
    # the single dry-run plan line is still there, untouched
    assert json.loads(out)["status"] == "dry_run"


def test_research_run_signal_failure_emits_no_event_after_the_failing_phase(
    tmp_path: Path, ohlcv_sample_1m_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A job that fails mid-phase emits no further phase events (D-S064-04):
    the failure is the exit code, not an event."""
    config_path = _build_signal_config(tmp_path, ohlcv_sample_1m_path)

    with patch(
        "trading_cli.commands.research.run_signal_research",
        side_effect=SignalResearchError("synthetic failure for T005 test"),
    ):
        exit_code = main(["research", "run", "--config", str(config_path), "--json"])

    assert exit_code != EXIT_SUCCESS
    events = _phase_events(capsys.readouterr().out)
    assert [event["name"] for event in events] == [
        "load-definition",
        "resolve-models",
        "load-dataset",
        "evaluate",
    ]
