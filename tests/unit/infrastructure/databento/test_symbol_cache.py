"""Symbol cache tests."""

from trading_framework.infrastructure.importers.databento.symbol_cache import ContractSymbolCache


def test_symbol_cache_reuses_contract_lookup() -> None:
    cache = ContractSymbolCache(product="NQ")

    first = cache.resolve(symbol="NQU5", instrument_id=101)
    second = cache.resolve(symbol="NQU5", instrument_id=101)

    assert first == "NQU5"
    assert second == "NQU5"
    assert len(cache._by_symbol) == 1
    assert len(cache._by_instrument_id) == 1


def test_symbol_cache_remembers_rejected_symbols() -> None:
    cache = ContractSymbolCache(product="NQ")

    first = cache.resolve(symbol="NQ-spread", instrument_id=202)
    second = cache.resolve(symbol="NQ-spread", instrument_id=202)

    assert first is None
    assert second is None
