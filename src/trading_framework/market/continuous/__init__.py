"""Continuous futures roll schedule and materialization contracts."""

from trading_framework.market.continuous.builder import build_volume_rth_close_schedule
from trading_framework.market.continuous.identity import (
    CONTINUOUS_BUILDER_VERSION,
    CONTINUOUS_TRADES_PROVIDER,
    continuous_instrument_id,
    continuous_symbol_label,
)
from trading_framework.market.continuous.materializer import (
    is_roll_boundary_session,
    materialize_session_records,
    sessions_covered_by_schedule,
)
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
from trading_framework.market.continuous.trade_record import (
    MARKET_TRADE_CONTINUOUS_SCHEMA_VERSION,
    ContinuousTradeRecord,
)
from trading_framework.market.continuous.volumes import aggregate_rth_session_volumes

__all__ = [
    "CONTINUOUS_BUILDER_VERSION",
    "CONTINUOUS_TRADES_PROVIDER",
    "MARKET_TRADE_CONTINUOUS_SCHEMA_VERSION",
    "ROLL_SCHEDULE_BUILDER_VERSION",
    "ROLL_SCHEDULE_SCHEMA_VERSION",
    "VOLUME_RTH_CLOSE_POLICY_SLUG",
    "ContinuousTradeRecord",
    "RollSchedule",
    "RollScheduleEntry",
    "RollSwitchAt",
    "VolumeRthCloseRollPolicy",
    "aggregate_rth_session_volumes",
    "build_volume_rth_close_schedule",
    "continuous_instrument_id",
    "continuous_symbol_label",
    "is_roll_boundary_session",
    "materialize_session_records",
    "sessions_covered_by_schedule",
]
