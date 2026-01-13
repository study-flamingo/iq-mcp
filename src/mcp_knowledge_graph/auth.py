"""
Authentication configuration for IQ-MCP server - testing SupabaseProvider for OAuth 2.1.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import os

from .iq_logging import logger

if TYPE_CHECKING:
    from fastmcp.server.auth import AuthProvider, AccessToken


def get_auth_provider(require_auth: bool = False) -> "AuthProvider | None":
    """
    Create OAuth 2.1 auth provider using SupabaseProvider.
    """
    from .context import ctx

    logger.info("🔐 Configuring SupabaseProvider for OAuth 2.1")

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

        if not base_url:
            raise ValueError("IQ_BASE_URL is required")

        logger.info(f"✅ SupabaseProvider: project={supabase_auth.project_url}")
        logger.info(f"   base_url={base_url}, algorithm={supabase_auth.algorithm}")

        # Use SupabaseProvider (does JWT validation via JWKS)
        provider = SupabaseProvider(
            project_url=supabase_auth.project_url,
            base_url=base_url,
            algorithm=supabase_auth.algorithm,
            required_scopes=supabase_auth.required_scopes or None,
        )

        logger.info("🔐 SupabaseProvider configured")
        logger.info("   Users authenticate with Supabase, bring JWT tokens")

        return provider

    except ImportError as e:
        logger.error(f"❌ SupabaseProvider not available: {e}")
        raise RuntimeError("Need FastMCP with SupabaseProvider")

    except Exception as e:
        logger.error(f"❌ Failed to configure SupabaseProvider: {e}")
        raise


__all__ = ["get_auth_provider"]