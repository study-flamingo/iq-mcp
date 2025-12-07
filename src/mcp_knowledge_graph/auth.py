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


def get_auth_provider() -> "AuthProvider | None":
    """
    Create auth provider based on environment configuration.

    Returns:
        AuthProvider instance if IQ_API_KEY is set, None otherwise.

    Environment Variables:
        IQ_API_KEY: The API key required for authentication.
        IQ_CLIENT_ID: Client identifier for the token (default: "iq-mcp-user").

    Usage:
        Set IQ_API_KEY in your environment or .env file:
            IQ_API_KEY=iqmcp-sk-your-secret-key

        Clients authenticate with:
            Authorization: Bearer iqmcp-sk-your-secret-key
    """
    api_key = os.getenv("IQ_API_KEY")

    if not api_key:
        logger.warning(
            "⚠️  IQ_API_KEY not set - server will run WITHOUT authentication! "
            "Set IQ_API_KEY for production deployments."
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

