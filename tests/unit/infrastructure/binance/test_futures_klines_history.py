"""Tests for the paginated Binance USD-M historical klines reader."""

from __future__ import annotations

from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from trading_framework.infrastructure.providers.binance import (
    BINANCE_API_KEY_ENV_VAR,
    BinanceKlinesHistoryError,
    BinanceKlinesRetryExhaustedError,
    fetch_historical_klines,
    resolve_binance_api_key,
)

_INTERVAL_MS = 60_000


class _FakeResponse:
    def __init__(self, rows: list[list[Any]], used_weight: int = 100) -> None:
        import json

        self._body = json.dumps(rows).encode("utf-8")
        self.headers = _FakeHeaders({"X-MBX-USED-WEIGHT-1M": str(used_weight)})

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class _FakeHeaders:
    def __init__(self, values: dict[str, str]) -> None:
        self._values = values

    def get(self, name: str, default: str | None = None) -> str | None:
        return self._values.get(name, default)


def _row(open_ms: int, close: str) -> list[Any]:
    return [
        open_ms,
        close,
        close,
        close,
        close,
        "1.0",
        open_ms + _INTERVAL_MS - 1,
        "0",
        0,
        "0",
        "0",
        "0",
    ]


def _no_sleep_calls() -> tuple[list[float], Any]:
    calls: list[float] = []

    def sleep(delay: float) -> None:
        calls.append(delay)

    return calls, sleep


def test_fetch_historical_klines_assembles_multi_page_range_in_order() -> None:
    """A range spanning two pages assembles ascending bars with no duplicates."""
    page_one = [_row(0, "100"), _row(60_000, "101")]
    page_two = [_row(120_000, "102"), _row(180_000, "103")]
    pages = [page_one, page_two]
    calls: list[Request] = []

    def fake_urlopen(request: Request, timeout: float | None = None) -> _FakeResponse:
        calls.append(request)
        return _FakeResponse(pages.pop(0))

    result = fetch_historical_klines(
        symbol="btcusdt",
        interval="1m",
        start_ms=0,
        end_ms=240_000,
        page_limit=2,
        urlopen=fake_urlopen,
        now_ms=10_000_000,
    )

    assert [float(bar.close.value) for bar in result.bars] == [100.0, 101.0, 102.0, 103.0]
    assert len(calls) == 2
    assert result.stats.page_count == 2
    assert result.stats.gaps == ()
    assert result.stats.rows_rejected == 0
    open_times = [bar.observed_at for bar in result.bars]
    assert open_times == sorted(open_times)
    assert len(set(open_times)) == len(open_times)


def test_fetch_historical_klines_drops_duplicate_open_time_across_pages() -> None:
    """The last row of a page may reappear as the first row of the next page."""
    page_one = [_row(0, "100"), _row(60_000, "101")]
    page_two = [_row(60_000, "101"), _row(120_000, "102")]
    pages = [page_one, page_two]

    def fake_urlopen(request: Request, timeout: float | None = None) -> _FakeResponse:
        return _FakeResponse(pages.pop(0))

    result = fetch_historical_klines(
        symbol="BTCUSDT",
        interval="1m",
        start_ms=0,
        end_ms=180_000,
        page_limit=2,
        urlopen=fake_urlopen,
        now_ms=10_000_000,
    )

    assert len(result.bars) == 3
    open_times = [bar.observed_at for bar in result.bars]
    assert len(set(open_times)) == 3
    assert result.stats.rows_rejected == 1


def test_fetch_historical_klines_never_includes_the_open_candle() -> None:
    """A row whose close time has not passed ``now_ms`` must never be returned."""
    now_ms = 100_000
    # Second row closes at 119_999 >= now, so it must be dropped even though it
    # was returned in the page. The next page (queried past the dropped row's
    # open time) returns nothing yet, which is recorded as a gap.
    pages: list[list[Any]] = [[_row(0, "100"), _row(60_000, "999")], []]

    def fake_urlopen(request: Request, timeout: float | None = None) -> _FakeResponse:
        return _FakeResponse(pages.pop(0))

    result = fetch_historical_klines(
        symbol="BTCUSDT",
        interval="1m",
        start_ms=0,
        end_ms=200_000,
        page_limit=10,
        urlopen=fake_urlopen,
        now_ms=now_ms,
    )

    assert len(result.bars) == 1
    assert float(result.bars[0].close.value) == 100.0
    assert result.stats.rows_rejected == 1


