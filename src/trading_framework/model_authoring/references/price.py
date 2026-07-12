"""Canonical OHLCV field references."""

from trading_framework.model_authoring.references.operand import Operand
from trading_framework.model_expression.references import MarketField, MarketFieldReference


class PriceNamespace:
    """``price.close``, ``price.open``, ..."""

    @property
    def open(self) -> Operand:
        return Operand(MarketFieldReference(field=MarketField.OPEN))

    @property
    def high(self) -> Operand:
        return Operand(MarketFieldReference(field=MarketField.HIGH))

    @property
    def low(self) -> Operand:
        return Operand(MarketFieldReference(field=MarketField.LOW))

    @property
    def close(self) -> Operand:
        return Operand(MarketFieldReference(field=MarketField.CLOSE))

    @property
    def volume(self) -> Operand:
        return Operand(MarketFieldReference(field=MarketField.VOLUME))


price = PriceNamespace()
