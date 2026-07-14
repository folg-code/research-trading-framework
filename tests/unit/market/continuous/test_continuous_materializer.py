"""Continuous trade materializer tests."""

from datetime import date

from tests.fixtures.contracts.trade_record import make_rth_contract_trade_record
from trading_framework.market.continuous.materializer import (
    is_roll_boundary_session,
    materialize_session_records,
)
from trading_framework.market.continuous.policy import VolumeRthCloseRollPolicy
from trading_framework.market.continuous.schedule import RollSchedule, RollScheduleEntry
from trading_framework.market.contracts.trade_record import ContractTradeRecord


def _contract_record(*, contract: str, session_date: date, size: int) -> ContractTradeRecord:
    return make_rth_contract_trade_record(
        contract=contract,
        session_date=session_date,
        size=size,
    )


def _schedule() -> RollSchedule:
    policy = VolumeRthCloseRollPolicy(product="NQ")
    entries = (
        RollScheduleEntry(
            product="NQ",
            valid_from_session=date(2025, 7, 13),
            valid_to_session=date(2025, 7, 13),
            active_contract="NQU5",
            rule="volume-rth-close",
            evidence_volume=100,
            roll_id="roll-1",
        ),
        RollScheduleEntry(
            product="NQ",
            valid_from_session=date(2025, 7, 14),
            valid_to_session=date(2025, 7, 14),
            active_contract="NQZ5",
            rule="volume-rth-close",
            evidence_volume=200,
            roll_id="roll-2",
        ),
    )
    return RollSchedule(product="NQ", policy=policy, version=1, entries=entries)


def test_materialize_session_records_uses_active_contract_only() -> None:
    schedule = _schedule()
    records = materialize_session_records(
        schedule,
        session_date=date(2025, 7, 14),
        contract_records=[
            _contract_record(contract="NQU5", session_date=date(2025, 7, 14), size=10),
            _contract_record(contract="NQZ5", session_date=date(2025, 7, 14), size=20),
        ],
    )

    assert len(records) == 1
    assert records[0].actual_contract == "NQZ5"
    assert records[0].continuous_symbol == "NQ_CONT"
    assert records[0].roll_id == "roll-2"


def test_roll_boundary_session_flags_second_segment_start() -> None:
    schedule = _schedule()

    assert is_roll_boundary_session(schedule, date(2025, 7, 13)) is False
    assert is_roll_boundary_session(schedule, date(2025, 7, 14)) is True

    first_segment = materialize_session_records(
        schedule,
        session_date=date(2025, 7, 13),
        contract_records=[
            _contract_record(contract="NQU5", session_date=date(2025, 7, 13), size=10),
        ],
    )
    second_segment = materialize_session_records(
        schedule,
        session_date=date(2025, 7, 14),
        contract_records=[
            _contract_record(contract="NQZ5", session_date=date(2025, 7, 14), size=20),
        ],
    )

    assert first_segment[0].is_roll_boundary is False
    assert second_segment[0].is_roll_boundary is True