def test_fetch_historical_klines_records_empty_page_as_gap_not_error() -> None:
    """An empty page inside the requested range is recorded as a gap."""
    pages: list[list[Any]] = [[], [_row(120_000, "102")]]

    def fake_urlopen(request: Request, timeout: float | None = None) -> _FakeResponse:
        return _FakeResponse(pages.pop(0))

    result = fetch_historical_klines(
        symbol="BTCUSDT",
        interval="1m",
        start_ms=0,
        end_ms=180_000,
        page_limit=2,
        urlopen=fake_urlopen,
        now_ms=10_000_000,
    )

    assert len(result.stats.gaps) == 1
    gap = result.stats.gaps[0]
    assert gap.start_ms == 0
    assert gap.end_ms == 120_000
    assert len(result.bars) == 1


def test_fetch_historical_klines_throttles_on_used_weight_header() -> None:
    """Throttle pauses (via the injected sleep) once the weight ratio crosses the threshold."""
    pages = [[_row(0, "100")], [_row(60_000, "101")]]
    sleep_calls, sleep = _no_sleep_calls()

    def fake_urlopen(request: Request, timeout: float | None = None) -> _FakeResponse:
        return _FakeResponse(pages.pop(0), used_weight=1000)

    fetch_historical_klines(
        symbol="BTCUSDT",
        interval="1m",
        start_ms=0,
        end_ms=120_000,
        page_limit=1,
        urlopen=fake_urlopen,
        sleep=sleep,
        now_ms=10_000_000,
        weight_limit_per_minute=1000,
        weight_throttle_ratio=0.5,
    )

    assert sleep_calls, "expected the governor to throttle before the second page"


def _http_error(status: int, retry_after: str | None = None) -> HTTPError:
    import io

    headers: dict[str, str] = {}
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return HTTPError(
        url="https://fapi.binance.com/fapi/v1/klines",
        code=status,
        msg="error",
        hdrs=_FakeHeaders(headers),  # type: ignore[arg-type]
        fp=io.BytesIO(b"{}"),
    )


@pytest.mark.parametrize("status", [429, 418, 500, 503])
def test_fetch_historical_klines_backs_off_on_retryable_status_without_real_sleep(
    status: int,
) -> None:
    attempts = {"count": 0}
    sleep_calls, sleep = _no_sleep_calls()

    def fake_urlopen(request: Request, timeout: float | None = None) -> _FakeResponse:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise _http_error(status)
        return _FakeResponse([_row(0, "100")])

    result = fetch_historical_klines(
        symbol="BTCUSDT",
        interval="1m",
        start_ms=0,
        end_ms=60_000,
        page_limit=1,
        urlopen=fake_urlopen,
        sleep=sleep,
        now_ms=10_000_000,
        max_retries=3,
    )

    assert attempts["count"] == 2
    assert sleep_calls
    assert result.stats.retry_count == 1
    assert len(result.bars) == 1


def test_fetch_historical_klines_honours_retry_after_header() -> None:
    attempts = {"count": 0}
    sleep_calls, sleep = _no_sleep_calls()

    def fake_urlopen(request: Request, timeout: float | None = None) -> _FakeResponse:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise _http_error(429, retry_after="7")
        return _FakeResponse([_row(0, "100")])

    fetch_historical_klines(
        symbol="BTCUSDT",
        interval="1m",
        start_ms=0,
        end_ms=60_000,
        page_limit=1,
        urlopen=fake_urlopen,
        sleep=sleep,
        now_ms=10_000_000,
    )

    assert sleep_calls[0] == 7.0


