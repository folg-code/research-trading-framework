"""Base exception hierarchy for the trading framework."""


class TradingFrameworkError(Exception):
    """Base exception for all framework errors."""


class ValidationError(TradingFrameworkError):
    """Raised when domain or input validation fails."""


class ConfigurationError(TradingFrameworkError):
    """Raised when configuration is missing, malformed or invalid."""


class IncompatibleExecutionStateError(TradingFrameworkError):
    """Raised when persisted execution state is incompatible or unreadable.

    A runtime that finds this on start must refuse to start rather than
    silently discarding the persisted state (ADR-0035 S4.4).
    """
