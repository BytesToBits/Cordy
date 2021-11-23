"""All cordy exceptions"""

__all__ = (
    "CordyError",
)

class CordyError(Exception):
    """Base class for all cordy related exceptions"""
    pass

class RateLimitTooLong(CordyError):
    """Raised when rate limit is too long to be passed by sleeping."""
    pass

class MissingPermissions(CordyError):
    """Raised when an endpoint requiring permission is requested"""
    pass

class InvalidAuth(CordyError):
    """Raised when an invalid token is used in a request"""