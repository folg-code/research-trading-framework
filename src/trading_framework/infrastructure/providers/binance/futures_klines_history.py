"""Paginated Binance USD-M historical klines reader.

This module is the archive-import counterpart to ``futures_rest.py``'s
``fetch_closed_klines`` (live reconnect gap-fill). It is a **separate** code
path by design (ADR-0025 / S045_WAVE0_DECISIONS.md D-S045-04): the live
reconnect path is not modified, wrapped, or refactored, even at the cost of a
few duplicated lines.

Responsibilities:
    - page a ``[start, end)`` UTC range through ``/fapi/v1/klines``,
    - drop any row whose close time has not passed yet (never import an open
      candle),
    - record a page that returns zero rows inside the range as a gap, never
      an error,
    - throttle proactively on the ``X-MBX-USED-WEIGHT-1M`` response header
      and apply bounded, jittered backoff with a finite retry cap on
      429 / 418 / 5xx responses,
    - attach ``X-MBX-APIKEY`` from ``TRADING_FRAMEWORK_BINANCE_API_KEY`` when
      present; anonymous requests work identically otherwise.

No signing / HMAC code exists anywhere in this module (ADR-0025 §5): the API
key can only ever reach a public market-data GET.
"""

from __future__ import annotations

import json
import os
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, final
from urllib.request import Request

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.providers.binance.futures_mapper import map_kline_payload
from trading_framework.infrastructure.providers.binance.futures_payloads import BinanceKlinePayload
from trading_framework.infrastructure.providers.binance.futures_rest import (
    BINANCE_USDM_REST_BASE_URL,
)
from trading_framework.infrastructure.providers.binance.futures_streams import (
    normalize_stream_symbol,
)
from trading_framework.market.models import MarketBar

BINANCE_API_KEY_ENV_VAR = "TRADING_FRAMEWORK_BINANCE_API_KEY"
DEFAULT_HISTORY_PAGE_LIMIT = 1500
DEFAULT_HISTORY_TIMEOUT_SECONDS = 15.0
DEFAULT_MAX_RETRIES = 5
DEFAULT_WEIGHT_LIMIT_PER_MINUTE = 2400
DEFAULT_WEIGHT_THROTTLE_RATIO = 0.8
DEFAULT_THROTTLE_PAUSE_SECONDS = 60.0
DEFAULT_BACKOFF_BASE_SECONDS = 1.0
DEFAULT_BACKOFF_CAP_SECONDS = 60.0

_RETRYABLE_STATUSES = frozenset({429, 418})

_INTERVAL_DURATIONS_MS: Mapping[str, int] = {
    "1m": 60_000,
    "5m": 5 * 60_000,
    "15m": 15 * 60_000,
    "1h": 60 * 60_000,
    "4h": 4 * 60 * 60_000,
    "1d": 24 * 60 * 60_000,
}


class _KlinesResponse(Protocol):
    # ``headers`` is a header-mapping-like object (``email.message.Message``
    # for real urllib responses, a lightweight double in tests) that only
    # needs to support ``.get(name, default)``; typed as ``Any`` because the
    # stdlib overloads for ``Message.get`` don't structurally match a
    # narrower Protocol.
    headers: Any

    def read(self) -> bytes: ...
    def __enter__(self) -> _KlinesResponse: ...
    def __exit__(self, *args: object) -> None: ...


_Urlopener = Callable[[Request, float | None], _KlinesResponse]
_Sleeper = Callable[[float], None]


class BinanceKlinesHistoryError(ValidationError):
    """Raised when a historical klines request cannot be completed."""


@final
class BinanceKlinesRetryExhaustedError(BinanceKlinesHistoryError):
    """Raised when the finite retry cap for a klines page is exhausted."""


@final
@dataclass(frozen=True, slots=True)
class KlineGap:
    """A half-open ``[start_ms, end_ms)`` range with no returned bars."""

    start_ms: int
    end_ms: int


@final
@dataclass(frozen=True, slots=True)
class HistoricalKlinesFetchStats:
    """Per-request bookkeeping for one paginated historical klines fetch."""

    page_count: int
    request_count: int
    retry_count: int
    rows_decoded: int
    rows_rejected: int
    gaps: tuple[KlineGap, ...]
    api_key_used: bool


@final
@dataclass(frozen=True, slots=True)
class HistoricalKlinesResult:
    """Assembled bars plus fetch statistics for one historical klines fetch."""

    bars: tuple[MarketBar, ...]
    stats: HistoricalKlinesFetchStats


def resolve_binance_api_key(explicit_api_key: str | None = None) -> str | None:
    """Resolve the optional Binance API key from an explicit value or env var.

    Returns ``None`` when neither an explicit key nor the environment
    variable is set (anonymous request).
    """
    if explicit_api_key is not None:
        stripped = explicit_api_key.strip()
        return stripped or None
    from_env = os.environ.get(BINANCE_API_KEY_ENV_VAR)
    if from_env is None:
        return None
    stripped_env = from_env.strip()
    return stripped_env or None


