"""Output reference to a resolved computation."""

from dataclasses import dataclass

from trading_framework.market_analysis.identity.computation import ComputationIdentity
from trading_framework.market_analysis.models.outputs import OutputId


@dataclass(frozen=True, slots=True)
class OutputRef:
    """Resolved reference to one public output of a computation."""

    computation_identity: ComputationIdentity
    output_id: OutputId

    def canonical_key(self) -> str:
        return f"{self.computation_identity.canonical_key()}:{self.output_id}"
