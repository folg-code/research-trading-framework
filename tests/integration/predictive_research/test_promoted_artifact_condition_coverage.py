"""ADR-0024 condition coverage this sprint closes (S049-T012).

Sprint 049 closes exactly TWO of ADR-0024's five promotion conditions in
full, plus half of a third. This file is the one place a reviewer can look
to see, in executable form, which:

    Condition 1 (Training artifact identity) -- CLOSED here.
        The promoted artifact's fingerprint is present on every manifest,
        immutable (never recomputed from the fitted parameter values), and
        derived from exactly: the training dataset (via ``run_fingerprint``,
        which itself covers ``dataset_fingerprint``), the estimator spec, the
        seed (inside ``estimator_spec``), the fold, and the format
        (ADR-0024 §1 / ADR-0029 §2). See also
        ``test_promoted_artifact_determinism_and_refusal.py``, whose (a),
        (b), (c) cases are this same condition exercised from the
        determinism/refusal angle.

    Condition 5 (Model registry) -- CLOSED here.
        The store is a plain content-addressed directory: exactly two files,
        no index, no ``latest`` pointer, no lifecycle/status field, anywhere
        (ADR-0024 §5 / ADR-0029 §2). See also
        ``test_promoted_artifact_determinism_and_refusal.py``'s (d), (e), (f).

    Condition 4 (Offline/online parity) -- HALF closed: Path A (Comparison 2,
        NumPy evaluator vs sklearn) only, in
        ``test_promoted_artifact_parity.py``. NOT covered by this file.

**Explicitly NOT closed by this sprint** (ADR-0029 Follow-up / SPRINT_049 §12):

    Condition 2 (Data leakage / inference-time feature availability) --
        NOT closed. S049-T001's spike (``S049_AVAILABILITY_FINDING.md``)
        found the executor mechanism this condition presupposes does not yet
        exist. Sizing and closing it is Sprint 050's work, possibly via
        ADR-0030.

    Condition 3 (Feature lineage) -- NOT closed by new mechanism in this
        sprint (ADR-0024 already states it needs none); no Market Analysis
        component exists yet for a promoted artifact to attach lineage to.
        That component is Sprint 050's work.

    Condition 4, Path B (offline vs online / the release gate, Comparison 1)
        -- NOT closed. This sprint ships no dry-run/live runtime component,
        so there is no "online" side to compare against yet. Sprint 050
        closes this as a release gate.

Sprint 049 ships no Market Analysis component, no State, and no registry at
all -- conditions 2, 3 and Path B of 4 have no code to test here; they are
listed above precisely so a reader does not have to infer their absence.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.integration.predictive_research._fixtures import (
    promote,
    read_promoted,
    run_fixture,
)
from trading_framework.research.datasets.promoted_artifact import (
    compute_promoted_artifact_fingerprint,
)
from trading_framework.research.predictive import TaskType

pytest.importorskip("sklearn")

pytestmark = pytest.mark.ml


# --------------------------------------------------------------------------
# Condition 1 -- Training artifact identity.
# --------------------------------------------------------------------------


def test_condition_1_fingerprint_is_present_on_every_manifest(tmp_path: Path) -> None:
    """The fingerprint is not an optional field -- every promoted manifest has one."""
    storage_root = tmp_path / "workspace"
    run_result = run_fixture(
        storage_root,
        mode="regression",
        label_kind="REGRESSION",
        family="sklearn.ridge",
        task_type=TaskType.REGRESSION,
        dataset_id="5555666677778881",
    )
    artifact_ref = promote(storage_root, run_result)
    manifest, _ = read_promoted(storage_root, artifact_ref)

    assert manifest.artifact_fingerprint
    assert manifest.artifact_fingerprint == artifact_ref.artifact_fingerprint


def test_condition_1_fingerprint_is_immutable_never_derived_from_fitted_values(
    tmp_path: Path,
) -> None:
    """The fingerprint cannot be recomputed from the fitted parameter payload.

    ``compute_promoted_artifact_fingerprint`` accepts no
    coefficient/intercept/statistics argument at all (D-S049-05 / Q9): the
    payload's fitted numbers are not part of what identifies the artifact,
    so re-deriving the fingerprint from the same declared inputs -- but a
    *different* fitted payload -- must still land on the same value.
    """
    storage_root = tmp_path / "workspace"
    run_result = run_fixture(
        storage_root,
        mode="regression",
        label_kind="REGRESSION",
        family="sklearn.ridge",
        task_type=TaskType.REGRESSION,
        dataset_id="6666777788889991",
    )
    artifact_ref = promote(storage_root, run_result)
    manifest, payload = read_promoted(storage_root, artifact_ref)

    recomputed = compute_promoted_artifact_fingerprint(
        run_fingerprint=manifest.run_fingerprint,
        fold_id=manifest.fold_id,
        format=manifest.format,
        format_version=manifest.format_version,
        model_family=manifest.model_family,
        features=manifest.feature_output_refs,
        preprocessing_spec=manifest.preprocessing_spec,
        estimator_spec=manifest.estimator_spec,
    )
    assert recomputed == manifest.artifact_fingerprint
    # The payload's actual fitted numbers played no role in the recomputation
    # above -- proving immutability structurally, not just by observation.
    assert payload.coefficients


def test_condition_1_fingerprint_is_derived_from_dataset_estimator_fold_and_format(
    tmp_path: Path,
) -> None:
    """Changing any one declared input changes the fingerprint.

    Covers the fields ADR-0024 §1 names: the training dataset (via
    ``run_fingerprint``, itself derived from ``dataset_fingerprint``), the
    estimator spec, the seed (inside ``estimator_spec``), the fold, and the
    format.
    """
    storage_root = tmp_path / "workspace"
    run_result = run_fixture(
        storage_root,
        mode="regression",
        label_kind="REGRESSION",
        family="sklearn.ridge",
        task_type=TaskType.REGRESSION,
        dataset_id="7777888899990001",
    )
    artifact_ref = promote(storage_root, run_result)
    manifest, _ = read_promoted(storage_root, artifact_ref)
    baseline = manifest.artifact_fingerprint

    def _fingerprint(**overrides: object) -> str:
        fields: dict[str, object] = {
            "run_fingerprint": manifest.run_fingerprint,
            "fold_id": manifest.fold_id,
            "format": manifest.format,
            "format_version": manifest.format_version,
            "model_family": manifest.model_family,
            "features": manifest.feature_output_refs,
            "preprocessing_spec": manifest.preprocessing_spec,
            "estimator_spec": manifest.estimator_spec,
        }
        fields.update(overrides)
        return compute_promoted_artifact_fingerprint(**fields)  # type: ignore[arg-type]

    assert _fingerprint() == baseline
    assert _fingerprint(run_fingerprint="f" * 64) != baseline
    assert _fingerprint(fold_id=manifest.fold_id + 1) != baseline
    assert _fingerprint(format_version="v2") != baseline
    assert _fingerprint(estimator_spec={**manifest.estimator_spec, "seed": 999}) != baseline


# --------------------------------------------------------------------------
# Condition 5 -- Model registry (negative constraint: none exists).
# --------------------------------------------------------------------------


def test_condition_5_store_contains_no_registry_artifact(tmp_path: Path) -> None:
    """The promoted-artifact directory has exactly the manifest and the payload.

    No index file, no ``latest`` pointer, no lifecycle/status field, no lock
    file -- ADR-0024 §5's negative constraint asserted directly against the
    filesystem, not inferred from the absence of a registry module.
    """
    storage_root = tmp_path / "workspace"
    run_result = run_fixture(
        storage_root,
        mode="regression",
        label_kind="REGRESSION",
        family="sklearn.ridge",
        task_type=TaskType.REGRESSION,
        dataset_id="8888999900001112",
    )
    artifact_ref = promote(storage_root, run_result)
    manifest, payload = read_promoted(storage_root, artifact_ref)

    from trading_framework.infrastructure.storage.paths import (
        promoted_artifact_dir,
        promoted_artifacts_root,
    )

    artifact_dir = promoted_artifact_dir(storage_root, artifact_ref.artifact_fingerprint)
    entries = sorted(path.name for path in artifact_dir.iterdir())
    assert entries == ["artifact.json", "manifest.json"]

    # No index/registry file lives at the store root beside the
    # content-addressed directories either.
    root_entries = sorted(path.name for path in promoted_artifacts_root(storage_root).iterdir())
    assert root_entries == [artifact_ref.artifact_fingerprint]

    # No lifecycle/status vocabulary anywhere in the manifest's own fields.
    manifest_fields = set(manifest.to_dict())
    assert not manifest_fields & {"status", "lifecycle", "state", "latest"}
    assert payload.coefficients  # sanity: this is a real artifact, not an empty stub
