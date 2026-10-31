"""
Custom typed exceptions for LLM providers.
Ensures transparent error handling without silent synthetic mock fallbacks.
"""

from typing import Optional


class LLMProviderError(Exception):
    """Base exception for all LLM provider failures."""

    def __init__(self, message: str, provider: str = "unknown", status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.status_code = status_code

    def __str__(self):
        code_str = f" [HTTP {self.status_code}]" if self.status_code else ""
        return f"[{self.provider.upper()}{code_str}] {self.message}"


class AuthenticationError(LLMProviderError):
    """Raised when an API key is missing, invalid, or unauthorized (HTTP 401/403)."""
    pass


class RateLimitError(LLMProviderError):
    """Raised when rate limits or quotas are exceeded (HTTP 429)."""
    pass


class ProviderTimeoutError(LLMProviderError):
    """Raised when an LLM provider request times out."""
    pass


class NetworkError(LLMProviderError):
    """Raised when network connectivity fails (connection refused, DNS error)."""
    pass


class InvalidRequestError(LLMProviderError):
    """Raised when a request is malformed or exceeds model context limits (HTTP 400)."""
    pass
