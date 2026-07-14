"""Continuous futures roll schedule and materialization contracts."""

from trading_framework.market.continuous.builder import build_volume_rth_close_schedule
from trading_framework.market.continuous.policy import (
    ROLL_SCHEDULE_BUILDER_VERSION,
    VOLUME_RTH_CLOSE_POLICY_SLUG,
    RollSwitchAt,
    VolumeRthCloseRollPolicy,
)
from trading_framework.market.continuous.schedule import (
    ROLL_SCHEDULE_SCHEMA_VERSION,
    RollSchedule,
    RollScheduleEntry,
)
from trading_framework.market.continuous.volumes import aggregate_rth_session_volumes

__all__ = [
    "ROLL_SCHEDULE_BUILDER_VERSION",
    "ROLL_SCHEDULE_SCHEMA_VERSION",
    "VOLUME_RTH_CLOSE_POLICY_SLUG",
    "RollSchedule",
    "RollScheduleEntry",
    "RollSwitchAt",
    "VolumeRthCloseRollPolicy",
    "aggregate_rth_session_volumes",
    "build_volume_rth_close_schedule",
]
