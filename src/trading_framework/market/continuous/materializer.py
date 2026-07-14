"""Stitch contract trades into continuous trade records using a roll schedule."""

from __future__ import annotations

from datetime import date

from trading_framework.core.exceptions import ValidationError
from trading_framework.market.continuous.identity import continuous_symbol_label
from trading_framework.market.continuous.schedule import (
    RollSchedule,
    RollScheduleEntry,
    entry_for_session,
)
from trading_framework.market.continuous.trade_record import ContinuousTradeRecord
from trading_framework.market.contracts.trade_record import ContractTradeRecord


def _entry_for_session(
    schedule: RollSchedule,
    session_date: date,
) -> RollScheduleEntry | None:
    return entry_for_session(schedule, session_date)


def is_roll_boundary_session(schedule: RollSchedule, session_date: date) -> bool:
    """Return whether ``session_date`` is the first session of a post-roll segment."""
    entry = entry_for_session(schedule, session_date)
    if entry is None:
        return False
    for index, candidate in enumerate(schedule.entries):
        if candidate.roll_id == entry.roll_id:
            return index > 0 and session_date == entry.valid_from_session
    return False


def sessions_covered_by_schedule(
    schedule: RollSchedule,
    *,
    start_session: date,
    end_session: date,
) -> tuple[date, ...]:
    """Return sorted session dates in range that the schedule covers."""
    if end_session < start_session:
        msg = "end_session must not be before start_session"
        raise ValidationError(msg)
    covered: list[date] = []
    current = start_session
    while current <= end_session:
        if _entry_for_session(schedule, current) is not None:
            covered.append(current)
        current = date.fromordinal(current.toordinal() + 1)
    return tuple(covered)


def materialize_session_records(
    schedule: RollSchedule,
    *,
    session_date: date,
    contract_records: list[ContractTradeRecord],
) -> tuple[ContinuousTradeRecord, ...]:
    """Convert one session of contract trades into continuous trade records."""
    entry = _entry_for_session(schedule, session_date)
    if entry is None:
        return ()

    active_contract = entry.active_contract
    session_records = [
        record
        for record in contract_records
        if record.session_date == session_date and record.actual_contract == active_contract
    ]
    if not session_records:
        return ()

    boundary = is_roll_boundary_session(schedule, session_date)
    symbol = continuous_symbol_label(schedule.product)
    return tuple(
        ContinuousTradeRecord(
            trade=record.trade,
            actual_contract=record.actual_contract,
            product=record.product,
            session_date=record.session_date,
            continuous_symbol=symbol,
            roll_id=entry.roll_id,
            is_roll_boundary=boundary,
        )
        for record in sorted(session_records, key=lambda item: item.trade.event_at)
    )
