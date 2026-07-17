"""Column buffers for batch Databento contract trade decode."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np
import numpy.typing as npt

_EMPTY_I64: npt.NDArray[np.int64] = np.array([], dtype=np.int64)
_EMPTY_OBJ: npt.NDArray[np.object_] = np.array([], dtype=object)


def _as_i64(values: npt.NDArray[np.int64]) -> npt.NDArray[np.int64]:
    return np.asarray(values, dtype=np.int64)


def _concat_i64(parts: list[npt.NDArray[np.int64]]) -> npt.NDArray[np.int64]:
    if not parts:
        return _EMPTY_I64
    if len(parts) == 1:
        return parts[0]
    return np.concatenate(parts)


def _concat_obj(parts: list[npt.NDArray[np.object_]]) -> npt.NDArray[np.object_]:
    if not parts:
        return _EMPTY_OBJ
    if len(parts) == 1:
        return parts[0]
    return np.concatenate(parts)


@dataclass(slots=True)
class ContractChunkColumns:
    """Append-only trade column buffers for one outright contract.

    Numeric columns stay as NumPy ``int64`` arrays (chunk parts concatenated on read).
    ``side`` uses an object array of optional strings.
    """

    _ts_event_ns_parts: list[npt.NDArray[np.int64]] = field(default_factory=list)
    _ts_recv_ns_parts: list[npt.NDArray[np.int64]] = field(default_factory=list)
    _price_nanos_parts: list[npt.NDArray[np.int64]] = field(default_factory=list)
    _size_parts: list[npt.NDArray[np.int64]] = field(default_factory=list)
    _instrument_id_parts: list[npt.NDArray[np.int64]] = field(default_factory=list)
    _sequence_parts: list[npt.NDArray[np.int64]] = field(default_factory=list)
    _publisher_id_parts: list[npt.NDArray[np.int64]] = field(default_factory=list)
    _side_parts: list[npt.NDArray[np.object_]] = field(default_factory=list)
    _row_count: int = 0
    _ts_event_ns_cache: npt.NDArray[np.int64] | None = field(default=None, repr=False)
    _ts_recv_ns_cache: npt.NDArray[np.int64] | None = field(default=None, repr=False)
    _price_nanos_cache: npt.NDArray[np.int64] | None = field(default=None, repr=False)
    _size_cache: npt.NDArray[np.int64] | None = field(default=None, repr=False)
    _instrument_id_cache: npt.NDArray[np.int64] | None = field(default=None, repr=False)
    _sequence_cache: npt.NDArray[np.int64] | None = field(default=None, repr=False)
    _publisher_id_cache: npt.NDArray[np.int64] | None = field(default=None, repr=False)
    _side_cache: npt.NDArray[np.object_] | None = field(default=None, repr=False)

    @classmethod
    def empty(cls) -> ContractChunkColumns:
        """Return an empty column buffer."""
        return cls()

    @classmethod
    def from_arrays(
        cls,
        *,
        ts_event_ns: npt.NDArray[np.int64],
        ts_recv_ns: npt.NDArray[np.int64],
        price_nanos: npt.NDArray[np.int64],
        size: npt.NDArray[np.int64],
        instrument_id: npt.NDArray[np.int64],
        sequence: npt.NDArray[np.int64],
        publisher_id: npt.NDArray[np.int64],
        side: npt.NDArray[np.object_],
    ) -> ContractChunkColumns:
        """Build a buffer from already-materialized NumPy columns."""
        row_count = int(ts_event_ns.shape[0])
        return cls(
            _ts_event_ns_parts=[_as_i64(ts_event_ns)],
            _ts_recv_ns_parts=[_as_i64(ts_recv_ns)],
            _price_nanos_parts=[_as_i64(price_nanos)],
            _size_parts=[_as_i64(size)],
            _instrument_id_parts=[_as_i64(instrument_id)],
            _sequence_parts=[_as_i64(sequence)],
            _publisher_id_parts=[_as_i64(publisher_id)],
            _side_parts=[np.asarray(side, dtype=object)],
            _row_count=row_count,
            _ts_event_ns_cache=_as_i64(ts_event_ns),
            _ts_recv_ns_cache=_as_i64(ts_recv_ns),
            _price_nanos_cache=_as_i64(price_nanos),
            _size_cache=_as_i64(size),
            _instrument_id_cache=_as_i64(instrument_id),
            _sequence_cache=_as_i64(sequence),
            _publisher_id_cache=_as_i64(publisher_id),
            _side_cache=np.asarray(side, dtype=object),
        )

    def __len__(self) -> int:
        return self._row_count

    def _invalidate_cache(self) -> None:
        self._ts_event_ns_cache = None
        self._ts_recv_ns_cache = None
        self._price_nanos_cache = None
        self._size_cache = None
        self._instrument_id_cache = None
        self._sequence_cache = None
        self._publisher_id_cache = None
        self._side_cache = None

    @property
    def ts_event_ns(self) -> npt.NDArray[np.int64]:
        if self._ts_event_ns_cache is None:
            self._ts_event_ns_cache = _concat_i64(self._ts_event_ns_parts)
        return self._ts_event_ns_cache

    @property
    def ts_recv_ns(self) -> npt.NDArray[np.int64]:
        if self._ts_recv_ns_cache is None:
            self._ts_recv_ns_cache = _concat_i64(self._ts_recv_ns_parts)
        return self._ts_recv_ns_cache

    @property
    def price_nanos(self) -> npt.NDArray[np.int64]:
        if self._price_nanos_cache is None:
            self._price_nanos_cache = _concat_i64(self._price_nanos_parts)
        return self._price_nanos_cache

    @property
    def size(self) -> npt.NDArray[np.int64]:
        if self._size_cache is None:
            self._size_cache = _concat_i64(self._size_parts)
        return self._size_cache

    @property
    def instrument_id(self) -> npt.NDArray[np.int64]:
        if self._instrument_id_cache is None:
            self._instrument_id_cache = _concat_i64(self._instrument_id_parts)
        return self._instrument_id_cache

    @property
    def sequence(self) -> npt.NDArray[np.int64]:
        if self._sequence_cache is None:
            self._sequence_cache = _concat_i64(self._sequence_parts)
        return self._sequence_cache

    @property
    def publisher_id(self) -> npt.NDArray[np.int64]:
        if self._publisher_id_cache is None:
            self._publisher_id_cache = _concat_i64(self._publisher_id_parts)
        return self._publisher_id_cache

    @property
    def side(self) -> npt.NDArray[np.object_]:
        if self._side_cache is None:
            self._side_cache = _concat_obj(self._side_parts)
        return self._side_cache

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
        side: Sequence[str | None] | npt.NDArray[np.object_],
    ) -> None:
        """Append rows selected by ``mask`` from aligned numpy columns."""
        selected = np.asarray(mask, dtype=bool)
        if selected.size == 0 or not bool(selected.any()):
            return
        row_count = int(selected.sum())
        self._ts_event_ns_parts.append(_as_i64(ts_event_ns[selected]))
        self._ts_recv_ns_parts.append(_as_i64(ts_recv_ns[selected]))
        self._price_nanos_parts.append(_as_i64(price_nanos[selected]))
        self._size_parts.append(_as_i64(size[selected]))
        self._instrument_id_parts.append(_as_i64(instrument_id[selected]))
        self._sequence_parts.append(_as_i64(sequence[selected]))
        self._publisher_id_parts.append(_as_i64(publisher_id[selected]))
        side_array = np.asarray(side, dtype=object)
        self._side_parts.append(side_array[selected])
        self._row_count += row_count
        self._invalidate_cache()

    def take(self, indices: Sequence[int] | npt.NDArray[np.int64]) -> ContractChunkColumns:
        """Return a subset of rows by index."""
        picked = np.asarray(indices, dtype=np.int64)
        if picked.size == 0:
            return ContractChunkColumns.empty()
        return ContractChunkColumns.from_arrays(
            ts_event_ns=self.ts_event_ns[picked],
            ts_recv_ns=self.ts_recv_ns[picked],
            price_nanos=self.price_nanos[picked],
            size=self.size[picked],
            instrument_id=self.instrument_id[picked],
            sequence=self.sequence[picked],
            publisher_id=self.publisher_id[picked],
            side=self.side[picked],
        )

    def merge(self, other: ContractChunkColumns) -> None:
        """Append all rows from ``other``."""
        if len(other) == 0:
            return
        self._ts_event_ns_parts.extend(other._ts_event_ns_parts)
        self._ts_recv_ns_parts.extend(other._ts_recv_ns_parts)
        self._price_nanos_parts.extend(other._price_nanos_parts)
        self._size_parts.extend(other._size_parts)
        self._instrument_id_parts.extend(other._instrument_id_parts)
        self._sequence_parts.extend(other._sequence_parts)
        self._publisher_id_parts.extend(other._publisher_id_parts)
        self._side_parts.extend(other._side_parts)
        self._row_count += other._row_count
        self._invalidate_cache()
