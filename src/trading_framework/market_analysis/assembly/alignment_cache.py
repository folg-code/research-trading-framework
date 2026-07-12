"""Alignment-stage cache keyed by ``AlignmentIdentity``."""

from trading_framework.market_analysis.identity.mtf import AlignmentIdentity


class AlignmentCache:
    """In-memory exact-match cache scoped to one frame assembly or execution."""

    def __init__(self) -> None:
        self._entries: dict[str, tuple[float, ...]] = {}

    def get(self, identity: AlignmentIdentity) -> tuple[float, ...] | None:
        return self._entries.get(identity.canonical_key())

    def put(self, identity: AlignmentIdentity, values: tuple[float, ...]) -> None:
        self._entries[identity.canonical_key()] = values

    def __len__(self) -> int:
        return len(self._entries)
