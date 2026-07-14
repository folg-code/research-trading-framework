"""Column buffers for batch Databento contract trade decode."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt


@dataclass(slots=True)
class ContractChunkColumns:
    """Append-only trade column buffers for one outright contract."""

    ts_event_ns: list[int] = field(default_factory=list)
    ts_recv_ns: list[int] = field(default_factory=list)
    price_nanos: list[int] = field(default_factory=list)
    size: list[int] = field(default_factory=list)
    instrument_id: list[int] = field(default_factory=list)
    sequence: list[int] = field(default_factory=list)
    publisher_id: list[int] = field(default_factory=list)
    side: list[str | None] = field(default_factory=list)

    @classmethod
    def empty(cls) -> ContractChunkColumns:
        """Return an empty column buffer."""
        return cls()

    def __len__(self) -> int:
        return len(self.ts_event_ns)

    def extend_masked(
        self,
        mask: npt.NDArray[np.bool_],
        *,
        ts_event_ns: npt.NDArray[np.int64],
        ts_recv_ns: npt.NDArray[np.int64],
        price_nanos: npt.NDArray[np.int64],
        size: npt.NDArray[np.int64],
        instrument_id: npt.NDArray[np.int64],
        sequence: npt.NDArray[np.int64],
        publisher_id: npt.NDArray[np.int64],
        side: Sequence[str | None],
    ) -> None:
        """Append rows selected by ``mask`` from aligned numpy columns."""
        self.ts_event_ns.extend(ts_event_ns[mask].tolist())
        self.ts_recv_ns.extend(ts_recv_ns[mask].tolist())
        self.price_nanos.extend(price_nanos[mask].tolist())
        self.size.extend(size[mask].tolist())
        self.instrument_id.extend(instrument_id[mask].tolist())
        self.sequence.extend(sequence[mask].tolist())
        self.publisher_id.extend(publisher_id[mask].tolist())
        side_array = np.asarray(side, dtype=object)
        self.side.extend(side_array[mask].tolist())

    def take(self, indices: Sequence[int]) -> ContractChunkColumns:
        """Return a subset of rows by index."""
        picked = list(indices)
        return ContractChunkColumns(
            ts_event_ns=[self.ts_event_ns[index] for index in picked],
            ts_recv_ns=[self.ts_recv_ns[index] for index in picked],
            price_nanos=[self.price_nanos[index] for index in picked],
            size=[self.size[index] for index in picked],
            instrument_id=[self.instrument_id[index] for index in picked],
            sequence=[self.sequence[index] for index in picked],
            publisher_id=[self.publisher_id[index] for index in picked],
            side=[self.side[index] for index in picked],
        )

    def merge(self, other: ContractChunkColumns) -> None:
        """Append all rows from ``other``."""
        self.ts_event_ns.extend(other.ts_event_ns)
        self.ts_recv_ns.extend(other.ts_recv_ns)
        self.price_nanos.extend(other.price_nanos)
        self.size.extend(other.size)
        self.instrument_id.extend(other.instrument_id)
        self.sequence.extend(other.sequence)
        self.publisher_id.extend(other.publisher_id)
        self.side.extend(other.side)
