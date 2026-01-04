"""
Authentication middleware for web routes.

Validates JWT tokens passed via Authorization header for securing
the graph visualizer and API endpoints.
"""

from functools import wraps
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Callable
import os

from ..iq_logging import logger
from ..context import ctx

security = HTTPBearer()


def get_expected_token() -> str | None:
    """Get the expected API key from environment or context."""
    # First try the web-specific token
    token = os.getenv("IQ_GRAPH_JWT_TOKEN")
    if token:
        return token

    # Fall back to the main API key
    token = os.getenv("IQ_API_KEY")
    if token:
        return token

    return None


async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    Verify the JWT token from the Authorization header.

    Args:
        credentials: HTTP authorization credentials

    Returns:
        The validated token

    Raises:
        HTTPException: If token is invalid or missing
    """
    expected_token = get_expected_token()

    if not expected_token:
        logger.warning("⚠️  No IQ_GRAPH_JWT_TOKEN or IQ_API_KEY set - web access is UNPROTECTED!")
        return credentials.token  # Allow access but warn

    if credentials.token != expected_token:
        logger.warning(f"❌ Invalid token attempt: {credentials.token[:10]}...")
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.token


def require_auth(func: Callable) -> Callable:
    """
    Decorator to require authentication for route handlers.

    Usage:
        @app.get("/protected")
        @require_auth
        async def protected_route(token: str = Depends(verify_token)):
            return {"message": "authenticated"}
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Token verification happens via Depends(verify_token) in route signature
        return await func(*args, **kwargs)
    return wrapper
