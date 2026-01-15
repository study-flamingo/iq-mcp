"""
Authentication configuration for IQ-MCP server using SupabaseProvider.

SupabaseProvider integrates with Supabase Auth's JWT verification and supports
Dynamic Client Registration (DCR) through metadata forwarding. Supabase handles
the OAuth flow directly while FastMCP acts as a resource server.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import os

from .iq_logging import logger

if TYPE_CHECKING:
    from fastmcp.server.auth import AuthProvider


def get_auth_provider(require_auth: bool = False) -> "AuthProvider | None":
    """
    Create SupabaseProvider for OAuth 2.1 with Supabase Auth.

    Uses Supabase's OAuth 2.1 server with metadata forwarding. Supabase handles
    the OAuth flow directly (including DCR) while FastMCP validates JWTs.

    Required environment variables:
    - IQ_ENABLE_SUPABASE_AUTH=true
    - IQ_SUPABASE_AUTH_PROJECT_URL=https://xxx.supabase.co
    - IQ_SUPABASE_AUTH_ALGORITHM=ES256
    - IQ_BASE_URL=https://your-server.com

    NOT required (Supabase handles OAuth flow):
    - IQ_OAUTH_CLIENT_ID
    - IQ_OAUTH_CLIENT_SECRET
    """
    from .context import ctx

    logger.info("🔐 Configuring SupabaseProvider")

    if not ctx.is_initialized:
        raise RuntimeError("Context not initialized")

    if not ctx.settings.supabase_auth_enabled:
        if require_auth:
            raise ValueError("IQ_ENABLE_SUPABASE_AUTH must be true")
        logger.warning("⚠️  Supabase auth not enabled")
        return None

    try:
        from fastmcp.server.auth.providers.supabase import SupabaseProvider

        supabase_auth = ctx.settings.supabase_auth
        base_url = os.getenv("IQ_BASE_URL")
        mcp_path = os.getenv("IQ_MCP_PATH", "/")

        # Validate required configuration
        if not base_url:
            raise ValueError("IQ_BASE_URL is required for SupabaseProvider")

        project_url = supabase_auth.project_url.rstrip("/")

        # Include MCP path in base_url for correct OAuth discovery
        if mcp_path and mcp_path != "/":
            auth_base_url = f"{base_url.rstrip('/')}{mcp_path}"
        else:
            auth_base_url = base_url.rstrip("/")

        logger.info("✅ SupabaseProvider configuration:")
        logger.info(f"   Project URL: {project_url}")
        logger.info(f"   Base URL: {auth_base_url}")
        logger.info(f"   Algorithm: {supabase_auth.algorithm}")

        # SupabaseProvider handles JWT validation via JWKS and metadata forwarding
        auth = SupabaseProvider(
            project_url=project_url,
            base_url=auth_base_url,
            algorithm=supabase_auth.algorithm,
            required_scopes=supabase_auth.required_scopes or None,
        )

        logger.info("🔐 SupabaseProvider ready")
        logger.info(f"   🌐 JWKS: {project_url}/auth/v1/.well-known/jwks.json")
        logger.info(f"   🌐 Auth Server: {project_url}/auth/v1")
        logger.info("   ✨ Supabase handles OAuth flow, FastMCP validates JWTs")

        return auth

    except ImportError as e:
        logger.error(f"❌ SupabaseProvider not available: {e}")
        logger.error("   Ensure FastMCP 2.14.3+ is installed")
        raise RuntimeError("SupabaseProvider not available")

    except Exception as e:
        logger.error(f"❌ Failed to configure SupabaseProvider: {e}")
        raise


__all__ = ["get_auth_provider"]
