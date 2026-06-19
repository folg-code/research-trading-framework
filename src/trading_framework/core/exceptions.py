"""Base exception hierarchy for the trading framework."""


class TradingFrameworkError(Exception):
    """Base exception for all framework errors."""


class ValidationError(TradingFrameworkError):
    """Raised when domain or input validation fails."""


class ConfigurationError(TradingFrameworkError):
    """Raised when configuration is missing, malformed or invalid."""
