"""Continuous trade Arrow table mapper tests."""

from datetime import date

from tests.fixtures.contracts.trade_record import make_rth_contract_trade_record
from trading_framework.infrastructure.storage.parquet.continuous_trade_table_mapper import (
    contract_table_to_continuous_table,
)
from trading_framework.infrastructure.storage.parquet.continuous_trade_writer import (
    continuous_trade_records_to_table,
)
from trading_framework.infrastructure.storage.parquet.contract_trade_writer import (
    contract_trade_records_to_table,
)
from trading_framework.market.continuous.materializer import materialize_session_records
from trading_framework.market.continuous.policy import VolumeRthCloseRollPolicy
from trading_framework.market.continuous.schedule import RollSchedule, RollScheduleEntry


def _schedule() -> RollSchedule:
    policy = VolumeRthCloseRollPolicy(product="NQ")
    return RollSchedule(
        product="NQ",
        policy=policy,
        version=1,
        entries=(
            RollScheduleEntry(
                product="NQ",
                valid_from_session=date(2025, 7, 14),
                valid_to_session=date(2025, 7, 14),
                active_contract="NQZ5",
                rule="volume-rth-close",
                evidence_volume=200,
                roll_id="roll-2",
            ),
        ),
    )


def test_contract_table_to_continuous_table_matches_domain_materializer() -> None:
    schedule = _schedule()
    session_date = date(2025, 7, 14)
    contract_records = [
        make_rth_contract_trade_record(
            contract="NQU5",
            session_date=session_date,
            size=10,
        ),
        make_rth_contract_trade_record(
            contract="NQZ5",
            session_date=session_date,
            size=20,
        ),
    ]
    contract_table = contract_trade_records_to_table(contract_records)
    domain_records = materialize_session_records(
        schedule,
        session_date=session_date,
        contract_records=contract_records,
    )
    expected = continuous_trade_records_to_table(domain_records).cast(
        contract_table_to_continuous_table(
            contract_table,
            schedule=schedule,
            session_date=session_date,
            active_contract="NQZ5",
        ).schema
    )
    actual = contract_table_to_continuous_table(
        contract_table,
        schedule=schedule,
        session_date=session_date,
        active_contract="NQZ5",
    )

    assert actual.num_rows == 1
    assert actual.to_pylist() == expected.to_pylist()
