# Supabase MCP Authentication Guide

> Source: https://supabase.com/docs/guides/auth/oauth-server/mcp-authentication

## Core Setup

MCP servers authenticate through Supabase Auth's OAuth 2.1 implementation. Configure your server to use:

```
https://<project-ref>.supabase.co/auth/v1
```

Replace `<project-ref>` with your actual project reference ID from the Supabase dashboard.

## Discovery Endpoint

MCP clients will automatically discover your OAuth configuration from the well-known endpoint:

```
https://<project-ref>.supabase.co/.well-known/oauth-authorization-server/auth/v1
```

## Redirect URI Requirements

**CRITICAL:** When registering OAuth clients, redirect URIs must be **valid, complete URLs** including:

- **Protocol** (http/https)
- **Full domain**
- **Path specification**
- **Port number** (if non-standard)

**Examples of valid redirect URIs:**
- `https://api.example.com/oauth/callback`
- `https://api.example.com/mcp/oauth/callback` (with path prefix)
- `http://localhost:8000/oauth/callback` (development)

**Incomplete redirect URIs will cause token exchange failures.**

## OAuth Flow

1. User redirected to authorization endpoint
2. Supabase Auth validates request and displays authorization UI
3. User authenticates and approves access
4. Authorization code issued
5. Application exchanges code for access and refresh tokens (must use **exact matching redirect URI**)
6. Access token used for authenticated API requests

## Required Parameters

| Parameter | Description |
|-----------|-------------|
| `response_type` | Must be `code` for authorization code flow |
| `client_id` | The client ID from registration |
| `redirect_uri` | Must **exactly match** a registered redirect URI |
| `code_challenge` | The generated code challenge |
| `code_challenge_method` | Must be `S256` (SHA-256) |

## Key Security Consideration

Always require explicit user approval for MCP clients before granting access, displaying client details and requested scopes clearly.

## Troubleshooting

**Token exchange failures:** Verify redirect URIs are valid, complete URLs (protocol, domain, path, and port). Mismatch between registered redirect URI and the one used in authorization request is a common issue.
