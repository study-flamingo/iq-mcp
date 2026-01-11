"""
Authentication configuration for IQ-MCP server.

Provides flexible authentication for HTTP transport deployments.
For single-user deployments, uses StaticTokenVerifier with API keys.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import httpx
from starlette.responses import JSONResponse
from starlette.routing import Route

from .iq_logging import logger

if TYPE_CHECKING:
    from fastmcp.server.auth import AuthProvider, AccessToken


class SupabaseRemoteAuthProvider:
    """
    Extended RemoteAuthProvider that forwards Supabase's authorization server metadata.

    This adds the /.well-known/oauth-authorization-server endpoint that Claude Desktop
    needs to discover OAuth endpoints (authorize, token, register).
    """

    def __init__(self, base_provider, project_url: str):
        self._base = base_provider
        self._project_url = project_url.rstrip("/")
        self._auth_server_url = f"{self._project_url}/auth/v1"

        # Proxy attributes from base provider
        self.base_url = base_provider.base_url
        self.required_scopes = getattr(base_provider, 'required_scopes', [])

    async def verify_token(self, token: str):
        """Delegate to base provider."""
        return await self._base.verify_token(token)

    def get_routes(self, mcp_path: str | None = None) -> list:
        """Get routes including authorization server metadata forwarding."""
        # Get base routes
        routes = list(self._base.get_routes(mcp_path) if hasattr(self._base, 'get_routes') else [])

        # Add authorization server metadata forwarding
        async def authorization_server_metadata(request):
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(
                        f"{self._auth_server_url}/.well-known/oauth-authorization-server",
                        timeout=10.0
                    )
                    response.raise_for_status()
                    return JSONResponse(response.json())
                except Exception as e:
                    logger.error(f"Failed to fetch authorization server metadata: {e}")
                    return JSONResponse(
                        {"error": "Failed to fetch authorization server metadata"},
                        status_code=502
                    )

        routes.append(
            Route("/.well-known/oauth-authorization-server", authorization_server_metadata)
        )

        return routes

    def get_middleware(self) -> list:
        """Delegate to base provider."""
        if hasattr(self._base, 'get_middleware'):
            return self._base.get_middleware()
        return []

    def _get_resource_url(self, path: str | None = None) -> str:
        """Delegate to base provider."""
        if hasattr(self._base, '_get_resource_url'):
            return self._base._get_resource_url(path)
        if path:
            return f"{self.base_url.rstrip('/')}{path}"
        return self.base_url


class ChainedAuthProvider:
    """
    Composite auth provider that tries multiple verification methods in sequence.

    This allows supporting multiple authentication methods simultaneously (e.g., API keys
    and OAuth) without breaking backward compatibility.

    Verification order:
    1. Try each provider in sequence
    2. Return first successful verification
    3. Return None if all providers fail

    Route aggregation:
    - Combines routes from all providers (OAuth metadata, etc.)
    - Deduplicates routes by path
    """

    def __init__(self, providers: list["AuthProvider"]):
        if not providers:
            raise ValueError("At least one provider required")
        self.providers = providers
        self.base_url = providers[0].base_url
        self.required_scopes = providers[0].required_scopes

    async def verify_token(self, token: str) -> "AccessToken | None":
        """Try each provider in sequence until one succeeds."""
        for i, provider in enumerate(self.providers):
            try:
                result = await provider.verify_token(token)
                if result is not None:
                    logger.debug(f"Token verified by provider {i}: {type(provider).__name__}")
                    return result
            except Exception as e:
                logger.debug(f"Provider {i} ({type(provider).__name__}) failed: {e}")
                continue

        logger.warning("Token verification failed for all providers")
        return None

    def get_routes(self, mcp_path: str | None = None) -> list:
        """Aggregate routes from all providers, deduplicating by path."""
        routes = []
        seen_paths = set()

        for provider in self.providers:
            if hasattr(provider, "get_routes"):
                for route in provider.get_routes(mcp_path):
                    if route.path not in seen_paths:
                        routes.append(route)
                        seen_paths.add(route.path)

        return routes

    def get_middleware(self) -> list:
        """Use middleware from first provider (should be same for all)."""
        if hasattr(self.providers[0], "get_middleware"):
            return self.providers[0].get_middleware()
        return []

    def _get_resource_url(self, path: str | None = None) -> str:
        """Get OAuth resource URL from first provider that supports it."""
        for provider in self.providers:
            if hasattr(provider, "_get_resource_url"):
                return provider._get_resource_url(path)
        # Fallback to base_url + path
        if path:
            return f"{self.base_url.rstrip('/')}{path}"
        return self.base_url


def get_auth_provider(require_auth: bool = False) -> "AuthProvider | None":
    """
    Create auth provider based on environment configuration.

    Supports multiple authentication methods simultaneously:
    - Static API keys (IQ_API_KEY) via StaticTokenVerifier
    - Supabase OAuth (IQ_ENABLE_SUPABASE_AUTH) via SupabaseProvider

    When multiple methods enabled, creates ChainedAuthProvider that
    tries each method in sequence (API key first, then OAuth).

    Args:
        require_auth: If True, raises an error when no auth is configured.
                     Use this for production deployments to prevent accidental
                     deployment without authentication.

    Returns:
        AuthProvider instance (may be chained), or None if no auth configured.

    Raises:
        ValueError: If require_auth=True and no auth is configured.

    Environment Variables:
        IQ_API_KEY: Static API key for authentication
        IQ_CLIENT_ID: Client identifier (default: "iq-mcp-user")
        IQ_ENABLE_SUPABASE_AUTH: Enable Supabase OAuth (true/false)
        IQ_SUPABASE_AUTH_PROJECT_URL: Supabase project URL
        IQ_SUPABASE_AUTH_ALGORITHM: JWT algorithm (ES256/RS256/HS256)
        IQ_BASE_URL: Public base URL (required for OAuth)
        IQ_REQUIRE_AUTH: Set to "true" to enforce authentication
    """
    from .context import ctx

    require_auth = require_auth or os.getenv("IQ_REQUIRE_AUTH", "false").lower() == "true"
    providers: list["AuthProvider"] = []

    # 1. Static API Key Provider
    api_key = os.getenv("IQ_API_KEY")
    if api_key:
        try:
            from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

            client_id = os.getenv("IQ_CLIENT_ID", "iq-mcp-user")
            static_provider = StaticTokenVerifier(
                tokens={
                    api_key: {
                        "client_id": client_id,
                        "scopes": ["read", "write", "admin"],
                    }
                },
                required_scopes=["read"],
            )
            providers.append(static_provider)
            logger.info(f"🔑 Static API key auth enabled for: {client_id}")
        except ImportError:
            logger.error("❌ StaticTokenVerifier not available. Upgrade fastmcp >=2.13.0")

    # 2. Supabase OAuth Provider (using RemoteAuthProvider for full OAuth flow)
    if ctx.is_initialized and ctx.settings.supabase_auth_enabled:
        try:
            from fastmcp.server.auth import RemoteAuthProvider
            from fastmcp.server.auth.providers.jwt import JWTVerifier
            from pydantic import AnyHttpUrl

            supabase_auth = ctx.settings.supabase_auth
            base_url = os.getenv("IQ_BASE_URL")

            if not base_url:
                logger.error("❌ IQ_BASE_URL required for OAuth. Skipping Supabase auth.")
            else:
                # Use RemoteAuthProvider for full OAuth flow with DCR support
                # This tells clients where to authenticate (Supabase) and validates their tokens
                project_url = supabase_auth.project_url.rstrip("/")

                # JWTVerifier validates tokens using Supabase's JWKS
                token_verifier = JWTVerifier(
                    jwks_uri=f"{project_url}/auth/v1/.well-known/jwks.json",
                    issuer=f"{project_url}/auth/v1",
                    audience="authenticated",  # Supabase default audience
                )

                # RemoteAuthProvider points clients to Supabase for OAuth
                base_remote_provider = RemoteAuthProvider(
                    token_verifier=token_verifier,
                    authorization_servers=[AnyHttpUrl(f"{project_url}/auth/v1")],
                    base_url=base_url,
                )

                # Wrap with our extended provider that forwards auth server metadata
                supabase_provider = SupabaseRemoteAuthProvider(
                    base_provider=base_remote_provider,
                    project_url=project_url,
                )
                providers.append(supabase_provider)
                logger.info(f"🔐 Supabase OAuth enabled via SupabaseRemoteAuthProvider (project: {project_url})")
        except ImportError as e:
            logger.error(f"❌ RemoteAuthProvider not available. Upgrade fastmcp >=2.13.0: {e}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase auth: {e}")

    # 3. Return appropriate provider(s)
    if not providers:
        if require_auth:
            raise ValueError(
                "❌ SECURITY: No auth configured but required! "
                "Set IQ_API_KEY or enable Supabase auth, or set IQ_REQUIRE_AUTH=false."
            )
        logger.warning("⚠️  No auth configured - server will run WITHOUT authentication!")
        return None

    if len(providers) == 1:
        logger.info(f"✅ Authentication: {type(providers[0]).__name__}")
        return providers[0]
    else:
        logger.info(f"✅ Authentication: {len(providers)} methods (chained)")
        return ChainedAuthProvider(providers)


__all__ = ["get_auth_provider"]

