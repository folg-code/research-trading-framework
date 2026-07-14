"""Roll schedule Parquet persistence."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from trading_framework.market.continuous.schedule import RollScheduleEntry

ROLL_SCHEDULE_PARQUET_SCHEMA = pa.schema(
    [
        ("product", pa.string()),
        ("valid_from_session", pa.date32()),
        ("valid_to_session", pa.date32()),
        ("active_contract", pa.string()),
        ("rule", pa.string()),
        ("evidence_volume", pa.int64()),
        ("roll_id", pa.string()),
    ]
)


def _entry_to_columns(entry: RollScheduleEntry) -> dict[str, object]:
    return {
        "product": entry.product,
        "valid_from_session": entry.valid_from_session,
        "valid_to_session": entry.valid_to_session,
        "active_contract": entry.active_contract,
        "rule": entry.rule,
        "evidence_volume": entry.evidence_volume,
        "roll_id": entry.roll_id,
    }


def roll_schedule_entries_to_table(entries: Sequence[RollScheduleEntry]) -> pa.Table:
    """Convert roll schedule entries to a Parquet table."""
    if not entries:
        return pa.table(
            {field.name: pa.array([], type=field.type) for field in ROLL_SCHEDULE_PARQUET_SCHEMA},
            schema=ROLL_SCHEDULE_PARQUET_SCHEMA,
        )
    return pa.table(
        {
            field.name: [_entry_to_columns(entry)[field.name] for entry in entries]
            for field in ROLL_SCHEDULE_PARQUET_SCHEMA
        },
        schema=ROLL_SCHEDULE_PARQUET_SCHEMA,
    )


def roll_schedule_entries_from_table(table: pa.Table) -> list[RollScheduleEntry]:
    """Materialize roll schedule entries from Parquet."""
    normalized = table.cast(ROLL_SCHEDULE_PARQUET_SCHEMA)
    rows = normalized.to_pylist()
    entries: list[RollScheduleEntry] = []
    for row in rows:
        valid_from = row["valid_from_session"]
        valid_to = row["valid_to_session"]
        entries.append(
            RollScheduleEntry(
                product=str(row["product"]),
                valid_from_session=(
                    valid_from
                    if isinstance(valid_from, date)
                    else date.fromisoformat(str(valid_from))
                ),
                valid_to_session=(
                    valid_to if isinstance(valid_to, date) else date.fromisoformat(str(valid_to))
                ),
                active_contract=str(row["active_contract"]),
                rule=str(row["rule"]),
                evidence_volume=int(row["evidence_volume"]),
                roll_id=str(row["roll_id"]),
            )
        )
    return entries


class ParquetRollScheduleWriter:
    """Write roll schedule entries to Parquet."""

    def write(self, path: Path, entries: Sequence[RollScheduleEntry]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        table = roll_schedule_entries_to_table(entries)
        pq.write_table(table, path)  # type: ignore[no-untyped-call]

    def read(self, path: Path) -> list[RollScheduleEntry]:
        table = pq.ParquetFile(path).read()  # type: ignore[no-untyped-call]
        return roll_schedule_entries_from_table(table)
