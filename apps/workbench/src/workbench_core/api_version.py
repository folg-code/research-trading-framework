"""Versioned contract for the workbench-api loopback JSON API (ADR-0037 section 4).

``WORKBENCH_API_VERSION`` is what keeps the deferred frontend-framework choice
reversible: any client that can call HTTP and read this version string
satisfies the contract.
"""

from __future__ import annotations

from typing import Final

WORKBENCH_API_VERSION: Final = "workbench.api.v1"
