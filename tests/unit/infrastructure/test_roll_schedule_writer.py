"""Roll schedule Parquet writer tests."""

from datetime import date
from pathlib import Path

from trading_framework.infrastructure.storage.parquet.roll_schedule_writer import (
    ParquetRollScheduleWriter,
    roll_schedule_entries_from_table,
    roll_schedule_entries_to_table,
)
from trading_framework.market.continuous.schedule import RollScheduleEntry


def _entry() -> RollScheduleEntry:
    return RollScheduleEntry(
        product="NQ",
        valid_from_session=date(2025, 3, 13),
        valid_to_session=date(2025, 3, 14),
        active_contract="NQH5",
        rule="volume-rth-close",
        evidence_volume=1000,
        roll_id="NQ-2025-03-13-NQH5",
    )


def test_roll_schedule_entries_round_trip_table() -> None:
    table = roll_schedule_entries_to_table([_entry()])
    restored = roll_schedule_entries_from_table(table)
    assert len(restored) == 1
    assert restored[0].active_contract == "NQH5"


def test_parquet_roll_schedule_writer_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "schedule.parquet"
    writer = ParquetRollScheduleWriter()
    writer.write(path, [_entry()])
    restored = writer.read(path)
    assert restored[0].roll_id == "NQ-2025-03-13-NQH5"
