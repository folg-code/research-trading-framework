"""Tests for local BTC futures dry-run runtime assembly."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from trading_framework.application.execution import (
    LocalBtcFuturesDryRunConfig,
    RunLocalBtcFuturesDryRunRequest,
    create_local_btc_futures_dry_run_runtime,
    run_local_btc_futures_closed_bar_feed_step,
    run_local_btc_futures_closed_bar_step,
    run_local_btc_futures_dry_run,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.core.types import Price, Volume
from trading_framework.execution import (
    BestBidAskSnapshot,
    ExecutionEventType,
    ExecutionReadModelQuery,
    OrderIntent,
    OrderSide,
    OrderType,
)
from trading_framework.infrastructure.storage.execution_events import read_jsonl_execution_events
from trading_framework.market.models import MarketBar
from trading_framework.strategy import BtcFuturesDemoStrategyConfig
from trading_framework.time.clocks.fixed import FixedClock

NOW = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)


def _bar(close: str, index: int) -> MarketBar:
    close_price = Price(Decimal(close))
    observed_at = NOW + timedelta(minutes=index)
    return MarketBar(
        open=close_price,
        high=close_price,
        low=close_price,
        close=close_price,
        volume=Volume(1),
        observed_at=observed_at,
        available_at=observed_at + timedelta(minutes=1),
    )


def test_create_local_btc_futures_dry_run_runtime_assembles_components(tmp_path: Path) -> None:
    runtime = create_local_btc_futures_dry_run_runtime(
        LocalBtcFuturesDryRunConfig(event_log_path=tmp_path / "events.jsonl"),
        clock=FixedClock(NOW),
    )

    assert runtime.config.symbol == "BTCUSDT"
    assert runtime.initial_state.account.equity == Decimal("10000")
    assert runtime.initial_state.position.quantity == Decimal("0")
    assert runtime.session.latest_status(runtime.config.runtime_id) is None


def test_local_btc_futures_runtime_decision_step_writes_jsonl_events(tmp_path: Path) -> None:
    event_log_path = tmp_path / "execution" / "events.jsonl"
    runtime = create_local_btc_futures_dry_run_runtime(
        LocalBtcFuturesDryRunConfig(event_log_path=event_log_path),
        clock=FixedClock(NOW),
    )
    quote = BestBidAskSnapshot(
        symbol="BTCUSDT",
        bid_price=Price(Decimal("65000")),
        ask_price=Price(Decimal("65010")),
        event_at=NOW,
    )

    result = runtime.decision_step.run(
        entry_signal_active=True,
        exit_signal_active=False,
        position=runtime.initial_state.position,
        quote=quote,
    )

    assert result.order_submitted
    rows = read_jsonl_execution_events(event_log_path)
    assert [row["event_type"] for row in rows] == [
        ExecutionEventType.MARKET_EVENT_RECEIVED.value,
        ExecutionEventType.ORDER_INTENT_CREATED.value,
        ExecutionEventType.SIMULATED_ORDER_FILLED.value,
        ExecutionEventType.POSITION_UPDATED.value,
    ]
    assert rows[-1]["payload"]["side"] == "long"


def test_local_btc_futures_runtime_accepts_strategy_config(tmp_path: Path) -> None:
    runtime = create_local_btc_futures_dry_run_runtime(
        LocalBtcFuturesDryRunConfig(
            event_log_path=tmp_path / "events.jsonl",
            strategy_config=BtcFuturesDemoStrategyConfig(quantity=Decimal("0.002")),
        ),
        clock=FixedClock(NOW),
    )
    quote = BestBidAskSnapshot(
        symbol="BTCUSDT",
        bid_price=Price(Decimal("65000")),
        ask_price=Price(Decimal("65010")),
        event_at=NOW,
    )

    result = runtime.decision_step.run(
        entry_signal_active=True,
        exit_signal_active=False,
        position=runtime.initial_state.position,
        quote=quote,
    )

    assert result.broker_result is not None
    assert result.broker_result.position.quantity == Decimal("0.002")


def test_local_btc_futures_closed_bar_step_runs_signal_to_paper_fill(
    tmp_path: Path,
) -> None:
    event_log_path = tmp_path / "events.jsonl"
    runtime = create_local_btc_futures_dry_run_runtime(
        LocalBtcFuturesDryRunConfig(
            event_log_path=event_log_path,
            strategy_config=BtcFuturesDemoStrategyConfig(ema_period=3),
        ),
        clock=FixedClock(NOW),
    )

    result = run_local_btc_futures_closed_bar_step(
        runtime,
        (_bar("100", 0), _bar("100", 1), _bar("101", 2)),
    )

    assert result.signal_evaluation.entry_signal_active
    assert result.decision_result.order_submitted
    assert result.broker_state.position.quantity == Decimal("0.001")
    rows = read_jsonl_execution_events(event_log_path)
    assert [row["event_type"] for row in rows] == [
        ExecutionEventType.MARKET_EVENT_RECEIVED.value,
        ExecutionEventType.ORDER_INTENT_CREATED.value,
        ExecutionEventType.SIMULATED_ORDER_FILLED.value,
        ExecutionEventType.POSITION_UPDATED.value,
    ]
    assert rows[-1]["payload"]["simulated"] == "true"
    status_view = runtime.state_repository.latest_status_view(
        ExecutionReadModelQuery(runtime_id=runtime.config.runtime_id)
    )
    assert status_view is not None
    assert status_view.current_signal == "entry_signal_active"
    assert status_view.paper_equity is not None
    assert status_view.recent_orders[0].order_id == "paper-order-1"
    assert status_view.recent_fills[0].fill_id == "paper-fill-1"
    assert [event.event_type for event in status_view.recent_events] == [
        ExecutionEventType.MARKET_EVENT_RECEIVED,
        ExecutionEventType.ORDER_INTENT_CREATED,
        ExecutionEventType.SIMULATED_ORDER_FILLED,
        ExecutionEventType.POSITION_UPDATED,
    ]


def test_local_btc_futures_closed_bar_feed_step_keeps_rolling_history(
    tmp_path: Path,
) -> None:
    runtime = create_local_btc_futures_dry_run_runtime(
        LocalBtcFuturesDryRunConfig(
            event_log_path=tmp_path / "events.jsonl",
            strategy_config=BtcFuturesDemoStrategyConfig(ema_period=3),
        ),
        clock=FixedClock(NOW),
    )
    closed_bars: tuple[MarketBar, ...] = ()

    first = run_local_btc_futures_closed_bar_feed_step(
        runtime,
        closed_bars=closed_bars,
        bar=_bar("100", 0),
        max_closed_bars=3,
    )
    second = run_local_btc_futures_closed_bar_feed_step(
        runtime,
        closed_bars=first.closed_bars,
        bar=_bar("100", 1),
        max_closed_bars=3,
    )
    third = run_local_btc_futures_closed_bar_feed_step(
        runtime,
        closed_bars=second.closed_bars,
        bar=_bar("101", 2),
        max_closed_bars=3,
    )
    fourth = run_local_btc_futures_closed_bar_feed_step(
        runtime,
        closed_bars=third.closed_bars,
        bar=_bar("102", 3),
        max_closed_bars=3,
    )

    assert not first.step_result.decision_result.order_submitted
    assert not second.step_result.decision_result.order_submitted
    assert third.step_result.decision_result.order_submitted
    assert len(fourth.closed_bars) == 3
    assert fourth.closed_bars[0].close.value == Decimal("100")
    assert fourth.closed_bars[-1].close.value == Decimal("102")
    assert not fourth.step_result.decision_result.order_submitted


def test_local_btc_futures_closed_bar_feed_step_exits_after_fixed_bars(
    tmp_path: Path,
) -> None:
    runtime = create_local_btc_futures_dry_run_runtime(
        LocalBtcFuturesDryRunConfig(
            event_log_path=tmp_path / "events.jsonl",
            strategy_config=BtcFuturesDemoStrategyConfig(ema_period=3, exit_after_bars=2),
        ),
        clock=FixedClock(NOW),
    )
    closed_bars: tuple[MarketBar, ...] = ()

    first = run_local_btc_futures_closed_bar_feed_step(
        runtime,
        closed_bars=closed_bars,
        bar=_bar("100", 0),
        max_closed_bars=10,
    )
    second = run_local_btc_futures_closed_bar_feed_step(
        runtime,
        closed_bars=first.closed_bars,
        bar=_bar("100", 1),
        max_closed_bars=10,
    )
    entry = run_local_btc_futures_closed_bar_feed_step(
        runtime,
        closed_bars=second.closed_bars,
        bar=_bar("101", 2),
        max_closed_bars=10,
    )
    hold = run_local_btc_futures_closed_bar_feed_step(
        runtime,
        closed_bars=entry.closed_bars,
        bar=_bar("102", 3),
        max_closed_bars=10,
    )
    exit_step = run_local_btc_futures_closed_bar_feed_step(
        runtime,
        closed_bars=hold.closed_bars,
        bar=_bar("103", 4),
        max_closed_bars=10,
    )

    assert entry.step_result.decision_result.order_submitted
    assert entry.step_result.broker_state.position.quantity == Decimal("0.001")
    assert not hold.step_result.decision_result.order_submitted
    assert exit_step.step_result.signal_evaluation.exit_signal_active
    assert exit_step.step_result.decision_result.order_submitted
    assert exit_step.step_result.broker_state.position.quantity == Decimal("0")

    status_view = runtime.state_repository.latest_status_view(
        ExecutionReadModelQuery(runtime_id=runtime.config.runtime_id)
    )
    assert status_view is not None
    assert status_view.current_position is not None
    assert status_view.current_position.quantity == Decimal("0")
    assert [fill.side for fill in status_view.recent_fills] == [
        OrderSide.BUY,
        OrderSide.SELL,
    ]
    assert status_view.current_signal == "exit_signal_active"


def test_local_btc_futures_runtime_restores_previous_paper_state(tmp_path: Path) -> None:
    config = LocalBtcFuturesDryRunConfig(
        event_log_path=tmp_path / "execution" / "events.jsonl",
        strategy_config=BtcFuturesDemoStrategyConfig(ema_period=3),
    )
    runtime = create_local_btc_futures_dry_run_runtime(config, clock=FixedClock(NOW))

    result = run_local_btc_futures_closed_bar_step(
        runtime,
        (_bar("100", 0), _bar("100", 1), _bar("101", 2)),
    )
    restored_runtime = create_local_btc_futures_dry_run_runtime(
        config,
        clock=FixedClock(NOW + timedelta(minutes=10)),
    )

    assert result.decision_result.order_submitted
    assert restored_runtime.initial_state.position.quantity == Decimal("0.001")
    assert restored_runtime.initial_state.position.average_entry_price == Price(Decimal("101"))
    assert restored_runtime.initial_state.account.equity == Decimal("10000")
    marked = restored_runtime.broker.mark_to_market(
        Price(Decimal("103")),
        NOW + timedelta(minutes=10),
    )
    next_order = restored_runtime.broker.accept_market_order(
        OrderIntent(
            intent_id="restart-intent-1",
            strategy_id="demo-momentum",
            symbol="BTCUSDT",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=Decimal("0.001"),
            requested_at=NOW + timedelta(minutes=10),
        ),
        BestBidAskSnapshot(
            symbol="BTCUSDT",
            bid_price=Price(Decimal("103")),
            ask_price=Price(Decimal("104")),
            event_at=NOW + timedelta(minutes=10),
        ),
    )
    assert marked.position.quantity == Decimal("0.001")
    assert marked.account.unrealized_pnl == Decimal("0.002")
    assert next_order.order.order_id == "paper-order-2"
    assert next_order.fill.fill_id == "paper-fill-2"


def test_run_local_btc_futures_dry_run_records_bounded_lifecycle(tmp_path: Path) -> None:
    event_log_path = tmp_path / "events.jsonl"

    result = run_local_btc_futures_dry_run(
        RunLocalBtcFuturesDryRunRequest(
            config=LocalBtcFuturesDryRunConfig(event_log_path=event_log_path),
            duration_minutes=0,
            heartbeat_seconds=1,
        ),
        clock=FixedClock(NOW),
    )

    assert result.stopped_status.status.value == "stopped"
    rows = read_jsonl_execution_events(event_log_path)
    assert [row["event_type"] for row in rows] == [
        "runtime_started",
        "heartbeat_recorded",
        "runtime_stopped",
    ]
    status_view = result.runtime.state_repository.latest_status_view(
        ExecutionReadModelQuery(runtime_id=result.runtime.config.runtime_id)
    )
    assert status_view is not None
    assert status_view.status.value == "stopped"
    assert status_view.paper_equity == Decimal("10000")
    assert [event.event_type.value for event in status_view.recent_events] == [
        "runtime_started",
        "heartbeat_recorded",
        "runtime_stopped",
    ]


def test_local_btc_futures_config_rejects_invalid_values(tmp_path: Path) -> None:
    with pytest.raises(ValidationError, match="runtime_id"):
        LocalBtcFuturesDryRunConfig(
            event_log_path=tmp_path / "events.jsonl",
            runtime_id=" ",
        )

    with pytest.raises(ValidationError, match="starting_equity"):
        LocalBtcFuturesDryRunConfig(
            event_log_path=tmp_path / "events.jsonl",
            starting_equity=Decimal("0"),
        )

    with pytest.raises(ValidationError, match="duration_minutes"):
        RunLocalBtcFuturesDryRunRequest(
            config=LocalBtcFuturesDryRunConfig(event_log_path=tmp_path / "events.jsonl"),
            duration_minutes=-1,
        )
