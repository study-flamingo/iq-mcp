"""
Authentication configuration for IQ-MCP server using RemoteAuthProvider.

RemoteAuthProvider enables Dynamic Client Registration (DCR) with Supabase Auth,
allowing MCP clients to automatically register without manual OAuth app setup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import os

from .iq_logging import logger

if TYPE_CHECKING:
    from fastmcp.server.auth import AuthProvider


def get_auth_provider(require_auth: bool = False) -> "AuthProvider | None":
    """
    Create RemoteAuthProvider for DCR with Supabase Auth.

    Uses Supabase's OAuth 2.1 server with Dynamic Client Registration,
    allowing MCP clients to self-register without manual client credentials.

    Required environment variables:
    - IQ_ENABLE_SUPABASE_AUTH=true
    - IQ_SUPABASE_AUTH_PROJECT_URL=https://xxx.supabase.co
    - IQ_SUPABASE_AUTH_ALGORITHM=ES256
    - IQ_BASE_URL=https://iq-mcp-dev.up.railway.app

    NOT required:
    - IQ_OAUTH_CLIENT_ID (DCR handles this)
    - IQ_OAUTH_CLIENT_SECRET (DCR handles this)
    """
    from .context import ctx

    logger.info("🔐 Configuring RemoteAuthProvider for DCR")

    if not ctx.is_initialized:
        raise RuntimeError("Context not initialized")

    if not ctx.settings.supabase_auth_enabled:
        if require_auth:
            raise ValueError("IQ_ENABLE_SUPABASE_AUTH must be true")
        logger.warning("⚠️  Supabase auth not enabled")
        return None

    try:
        from fastmcp.server.auth import RemoteAuthProvider
        from fastmcp.server.auth.providers.jwt import JWTVerifier
        from pydantic import AnyHttpUrl

        supabase_auth = ctx.settings.supabase_auth
        base_url = os.getenv("IQ_BASE_URL")

        # Validate required configuration
        if not base_url:
            raise ValueError("IQ_BASE_URL is required for RemoteAuthProvider")

        project_url = supabase_auth.project_url.rstrip("/")
        auth_base_url = base_url.rstrip("/")

        logger.info("✅ RemoteAuthProvider configuration:")
        logger.info(f"   Project: {project_url}")
        logger.info(f"   Base URL: {auth_base_url}")
        logger.info(f"   Algorithm: {supabase_auth.algorithm}")

        # JWT verifier for token validation
        token_verifier = JWTVerifier(
            jwks_uri=f"{project_url}/auth/v1/.well-known/jwks.json",
            issuer=f"{project_url}/auth/v1",
            audience=auth_base_url,
            required_scopes=supabase_auth.required_scopes or None,
        )

        # RemoteAuthProvider for DCR
        auth = RemoteAuthProvider(
            token_verifier=token_verifier,
            authorization_servers=[AnyHttpUrl(f"{project_url}/auth/v1")],
            base_url=auth_base_url,
        )

        logger.info("🔐 RemoteAuthProvider ready for DCR")
        logger.info(f"   🌐 Discovery: {auth_base_url}/.well-known/oauth-protected-resource")
        logger.info(f"   🌐 Authorization server: {project_url}/auth/v1")
        logger.info("   ✨ MCP clients can now self-register via DCR!")

        return auth

    except ImportError as e:
        logger.error(f"❌ RemoteAuthProvider not available: {e}")
        logger.error("   Ensure FastMCP 2.13.3+ is installed")
        raise RuntimeError("RemoteAuthProvider not available")

    except Exception as e:
        logger.error(f"❌ Failed to configure RemoteAuthProvider: {e}")
        raise


__all__ = ["get_auth_provider"]
