"""The copy-pasteable authoring example in docs must stay executable and IR-free."""

from __future__ import annotations

import ast
from pathlib import Path

from trading_framework.model_authoring import AuthoredMarketModel, AuthoredSignalModel

_REPO_ROOT = Path(__file__).resolve().parents[3]
_AUTHORING_DOC = _REPO_ROOT / "docs" / "reference" / "modules" / "MODEL_AUTHORING.md"
_ALLOWED_IMPORT_PREFIX = "trading_framework.model_authoring"


def _python_fence(markdown: str) -> str:
    start = markdown.find("```python")
    if start < 0:
        msg = "MODEL_AUTHORING.md must contain one python code fence"
        raise AssertionError(msg)
    body_start = markdown.find("\n", start) + 1
    end = markdown.find("```", body_start)
    if end < 0:
        msg = "MODEL_AUTHORING.md python fence is unclosed"
        raise AssertionError(msg)
    return markdown[body_start:end]


def _imported_modules(source: str) -> tuple[str, ...]:
    tree = ast.parse(source)
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.append(node.module)
    return tuple(names)


def test_copy_paste_example_imports_only_model_authoring() -> None:
    source = _python_fence(_AUTHORING_DOC.read_text(encoding="utf-8"))
    imported = _imported_modules(source)
    assert imported == (_ALLOWED_IMPORT_PREFIX,)
    assert "model_expression" not in source

    namespace: dict[str, object] = {}
    exec(compile(source, str(_AUTHORING_DOC), "exec"), namespace)

    trend_and_range = namespace["trend_and_range"]
    higher_low_long = namespace["higher_low_long"]
    assert isinstance(trend_and_range, AuthoredMarketModel)
    assert isinstance(higher_low_long, AuthoredSignalModel)
    assert trend_and_range.definition.market_model_id == "trend_and_range"
    assert higher_low_long.definition.signal_model_id == "higher_low_long"
    assert len(trend_and_range.dependencies().component_requests) == 2
    assert len(higher_low_long.dependencies().component_requests) == 1
