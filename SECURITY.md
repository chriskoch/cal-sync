# Security Best Practices

## Secrets Management

### Never Commit Secrets
- `.env` file is in `.gitignore` - never remove it
- Never commit API keys, passwords, or encryption keys to git
- Use `.env.example` as a template (safe to commit)

### Setting Up Secrets

1. **Copy the template:**
   ```bash
   cp .env.example .env
   ```

2. **Generate secure keys:**
   ```bash
   # Generate JWT secret
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   
   # Generate encryption key
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

3. **Set strong database password:**
   - Use a random password generator
   - Minimum 16 characters recommended
   - Include uppercase, lowercase, numbers, and special characters

4. **Configure OAuth:**
   - Get credentials from [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   - Create OAuth 2.0 Client ID (Web Application)
   - Add authorized redirect URIs

### Production Deployment

For production, use a secrets manager:
- **AWS:** AWS Secrets Manager or Parameter Store
- **Google Cloud:** Secret Manager
- **Azure:** Key Vault
- **Self-hosted:** HashiCorp Vault

Never use `.env` files in production.

### Debug Mode

**CRITICAL: Always disable debug mode in production**

Debug mode (`DEBUG=true`) exposes sensitive information:
- Detailed error stack traces
- SQL queries with data
- Internal file paths
- Dependency versions

Production deployment checklist:
1. Set `ENVIRONMENT=production` in environment variables
2. Set `DEBUG=false` (or omit - defaults to False)
3. The application will enforce `DEBUG=false` in production automatically
4. Never override this in production

Development vs Production:
```bash
# Development (local only)
ENVIRONMENT=development
DEBUG=true

# Production (REQUIRED)
ENVIRONMENT=production
DEBUG=false  # or omit this line
```

## Authentication

**Google OAuth Only**: This application uses Google OAuth exclusively for authentication. No passwords are stored or required.

## Rate Limiting

**⚠️ NOT CURRENTLY IMPLEMENTED** - Rate limiting should be added to prevent abuse:
- Recommended: OAuth registration endpoint (10 per hour per IP)
- Recommended: OAuth connection endpoints (20 per hour per IP)
- Recommended: API endpoints (100 per minute per IP)
- Consider using: slowapi or fastapi-limiter libraries

## HTTPS

**Production deployments MUST use HTTPS:**
- Use a reverse proxy (nginx, Caddy, Traefik)
- Obtain SSL certificates (Let's Encrypt recommended)
- Enable HSTS headers
- Redirect all HTTP traffic to HTTPS

## Token Security

- JWT tokens expire after 30 minutes (configured via JWT_EXPIRATION_MINUTES)
- **⚠️ Access tokens currently stored in localStorage (vulnerable to XSS attacks)**
  - For production, consider migrating to HTTP-only cookies with CSRF protection
  - localStorage is convenient but less secure than HttpOnly cookies
- Google OAuth tokens encrypted in database with Fernet before storage
- OAuth refresh tokens automatically managed by Google OAuth library
- **⚠️ CSRF protection NOT currently implemented**
  - Required if migrating to cookie-based authentication

## Database Security

- Use strong passwords
- Limit database user permissions (no superuser for app)
- Enable SSL/TLS for database connections in production
- Regular backups with encryption

## Monitoring

Log and monitor for:
- Failed login attempts
- Rate limit violations
- OAuth failures
- Sync errors
- Unexpected API access patterns

## Incident Response

If secrets are compromised:
1. Immediately revoke all affected credentials
2. Generate new secrets
3. Force logout all users
4. Audit logs for unauthorized access
5. Notify affected users if data was accessed

## Security Audits

- Run `pip-audit` regularly for dependency vulnerabilities
- Update dependencies monthly
- Review access logs weekly
- Test authentication flows after updates

## Reporting Security Vulnerabilities

If you discover a security vulnerability:

1. **DO NOT** open a public GitHub issue
2. Email: koch.chris@gmail.com
3. Include:
   - Vulnerability description
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours with a timeline for a fix.

## Known Security Limitations

This is a development/personal project with the following known security limitations:

1. **Token Storage**: JWT tokens stored in localStorage (vulnerable to XSS)
2. **Rate Limiting**: Not implemented (vulnerable to abuse)
3. **CSRF Protection**: Not implemented (would be needed for cookie-based auth)
4. **Account Recovery**: Not implemented (users must re-register if access is lost)
5. **Email Verification**: Not implemented (Google OAuth handles this)

For production deployment, consider addressing these limitations based on your security requirements.
