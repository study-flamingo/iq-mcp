# Security Guide

This document covers security best practices for deploying and operating IQ-MCP.

## Table of Contents

1. [Quick Security Checklist](#quick-security-checklist)
2. [Authentication](#authentication)
3. [Credential Management](#credential-management)
4. [Production Deployment](#production-deployment)
5. [Network Security](#network-security)
6. [Data Protection](#data-protection)
7. [Security Monitoring](#security-monitoring)
8. [Incident Response](#incident-response)

---

## Quick Security Checklist

Before deploying to production, verify:

- [ ] `IQ_API_KEY` is set to a strong, randomly generated key
- [ ] `IQ_REQUIRE_AUTH=true` is set for production deployments
- [ ] `.env` file is in `.gitignore` and never committed
- [ ] No hardcoded credentials in code or documentation
- [ ] HTTPS/TLS is configured (nginx handles SSL termination)
- [ ] Supabase keys use service role key (not anon key) if applicable
- [ ] `IQ_DEBUG=false` in production
- [ ] Regular backups are configured
- [ ] Monitoring and alerting is set up

---

## Authentication

### API Key Generation

Generate a secure API key using:

```bash
# Generate a 32-byte random key (recommended)
openssl rand -base64 32

# Format: iqmcp-sk-<random-string>
# Example: iqmcp-sk-Abc123XyzRandomString789
```

### Enforcing Authentication

For production deployments, set `IQ_REQUIRE_AUTH=true` to prevent accidental deployment without authentication:

```bash
# .env
IQ_REQUIRE_AUTH=true
IQ_API_KEY=iqmcp-sk-your-secure-key-here
```

If authentication is required but `IQ_API_KEY` is not set, the server will **fail to start** with a clear error message.

### Client Configuration

Clients authenticate via the `Authorization` header:

```json
{
  "mcpServers": {
    "iq-mcp": {
      "type": "http",
      "url": "https://mcp.casimir.ai/iq",
      "headers": {
        "Authorization": "Bearer iqmcp-sk-your-secure-key-here"
      }
    }
  }
}
```

**Never commit client configurations with real API keys to version control!**

### URL Query Parameter Auth (Optional)

For web UI access, you can enable URL-based auth:

```bash
# .env
IQ_URL_AUTH=true
```

Then access the UI with:
```
https://mcp.casimir.ai/iq?token=iqmcp-sk-your-key
```

**Warning:** URL-based auth is less secure than header-based auth. Only enable if needed for web UI access.

---

## Credential Management

### What to Protect

These credentials must NEVER be committed to version control:

1. **IQ_API_KEY** - Service authentication key
2. **IQ_SUPABASE_KEY** - Supabase service role key
3. **IQ_SUPABASE_URL** - May contain sensitive project info
4. **Production .env files** - Contains all secrets

### Safe Practices

✅ **DO:**
- Use `.env.example` with placeholder values
- Store real credentials in `.env` (gitignored)
- Use environment variables in CI/CD
- Rotate keys if exposed (see [Key Rotation](#key-rotation))
- Use secret management tools (Vault, AWS Secrets Manager, etc.)

❌ **DON'T:**
- Commit `.env` files
- Put credentials in code comments
- Include credentials in documentation
- Share credentials via unencrypted channels
- Use the same credentials across environments

### Key Rotation

If a key is compromised:

1. **Generate a new key immediately:**
   ```bash
   openssl rand -base64 32
   ```

2. **Update production environment:**
   ```bash
   # On the production VM:
   ssh iq-mcp-vm
   cd /opt/iq-mcp
   nano .env  # Update IQ_API_KEY
   docker-compose restart
   ```

3. **Update all clients** with the new key

4. **Verify old key no longer works:**
   ```bash
   curl -H "Authorization: Bearer OLD_KEY" https://mcp.casimir.ai/iq
   # Should return 401 Unauthorized
   ```

5. **Review git history** if key was committed:
   ```bash
   # Check if key exists in git history
   git log -S "iqmcp-sk-" --all

   # If found, consider using git-filter-repo or BFG Repo-Cleaner
   # to remove from history (requires force push)
   ```

---

## Production Deployment

### Minimum Security Requirements

1. **HTTPS/TLS Required**
   - nginx handles SSL termination
   - Let's Encrypt certificates (auto-renewed)
   - Force HTTPS redirects

2. **Authentication Enforced**
   ```bash
   IQ_REQUIRE_AUTH=true
   IQ_API_KEY=<strong-random-key>
   ```

3. **Debug Mode Disabled**
   ```bash
   IQ_DEBUG=false
   ```

4. **Firewall Configuration**
   - Only expose necessary ports (443 for HTTPS)
   - Block direct access to port 8000 (FastMCP)
   - Use security groups / firewall rules

### Docker Security

The IQ-MCP container runs with these security measures:

- Non-root user (if configured)
- Read-only root filesystem (where possible)
- Limited capabilities
- Resource limits (memory, CPU)

Review `docker-compose.yml` for current configuration.

### Environment Validation

Run security checks before deployment:

```python
from mcp_knowledge_graph.security import check_production_security

warnings = check_production_security()
if warnings:
    for warning in warnings:
        print(f"⚠️  {warning}")
```

---

## Network Security

### Nginx Configuration

The nginx reverse proxy provides:

- **SSL/TLS termination** - Strong cipher suites, modern protocols
- **Rate limiting** - Prevent abuse (configure per your needs)
- **Request size limits** - Prevent large payload attacks
- **Header security** - HSTS, X-Frame-Options, CSP (if configured)

Review `nginx/conf.d/mcp.conf` for current settings.

### Supabase Security

If using Supabase:

1. **Use service role key** - Never use anon key for server-side
2. **Enable Row Level Security (RLS)** - Restrict data access
3. **Limit API rate** - Set reasonable limits in Supabase dashboard
4. **Enable 2FA** - Protect Supabase account access
5. **Review access logs** - Monitor for suspicious activity

---

## Data Protection

### Memory File (`memory.jsonl`)

The local memory file may contain sensitive user data:

- Store on encrypted disk
- Restrict file permissions (600 or 640)
- Regular backups to secure location
- Consider encryption at rest

```bash
# Set restrictive permissions
chmod 600 /data/memory.jsonl
```

### Supabase Data

- Enable encryption at rest (default in Supabase)
- Regular backups (configure in Supabase)
- Row Level Security (RLS) policies
- Audit logging enabled

### Personal Data (GDPR/CCPA)

If storing personal data:

1. Document what data is collected
2. Provide data export functionality
3. Implement data deletion requests
4. Maintain data processing records
5. Consider data residency requirements

---

## Security Monitoring

### What to Monitor

1. **Authentication failures** - Multiple failed auth attempts
2. **Unusual traffic patterns** - Spikes, geographic anomalies
3. **Error rates** - Sudden increases may indicate attacks
4. **Resource usage** - CPU/memory spikes could be DoS
5. **File system changes** - Unexpected modifications

### Logging

Enable structured logging:

```bash
# .env
IQ_DEBUG=false  # Production logging level
```

Review logs regularly:

```bash
# Container logs
docker logs iq-mcp

# Nginx access logs
tail -f /var/log/nginx/access.log

# Nginx error logs
tail -f /var/log/nginx/error.log
```

### Alerting

Set up alerts for:

- Service downtime
- High error rates (>5% of requests)
- Authentication failures (>10 in 5 minutes)
- Disk space low (<10% free)
- Certificate expiration (<30 days)

---

## Incident Response

### If Credentials are Compromised

1. **Immediately rotate the compromised credential**
2. **Review access logs** for unauthorized usage
3. **Update all clients** with new credentials
4. **Document the incident** (when, what, how discovered)
5. **Review security controls** to prevent recurrence

### If Service is Breached

1. **Isolate the system** (take offline if necessary)
2. **Preserve evidence** (logs, memory dumps, etc.)
3. **Identify entry point** and affected data
4. **Notify affected users** if personal data exposed
5. **Implement fixes** before restoring service
6. **Conduct post-mortem** and update procedures

### Emergency Contacts

Document:

- On-call engineer contact
- Security team contact
- Incident response procedures
- Escalation path

---

## Security Updates

### Keeping Dependencies Updated

Regularly update dependencies for security patches:

```bash
# Update Python dependencies
uv pip compile pyproject.toml --upgrade

# Rebuild Docker image
./deploy/push-image.sh

# Deploy updated image
./deploy/push-and-deploy.sh
```

### Security Advisories

Subscribe to security advisories for:

- FastMCP
- FastAPI
- Supabase Python client
- nginx
- Docker

### Vulnerability Scanning

Periodically scan for vulnerabilities:

```bash
# Python dependencies
pip-audit

# Docker image
docker scan us-central1-docker.pkg.dev/dted-ai-agent/iq-mcp/iq-mcp:latest
```

---

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Supabase Security](https://supabase.com/docs/guides/security)
- [Docker Security Best Practices](https://docs.docker.com/engine/security/)

---

## Security Contact

To report security vulnerabilities, please contact: [your-security-contact@example.com]

**Do not report security issues via public GitHub issues.**
