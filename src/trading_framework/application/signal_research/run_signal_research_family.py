"""Run bounded model-family Signal Research experiments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from trading_framework.application.signal_research.analyze_signal_research import (
    AnalyzeSignalResearchResult,
    analyze_signal_research_run,
)
from trading_framework.application.signal_research.map_definition import (
    map_definition_to_analyze_request,
    map_definition_to_run_request,
    resolve_signal_research_definition,
)
from trading_framework.application.signal_research.run_signal_research import (
    RunSignalResearchResult,
    run_signal_research,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.research.analytics.family_comparison import summarize_family_comparison
from trading_framework.research.datasets.signal_research_family import (
    SignalResearchFamilyExperimentManifest,
    SignalResearchFamilyExperimentRepository,
)
from trading_framework.research.signal_research.definition import SignalResearchDefinitionSpec
from trading_framework.research.signal_research.family_planning import (
    FamilyExperimentPlan,
    plan_model_family_experiment,
)
from trading_framework.time.sessions.protocol import TradingSessionResolver


class RunSignalResearchFamilyError(ValidationError):
    """Raised when model-family experiment orchestration fails."""


@dataclass(frozen=True, slots=True)
class FamilyVariantResult:
    """One evaluated variant inside a family experiment."""

    variant_id: str
    run_id: str
    run_result: RunSignalResearchResult
    analytics: AnalyzeSignalResearchResult | None = None


@dataclass(frozen=True, slots=True)
class RunSignalResearchFamilyRequest:
    """Input for one bounded model-family experiment."""

    spec: SignalResearchDefinitionSpec
    storage_root: Path
    session_resolver: TradingSessionResolver | None = None
    analyze_variants: bool = True
    persist_manifest: bool = True


@dataclass(frozen=True, slots=True)
class RunSignalResearchFamilyResult:
    """Outcome of one bounded model-family experiment."""

    experiment_id: str
    plan: FamilyExperimentPlan
    variant_results: tuple[FamilyVariantResult, ...]
    family_comparison: pl.DataFrame
    manifest: SignalResearchFamilyExperimentManifest | None = None


def run_signal_research_family_experiment(
    request: RunSignalResearchFamilyRequest,
    *,
    experiment_repository: SignalResearchFamilyExperimentRepository | None = None,
) -> RunSignalResearchFamilyResult:
    """Evaluate an ordered model family within explicit candidate bounds."""
    if request.spec.model_family is None:
        msg = "spec.model_family must be declared"
        raise RunSignalResearchFamilyError(msg)

    resolved_base = resolve_signal_research_definition(request.spec)
    plan = plan_model_family_experiment(resolved_base.spec)
    experiment_repo = experiment_repository or SignalResearchFamilyExperimentRepository(
        request.storage_root
    )
    if request.persist_manifest and experiment_repo.manifest_exists(plan.experiment_id):
        msg = f"family experiment already exists: {plan.experiment_id}"
        raise FileExistsError(msg)

    variant_results: list[FamilyVariantResult] = []
    comparison_inputs: list[tuple[str, str, AnalyzeSignalResearchResult]] = []

    for candidate in plan.candidates:
        resolved = resolve_signal_research_definition(candidate.spec)
        run_result = run_signal_research(
            map_definition_to_run_request(
                resolved,
                storage_root=request.storage_root,
                session_resolver=request.session_resolver,
            )
        )
        analytics = None
        if request.analyze_variants:
            analytics = analyze_signal_research_run(
                map_definition_to_analyze_request(
                    resolved,
                    run_ref=run_result.run_ref,
                    storage_root=request.storage_root,
                )
            )
            comparison_inputs.append((candidate.variant_id, run_result.run_id, analytics))
        variant_results.append(
            FamilyVariantResult(
                variant_id=candidate.variant_id,
                run_id=run_result.run_id,
                run_result=run_result,
                analytics=analytics,
            )
        )

    family_comparison = summarize_family_comparison(tuple(comparison_inputs))
    manifest = None
    if request.persist_manifest:
        manifest = SignalResearchFamilyExperimentManifest(
            experiment_id=plan.experiment_id,
            research_id=resolved_base.spec.research_id,
            family_id=plan.family_id,
            definition_hash=resolved_base.spec.definition_hash,
            created_at_utc=datetime.now(tz=UTC),
            candidates_generated=plan.candidates_generated,
            candidates_evaluated=plan.candidates_evaluated,
            candidates_skipped=plan.candidates_skipped,
            skipped_variant_ids=plan.skipped_variant_ids,
            variant_runs=tuple((result.variant_id, result.run_id) for result in variant_results),
        )
        experiment_repo.write_manifest(manifest)

    return RunSignalResearchFamilyResult(
        experiment_id=plan.experiment_id,
        plan=plan,
        variant_results=tuple(variant_results),
        family_comparison=family_comparison,
        manifest=manifest,
    )
