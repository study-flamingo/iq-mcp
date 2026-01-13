"""
Authentication configuration for IQ-MCP server - OAuth 2.1 with DCR ONLY.

This server ONLY supports OAuth 2.1 with Dynamic Client Registration (DCR) via Supabase.
No API key or other authentication methods are provided.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .iq_logging import logger

if TYPE_CHECKING:
    from fastmcp.server.auth import AuthProvider, AccessToken


class ChainedAuthProvider:
    """
    Composite auth provider that tries multiple verification methods in sequence.

    Note: Used only if we need multiple auth methods in the future.
    For now, we use RemoteAuthProvider directly.
    """
    def __init__(self, providers: list["AuthProvider"]):
        if not providers:
            raise ValueError("At least one provider required")
        self.providers = providers
        self.base_url = providers[0].base_url
        self.required_scopes = providers[0].required_scopes

    async def verify_token(self, token: str) -> "AccessToken | None":
        for i, provider in enumerate(self.providers):
            try:
                result = await provider.verify_token(token)
                if result is not None:
                    logger.debug(f"Token verified by provider {i}: {type(provider).__name__}")
                    return result
            except Exception as e:
                logger.debug(f"Provider {i} verification failed: {e}")
                continue
        return None

    def get_routes(self, mcp_path: str | None = None) -> list:
        routes = []
        seen_paths = set()
        for provider in self.providers:
            for route in provider.get_routes(mcp_path=mcp_path):
                if route.path not in seen_paths:
                    routes.append(route)
                    seen_paths.add(route.path)
        return routes

    def get_middleware(self) -> list:
        if hasattr(self.providers[0], "get_middleware"):
            return self.providers[0].get_middleware()
        return []


def get_auth_provider(require_auth: bool = False) -> "AuthProvider | None":
    """
    Create OAuth 2.1 with DCR auth provider (RemoteAuthProvider only).

    This is the ONLY authentication method supported by IQ-MCP v1.6.0+.
    Clients must use OAuth 2.1 discovery with DCR through Supabase.

    Required Environment Variables:
        IQ_ENABLE_SUPABASE_AUTH=true
        IQ_SUPABASE_AUTH_PROJECT_URL=https://your-project.supabase.co
        IQ_SUPABASE_AUTH_ALGORITHM=ES256  # ES256 or RS256 only (asymmetric)
        IQ_BASE_URL=https://your-public-server-url.com

    Optional:
        IQ_OAUTH_AUTHORIZATION_SERVERS=https://your-project.supabase.co/auth/v1
        IQ_REQUIRED_SCOPES=read,write  # Comma-separated scopes

    Returns:
        RemoteAuthProvider instance configured for Supabase DCR

    Raises:
        RuntimeError: If configuration is invalid or providers unavailable
    """
    from .context import ctx
    import os

    logger.info("🔐 Configuring OAuth 2.1 with Dynamic Client Registration (DCR)")

    # Verify context is ready
    if not ctx.is_initialized:
        error = "❌ Server context not initialized"
        logger.error(error)
        raise RuntimeError(error)

    # Verify Supabase auth is enabled
    if not ctx.settings.supabase_auth_enabled:
        error = "❌ IQ_ENABLE_SUPABASE_AUTH must be true"
        logger.error(error)
        raise RuntimeError(error)

    try:
        from fastmcp.server.auth import RemoteAuthProvider
        from fastmcp.server.auth.providers.jwt import JWTVerifier
        from pydantic import AnyHttpUrl

        supabase_auth = ctx.settings.supabase_auth
        base_url = os.getenv("IQ_BASE_URL")

        # Validate required configuration
        if not base_url:
            raise ValueError("IQ_BASE_URL is required (e.g., https://your-server.com)")

        if not supabase_auth.project_url:
            raise ValueError("IQ_SUPABASE_AUTH_PROJECT_URL is required")

        if supabase_auth.algorithm not in ["ES256", "RS256"]:
            raise ValueError("IQ_SUPABASE_AUTH_ALGORITHM must be ES256 or RS256 (asymmetric only)")

        project_url = supabase_auth.project_url.rstrip("/")

        # Configuration summary
        logger.info("✅ Configuration valid:")
        logger.info(f"   Project URL: {project_url}")
        logger.info(f"   Base URL: {base_url}")
        logger.info(f"   Algorithm: {supabase_auth.algorithm}")
        logger.info(f"   Auth servers: {supabase_auth.authorization_servers}")

        # JWT Verifier - validates tokens from Supabase
        token_verifier = JWTVerifier(
            jwks_uri=f"{project_url}/auth/v1/.well-known/jwks.json",
            issuer=f"{project_url}/auth/v1",
            audience=base_url,
            required_scopes=supabase_auth.required_scopes or None,
        )

        # RemoteAuthProvider - provides DCR and OAuth 2.1 metadata
        remote_auth = RemoteAuthProvider(
            token_verifier=token_verifier,
            authorization_servers=[
                AnyHttpUrl(server) for server in supabase_auth.authorization_servers
            ],
            base_url=base_url,
        )

        logger.info("🔐 OAuth 2.1 DCR configured successfully")
        logger.info(f"   🌐 Discovery: {base_url}/.well-known/oauth-protected-resource")
        logger.info("   ✨ MCP clients can auto-discover and register via DCR")
        logger.info("   🔑 Users authenticate directly with Supabase - no server secrets needed")

        return remote_auth

    except ImportError as e:
        error = f"❌ Required packages not available: {e}"
        logger.error(error)
        raise RuntimeError("RemoteAuthProvider requires FastMCP >= 2.13.0 and pydantic")

    except Exception as e:
        error = f"❌ Failed to configure OAuth 2.1 DCR: {e}"
        logger.error(error)
        raise RuntimeError(error)


# Simpler name for server.py to import
__all__ = ["get_auth_provider"]