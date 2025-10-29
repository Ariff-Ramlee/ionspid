"""
Custom exception hierarchy for iONspID pipeline.

Defines base and specialized exceptions for CLI, input, processing, and configuration errors.
"""

class iONspIDError(Exception):
    """Base class for all iONspID exceptions."""
    pass

class CLIError(iONspIDError):
    """Errors related to command-line interface usage."""
    pass

class InputError(iONspIDError):
    """Errors related to invalid or missing input data."""
    pass

class ProcessingError(iONspIDError):
    """Errors occurring during data processing."""
    pass

class ConfigError(iONspIDError):
    """Errors related to configuration issues."""
    pass
