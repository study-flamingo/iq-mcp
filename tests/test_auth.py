"""Tests for authentication providers."""

import sys
from pathlib import Path

import pytest
from unittest.mock import Mock, AsyncMock

sys.path.insert(0, str((Path(__file__).parents[1] / "src").resolve()))

from mcp_knowledge_graph.auth import ChainedAuthProvider


@pytest.mark.asyncio
async def test_chained_auth_first_succeeds():
    """First provider succeeds, second not called."""
    # Mock access token
    mock_token = Mock()
    mock_token.client_id = "test"

    # First provider succeeds
    provider1 = Mock()
    provider1.verify_token = AsyncMock(return_value=mock_token)
    provider1.base_url = "http://test"
    provider1.required_scopes = ["read"]

    # Second provider (should not be called)
    provider2 = Mock()
    provider2.verify_token = AsyncMock(return_value=None)

    chained = ChainedAuthProvider([provider1, provider2])
    result = await chained.verify_token("test-token")

    assert result.client_id == "test"
    provider1.verify_token.assert_called_once()
    provider2.verify_token.assert_not_called()


@pytest.mark.asyncio
async def test_chained_auth_fallback():
    """First fails, second succeeds."""
    mock_token = Mock()
    mock_token.client_id = "oauth"

    provider1 = Mock()
    provider1.verify_token = AsyncMock(return_value=None)
    provider1.base_url = "http://test"
    provider1.required_scopes = ["read"]

    provider2 = Mock()
    provider2.verify_token = AsyncMock(return_value=mock_token)

    chained = ChainedAuthProvider([provider1, provider2])
    result = await chained.verify_token("oauth-token")

    assert result.client_id == "oauth"
    provider1.verify_token.assert_called_once()
    provider2.verify_token.assert_called_once()


@pytest.mark.asyncio
async def test_chained_auth_all_fail():
    """All providers fail."""
    provider1 = Mock()
    provider1.verify_token = AsyncMock(return_value=None)
    provider1.base_url = "http://test"
    provider1.required_scopes = ["read"]

    provider2 = Mock()
    provider2.verify_token = AsyncMock(return_value=None)

    chained = ChainedAuthProvider([provider1, provider2])
    result = await chained.verify_token("invalid")

    assert result is None
    provider1.verify_token.assert_called_once()
    provider2.verify_token.assert_called_once()


def test_chained_auth_requires_providers():
    """Empty provider list raises ValueError."""
    with pytest.raises(ValueError, match="At least one provider required"):
        ChainedAuthProvider([])


@pytest.mark.asyncio
async def test_chained_auth_exception_handling():
    """Provider exceptions are caught and next provider is tried."""
    mock_token = Mock()
    mock_token.client_id = "fallback"

    provider1 = Mock()
    provider1.verify_token = AsyncMock(side_effect=Exception("Provider 1 failed"))
    provider1.base_url = "http://test"
    provider1.required_scopes = ["read"]

    provider2 = Mock()
    provider2.verify_token = AsyncMock(return_value=mock_token)

    chained = ChainedAuthProvider([provider1, provider2])
    result = await chained.verify_token("test-token")

    assert result.client_id == "fallback"
    provider1.verify_token.assert_called_once()
    provider2.verify_token.assert_called_once()


def test_chained_auth_get_routes():
    """Routes are aggregated from all providers and deduplicated."""
    route1 = Mock()
    route1.path = "/auth"

    route2 = Mock()
    route2.path = "/token"

    route3_duplicate = Mock()
    route3_duplicate.path = "/auth"  # Duplicate of route1

    provider1 = Mock()
    provider1.get_routes = Mock(return_value=[route1, route2])
    provider1.base_url = "http://test"
    provider1.required_scopes = ["read"]

    provider2 = Mock()
    provider2.get_routes = Mock(return_value=[route3_duplicate])

    chained = ChainedAuthProvider([provider1, provider2])
    routes = chained.get_routes("/mcp")

    # Should have 2 routes (route1 and route2), not 3 (duplicate removed)
    assert len(routes) == 2
    assert route1 in routes
    assert route2 in routes


def test_chained_auth_get_middleware():
    """Middleware is taken from first provider."""
    middleware = [Mock()]

    provider1 = Mock()
    provider1.get_middleware = Mock(return_value=middleware)
    provider1.base_url = "http://test"
    provider1.required_scopes = ["read"]

    provider2 = Mock()
    provider2.get_middleware = Mock(return_value=[Mock()])

    chained = ChainedAuthProvider([provider1, provider2])
    result = chained.get_middleware()

    assert result == middleware
    provider1.get_middleware.assert_called_once()
    provider2.get_middleware.assert_not_called()
