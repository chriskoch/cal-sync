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

## Password Requirements

Users must create passwords with:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter  
- At least one number
- At least one special character

## Rate Limiting

API endpoints are rate-limited to prevent brute force attacks:
- Login: 5 attempts per minute per IP
- Registration: 10 per hour per IP
- OAuth: 20 per hour per IP

## HTTPS

**Production deployments MUST use HTTPS:**
- Use a reverse proxy (nginx, Caddy, Traefik)
- Obtain SSL certificates (Let's Encrypt recommended)
- Enable HSTS headers
- Redirect all HTTP traffic to HTTPS

## Token Security

- JWT tokens expire after 30 minutes
- Access tokens stored in HTTP-only cookies (not localStorage)
- Refresh tokens encrypted in database with Fernet
- CSRF protection enabled for cookie-based auth

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

## Reporting Security Issues

To report security vulnerabilities:
- Email: security@yourcompany.com (update this)
- Do NOT create public GitHub issues for security bugs
- Allow 90 days for fix before public disclosure
