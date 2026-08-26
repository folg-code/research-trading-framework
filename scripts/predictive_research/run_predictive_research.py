"""Run Predictive Research baselines on one persisted dataset."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from trading_framework.application.predictive_research import (
    RunPredictiveResearchRequest,
    run_predictive_research,
)
from trading_framework.core.exceptions import ValidationError
from trading_framework.research.datasets.predictive import PredictiveDatasetRef
from trading_framework.research.predictive.errors import PredictiveSpecError
from trading_framework.research.predictive.estimators import EstimatorSpec


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Predictive Research on one persisted dataset envelope.",
    )
    parser.add_argument(
        "--storage-root",
        required=True,
        type=Path,
        help="Workspace root (contains market_data/ and research/)",
    )
    parser.add_argument(
        "--dataset-id",
        required=True,
        help="Persisted Predictive Research dataset_id",
    )
    parser.add_argument(
        "--estimator",
        type=Path,
        help="Path to EstimatorSpec YAML or JSON file",
    )
    parser.add_argument("--family", help="Estimator family id (for example sklearn.ridge)")
    parser.add_argument("--seed", type=int, help="Required estimator seed")
    parser.add_argument("--task-type", dest="task_type", help="REGRESSION or CLASSIFICATION")
    parser.add_argument(
        "--hyperparameters",
        help="JSON object of estimator hyperparameters (flag spec only)",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Run without writing the run envelope to storage",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print run result as JSON",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        estimator = _estimator_spec_from_args(args)
        result = run_predictive_research(
            RunPredictiveResearchRequest(
                dataset_ref=PredictiveDatasetRef(dataset_id=args.dataset_id),
                estimator=estimator,
                storage_root=args.storage_root,
                persist=not args.no_persist,
            )
        )
    except (ValidationError, FileNotFoundError, FileExistsError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    payload = {
        "run_id": result.run_id,
        "fingerprint": result.fingerprint,
        "persisted": result.persisted,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"run_id: {payload['run_id']}")
        print(f"fingerprint: {payload['fingerprint']}")
        print(f"persisted: {payload['persisted']}")
    return 0


def _estimator_spec_from_args(args: argparse.Namespace) -> EstimatorSpec:
    flag_present = any(
        value is not None
        for value in (args.family, args.seed, args.task_type, args.hyperparameters)
    )
    if args.estimator is not None and flag_present:
        msg = "use --estimator or flag spec (--family/--seed/--task-type), not both"
        raise PredictiveSpecError(msg)
    if args.estimator is not None:
        return EstimatorSpec.from_dict(_load_estimator_mapping(args.estimator))
    if args.family is None or args.seed is None or args.task_type is None:
        msg = "provide --estimator or --family, --seed, and --task-type"
        raise PredictiveSpecError(msg)
    hyperparameters: dict[str, Any] = {}
    if args.hyperparameters is not None:
        hyperparameters = _hyperparameters_from_json(args.hyperparameters)
    return EstimatorSpec.from_dict(
        {
            "family": args.family,
            "seed": args.seed,
            "task_type": args.task_type,
            "hyperparameters": hyperparameters,
        }
    )


def _load_estimator_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        msg = f"estimator file not found: {path}"
        raise PredictiveSpecError(msg)
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        payload = _load_json_mapping(text, source_path=path)
    elif suffix in {".yaml", ".yml"}:
        payload = _load_yaml_mapping(text, source_path=path)
    else:
        msg = f"unsupported estimator file extension: {suffix!r}"
        raise PredictiveSpecError(msg)
    if not isinstance(payload, dict):
        msg = "estimator spec root must be a mapping"
        raise PredictiveSpecError(msg)
    return payload


def _load_json_mapping(text: str, *, source_path: Path) -> object:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        msg = f"invalid JSON estimator file: {source_path}"
        raise PredictiveSpecError(msg) from exc


def _load_yaml_mapping(text: str, *, source_path: Path) -> object:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:
        msg = (
            "PyYAML is required to load YAML estimator specs; "
            f"install pyyaml or use JSON for {source_path}"
        )
        raise PredictiveSpecError(msg) from exc
    return yaml.safe_load(text)


def _hyperparameters_from_json(raw: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        msg = "estimator hyperparameters must be valid JSON"
        raise PredictiveSpecError(msg) from exc
    if not isinstance(payload, dict):
        msg = "estimator hyperparameters must be a mapping"
        raise PredictiveSpecError(msg)
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
