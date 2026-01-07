"""
ASGI middleware for IQ-MCP server.
"""

from urllib.parse import parse_qs

from .iq_logging import logger


class TokenQueryParamMiddleware:
    """
    ASGI middleware that converts ?token= query param to Authorization header.

    This allows clients to authenticate via URL query parameter instead of
    (or in addition to) the Authorization header. Useful for browser access
    and quick testing.

    The token is extracted from the query string and added as a Bearer token
    in the Authorization header if no Authorization header is already present.

    Usage:
        app = TokenQueryParamMiddleware(app)

    Then clients can authenticate with:
        GET /iq?token=your-api-key

    Which is converted to:
        Authorization: Bearer your-api-key
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Parse query string
            query_string = scope.get("query_string", b"").decode()
            query_params = parse_qs(query_string)

            # Check if token is in query params
            if "token" in query_params:
                token = query_params["token"][0]

                # Check if Authorization header already exists
                headers = dict(scope.get("headers", []))
                if b"authorization" not in headers:
                    # Add Authorization header
                    new_headers = list(scope["headers"]) + [
                        (b"authorization", f"Bearer {token}".encode())
                    ]
                    scope = dict(scope)
                    scope["headers"] = new_headers
                    logger.debug("🔗 Converted ?token= to Authorization header")

        await self.app(scope, receive, send)


__all__ = ["TokenQueryParamMiddleware"]
