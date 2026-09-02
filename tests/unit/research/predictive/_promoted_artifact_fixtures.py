"""Shared manifest-like fixture for promoted-artifact evaluator/guard tests.

Not named ``test_*`` so pytest never collects it. ``_FakeManifest`` is a plain
stand-in that satisfies ``PromotedManifestLike`` structurally -- deliberately
not ``research.datasets.promoted_artifact.PromotedArtifactManifest``, since
``research/predictive/`` must not depend on ``research/datasets``
(ADR-0029 Section 9).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class _FakeManifest:
    format_version: str
    model_family: str
    feature_output_refs: tuple[str, ...]
    preprocessing_spec: dict[str, object] = field(
        default_factory=lambda: {"steps": ["IMPUTE_MEDIAN", "STANDARDIZE"]}
    )
    artifact_fingerprint: str = "fp-0000"
    #: Provenance only (D-S049-07) -- the evaluator never reads this field.
    training_library_version: str = "1.3.0"


def _manifest(
    *,
    model_family: str = "sklearn.ridge",
    n_features: int = 2,
    format_version: str = "v1",
    steps: tuple[str, ...] = ("IMPUTE_MEDIAN", "STANDARDIZE"),
    fingerprint: str = "fp-0000",
    training_library_version: str = "1.3.0",
) -> _FakeManifest:
    return _FakeManifest(
        format_version=format_version,
        model_family=model_family,
        feature_output_refs=tuple(f"feature_{i}" for i in range(n_features)),
        preprocessing_spec={"steps": list(steps)},
        artifact_fingerprint=fingerprint,
        training_library_version=training_library_version,
    )
