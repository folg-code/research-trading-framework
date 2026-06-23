"""Execution-scoped result store."""

from collections.abc import Mapping, Sequence

from trading_framework.core.exceptions import ValidationError
from trading_framework.market_analysis.identity.computation import ComputationIdentity
from trading_framework.market_analysis.models.output_ref import OutputRef
from trading_framework.market_analysis.models.result import AnalysisResult, OutputSeries


class AnalysisResultStore:
    """Maps resolved computation identities to analysis results for one plan."""

    def __init__(self) -> None:
        self._results: dict[str, AnalysisResult] = {}

    def put(self, result: AnalysisResult) -> None:
        self._results[result.computation_identity.canonical_key()] = result

    def get(self, identity: ComputationIdentity) -> AnalysisResult | None:
        return self._results.get(identity.canonical_key())

    def contains(self, identity: ComputationIdentity) -> bool:
        return identity.canonical_key() in self._results

    def dependency_results(
        self,
        dependency_keys: Sequence[str],
    ) -> dict[str, AnalysisResult]:
        missing = [key for key in dependency_keys if key not in self._results]
        if missing:
            msg = f"missing dependency results: {missing!r}"
            raise ValidationError(msg)
        return {key: self._results[key] for key in dependency_keys}

    def lookup_output(self, output_ref: OutputRef) -> OutputSeries:
        result = self.get(output_ref.computation_identity)
        if result is None:
            msg = f"computation not found: {output_ref.computation_identity.canonical_key()}"
            raise ValidationError(msg)
        return result.outputs[output_ref.output_id]

    def results(self) -> Mapping[str, AnalysisResult]:
        return dict(self._results)

    def __len__(self) -> int:
        return len(self._results)
