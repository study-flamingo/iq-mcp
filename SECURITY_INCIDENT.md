# 🚨 Security Incident Notice - API Key Exposure

## Date: 2026-01-09

## Summary

Production API key was found hardcoded in `AGENTS.md` (committed to git).

## Affected Credentials

- **IQ_API_KEY**: `iqmcp-sk-qwA9sdZrWdunSPpvUBu9IYju9hbGXRcDOaSRQ0xT7MU` (COMPROMISED)
- **Location**: `AGENTS.md` lines 9 and 88
- **Exposure**: Git history (committed)

## Immediate Actions Required

### 1. Rotate Production API Key ⚠️ URGENT

```bash
# Generate new key
NEW_KEY="iqmcp-sk-$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)"

# Update on production VM
ssh iq-mcp-vm
cd /opt/iq-mcp
nano .env  # Update IQ_API_KEY with new key
docker-compose restart

# Update GCP Secret Manager (if used)
# gcloud secrets versions add iq-mcp-api-key --data-file=-
# (paste new key)
```

### 2. Update All Clients

Update MCP client configurations with the new key:

- Cursor: `~/.cursor/mcp.json`
- Any other MCP clients
- CI/CD pipelines
- Development environments

### 3. Verify Old Key is Disabled

```bash
# Test with old key (should fail)
curl -H "Authorization: Bearer iqmcp-sk-qwA9sdZrWdunSPpvUBu9IYju9hbGXRcDOaSRQ0xT7MU" \
  https://mcp.casimir.ai/iq

# Should return 401 Unauthorized
```

### 4. Review Git History

```bash
# Check for other exposed secrets
git log -S "iqmcp-sk-" --all
git log -S "IQ_API_KEY" --all

# If found in public repo, consider:
# - Using git-filter-repo to remove from history
# - Force pushing (breaks forks - coordinate with team)
# - Making repo private if currently public
```

### 5. Review Access Logs

Check for unauthorized access using the compromised key:

```bash
# On production VM
sudo cat /var/log/nginx/access.log | grep -i "authorization"

# Check Docker logs
docker logs iq-mcp 2>&1 | grep -i "auth"
```

## Remediation Completed

The following security fixes have been implemented:

1. ✅ Removed hardcoded credentials from `AGENTS.md`
2. ✅ Created `.env.example` template with placeholders
3. ✅ Added `IQ_REQUIRE_AUTH` enforcement option
4. ✅ Created `security.py` module with validation utilities
5. ✅ Created comprehensive `docs/SECURITY.md` documentation
6. ⚠️ **Production key rotation - ACTION REQUIRED**

## Prevention Measures

To prevent future credential exposure:

1. **Never commit credentials** - Use `.env` files (gitignored)
2. **Use templates** - `.env.example` with placeholders only
3. **Pre-commit hooks** - Consider adding secret detection (e.g., `detect-secrets`)
4. **Code review** - Check for hardcoded credentials before merging
5. **Enforce auth** - Set `IQ_REQUIRE_AUTH=true` in production

## Post-Incident Actions

- [ ] Rotate production API key
- [ ] Update all clients
- [ ] Review access logs for suspicious activity
- [ ] Consider git history cleanup
- [ ] Add pre-commit hook for secret detection
- [ ] Update deployment documentation
- [ ] Schedule security audit (quarterly)

## References

- Security Guide: `docs/SECURITY.md`
- Key Rotation: `docs/SECURITY.md#key-rotation`
- Environment Template: `.env.example`

---

**This file should be deleted after incident remediation is complete.**
