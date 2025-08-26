# Tor Hidden Service Deployment Complete

## Onion Address
Your Django marketplace is now accessible at:
```
http://qeuueyrrxgksggiq3i4ejb3dritg5kl37ddtpa6woystvf2urtwfl5yd.onion
```

## Services Status

### 1. Tor Hidden Service
- **Status**: ✅ Running
- **Configuration**: `/etc/tor/torrc`
- **Hidden Service Directory**: `/var/lib/tor/django_marketplace/`
- **Forwarding**: Port 80 → 127.0.0.1:8080

### 2. Nginx Reverse Proxy
- **Status**: ✅ Running
- **Configuration**: `/etc/nginx/sites-available/django_marketplace`
- **Listening**: Port 8080 (for Tor) and Port 80 (for local access)
- **Upstream**: Gunicorn on 127.0.0.1:8000

### 3. Gunicorn Application Server
- **Status**: ✅ Running (10 workers)
- **Configuration**: `/workspace/gunicorn_config.py`
- **Binding**: 127.0.0.1:8000
- **Workers**: CPU cores × 2 + 1
- **Logs**: `/workspace/logs/gunicorn-*.log`

### 4. Redis Cache/Session Store
- **Status**: ✅ Running
- **Port**: 6379
- **Databases**:
  - DB 0: General Redis usage
  - DB 1: Django cache
  - DB 2: Celery broker
  - DB 3: Celery results

### 5. Django Application
- **Status**: ✅ Running
- **Environment**: Production
- **Database**: SQLite at `/workspace/db.sqlite3`
- **Static Files**: `/workspace/staticfiles/`
- **Media Files**: `/workspace/media/`
- **Settings**: `/workspace/marketplace/settings.py`
- **Environment Variables**: `/workspace/.env`

## Security Features Enabled

1. **Tor-specific Headers**: No-referrer policy, strict CSP
2. **HTTPS-only Cookies**: Secure flag enabled
3. **XSS Protection**: Enabled via headers
4. **Frame Options**: DENY to prevent clickjacking
5. **Content Type Options**: nosniff enabled
6. **JavaScript**: Disabled for enhanced security
7. **Rate Limiting**: Configured via Django middleware
8. **Session Security**: Redis-backed sessions with secure cookies

## Management Commands

### Start Services
```bash
# Start Tor
sudo service tor start

# Start Redis
sudo service redis-server start

# Start Nginx
sudo service nginx start

# Start Gunicorn (from /workspace with venv activated)
source venv/bin/activate
gunicorn -c gunicorn_config.py marketplace.wsgi:application &
```

### Stop Services
```bash
# Stop Gunicorn
pkill gunicorn

# Stop Nginx
sudo service nginx stop

# Stop Redis
sudo service redis-server stop

# Stop Tor
sudo service tor stop
```

### Monitor Services
```bash
# Check Tor status
sudo service tor status

# Check Nginx status
sudo service nginx status

# Check Redis status
sudo service redis-server status

# Check Gunicorn processes
ps aux | grep gunicorn

# View Gunicorn logs
tail -f /workspace/logs/gunicorn-*.log

# Test onion service
curl --socks5-hostname 127.0.0.1:9050 -I http://qeuueyrrxgksggiq3i4ejb3dritg5kl37ddtpa6woystvf2urtwfl5yd.onion
```

## Important Notes

1. **Database Migrations**: Already applied. Use `python manage.py migrate` for future updates.
2. **Static Files**: Run `python manage.py collectstatic` after any static file changes.
3. **Environment Variables**: Update `/workspace/.env` for configuration changes.
4. **Allowed Hosts**: The onion address has been added to Django's ALLOWED_HOSTS.
5. **Security**: The marketplace is configured for maximum security over Tor.

## Troubleshooting

If services aren't working:

1. Check service logs:
   - Tor: `sudo journalctl -u tor`
   - Nginx: `sudo tail -f /var/log/nginx/error.log`
   - Gunicorn: `tail -f /workspace/logs/gunicorn-error.log`

2. Verify port availability:
   - `sudo netstat -tlnp | grep -E '8080|8000|6379'`

3. Test connectivity:
   - Local: `curl http://localhost:8000`
   - Nginx: `curl http://localhost:8080`
   - Tor: `curl --socks5-hostname 127.0.0.1:9050 http://[onion-address]`

## Backup Recommendation

Important files to backup:
- `/workspace/db.sqlite3` (database)
- `/workspace/.env` (configuration)
- `/var/lib/tor/django_marketplace/` (onion keys)
- `/workspace/media/` (user uploads)

Your Django marketplace is now fully operational as a Tor hidden service!