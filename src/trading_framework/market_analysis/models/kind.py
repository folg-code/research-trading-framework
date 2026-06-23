"""Component classification enums."""

from enum import StrEnum


class ComponentKind(StrEnum):
    """Public Market Analysis component categories for MVP."""

    FEATURE = "feature"
    STRUCTURE = "structure"
    STATE = "state"


class Causality(StrEnum):
    """Declared causality category for a component."""

    CAUSAL = "causal"
    DELAYED = "delayed"
    RETROSPECTIVE = "retrospective"
