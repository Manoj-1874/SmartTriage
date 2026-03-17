# SmartTriage Dashboard - Production Deployment Guide

## 🎯 Professional Deployment Checklist

### 1. Pre-Deployment Security Audit ✅

#### Environment Configuration
```bash
# Generate secure secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Set in .env
FLASK_ENV=production
FLASK_SECRET_KEY=<your-generated-secret-key>
SESSION_COOKIE_SECURE=true
```

#### Security Headers
✅ **Enabled by default**
- Content Security Policy (CSP)
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- X-XSS-Protection
- Strict-Transport-Security (HSTS)

#### Rate Limiting
✅ **Configured**
- Login: 5 attempts/minute
- Signup: 3 registrations/hour
- Triage: 10 requests/minute

#### Input Validation
✅ **Implemented**
- Email sanitization
- HTML sanitization (XSS prevention)
- SQL injection prevention (parameterized queries)
- Phone number validation

---

## 🚀 Deployment Options

### Option 1: Docker Deployment (Recommended)

#### Step 1: Create Dockerfile
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:5000/health/ping')"

# Run with Gunicorn
CMD ["gunicorn", "-w", "4", "--threads", "4", "-b", "0.0.0.0:5000", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
```

#### Step 2: Create docker-compose.yml
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://user:pass@db:5432/smarttriage
      - RATELIMIT_STORAGE_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health/ping"]
      interval: 30s
      timeout: 10s
      retries: 3
    volumes:
      - ./logs:/app/logs

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=smarttriage_user
      - POSTGRES_PASSWORD=secure_password_here
      - POSTGRES_DB=smarttriage
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - app
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

#### Step 3: Deploy
```bash
# Build and start
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f app

# Stop
docker-compose down
```

---

### Option 2: Traditional Server Deployment

#### System Requirements
- Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- Python 3.11+
- PostgreSQL 13+ (recommended) or SQLite
- Redis 6+ (for rate limiting)
- Nginx (reverse proxy)
- 2GB RAM minimum, 4GB recommended
- 10GB disk space

#### Step 1: Install Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip

# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Install Redis
sudo apt install -y redis-server

# Install Nginx
sudo apt install -y nginx

# Install supervisor for process management
sudo apt install -y supervisor
```

#### Step 2: Setup Application
```bash
# Create application user
sudo useradd -m -s /bin/bash smarttriage

# Clone/copy application
sudo mkdir -p /opt/smarttriage
sudo cp -r /path/to/SmartTriage_Dashboard /opt/smarttriage/
sudo chown -R smarttriage:smarttriage /opt/smarttriage

# Switch to app user
sudo su - smarttriage

# Create virtual environment
cd /opt/smarttriage
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn

# Setup environment
cp .env.example .env
# Edit .env with production values
nano .env
```

#### Step 3: Configure PostgreSQL
```bash
# Switch to postgres user
sudo su - postgres

# Create database and user
createuser smarttriage_user
createdb smarttriage -O smarttriage_user
psql -c "ALTER USER smarttriage_user WITH PASSWORD 'secure_password_here';"

# Exit postgres user
exit
```

#### Step 4: Configure Supervisor
Create `/etc/supervisor/conf.d/smarttriage.conf`:
```ini
[program:smarttriage]
directory=/opt/smarttriage
command=/opt/smarttriage/venv/bin/gunicorn -w 4 --threads 4 -b 127.0.0.1:5000 app:app
user=smarttriage
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=/var/log/smarttriage/error.log
stdout_logfile=/var/log/smarttriage/access.log
environment=PATH="/opt/smarttriage/venv/bin"
```

```bash
# Create log directory
sudo mkdir -p /var/log/smarttriage
sudo chown smarttriage:smarttriage /var/log/smarttriage

# Reload supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start smarttriage

# Check status
sudo supervisorctl status smarttriage
```

#### Step 5: Configure Nginx
Create `/etc/nginx/sites-available/smarttriage`:
```nginx
upstream smarttriage {
    server 127.0.0.1:5000 fail_timeout=0;
}

server {
    listen 80;
    server_name your-domain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;

    # Client body size limit
    client_max_body_size 16M;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # Static files
    location /static {
        alias /opt/smarttriage/static;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # Health checks (no auth required)
    location /health {
        proxy_pass http://smarttriage;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        access_log off;
    }

    # Application
    location / {
        proxy_pass http://smarttriage;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/smarttriage /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

#### Step 6: SSL/TLS with Let's Encrypt
```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
sudo certbot renew --dry-run
```

---

## 🔐 Security Hardening

### Firewall Configuration
```bash
# UFW (Ubuntu/Debian)
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp # HTTPS
sudo ufw enable

# Fail2ban for brute force protection
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### Database Security
```bash
# PostgreSQL - restrict connections
sudo nano /etc/postgresql/*/main/pg_hba.conf
# Change to:
# local   all             all                                     md5
# host    all             all             127.0.0.1/32            md5

sudo systemctl restart postgresql
```

### Application Security
1. **Change default passwords** - Ensure all default credentials are changed
2. **Enable audit logging** - Set `AUDIT_LOGGING_ENABLED=true`
3. **Configure SMTP** - For email notifications and password resets
4. **Regular updates** - Keep dependencies updated

---

## 📊 Monitoring & Maintenance

### Health Check Endpoints
- `/health/ping` - Simple ping (200 OK)
- `/health/ready` - Readiness check (DB + models)
- `/health/live` - Liveness check
- `/health/status` - Detailed status with metrics
- `/health/metrics` - Prometheus metrics

### Log Files
```bash
# Application logs
tail -f /opt/smarttriage/logs/smarttriage.log

# Error logs
tail -f /opt/smarttriage/logs/errors.log

# Audit logs
tail -f /opt/smarttriage/logs/audit.log

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Monitoring with Prometheus & Grafana
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'smarttriage'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/health/metrics'
    scrape_interval: 15s
```

### Backup Strategy
```bash
# Database backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/backup/smarttriage

# PostgreSQL
pg_dump smarttriage | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Application data
tar -czf $BACKUP_DIR/app_$DATE.tar.gz /opt/smarttriage

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

# Setup cron job
# sudo crontab -e
# 0 2 * * * /path/to/backup_script.sh
```

---

## 🧪 Testing Deployment

### Smoke Tests
```bash
# Health check
curl https://your-domain.com/health/ping

# Status check
curl https://your-domain.com/health/status

# Metrics
curl https://your-domain.com/health/metrics
```

### Load Testing
```bash
# Install Apache Bench
sudo apt install -y apache2-utils

# Test
ab -n 1000 -c 10 https://your-domain.com/
```

---

## 🆘 Troubleshooting

### Application won't start
```bash
# Check supervisor logs
sudo supervisorctl tail -f smarttriage stderr

# Check if port is in use
sudo lsof -i :5000

# Check database connection
sudo su - smarttriage
cd /opt/smarttriage
source venv/bin/activate
python -c "from utils.database import DatabaseManager; from config import get_config; db = DatabaseManager(get_config()); print('DB OK')"
```

### High memory usage
```bash
# Check process memory
ps aux | grep gunicorn

# Reduce worker count in supervisor config
# -w 2 --threads 4 instead of -w 4 --threads 4
```

### Slow response times
```bash
# Check database queries
# Enable query logging in PostgreSQL
sudo nano /etc/postgresql/*/main/postgresql.conf
# log_statement = 'all'

# Check connection pool status
curl https://your-domain.com/health/status
```

---

## 🎓 Best Practices

1. **Never run as root** - Always use dedicated user
2. **Keep logs rotated** - Prevent disk space issues
3. **Monitor regularly** - Set up alerts for errors
4. **Update dependencies** - Monthly security patches
5. **Test backups** - Verify restore procedure works
6. **Document changes** - Keep deployment log
7. **Use environment variables** - Never hardcode secrets
8. **Enable SSL/TLS** - Always use HTTPS
9. **Rate limiting** - Protect against abuse
10. **Audit logging** - Track security events

---

## 📞 Support & Maintenance

### Regular Maintenance Tasks
- [ ] Weekly: Check error logs
- [ ] Weekly: Review audit logs for suspicious activity
- [ ] Monthly: Update dependencies (`pip list --outdated`)
- [ ] Monthly: Review and rotate logs
- [ ] Quarterly: Security audit
- [ ] Quarterly: Performance optimization review

### Emergency Contacts
- Application logs: `/opt/smarttriage/logs/`
- System administrator: [Contact Info]
- Database administrator: [Contact Info]
- Security team: [Contact Info]

---

**Version**: 2.0.0-professional
**Last Updated**: March 10, 2026
**Deployment Status**: ✅ Production-Ready
