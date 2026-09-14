"""``workbench_ui`` -- Research Workbench presentation package (ADR-0037 section 2).

Deliberately minimal: the frontend framework choice is a separate, deferred
decision (ADR-0037 Follow-up; PRD non-goal). This package MUST NOT import
``trading_framework`` at all -- it talks to ``workbench_core`` only over the
loopback JSON API (``workbench.api.v1``). Enforced by
``tests/unit/test_apps_boundaries.py``.
"""
