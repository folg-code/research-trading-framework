"""Dataset content checksum helpers."""

import hashlib
import json
from collections.abc import Sequence

from trading_framework.market.models import MarketBar


def compute_dataset_checksum(bars: Sequence[MarketBar]) -> str:
    """Return a stable checksum for a sequence of market bars."""
    payload = [
        {
            "open": str(bar.open.value),
            "high": str(bar.high.value),
            "low": str(bar.low.value),
            "close": str(bar.close.value),
            "volume": bar.volume.value,
            "observed_at": bar.observed_at.isoformat(),
            "available_at": bar.available_at.isoformat(),
        }
        for bar in bars
    ]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
