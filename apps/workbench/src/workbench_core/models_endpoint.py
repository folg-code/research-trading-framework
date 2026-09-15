"""Model-alias listing endpoint body (T008 model picker).

Transport-independent by design, same pattern as `datasets_endpoint.py`.
Lets the UI offer `market_model`/`signal_model` as a pick-from-a-list
control instead of a free-text field an operator has to already know the
answer to.
"""

from __future__ import annotations

from typing import Any

from trading_framework.application.signal_research import list_known_model_aliases

from workbench_core.api_version import WORKBENCH_API_VERSION


def build_models_response() -> dict[str, Any]:
    aliases = list_known_model_aliases()
    return {
        "schema_version": WORKBENCH_API_VERSION,
        "market_models": list(aliases.market_model_aliases),
        "signal_models": list(aliases.signal_model_aliases),
    }
