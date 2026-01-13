"""
Authentication configuration for IQ-MCP server with Claude Desktop compatibility.

Claude Desktop requires full OAuth server endpoints, not just DCR discovery.
We use OAuthProxy to bridge Claude Desktop ↔ Supabase Auth.

REQUIREMENT: You must create OAuth client credentials in Supabase:
1. Go to Supabase Dashboard → Authentication → OAuth Apps
2. Create a new OAuth app for IQ-MCP
3. Get client_id and client_secret
4. Set IQ_OAUTH_CLIENT_ID and IQ_OAUTH_CLIENT_SECRET in Railway
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import os

from .iq_logging import logger

if TYPE_CHECKING:
    from fastmcp.server.auth import AuthProvider


def get_auth_provider(require_auth: bool = False) -> "AuthProvider | None":
    """
    Create OAuth 2.1 provider using OAuthProxy for Claude Desktop compatibility.

    Requires OAuth client credentials:
    - IQ_OAUTH_CLIENT_ID (from Supabase OAuth app)
    - IQ_OAUTH_CLIENT_SECRET (from Supabase OAuth app)

    OAuthProxy provides full OAuth endpoints:
    - /.well-known/oauth-protected-resource (discovery)
    - /oauth/authorize (authorization)
    - /oauth/callback (callback handler)
    - /oauth/consent (consent page)
    """
    from .context import ctx

    logger.info("🔐 Configuring OAuthProxy for Claude Desktop")

    if not ctx.is_initialized:
        raise RuntimeError("Context not initialized")

    if not ctx.settings.supabase_auth_enabled:
        if require_auth:
            raise ValueError("IQ_ENABLE_SUPABASE_AUTH must be true")
        logger.warning("⚠️  Supabase auth not enabled")
        return None

    try:
        from fastmcp.server.auth.providers.oauth_proxy import OAuthProxy
        from fastmcp.server.auth.providers.jwt import JWTVerifier

        supabase_auth = ctx.settings.supabase_auth
        base_url = os.getenv("IQ_BASE_URL")
        client_id = os.getenv("IQ_OAUTH_CLIENT_ID")
        client_secret = os.getenv("IQ_OAUTH_CLIENT_SECRET")

        # Validate required credentials
        if not base_url:
            raise ValueError("IQ_BASE_URL is required")

        if not client_id or not client_secret:
            logger.error("❌ Missing OAuth client credentials")
            logger.error("   Required: IQ_OAUTH_CLIENT_ID, IQ_OAUTH_CLIENT_SECRET")
            logger.error("   Create at: Supabase Dashboard → Authentication → OAuth Apps")
            if require_auth:
                raise ValueError("OAuth client credentials required")
            return None

        project_url = supabase_auth.project_url.rstrip("/")
        auth_base_url = base_url.rstrip("/")

        logger.info("✅ OAuthProxy configured with client credentials")
        logger.info(f"   Project: {project_url}")
        logger.info(f"   Base URL: {auth_base_url}")
        logger.info(f"   Client ID: {client_id[:10]}...")  # Partial for security

        # JWT verifier for token validation
        token_verifier = JWTVerifier(
            jwks_uri=f"{project_url}/auth/v1/.well-known/jwks.json",
            issuer=f"{project_url}/auth/v1",
            audience=auth_base_url,
            required_scopes=supabase_auth.required_scopes or None,
        )

        # OAuthProxy for full OAuth endpoints
        oauth_proxy = OAuthProxy(
            upstream_authorization_endpoint=f"{project_url}/auth/v1/oauth/authorize",
            upstream_token_endpoint=f"{project_url}/auth/v1/oauth/token",
            upstream_client_id=client_id,
            upstream_client_secret=client_secret,
            token_verifier=token_verifier,
            base_url=auth_base_url,
            redirect_path="/oauth/callback",
            issuer_url=auth_base_url,
        )

        logger.info("🔐 OAuthProxy ready for Claude Desktop")
        logger.info(f"   🌐 Discovery: {auth_base_url}/.well-known/oauth-protected-resource")
        logger.info(f"   🌐 Authorization: {auth_base_url}/oauth/authorize")
        logger.info(f"   🌐 Callback: {auth_base_url}/oauth/callback")
        logger.info("   ✨ Claude Desktop can now use full OAuth flow")

        return oauth_proxy

    except ImportError as e:
        logger.error(f"❌ OAuthProxy not available: {e}")
        logger.error("   This FastMCP version may not include OAuthProxy")
        raise RuntimeError("OAuthProxy provider not available")

    except Exception as e:
        logger.error(f"❌ Failed to configure OAuthProxy: {e}")
        raise


__all__ = ["get_auth_provider"]