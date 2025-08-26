# 🚀 Django Marketplace Deployment Guide

## 📋 Quick Deployment

This repository contains a complete Django marketplace with Tor hidden service support, including a pre-configured database.

### 🔧 System Requirements

- Ubuntu 20.04+ or Debian 11+
- Python 3.8+
- PostgreSQL 13+
- Redis 6+
- Tor
- Nginx (optional)

### ⚡ Fast Setup (5 minutes)

```bash
# 1. Clone repository
git clone <your-repo-url>
cd django-marketplace

# 2. Install system dependencies
sudo apt update
sudo apt install python3-pip python3-venv postgresql redis-server tor nginx

# 3. Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Configure PostgreSQL
sudo -u postgres createdb marketplace_db
sudo -u postgres createuser marketplace_user
sudo -u postgres psql -c "ALTER USER marketplace_user PASSWORD 'marketplace_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE marketplace_db TO marketplace_user;"

# 5. Restore database
sudo -u postgres psql marketplace_db < database_backup.sql

# 6. Setup environment
cp .env.example .env
# Edit .env with your settings

# 7. Start services
sudo systemctl start postgresql redis-server

# 8. Run Django
python manage.py collectstatic --noinput
gunicorn --config gunicorn.conf.py marketplace.wsgi:application &

# 9. Setup Tor
sudo cp torrc_final /etc/tor/torrc
sudo systemctl restart tor
```

## 🧅 Tor Configuration

### Auto-Setup Script

```bash
#!/bin/bash
# setup_tor.sh

# Create Tor configuration
sudo tee /etc/tor/torrc << EOF
DataDirectory /var/lib/tor
SocksPort 9050
ControlPort 9051
CookieAuthentication 1

# Hidden service configuration
HiddenServiceDir /var/lib/tor/marketplace/
HiddenServicePort 80 127.0.0.1:8000
HiddenServiceVersion 3

ClientOnly 1
RunAsDaemon 1
EOF

# Set permissions
sudo mkdir -p /var/lib/tor/marketplace
sudo chown -R debian-tor:debian-tor /var/lib/tor
sudo chmod 700 /var/lib/tor/marketplace

# Start Tor
sudo systemctl enable tor
sudo systemctl start tor

# Get onion address
sleep 10
echo "Your onion address:"
sudo cat /var/lib/tor/marketplace/hostname
```

## 🔧 Production Configuration

### Nginx Setup

```nginx
server {
    listen 80;
    server_name your-onion-address.onion localhost;

    location /static/ {
        alias /path/to/your/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias /path/to/your/media/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Systemd Services

**Django Service (`/etc/systemd/system/marketplace.service`):**

```ini
[Unit]
Description=Django Marketplace
After=network.target postgresql.service redis.service

[Service]
Type=exec
User=ubuntu
Group=ubuntu
WorkingDirectory=/workspace
Environment=PATH=/workspace/venv/bin
ExecStart=/workspace/venv/bin/gunicorn --config gunicorn.conf.py marketplace.wsgi:application
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Tor Service (if needed):**

```ini
[Unit]
Description=Tor Hidden Service
After=network.target

[Service]
Type=exec
User=debian-tor
Group=debian-tor
ExecStart=/usr/bin/tor -f /etc/tor/torrc
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## 🗄️ Database Information

The included `database_backup.sql` contains:

- **Admin User**: `admin` / `admin123`
- **Sample Data**: Pre-configured marketplace structure
- **All Migrations**: Applied and ready to use

### Database Schema
- Users with custom authentication
- Products and categories
- Orders and transactions
- Cryptocurrency wallets (Bitcoin/Monero)
- Messaging system
- Dispute resolution
- Security audit logs

## 🔒 Security Configuration

### Environment Variables

Key settings in `.env`:

```bash
# Change these in production!
DJANGO_SECRET_KEY=your-unique-secret-key
DEBUG=False
ALLOWED_HOSTS=your-onion-address.onion,localhost

# Database
DATABASE_URL=postgresql://marketplace_user:marketplace_password@localhost:5432/marketplace_db

# Security
CSRF_COOKIE_SECURE=True
SESSION_COOKIE_SECURE=True
```

### SSL/TLS (if using clearnet)

```bash
# Get Let's Encrypt certificate
sudo certbot --nginx -d yourdomain.com

# Update Nginx config for HTTPS
# Update Django settings for HTTPS
```

## 📊 Monitoring & Maintenance

### Health Checks

```bash
# Check services
systemctl status marketplace tor nginx postgresql redis

# Check Django
curl -H "Host: your-onion.onion" http://127.0.0.1:8000/

# Check database
sudo -u postgres psql marketplace_db -c "SELECT COUNT(*) FROM accounts_user;"
```

### Backup Scripts

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
sudo -u postgres pg_dump marketplace_db > "backup_${DATE}.sql"

# Files backup
tar -czf "files_${DATE}.tar.gz" staticfiles/ media/

# Tor keys backup (secure!)
sudo tar -czf "tor_keys_${DATE}.tar.gz" /var/lib/tor/marketplace/
```

## 🐛 Troubleshooting

### Common Issues

**1. 500 Errors after login:**
```bash
python manage.py migrate
python manage.py collectstatic --noinput
systemctl restart marketplace
```

**2. Tor not accessible:**
```bash
sudo systemctl status tor
sudo cat /var/lib/tor/marketplace/hostname
sudo chown -R debian-tor:debian-tor /var/lib/tor
```

**3. Database connection issues:**
```bash
sudo systemctl status postgresql
sudo -u postgres psql -c "SELECT version();"
```

**4. Static files not loading:**
```bash
python manage.py collectstatic --noinput
chown -R ubuntu:ubuntu staticfiles/
```

## 📞 Support

- Check logs in `/workspace/logs/`
- Review Django admin at `/admin/`
- Monitor system logs: `journalctl -f`

---

**🎯 Ready for production deployment!**