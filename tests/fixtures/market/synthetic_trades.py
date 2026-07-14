"""Synthetic market trade fixtures for derivation integration tests."""

from tests.fixtures.databento import SyntheticTradeRowSpec


def synthetic_trade_row_specs_across_minutes() -> list[SyntheticTradeRowSpec]:
    """Return DBN row specs spanning two 1m buckets for trades→bars tests."""
    return [
        SyntheticTradeRowSpec(minute=0, second=0, price=100.0, size=10, sequence=0),
        SyntheticTradeRowSpec(minute=0, second=15, price=101.5, size=5, sequence=1),
        SyntheticTradeRowSpec(minute=0, second=45, price=99.25, size=8, sequence=2),
        SyntheticTradeRowSpec(minute=0, second=59, price=100.75, size=3, sequence=3),
        SyntheticTradeRowSpec(minute=1, second=0, price=101.0, size=12, sequence=4),
    ]