def test_fetch_historical_klines_retry_cap_exhaustion_raises_typed_error() -> None:
    _, sleep = _no_sleep_calls()

    def fake_urlopen(request: Request, timeout: float | None = None) -> _FakeResponse:
        raise _http_error(429)

    with pytest.raises(BinanceKlinesRetryExhaustedError):
        fetch_historical_klines(
            symbol="BTCUSDT",
            interval="1m",
            start_ms=0,
            end_ms=60_000,
            page_limit=1,
            urlopen=fake_urlopen,
            sleep=sleep,
            now_ms=10_000_000,
            max_retries=2,
        )


def test_fetch_historical_klines_maps_non_retryable_http_error() -> None:
    def fake_urlopen(request: Request, timeout: float | None = None) -> _FakeResponse:
        raise _http_error(400)

    with pytest.raises(BinanceKlinesHistoryError, match="HTTP 400"):
        fetch_historical_klines(
            symbol="BTCUSDT",
            interval="1m",
            start_ms=0,
            end_ms=60_000,
            page_limit=1,
            urlopen=fake_urlopen,
            now_ms=10_000_000,
        )


def test_fetch_historical_klines_maps_network_errors() -> None:
    def fake_urlopen(request: Request, timeout: float | None = None) -> _FakeResponse:
        raise URLError("timed out")

    with pytest.raises(BinanceKlinesHistoryError, match="unreachable"):
        fetch_historical_klines(
            symbol="BTCUSDT",
            interval="1m",
            start_ms=0,
            end_ms=60_000,
            page_limit=1,
            urlopen=fake_urlopen,
            now_ms=10_000_000,
        )


def test_fetch_historical_klines_sets_api_key_header_when_present() -> None:
    captured: list[Request] = []

    def fake_urlopen(request: Request, timeout: float | None = None) -> _FakeResponse:
        captured.append(request)
        return _FakeResponse([_row(0, "100")])

    result = fetch_historical_klines(
        symbol="BTCUSDT",
        interval="1m",
        start_ms=0,
        end_ms=60_000,
        page_limit=1,
        urlopen=fake_urlopen,
        now_ms=10_000_000,
        api_key="super-secret-key",
    )

    assert captured[0].get_header("X-mbx-apikey") == "super-secret-key"
    assert result.stats.api_key_used is True


def test_fetch_historical_klines_omits_api_key_header_when_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(BINANCE_API_KEY_ENV_VAR, raising=False)
    captured: list[Request] = []

    def fake_urlopen(request: Request, timeout: float | None = None) -> _FakeResponse:
        captured.append(request)
        return _FakeResponse([_row(0, "100")])

    result = fetch_historical_klines(
        symbol="BTCUSDT",
        interval="1m",
        start_ms=0,
        end_ms=60_000,
        page_limit=1,
        urlopen=fake_urlopen,
        now_ms=10_000_000,
    )

    assert captured[0].get_header("X-mbx-apikey") is None
    assert result.stats.api_key_used is False


def test_resolve_binance_api_key_reads_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(BINANCE_API_KEY_ENV_VAR, "from-env")
    assert resolve_binance_api_key(None) == "from-env"


def test_resolve_binance_api_key_absent_is_anonymous(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(BINANCE_API_KEY_ENV_VAR, raising=False)
    assert resolve_binance_api_key(None) is None


def test_api_key_never_appears_in_any_raised_exception_text() -> None:
    """The key must not leak into HTTP error detail, network error text, or JSON error text."""
    secret_key = "do-not-leak-me-12345"

    def fake_urlopen(request: Request, timeout: float | None = None) -> _FakeResponse:
        raise _http_error(400)

    with pytest.raises(BinanceKlinesHistoryError) as exc_info:
        fetch_historical_klines(
            symbol="BTCUSDT",
            interval="1m",
            start_ms=0,
            end_ms=60_000,
            page_limit=1,
            urlopen=fake_urlopen,
            now_ms=10_000_000,
            api_key=secret_key,
        )

    assert secret_key not in str(exc_info.value)
    assert secret_key not in repr(exc_info.value)
