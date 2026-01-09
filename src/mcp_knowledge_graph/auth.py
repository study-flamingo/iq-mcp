"""
Authentication configuration for IQ-MCP server.

Provides flexible authentication for HTTP transport deployments.
For single-user deployments, uses StaticTokenVerifier with API keys.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from .iq_logging import logger

if TYPE_CHECKING:
    from fastmcp.server.auth import AuthProvider


def get_auth_provider(require_auth: bool = False) -> "AuthProvider | None":
    """
    Create auth provider based on environment configuration.

    Args:
        require_auth: If True, raises an error when IQ_API_KEY is not set.
                     Use this for production deployments to prevent accidental
                     deployment without authentication.

    Returns:
        AuthProvider instance if IQ_API_KEY is set, None otherwise.

    Raises:
        ValueError: If require_auth=True and IQ_API_KEY is not set.

    Environment Variables:
        IQ_API_KEY: The API key required for authentication.
        IQ_CLIENT_ID: Client identifier for the token (default: "iq-mcp-user").
        IQ_REQUIRE_AUTH: Set to "true" to enforce authentication (same as require_auth=True).

    Usage:
        Set IQ_API_KEY in your environment or .env file:
            IQ_API_KEY=iqmcp-sk-your-secret-key

        Clients authenticate with:
            Authorization: Bearer iqmcp-sk-your-secret-key
    """
    api_key = os.getenv("IQ_API_KEY")

    # Check if auth is required via env var or parameter
    require_auth = require_auth or os.getenv("IQ_REQUIRE_AUTH", "false").lower() == "true"

    if not api_key:
        if require_auth:
            raise ValueError(
                "❌ SECURITY: IQ_API_KEY not set but authentication is required! "
                "Set IQ_API_KEY or set IQ_REQUIRE_AUTH=false to allow unauthenticated access (NOT recommended for production)."
            )
        logger.warning(
            "⚠️  IQ_API_KEY not set - server will run WITHOUT authentication! "
            "Set IQ_API_KEY for production deployments or IQ_REQUIRE_AUTH=true to enforce."
        )
        return None

    # Import here to avoid issues if fastmcp version doesn't have this
    try:
        from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
    except ImportError:
        logger.error(
            "❌ StaticTokenVerifier not available. "
            "Upgrade fastmcp to >=2.13.0 for authentication support."
        )
        return None

    client_id = os.getenv("IQ_CLIENT_ID", "iq-mcp-user")

    verifier = StaticTokenVerifier(
        tokens={
            api_key: {
                "client_id": client_id,
                "scopes": ["read", "write", "admin"],
            }
        },
        required_scopes=["read"],
    )

    logger.info(f"🔐 Authentication enabled for client: {client_id}")
    return verifier


__all__ = ["get_auth_provider"]

