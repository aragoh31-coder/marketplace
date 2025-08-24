# Marketplace Setup Guide

## Overview

This is a fully-featured dark web marketplace built with Django, supporting Tor hidden services, Bitcoin/Monero payments, and advanced security features.

## Installation Complete

All required software has been installed:
- ✅ Python 3.13 with virtual environment
- ✅ Django 5.1.4 with all dependencies
- ✅ Redis for caching and sessions
- ✅ Nginx for reverse proxy
- ✅ Tor for hidden service access
- ✅ PostgreSQL support (using SQLite for development)

## Quick Start

### 1. Start All Services

```bash
cd /workspace
./start_marketplace.sh
```

This script will:
- Start Redis server
- Start Tor hidden service
- Start Celery worker and beat
- Collect static files
- Run database migrations
- Start Gunicorn application server
- Start Nginx reverse proxy

### 2. Access the Marketplace

- **Local access**: http://localhost
- **Tor access**: Check your .onion address with:
  ```bash
  sudo cat /var/lib/tor/marketplace/hostname
  ```

### 3. Create Admin Account

```bash
cd /workspace
source venv/bin/activate
python manage.py createsuperuser
```

Follow the prompts to create an admin account.

## Manual Service Management

### Start Individual Services

```bash
# Start Redis
redis-server --daemonize yes

# Start Tor
sudo tor -f /workspace/torrc

# Start Django development server (for testing)
cd /workspace
source venv/bin/activate
python manage.py runserver

# Start Gunicorn (production)
gunicorn marketplace.wsgi:application --bind 127.0.0.1:8000 --daemon

# Start Nginx
sudo nginx -c /workspace/nginx.conf
```

### Stop Services

```bash
# Stop Redis
redis-cli shutdown

# Stop Tor
sudo killall tor

# Stop Gunicorn
pkill gunicorn

# Stop Nginx
sudo nginx -s stop
```

## Key Features

### 1. Security
- PGP authentication support
- Two-factor authentication (TOTP)
- Anti-DDoS protection
- CSRF protection
- Rate limiting
- Secure session management

### 2. Marketplace Features
- Product listings with categories
- Vendor profiles and ratings
- Order management system
- Dispute resolution
- Messaging system
- Wallet integration (Bitcoin/Monero)

### 3. Admin Panel
- User management
- Order monitoring
- Security alerts
- System metrics
- Content moderation

## Configuration

### Environment Variables
Edit `/workspace/.env` to configure:
- Database settings
- Redis connection
- Security keys
- Bitcoin/Monero RPC settings
- Email configuration

### Nginx Configuration
Edit `/workspace/nginx.conf` to modify:
- Server names
- SSL certificates (for HTTPS)
- Proxy settings
- Cache configuration

### Tor Configuration
Edit `/workspace/torrc` to modify:
- Hidden service settings
- Security policies
- Logging levels

## Development

### Run Tests
```bash
cd /workspace
source venv/bin/activate
python manage.py test
```

### Code Quality
```bash
# Run linting
flake8 .

# Format code
black .

# Sort imports
isort .
```

### Database Management
```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Database shell
python manage.py dbshell
```

## Monitoring

### Check Service Status
```bash
# Redis
redis-cli ping

# Tor
sudo systemctl status tor

# Nginx
sudo nginx -t

# Django/Gunicorn
ps aux | grep gunicorn
```

### View Logs
```bash
# Django logs
tail -f /workspace/logs/errors.log

# Nginx access logs
tail -f /var/log/nginx/access.log

# Tor logs
sudo tail -f /var/log/tor/notices.log
```

## Security Best Practices

1. **Change default passwords** in `.env`
2. **Enable HTTPS** for clearnet access
3. **Regular backups** of database and media files
4. **Monitor logs** for suspicious activity
5. **Keep dependencies updated**
6. **Use strong admin passwords**
7. **Enable 2FA** for all admin accounts

## Troubleshooting

### Redis Connection Error
```bash
# Check if Redis is running
redis-cli ping

# Restart Redis
redis-server --daemonize yes
```

### Tor Not Starting
```bash
# Check Tor logs
sudo journalctl -u tor

# Verify configuration
tor --verify-config -f /workspace/torrc
```

### Static Files Not Loading
```bash
# Collect static files
python manage.py collectstatic --noinput

# Check Nginx configuration
sudo nginx -t
```

## Support

For issues or questions:
1. Check logs in `/workspace/logs/`
2. Review Django debug toolbar (if DEBUG=True)
3. Consult documentation in `/workspace/docs/`

## Next Steps

1. Configure SSL certificates for HTTPS
2. Set up automated backups
3. Configure monitoring tools
4. Customize marketplace theme
5. Add payment gateway integration
6. Set up email notifications

---

**Note**: This marketplace is configured for development/testing. Additional security hardening is required for production use.