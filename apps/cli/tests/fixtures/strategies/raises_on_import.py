"""A fixture strategy file that raises while the module itself is imported."""

raise RuntimeError("deliberate failure at import time (fixture)")


def build_strategy():  # pragma: no cover - never reached
    raise AssertionError("unreachable")
