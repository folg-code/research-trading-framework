"""Volume-based roll schedule construction."""

from __future__ import annotations

from datetime import date

from trading_framework.market.continuous.policy import (
    VOLUME_RTH_CLOSE_POLICY_SLUG,
    VolumeRthCloseRollPolicy,
)
from trading_framework.market.continuous.schedule import RollScheduleEntry


def build_volume_rth_close_schedule(
    session_volumes: dict[date, dict[str, int]],
    *,
    policy: VolumeRthCloseRollPolicy,
) -> tuple[RollScheduleEntry, ...]:
    """Build roll schedule segments from per-session RTH volumes by contract."""
    if policy.slug != VOLUME_RTH_CLOSE_POLICY_SLUG:
        msg = f"unsupported roll policy slug: {policy.slug!r}"
        raise ValueError(msg)

    sessions = sorted(session for session, volumes in session_volumes.items() if volumes)
    if not sessions:
        return ()

    active_contract = _initial_active_contract(session_volumes[sessions[0]])
    segment_start = sessions[0]
    pending_candidate: str | None = None
    pending_confirmations = 0
    entries: list[RollScheduleEntry] = []

    for index, session in enumerate(sessions):
        volumes = session_volumes[session]
        leader = max(volumes, key=volumes.get)  # type: ignore[arg-type]

        if leader != active_contract:
            if pending_candidate == leader:
                pending_confirmations += 1
            else:
                pending_candidate = leader
                pending_confirmations = 1

            if pending_confirmations >= policy.confirmation_sessions:
                entries.append(
                    _schedule_entry(
                        product=policy.product,
                        valid_from_session=segment_start,
                        valid_to_session=session,
                        active_contract=active_contract,
                        evidence_volume=volumes.get(active_contract, 0),
                    )
                )
                if index + 1 < len(sessions):
                    segment_start = sessions[index + 1]
                    active_contract = leader
                else:
                    segment_start = session
                    active_contract = leader
                pending_candidate = None
                pending_confirmations = 0
        else:
            pending_candidate = None
            pending_confirmations = 0

    if segment_start <= sessions[-1]:
        entries.append(
            _schedule_entry(
                product=policy.product,
                valid_from_session=segment_start,
                valid_to_session=sessions[-1],
                active_contract=active_contract,
                evidence_volume=session_volumes[sessions[-1]].get(active_contract, 0),
            )
        )

    return _dedupe_adjacent_entries(entries)


def _initial_active_contract(volumes: dict[str, int]) -> str:
    return max(volumes, key=volumes.get)  # type: ignore[arg-type]


def _schedule_entry(
    *,
    product: str,
    valid_from_session: date,
    valid_to_session: date,
    active_contract: str,
    evidence_volume: int,
) -> RollScheduleEntry:
    return RollScheduleEntry(
        product=product,
        valid_from_session=valid_from_session,
        valid_to_session=valid_to_session,
        active_contract=active_contract,
        rule=VOLUME_RTH_CLOSE_POLICY_SLUG,
        evidence_volume=evidence_volume,
        roll_id=f"{product}-{valid_from_session.isoformat()}-{active_contract}",
    )


def _dedupe_adjacent_entries(entries: list[RollScheduleEntry]) -> tuple[RollScheduleEntry, ...]:
    if not entries:
        return ()
    merged: list[RollScheduleEntry] = [entries[0]]
    for entry in entries[1:]:
        previous = merged[-1]
        if (
            previous.active_contract == entry.active_contract
            and previous.valid_to_session < entry.valid_from_session
        ):
            merged[-1] = _schedule_entry(
                product=previous.product,
                valid_from_session=previous.valid_from_session,
                valid_to_session=entry.valid_to_session,
                active_contract=previous.active_contract,
                evidence_volume=entry.evidence_volume,
            )
        else:
            merged.append(entry)
    return tuple(merged)
