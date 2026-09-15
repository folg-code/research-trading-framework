"""``workbench_core`` -- Research Workbench control core (ADR-0037 section 2).

MAY import ``trading_framework.application.*`` and the ADR-0026 Amendment 1
allow-list (value objects, typed identifiers, spec loaders). MUST NOT import
``trading_framework.research.*``, ``.market_analysis.*``, ``.strategy.*``,
``.execution.*``, or an infrastructure adapter beyond that allow-list, and
MUST NOT reimplement anything already in ``trading_framework.application``.
Enforced by ``tests/unit/test_apps_boundaries.py``.
"""
