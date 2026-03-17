# SmartTriage Dashboard - Professional Security Features

## 🔒 Security Overview

SmartTriage Dashboard implements enterprise-grade security features following OWASP best practices and healthcare data protection standards.

---

## Security Features Implemented

### 1. **Security Headers** ✅

All HTTP responses include comprehensive security headers:

#### Content Security Policy (CSP)
- Prevents XSS attacks by controlling resource loading
- Restricts inline JavaScript execution
- Whitelists approved CDNs only

#### Frame Protection
- `X-Frame-Options: DENY` - Prevents clickjacking attacks
- `frame-ancestors 'none'` in CSP

#### MIME Type Protection
- `X-Content-Type-Options: nosniff` - Prevents MIME sniffing attacks

#### XSS Protection
- `X-XSS-Protection: 1; mode=block` - Legacy browser protection

#### HSTS (HTTP Strict Transport Security)
- Enforces HTTPS connections
- Enabled in production only
- 1-year max-age with subdomains

#### Referrer Policy
- `strict-origin-when-cross-origin` - Privacy-focused

---

### 2. **Input Sanitization** ✅

#### Email Validation
```python
# RFC-compliant email validation
email = InputSanitizer.sanitize_email(user_input)
```

#### HTML Sanitization
```python
# Prevents XSS via rich text fields
clean_html = InputSanitizer.sanitize_html(user_input)
```

#### String Sanitization
```python
# Removes control characters, null bytes
safe_string = InputSanitizer.sanitize_string(user_input, max_length=200)
```

#### Phone Number Sanitization
```python
# Keeps only valid phone characters
clean_phone = InputSanitizer.sanitize_phone(user_input)
```

---

### 3. **Authentication & Authorization** ✅

