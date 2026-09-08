"""Evaluate the analyst verdict for one persisted Predictive Research run (ADR-0032).

The I/O layer for ``research/predictive/verdict.py``'s pure vocabulary, rule
set and cascade (S057-T002/T003): reads the run envelope (never a fitted
model blob — mirrors ``analyze_predictive_run.py``'s own rule), the dataset
envelope, ``metrics.json``, and the optional ``importance.json``; turns them
into a :class:`~trading_framework.research.predictive.verdict.VerdictFacts`
via :func:`extract_verdict_facts`; evaluates ``verdict_rules.v1`` via
:func:`evaluate_verdict`; and writes the sidecar at
``runs/<run_id>/verdict.json`` (:func:`predictive_research_run_verdict_path`).

``VerdictReport`` (S057-T002) deliberately carries no run identity — this
module adds ``run_id`` / ``dataset_id`` / ``dataset_fingerprint`` at
serialization time, the same "domain declares/computes, application
resolves/persists" seam ADR-0029 and ADR-0031 already use.

Nothing in the run directory or the dataset directory is rewritten, moved,
re-derived or re-persisted (ADR-0032 §4): every artifact this module reads is
opened read-only. ``verdict.json`` carries no wall-clock field; evaluation is
pure, so re-evaluating the same run directory produces a byte-identical file
(the JSON encoder here uses ``sort_keys=True`` so no dict-iteration-order
non-determinism leaks into the written bytes).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import fields as dataclass_fields
from datetime import timedelta
from pathlib import Path
from typing import Any

import polars as pl

from trading_framework.core.exceptions import ValidationError
from trading_framework.infrastructure.storage.paths import (
    predictive_research_run_importance_path,
    predictive_research_run_metrics_path,
    predictive_research_run_verdict_path,
)
from trading_framework.research.datasets.predictive import (
    PredictiveDatasetRef,
    PredictiveDatasetRepository,
)
from trading_framework.research.datasets.predictive_run import (
    PredictiveRunRef,
    PredictiveRunRepository,
)
from trading_framework.research.predictive.estimators import TaskType
from trading_framework.research.predictive.importance import ImportanceTrace
from trading_framework.research.predictive.metrics import PredictiveMetricsReport
from trading_framework.research.predictive.splitting import FoldRole
from trading_framework.research.predictive.verdict import (
    VERDICT_RULES_V1,
    VerdictFacts,
    VerdictReport,
    evaluate_verdict,
    extract_verdict_facts,
)

#: Schema version of the ``verdict.json`` sidecar itself — distinct from
#: ``rule_set_version`` (``verdict_rules.v1``), which is the rule set's own
#: version. Owned here, not in ``research/predictive/verdict.py``, because it
#: describes this module's persisted envelope shape, not the pure rule set.
VERDICT_SIDECAR_SCHEMA_VERSION = "predictive_run_verdict.v1"


class EvaluateRunVerdictError(ValidationError):
    """Raised when analyst-verdict evaluation for a run cannot proceed."""


@dataclass(frozen=True, slots=True)
class EvaluateRunVerdictRequest:
    """Input for read-only analyst-verdict evaluation of one persisted run.

    Reads the run envelope (manifest + predictions), the dataset envelope
    (manifest + features + folds), ``metrics.json``, and the optional
    ``importance.json``. Never deserializes fitted model blobs.
    """

    run_ref: PredictiveRunRef
    storage_root: Path
    persist: bool = True
    run_repository: PredictiveRunRepository | None = None
    dataset_repository: PredictiveDatasetRepository | None = None


@dataclass(frozen=True, slots=True)
class EvaluateRunVerdictResult:
    """Analyst-verdict report for one Predictive Research run."""

    run_id: str
    dataset_id: str
    dataset_fingerprint: str
    report: VerdictReport
    verdict_path: Path | None


def evaluate_run_verdict(request: EvaluateRunVerdictRequest) -> EvaluateRunVerdictResult:
    """Load persisted artifacts, evaluate ``verdict_rules.v1``, optionally persist.

    Does not call ``joblib.load`` or inspect ``models/fold_*.bin``. Reads
    ``metrics.json`` (required), the dataset envelope (required, including
    ``features.parquet``'s pooled TEST-role ``label`` column for a
    ``CLASSIFICATION`` task's minority-class share), and ``importance.json``
    (optional — its absence is a legitimate, named fact, never an error).
    """
    run_repository = request.run_repository or PredictiveRunRepository(request.storage_root)
    dataset_repository = request.dataset_repository or PredictiveDatasetRepository(
        request.storage_root
    )

    envelope = run_repository.read(request.run_ref)
    dataset = dataset_repository.read(PredictiveDatasetRef(dataset_id=envelope.manifest.dataset_id))

    metrics_path = predictive_research_run_metrics_path(
        request.storage_root, envelope.manifest.run_id
    )
    if not metrics_path.exists():
        msg = f"missing metrics.json for run {envelope.manifest.run_id!r}: {metrics_path}"
        raise EvaluateRunVerdictError(msg)
    metrics = PredictiveMetricsReport.from_dict(
        json.loads(metrics_path.read_text(encoding="utf-8"))
    )

    importance_path = predictive_research_run_importance_path(
        request.storage_root, envelope.manifest.run_id
    )
    importance: ImportanceTrace | None = None
    if importance_path.exists():
        importance = ImportanceTrace.from_dict(
            json.loads(importance_path.read_text(encoding="utf-8"))
        )

    pooled_test_labels: list[float] | None = None
    if metrics.task_type is TaskType.CLASSIFICATION:
        test_rows = dataset.features.filter(pl.col("fold_role") == FoldRole.TEST.value)
        pooled_test_labels = [float(value) for value in test_rows.get_column("label").to_list()]

    facts = extract_verdict_facts(
        metrics=metrics,
        dataset_manifest=dataset.manifest,
        pooled_test_labels=pooled_test_labels,
        importance=importance,
    )
    report = evaluate_verdict(facts, VERDICT_RULES_V1)

    verdict_path: Path | None = None
    if request.persist:
        verdict_path = write_predictive_run_verdict(
            request.storage_root,
            envelope.manifest.run_id,
            dataset_id=envelope.manifest.dataset_id,
            dataset_fingerprint=envelope.manifest.dataset_fingerprint,
            facts=facts,
            report=report,
        )

    return EvaluateRunVerdictResult(
        run_id=envelope.manifest.run_id,
        dataset_id=envelope.manifest.dataset_id,
        dataset_fingerprint=envelope.manifest.dataset_fingerprint,
        report=report,
        verdict_path=verdict_path,
    )


def write_predictive_run_verdict(
    storage_root: Path,
    run_id: str,
    *,
    dataset_id: str,
    dataset_fingerprint: str,
    facts: VerdictFacts,
    report: VerdictReport,
) -> Path:
    """Write ``verdict.json`` next to ``metrics.json`` (ADR-0032 §4).

    ``sort_keys=True`` makes the written bytes depend only on the payload's
    values, never on dict-construction or iteration order — same facts and
    rule set on disk, byte-identical file, every time.
    """
    payload = _verdict_sidecar_payload(
        run_id=run_id,
        dataset_id=dataset_id,
        dataset_fingerprint=dataset_fingerprint,
        facts=facts,
        report=report,
    )
    path = predictive_research_run_verdict_path(storage_root, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _verdict_sidecar_payload(
    *,
    run_id: str,
    dataset_id: str,
    dataset_fingerprint: str,
    facts: VerdictFacts,
    report: VerdictReport,
) -> dict[str, Any]:
    return {
        "schema_version": VERDICT_SIDECAR_SCHEMA_VERSION,
        "rule_set_version": report.rule_set_version,
        "rule_set": VERDICT_RULES_V1.to_dict(),
        "run_id": run_id,
        "dataset_id": dataset_id,
        "dataset_fingerprint": dataset_fingerprint,
        "verdict": report.verdict.value,
        "facts": _facts_to_dict(facts),
        "rules": [evaluation.to_dict() for evaluation in report.evaluations],
    }


def _facts_to_dict(facts: VerdictFacts) -> dict[str, Any]:
    """Every extracted fact with its value and its source artifact (ADR-0032 §4).

    ``VerdictFacts`` has no ``to_dict`` of its own (D-S057-05's scope
    boundary): fact serialization for the sidecar is this I/O layer's job,
    not ``research/predictive/verdict.py``'s.
    """
    payload: dict[str, Any] = {}
    for field in dataclass_fields(facts):
        if field.name == "sources":
            continue
        payload[field.name] = {
            "value": _json_safe(getattr(facts, field.name)),
            "source": facts.sources.get(field.name),
        }
    return payload


def _json_safe(value: object) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, TaskType):
        return value.value
    if isinstance(value, timedelta):
        return value.total_seconds()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return value
