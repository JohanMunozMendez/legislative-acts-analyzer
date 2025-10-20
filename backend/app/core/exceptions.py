"""
Custom exceptions for the application.

Provides specific exception types for better error handling and logging.
"""


class AppBaseException(Exception):
    """Base exception for all application errors."""
    pass


# ═══════════════════════════════════════════════════════════
# Document Processing Errors
# ═══════════════════════════════════════════════════════════

class DocumentProcessingError(AppBaseException):
    """Base exception for document processing errors."""
    pass


class InvalidDocumentFormatError(DocumentProcessingError):
    """Raised when document format is not supported."""
    pass


class DocumentTooLargeError(DocumentProcessingError):
    """Raised when document exceeds size limits."""
    pass


class DocumentExtractionError(DocumentProcessingError):
    """Raised when text extraction fails."""
    pass


# ═══════════════════════════════════════════════════════════
# OpenAI Service Errors
# ═══════════════════════════════════════════════════════════

class OpenAIServiceError(AppBaseException):
    """Base exception for OpenAI service errors."""
    pass


class OpenAIRateLimitError(OpenAIServiceError):
    """Raised when OpenAI API rate limit is exceeded."""
    pass


class OpenAIAuthenticationError(OpenAIServiceError):
    """Raised when OpenAI API authentication fails."""
    pass


# ═══════════════════════════════════════════════════════════
# Configuration Errors
# ═══════════════════════════════════════════════════════════

class ConfigurationError(AppBaseException):
    """Base exception for configuration errors."""
    pass


class MissingCredentialsError(ConfigurationError):
    """Raised when required credentials are missing."""
    pass


class InvalidConfigError(ConfigurationError):
    """Raised when configuration is invalid."""
    pass