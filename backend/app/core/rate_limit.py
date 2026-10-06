"""
Rate limiting configuration using slowapi.

This provides protection against brute-force attacks on authentication endpoints
and general API abuse.
"""
from functools import lru_cache

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse


def get_client_ip(request: Request) -> str:
    """
    Get client IP address, respecting X-Forwarded-For header for proxied requests.
    In production behind Nginx/Apache, the real IP is in X-Forwarded-For.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can be a comma-separated list; first is the real client
        return forwarded_for.split(",")[0].strip()
    return get_remote_address(request)


# Create the limiter instance
limiter = Limiter(key_func=get_client_ip)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded errors."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. Please try again later.",
            "retry_after": exc.detail,
        },
    )


# Rate limit constants for different endpoint categories
class RateLimits:
    """Centralized rate limit definitions."""
    
    # Authentication endpoints - strictest limits
    LOGIN = "5/minute"  # 5 login attempts per minute
    PASSWORD_RESET = "3/minute"  # 3 password reset requests per minute
    
    # General API endpoints
    READ_DEFAULT = "60/minute"  # Standard read operations
    WRITE_DEFAULT = "30/minute"  # Standard write operations
    
    # File uploads
    FILE_UPLOAD = "10/minute"  # File upload limit
    
    # Public form submissions (contact, proposals, etc.)
    PUBLIC_FORM = "5/minute"  # Public form submissions
    
    # Heavy operations (CSV import, etc.)
    HEAVY_OPERATION = "5/minute"
