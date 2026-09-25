"""Domain-specific custom exceptions for the Delhi AQI & Weather system."""


class DelhiAQIError(Exception):
    """Base exception for all domain errors."""


class ConfigurationError(DelhiAQIError):
    """Raised when configuration is missing, incomplete, or invalid."""


class IngestionError(DelhiAQIError):
    """Base exception for ingestion issues."""


class ProviderUnavailableError(IngestionError):
    """Raised when an external data provider (API) is unreachable or times out."""


class RateLimitExceededError(IngestionError):
    """Raised when API rate limits are encountered."""


class ValidationError(DelhiAQIError):
    """Raised when incoming data violates validation constraints or schemas."""


class AlignmentError(DelhiAQIError):
    """Raised when spatial or temporal alignment fails."""


class ModelNotTrainedError(DelhiAQIError):
    """Raised when attempting inference on an uninitialized or missing model artifact."""