def _interval_duration_ms(interval: str) -> int:
    try:
        return _INTERVAL_DURATIONS_MS[interval]
    except KeyError as exc:
        msg = f"unsupported Binance interval for historical import: {interval!r}"
        raise BinanceKlinesHistoryError(msg) from exc


def fetch_historical_klines(
    *,
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
    base_url: str = BINANCE_USDM_REST_BASE_URL,
    page_limit: int = DEFAULT_HISTORY_PAGE_LIMIT,
    timeout_seconds: float = DEFAULT_HISTORY_TIMEOUT_SECONDS,
    urlopen: _Urlopener | None = None,
    sleep: _Sleeper | None = None,
    api_key: str | None = None,
    now_ms: int | None = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    weight_limit_per_minute: int = DEFAULT_WEIGHT_LIMIT_PER_MINUTE,
    weight_throttle_ratio: float = DEFAULT_WEIGHT_THROTTLE_RATIO,
    rng: random.Random | None = None,
) -> HistoricalKlinesResult:
    """Fetch a half-open ``[start_ms, end_ms)`` UTC range of closed klines.

    Pages through ``/fapi/v1/klines`` at ``page_limit`` rows per request,
    advancing the cursor to ``last_close_time_ms + 1`` after each page. Rows
    whose close time has not passed ``now_ms`` are dropped (never import an
    open candle). A page returning zero rows inside the range is recorded as
    a gap and the cursor advances by one page window; it is never raised as
    an error.
    """
    if end_ms <= start_ms:
        msg = "end_ms must be greater than start_ms"
        raise BinanceKlinesHistoryError(msg)
    if page_limit < 1:
        msg = "page_limit must be positive"
        raise BinanceKlinesHistoryError(msg)
    if timeout_seconds <= 0:
        msg = "timeout_seconds must be positive"
        raise BinanceKlinesHistoryError(msg)
    if max_retries < 0:
        msg = "max_retries must be non-negative"
        raise BinanceKlinesHistoryError(msg)

    normalized_symbol = normalize_stream_symbol(symbol).upper()
    resolved_now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    page_window_ms = _interval_duration_ms(interval) * page_limit
    opener: _Urlopener = urlopen or _default_urlopen
    sleep_fn: _Sleeper = sleep or time.sleep
    rng_instance = rng if rng is not None else random.Random()
    resolved_key = resolve_binance_api_key(api_key)

    governor = _RateGovernor(
        sleep=sleep_fn,
        weight_limit=weight_limit_per_minute,
        throttle_ratio=weight_throttle_ratio,
        pause_seconds=DEFAULT_THROTTLE_PAUSE_SECONDS,
    )

    bars: list[MarketBar] = []
    seen_open_times_ms: set[int] = set()
    gaps: list[KlineGap] = []
    page_count = 0
    request_count = 0
    retry_count = 0
    rows_decoded = 0
    rows_rejected = 0

    cursor_ms = start_ms
    while cursor_ms < end_ms:
        page_end_ms = end_ms - 1
        request = _build_klines_request(
            base_url=base_url,
            symbol=normalized_symbol,
            interval=interval,
            start_ms=cursor_ms,
            end_ms=page_end_ms,
            limit=page_limit,
            api_key=resolved_key,
        )
        payload, attempt_count = _request_page_with_retry(
            request=request,
            opener=opener,
            timeout_seconds=timeout_seconds,
            governor=governor,
            sleep=sleep_fn,
            max_retries=max_retries,
            rng_instance=rng_instance,
        )
        request_count += attempt_count
        retry_count += attempt_count - 1
        page_count += 1

        closed_rows = _select_closed_rows(payload, now_ms=resolved_now_ms)
        rows_rejected += len(payload) - len(closed_rows)
        if not closed_rows:
            gap_end_ms = min(cursor_ms + page_window_ms, end_ms)
            gaps.append(KlineGap(start_ms=cursor_ms, end_ms=gap_end_ms))
            cursor_ms = gap_end_ms
            continue

        for row in closed_rows:
            open_time_ms = int(row[0])
            if open_time_ms in seen_open_times_ms:
                rows_rejected += 1
                continue
            seen_open_times_ms.add(open_time_ms)
            kline_payload = _row_to_kline_payload(row, symbol=normalized_symbol, interval=interval)
            bars.append(map_kline_payload(kline_payload))
            rows_decoded += 1

        last_close_ms = int(closed_rows[-1][6])
        cursor_ms = last_close_ms + 1

    stats = HistoricalKlinesFetchStats(
        page_count=page_count,
        request_count=request_count,
        retry_count=retry_count,
        rows_decoded=rows_decoded,
        rows_rejected=rows_rejected,
        gaps=tuple(gaps),
        api_key_used=resolved_key is not None,
    )
    return HistoricalKlinesResult(bars=tuple(bars), stats=stats)


