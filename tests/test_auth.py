"""Tests for authentication providers using RemoteAuthProvider."""

import sys
from pathlib import Path

import pytest
from unittest.mock import Mock, patch

sys.path.insert(0, str((Path(__file__).parents[1] / "src").resolve()))


def test_get_auth_provider_returns_none_when_disabled():
    """Auth provider returns None when Supabase auth is disabled."""
    with patch("mcp_knowledge_graph.context.ctx") as mock_ctx:
        mock_ctx.is_initialized = True
        mock_ctx.settings.supabase_auth_enabled = False

        from mcp_knowledge_graph.auth import get_auth_provider
        result = get_auth_provider(require_auth=False)

        assert result is None


def test_get_auth_provider_raises_when_required_but_disabled():
    """Auth provider raises ValueError when required but Supabase auth is disabled."""
    with patch("mcp_knowledge_graph.context.ctx") as mock_ctx:
        mock_ctx.is_initialized = True
        mock_ctx.settings.supabase_auth_enabled = False

        from mcp_knowledge_graph.auth import get_auth_provider

        with pytest.raises(ValueError, match="IQ_ENABLE_SUPABASE_AUTH must be true"):
            get_auth_provider(require_auth=True)


def test_get_auth_provider_raises_when_context_not_initialized():
    """Auth provider raises RuntimeError when context not initialized."""
    with patch("mcp_knowledge_graph.context.ctx") as mock_ctx:
        mock_ctx.is_initialized = False

        from mcp_knowledge_graph.auth import get_auth_provider

        with pytest.raises(RuntimeError, match="Context not initialized"):
            get_auth_provider()


def test_get_auth_provider_raises_when_base_url_missing():
    """Auth provider raises ValueError when IQ_BASE_URL is not set."""
    with patch("mcp_knowledge_graph.context.ctx") as mock_ctx, \
         patch.dict("os.environ", {}, clear=True):
        mock_ctx.is_initialized = True
        mock_ctx.settings.supabase_auth_enabled = True

        # Create mock supabase_auth
        mock_supabase_auth = Mock()
        mock_supabase_auth.project_url = "https://test.supabase.co"
        mock_supabase_auth.algorithm = "ES256"
        mock_supabase_auth.required_scopes = []
        mock_ctx.settings.supabase_auth = mock_supabase_auth

        from mcp_knowledge_graph.auth import get_auth_provider

        with pytest.raises(ValueError, match="IQ_BASE_URL is required"):
            get_auth_provider()


def test_get_auth_provider_creates_remote_auth_provider():
    """Auth provider creates RemoteAuthProvider with correct configuration."""
    with patch("mcp_knowledge_graph.context.ctx") as mock_ctx, \
         patch.dict("os.environ", {"IQ_BASE_URL": "https://test.railway.app"}, clear=False):
        mock_ctx.is_initialized = True
        mock_ctx.settings.supabase_auth_enabled = True

        # Create mock supabase_auth
        mock_supabase_auth = Mock()
        mock_supabase_auth.project_url = "https://test.supabase.co"
        mock_supabase_auth.algorithm = "ES256"
        mock_supabase_auth.required_scopes = []
        mock_ctx.settings.supabase_auth = mock_supabase_auth

        from mcp_knowledge_graph.auth import get_auth_provider
        result = get_auth_provider()

        # Verify RemoteAuthProvider was created
        assert result is not None
        # The result should be a RemoteAuthProvider instance
        assert hasattr(result, "verify_token")


def test_remote_auth_provider_import():
    """Verify RemoteAuthProvider can be imported from fastmcp."""
    from fastmcp.server.auth import RemoteAuthProvider
    from fastmcp.server.auth.providers.jwt import JWTVerifier

    assert RemoteAuthProvider is not None
    assert JWTVerifier is not None
