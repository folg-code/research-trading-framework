"""T022: Predictive Research packages import without the optional ml extra."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import trading_framework


def test_predictive_packages_import_without_sklearn() -> None:
    src_root = Path(trading_framework.__file__).resolve().parents[1]
    repo_root = src_root.parent
    env = os.environ.copy()
    pythonpath = [str(src_root), str(repo_root)]
    existing = env.get("PYTHONPATH")
    if existing:
        pythonpath.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath)

    script = """
import sys

class _BlockMl:
    def find_spec(self, fullname, path=None, target=None):
        root = fullname.split('.', 1)[0]
        if root in {'sklearn', 'xgboost', 'lightgbm', 'catboost'}:
            raise ImportError(f'{root} must not be required to import predictive packages')
        return None

sys.meta_path.insert(0, _BlockMl())

import trading_framework.research.predictive as predictive
import trading_framework.application.predictive_research as application
from trading_framework.infrastructure.ml.registry import registered_families
from scripts.predictive_research import (
    analyze_predictive_run,
    render_predictive_report,
    run_predictive_research,
)

assert predictive.EstimatorSpec is not None
assert application.run_predictive_research is not None
assert application.analyze_predictive_run is not None
assert application.render_predictive_research_report is not None
assert run_predictive_research.main is not None
assert analyze_predictive_run.main is not None
assert render_predictive_report.main is not None
assert registered_families()['xgboost.regressor'] == 'ml-trees'

blocked = ('sklearn', 'xgboost', 'lightgbm', 'catboost')
loaded = [
    name for name in sys.modules
    if name in blocked or name.startswith(tuple(root + '.' for root in blocked))
]
assert loaded == [], loaded
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(repo_root),
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