def _default_urlopen(request: Request, timeout: float | None) -> _KlinesResponse:
    response: _KlinesResponse = urllib.request.urlopen(request, timeout=timeout)
    return response


def _build_klines_request(
    *,
    base_url: str,
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
    limit: int,
    api_key: str | None,
) -> Request:
    query = urllib.parse.urlencode(
        {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_ms,
            "endTime": end_ms,
            "limit": limit,
        }
    )
    headers = {"Accept": "application/json"}
    if api_key is not None:
        headers["X-MBX-APIKEY"] = api_key
    return Request(
        f"{base_url.rstrip('/')}/fapi/v1/klines?{query}",
        method="GET",
        headers=headers,
    )


def _select_closed_rows(payload: list[Any], *, now_ms: int) -> list[Any]:
    closed: list[Any] = []
    for row in payload:
        if not isinstance(row, list) or len(row) < 7:
            continue
        close_time_ms = int(row[6])
        if close_time_ms >= now_ms:
            continue
        closed.append(row)
    return closed


def _row_to_kline_payload(row: Sequence[Any], *, symbol: str, interval: str) -> BinanceKlinePayload:
    open_time_ms = int(row[0])
    close_time_ms = int(row[6])
    return BinanceKlinePayload(
        event_type="kline",
        event_time_ms=close_time_ms,
        symbol=symbol,
        interval=interval,
        open_time_ms=open_time_ms,
        close_time_ms=close_time_ms,
        open_price=str(row[1]),
        high_price=str(row[2]),
        low_price=str(row[3]),
        close_price=str(row[4]),
        volume=str(row[5]),
        is_closed=True,
    )


class _RateGovernor:
    """Reads the used-weight header and throttles before the budget is hit."""

    def __init__(
        self,
        *,
        sleep: _Sleeper,
        weight_limit: int,
        throttle_ratio: float,
        pause_seconds: float,
    ) -> None:
        self._sleep = sleep
        self._weight_limit = weight_limit
        self._throttle_ratio = throttle_ratio
        self._pause_seconds = pause_seconds
        self._used_weight = 0

    def observe_headers(self, headers: Any) -> None:
        raw_value = headers.get("X-MBX-USED-WEIGHT-1M")
        if raw_value is None:
            return
        try:
            self._used_weight = int(raw_value)
        except ValueError:
            return

    def throttle_if_needed(self) -> None:
        if self._weight_limit <= 0:
            return
        used_ratio = self._used_weight / self._weight_limit
        if used_ratio >= self._throttle_ratio:
            self._sleep(self._pause_seconds)
            self._used_weight = 0


def _parse_retry_after_seconds(headers: Any | None) -> float | None:
    if headers is None:
        return None
    raw_value = headers.get("Retry-After")
    if raw_value is None:
        return None
    try:
        return max(0.0, float(raw_value))
    except ValueError:
        return None


def _compute_backoff_seconds(
    attempt: int, retry_after_seconds: float | None, rng_instance: random.Random
) -> float:
    if retry_after_seconds is not None:
        return retry_after_seconds
    capped_base = min(DEFAULT_BACKOFF_CAP_SECONDS, DEFAULT_BACKOFF_BASE_SECONDS * (2**attempt))
    return rng_instance.uniform(0.0, capped_base)


def _request_page_with_retry(
    *,
    request: Request,
    opener: _Urlopener,
    timeout_seconds: float,
    governor: _RateGovernor,
    sleep: _Sleeper,
    max_retries: int,
    rng_instance: random.Random,
) -> tuple[list[Any], int]:
    attempt = 0
    while True:
        governor.throttle_if_needed()
        attempt += 1
        try:
            with opener(request, timeout_seconds) as response:
                headers = response.headers
                body = response.read()
        except urllib.error.HTTPError as exc:
            status = exc.code
            if status in _RETRYABLE_STATUSES or status >= 500:
                if attempt > max_retries:
                    msg = (
                        "Binance klines request exhausted "
                        f"{max_retries} retries (last HTTP status {status})"
                    )
                    raise BinanceKlinesRetryExhaustedError(msg) from exc
                retry_after_seconds = _parse_retry_after_seconds(exc.headers)
                delay_seconds = _compute_backoff_seconds(attempt, retry_after_seconds, rng_instance)
                sleep(delay_seconds)
                continue
            detail = exc.read().decode("utf-8", errors="replace")
            msg = f"Binance klines HTTP {status}: {detail[:200]}"
            raise BinanceKlinesHistoryError(msg) from exc
        except urllib.error.URLError as exc:
            msg = f"Binance klines unreachable: {exc.reason}"
            raise BinanceKlinesHistoryError(msg) from exc

        governor.observe_headers(headers)
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            msg = "Binance klines response is not valid JSON"
            raise BinanceKlinesHistoryError(msg) from exc
        if not isinstance(payload, list):
            msg = "Binance klines response must be a JSON array"
            raise BinanceKlinesHistoryError(msg)
        return payload, attempt