#### Password Policy
**Requirements**:
- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 digit
- At least 1 special character (!@#$%^&*()_+-=[]{}|;:,.<>?)
- Not in common weak passwords list

**Validation**:
```python
is_valid, message = PasswordPolicy.validate(password)
```

#### Role-Based Access Control (RBAC)
```python
@require_role('doctor', 'phc_doctor', 'phc_nurse')
def doctor_dashboard():
    # Only accessible by medical staff
    pass
```

**Roles**:
- `patient` - Basic patient access
- `doctor` - Medical professional
- `ddhs_admin` - District health administrator
- `phc_doctor` - Primary Health Center doctor
- `phc_nurse` - Primary Health Center nurse

#### Password Hashing
- Uses Werkzeug's `pbkdf2:sha256` (PBKDF2-HMAC-SHA256)
- Automatic salt generation
- Computationally expensive to prevent brute force

---

### 4. **Rate Limiting** ✅

Protects against brute force and DOS attacks:

| Endpoint | Limit | Purpose |
|----------|-------|---------|
| `/login` | 5 per minute | Prevent credential stuffing |
| `/signup` | 3 per hour | Prevent spam registration |
| `/triage` | 10 per minute | Prevent API abuse |
| Global | 200 per day | General protection |

**Rate limit headers** sent to clients:
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset`

---

### 5. **Audit Logging** ✅

All security-sensitive actions are logged:

#### Events Logged
- ✅ Login attempts (success/failure)
- ✅ Logout events
- ✅ Password changes
- ✅ Role escalations
- ✅ Data access (patient records)
- ✅ Configuration changes
- ✅ User creation/deletion

####  Audit Log Format
```
[2026-03-10 10:15:23] AUDIT | Request-ID: abc123 | User: user@example.com |
IP: 192.168.1.100 | Action: LOGIN_SUCCESS | Details: Role: doctor
```

#### Log Storage
- **File**: `logs/audit.log`
- **Rotation**: 10MB × 20 files (200MB total)
- **Encoding**: UTF-8
- **Retention**: Configure based on compliance requirements

---

### 6. **Request Tracking** ✅

Every request gets a unique ID for debugging and security:

#### Features
- UUID v4 for each request
- Timing measurement
- Full request lifecycle logging
- Response header: `X-Request-ID`

#### Example Log
```
Request completed - ID: 550e8400-e29b-41d4-a716-446655440000 |
Method: POST | Path: /login | Status: 200 | Duration: 0.235s
```

---

### 7. **SQL Injection Prevention** ✅

#### Parameterized Queries
All database queries use parameterized statements:
```python
# SECURE ✅
cursor.execute('SELECT * FROM users WHERE email = ?', (email,))

# INSECURE ❌ (never do this)
# cursor.execute(f'SELECT * FROM users WHERE email = "{email}"')
```

#### Database Connection Pooling
- Thread-safe connection management
- Automatic transaction isolation
- WAL mode for SQLite (prevents database locks)

---

### 8. **Session Security** ✅

#### Secure Cookies
```python
# Production settings
SESSION_COOKIE_SECURE = True      # HTTPS only
SESSION_COOKIE_HTTPONLY = True    # No JavaScript access
SESSION_COOKIE_SAMESITE = 'Lax'   # CSRF protection
```

#### Session Timeout
- Default: 1 hour (3600 seconds)
- Configurable via `PERMANENT_SESSION_LIFETIME`

#### Secret Key
- Cryptographically secure random key
- Must be changed in production
- Used for signing session cookies

---

## Security Testing

### Automated Security Tests

#### 1. SQL Injection Test
```bash
# Test parameterized queries
python -c "
from app import app
with app.test_client() as client:
    # Try SQL injection
    response = client.post('/login', data={
        'email': \"' OR '1'='1\",
        'password': 'test',
        'role': 'patient'
    })
    assert response.status_code != 200, 'SQL injection vulnerability!'
    print('✅ SQL injection test passed')
"
```

#### 2. XSS Test
```bash
# Test HTML sanitization
python -c "
from utils.security import InputSanitizer
xss_payload = '<script>alert(\"XSS\")</script>'
result = InputSanitizer.sanitize_html(xss_payload)
assert '<script>' not in result, 'XSS vulnerability!'
print('✅ XSS sanitization test passed')
"
```

#### 3. CSRF Test
```bash
# Check security headers
curl -I https://your-domain.com/ | grep -i "x-frame-options"
curl -I https://your-domain.com/ | grep -i "content-security-policy"
```

#### 4. Rate Limiting Test
```bash
# Test login rate limit
for i in {1..10}; do
    curl -X POST https://your-domain.com/login \
        -d "email=test@example.com&password=wrong&role=patient"
    sleep 5
done
# Should receive 429 after 5 attempts within a minute
```

---

## Compliance & Standards

### OWASP Top 10 Coverage

| Risk | Mitigation | Status |
|------|------------|--------|
| **A01: Broken Access Control** | RBAC, role decorators | ✅ |
| **A02: Cryptographic Failures** | Strong password hashing, HTTPS | ✅ |
| **A03: Injection** | Parameterized queries, input sanitization | ✅ |
| **A04: Insecure Design** | Security by design, defense in depth | ✅ |
| **A05: Security Misconfiguration** | Secure defaults, configuration validation | ✅ |
| **A06: Vulnerable Components** | Regular updates, dependency scanning | ⚠️ Manual |
| **A07: Authentication Failures** | Strong passwords, rate limiting, MFA ready | ✅ |
| **A08: Software & Data Integrity** | Hashing, audit logging | ✅ |
| **A09: Security Logging Failures** | Comprehensive audit logging | ✅ |
| **A10: Server-Side Request Forgery** | Input validation, URL sanitization | ✅ |

### Healthcare Compliance

#### HIPAA Considerations
While full HIPAA compliance requires additional infrastructure:
- ✅ **Audit trails** - All access logged
- ✅ **Access controls** - Role-based permissions
- ✅ **Encryption in transit** - HTTPS enforced
- ⚠️ **Encryption at rest** - Database encryption needed
- ⚠️ **Business Associate Agreements** - Required for vendors
- ⚠️ **PHI anonymization** - Consider for analytics

---

## Security Configuration

### Environment Variables

#### Production Security Settings
```bash
# .env
FLASK_ENV=production
FLASK_SECRET_KEY=<64-char-random-hex>

# Force HTTPS
SESSION_COOKIE_SECURE=true

# Security features
SECURITY_HEADERS_ENABLED=true
REQUEST_ID_ENABLED=true
AUDIT_LOGGING_ENABLED=true

# Rate limiting with Redis (persistent)
RATELIMIT_ENABLED=true
RATELIMIT_STORAGE_URL=redis://localhost:6379/0
```

#### Generating Secure Secret
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Security Monitoring

### What to Monitor

#### 1. Failed Login Attempts
```bash
# Check audit log for patterns
grep "LOGIN_FAILED" logs/audit.log | tail -n 50
```

#### 2. Rate Limit Hits
```bash
# Monitor 429 errors
grep "429" logs/smarttriage.log | wc -l
```

#### 3. Suspicious Activity
```bash
# Check for unusual access patterns
grep "403\|401" logs/smarttriage.log | tail -n 20
```

#### 4. Database Errors
```bash
# SQL injection attempts often cause syntax errors
grep "SQL" logs/errors.log
```

### Automated Alerts

#### Setup with Prometheus AlertManager
```yaml
# alert.rules
groups:
  - name: security
    rules:
      - alert: HighFailedLoginRate
        expr: rate(smarttriage_failed_logins[5m]) > 10
        annotations:
          summary: "High rate of failed login attempts"

      - alert: DatabaseConnectionFailure
        expr: smarttriage_health_status{component="database"} == 0
        annotations:
          summary: "Database health check failing"
```

---

## Incident Response

### Security Incident Checklist

1. **Detection**
   - [ ] Alert received or issue reported
   - [ ] Initial triage performed
   - [ ] Severity assessed

2. **Containment**
   - [ ] Affected systems identified
   - [ ] Potential attacker IP blocked
   - [ ] Compromised accounts disabled

3. **Investigation**
   - [ ] Audit logs reviewed
   - [ ] Attack vector identified
   - [ ] Scope of breach determined

4. **Remediation**
   - [ ] Vulnerability patched
   - [ ] Systems restored from backup if needed
   - [ ] Monitoring enhanced

5. **Recovery**
   - [ ] Services restored
   - [ ] Users notified (if required)
   - [ ] Passwords reset (if compromised)

6. **Post-Incident**
   - [ ] Incident report documented
   - [ ] Root cause analysis completed
   - [ ] Preventive measures implemented

---

## Penetration Testing

### Recommended Tools

#### Web Application Scanners
- **OWASP ZAP** - Free, open-source
- **Burp Suite** - Professional scanner
- **Nikto** - Web server scanner

#### Example ZAP Scan
```bash
# Install ZAP
docker pull owasp/zap2docker-stable

# Run baseline scan
docker run -t owasp/zap2docker-stable zap-baseline.py \
    -t https://your-domain.com \
    -r zap_report.html
```

---

## Security Updates

### Keeping Dependencies Secure

```bash
# Check for vulnerabilities
pip install safety
safety check -r requirements.txt

# Check outdated packages
pip list --outdated

# Update packages
pip install --upgrade -r requirements.txt
```

### Scheduled Tasks
```bash
# Add to crontab
0 2 * * 0 /opt/smarttriage/venv/bin/safety check -r /opt/smarttriage/requirements.txt
```

---

## Security Contacts

### Reporting Security Issues

**DO NOT** report security vulnerabilities via public GitHub issues.

**Email**: security@your-organization.com
**PGP Key**: [Your PGP key fingerprint]
**Response Time**: Within 48 hours

### Security Team
- Security Lead: [Name]
- Application Security: [Name]
- Infrastructure Security: [Name]

---

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

---

**Version**: 2.0.0-professional
**Last Security Audit**: March 10, 2026
**Next Audit Due**: June 10, 2026
**Security Status**: ✅ Production-Ready
