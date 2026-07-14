"""Process memory stats tests."""

from trading_framework.infrastructure.observability.memory_stats import process_rss_mb


def test_process_rss_mb_returns_positive_value() -> None:
    rss_mb = process_rss_mb()
    if rss_mb is None:
        return
    assert rss_mb > 0
