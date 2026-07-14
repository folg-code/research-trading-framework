"""Volume roll schedule builder tests."""

from datetime import date

from trading_framework.market.continuous import (
    VolumeRthCloseRollPolicy,
    build_volume_rth_close_schedule,
)


def test_build_volume_rth_close_schedule_switches_after_confirmation() -> None:
    session_volumes = {
        date(2025, 3, 13): {"NQH5": 1000, "NQM5": 500},
        date(2025, 3, 14): {"NQH5": 400, "NQM5": 900},
        date(2025, 3, 17): {"NQH5": 200, "NQM5": 1200},
    }
    policy = VolumeRthCloseRollPolicy(product="NQ", confirmation_sessions=1)

    entries = build_volume_rth_close_schedule(session_volumes, policy=policy)

    assert len(entries) == 2
    assert entries[0].active_contract == "NQH5"
    assert entries[0].valid_from_session == date(2025, 3, 13)
    assert entries[0].valid_to_session == date(2025, 3, 14)
    assert entries[1].active_contract == "NQM5"
    assert entries[1].valid_from_session == date(2025, 3, 17)


def test_roll_schedule_active_contract_lookup() -> None:
    from trading_framework.market.continuous.schedule import RollSchedule, RollScheduleEntry

    policy = VolumeRthCloseRollPolicy(product="NQ")
    entries = (
        RollScheduleEntry(
            product="NQ",
            valid_from_session=date(2025, 3, 13),
            valid_to_session=date(2025, 3, 14),
            active_contract="NQH5",
            rule="volume-rth-close",
            evidence_volume=1000,
            roll_id="roll-1",
        ),
        RollScheduleEntry(
            product="NQ",
            valid_from_session=date(2025, 3, 17),
            valid_to_session=date(2025, 3, 17),
            active_contract="NQM5",
            rule="volume-rth-close",
            evidence_volume=1200,
            roll_id="roll-2",
        ),
    )
    schedule = RollSchedule(product="NQ", policy=policy, version=1, entries=entries)

    assert schedule.active_contract_for_session(date(2025, 3, 14)) == "NQH5"
    assert schedule.active_contract_for_session(date(2025, 3, 17)) == "NQM5"
    assert schedule.active_contract_for_session(date(2025, 3, 16)) is None
