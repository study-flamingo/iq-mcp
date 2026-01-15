# FastMCP Authentication Documentation

> Source: https://gofastmcp.com/servers/auth/authentication

## Overview

FastMCP provides flexible authentication patterns designed for the Model Context Protocol (MCP), addressing unique challenges where automated systems must authenticate without human intervention. The framework supports three responsibility levels: token validation, external identity providers, and complete OAuth implementation.

## Core Authentication Patterns

### Token Validation (TokenVerifier)
This approach delegates token creation to external systems while your server validates them. It's ideal for organizations with existing JWT infrastructure, API gateways, or enterprise SSO systems. The server receives signed tokens and makes access decisions based on embedded claims.

**Example configuration:**
```python
from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import JWTVerifier

auth = JWTVerifier(
    jwks_uri="https://your-auth-system.com/.well-known/jwks.json",
    issuer="https://your-auth-system.com",
    audience="your-mcp-server"
)
mcp = FastMCP(name="Protected Server", auth=auth)
```

### External Identity Providers (RemoteAuthProvider)
For identity providers supporting Dynamic Client Registration (DCR) like Descope and WorkOS AuthKit, this pattern enables fully automated authentication without manual client configuration.

**Example with WorkOS AuthKit:**
```python
from fastmcp import FastMCP
from fastmcp.server.auth.providers.workos import AuthKitProvider

auth = AuthKitProvider(
    authkit_domain="https://your-project.authkit.app",
    base_url="https://your-fastmcp-server.com"
)
mcp = FastMCP(name="Enterprise Server", auth=auth)
```

### OAuth Proxy (OAuthProxy)
Bridges traditional OAuth providers (GitHub, Google, Azure, AWS) that require manual app registration. The proxy presents a DCR-compliant interface to MCP clients while using pre-registered credentials with the upstream provider.

**GitHub OAuth example:**
```python
from fastmcp import FastMCP
from fastmcp.server.auth.providers.github import GitHubProvider

auth = GitHubProvider(
    client_id="Ov23li...",
    client_secret="abc123...",
    base_url="https://your-server.com"
)
mcp = FastMCP(name="GitHub-Protected Server", auth=auth)
```

### Full OAuth Implementation (OAuthProvider)
Complete OAuth 2.0 server implementation handling the entire authentication lifecycle. Recommended only when external providers cannot meet specific requirements and you have security expertise.

## Environment Configuration

FastMCP supports environment-based configuration for deployment flexibility:

```bash
# GitHub OAuth
export FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.github.GitHubProvider
export FASTMCP_SERVER_AUTH_GITHUB_CLIENT_ID="Ov23li..."
export FASTMCP_SERVER_AUTH_GITHUB_CLIENT_SECRET="github_pat_..."

# JWT Token Verification
export FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.jwt.JWTVerifier
export FASTMCP_SERVER_AUTH_JWT_JWKS_URI="https://auth.example.com/jwks"
export FASTMCP_SERVER_AUTH_JWT_ISSUER="https://auth.example.com"
export FASTMCP_SERVER_AUTH_JWT_AUDIENCE="mcp-server"
```

With environment variables set, authentication configures automatically:
```python
from fastmcp import FastMCP
mcp = FastMCP(name="My Server")
```

## Implementation Selection Guide

**Choose OAuth Proxy** for traditional OAuth providers requiring manual app registration through developer consoles.

**Choose RemoteAuthProvider** for modern platforms supporting DCR, enabling fully automated client registration and the best user experience.

**Choose Token Validation** when your organization already issues structured tokens through existing infrastructure.

**Avoid Full OAuth Implementation** unless air-gapped environments, specialized compliance, or unique organizational constraints prevent using external providers.

## Key Considerations

FastMCP's architecture supports migration between approaches as requirements evolve. Start with token validation for existing systems, migrate to external providers as scaling requirements grow, or implement custom solutions when standard patterns become insufficient.

Authentication applies only to HTTP-based transports (`http` and `sse`). The STDIO transport inherits security from local execution environments.
