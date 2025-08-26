# 🛒 Django Marketplace - Tor Hidden Service

A secure, privacy-focused marketplace built with Django and configured for Tor hidden services.

**🎯 Complete Package**: Includes source code, database backup with admin user, and deployment scripts for immediate setup.

## 🌟 Features

- **🔐 Privacy First**: Designed for Tor hidden services
- **💰 Cryptocurrency Support**: Bitcoin and Monero integration
- **🛡️ Advanced Security**: DDoS protection, rate limiting, CSRF protection
- **👥 Multi-User System**: Vendors, buyers, and admin roles
- **💬 Messaging System**: Secure communication between users
- **🎫 Dispute Resolution**: Built-in dispute management
- **📱 Modern UI**: Responsive design with dark theme
- **🔍 Search & Categories**: Product discovery system
- **📊 Admin Panel**: Comprehensive marketplace management

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL
- Redis
- Tor
- Nginx (optional)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd django-marketplace
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Setup environment variables**
```bash
cp .env.example .env
# Edit .env with your configurations
```

4. **Database setup**
```bash
python manage.py migrate
python manage.py createsuperuser
```

5. **Collect static files**
```bash
python manage.py collectstatic
```

6. **Run the development server**
```bash
python manage.py runserver 127.0.0.1:8000
```

## 🧅 Tor Configuration

### Setup Tor Hidden Service

1. **Install Tor**
```bash
sudo apt update && sudo apt install tor
```

2. **Configure Tor**
Create `/etc/tor/torrc` or use the provided `torrc_final`:
```
DataDirectory /var/lib/tor
SocksPort 9050
ControlPort 9051
CookieAuthentication 1

# Hidden service configuration
HiddenServiceDir /var/lib/tor/marketplace/
HiddenServicePort 80 127.0.0.1:8000
HiddenServiceVersion 3

ClientOnly 1
RunAsDaemon 0
```

3. **Start Tor**
```bash
sudo -u debian-tor tor -f torrc_final
```

4. **Get your onion address**
```bash
sudo cat /var/lib/tor/marketplace/hostname
```

## 🔧 Production Setup

### Using Gunicorn + Nginx

1. **Install Gunicorn**
```bash
pip install gunicorn
```

2. **Create Gunicorn config** (see `gunicorn.conf.py.example`)

3. **Start Gunicorn**
```bash
gunicorn --config gunicorn.conf.py marketplace.wsgi:application
```

4. **Configure Nginx** (see `nginx.conf.example`)

## 🗂️ Project Structure

```
marketplace/
├── apps/                   # Django applications
│   ├── security/          # Security middleware and features
│   └── ...
├── accounts/              # User management
├── adminpanel/           # Admin interface
├── core/                 # Core functionality
├── disputes/             # Dispute resolution
├── messaging/            # User messaging
├── orders/               # Order management
├── products/             # Product catalog
├── support/              # Support system
├── vendors/              # Vendor management
├── wallets/              # Cryptocurrency wallets
├── marketplace/          # Django settings
├── static/               # Static files
├── templates/            # HTML templates
└── manage.py
```

## 🔒 Security Features

- **Enhanced Security Middleware**: Bot detection, rate limiting
- **CSRF Protection**: Custom Tor-safe CSRF middleware
- **DDoS Protection**: Advanced stateless protection with HMAC/PoW
- **Input Validation**: Comprehensive form validation
- **Audit Logging**: Security event tracking
- **Session Security**: Secure session management

## 💾 Database Models

- **Users**: Custom user model with privacy features
- **Products**: Product catalog with categories
- **Orders**: Order processing and tracking
- **Wallets**: Cryptocurrency wallet management
- **Messages**: Encrypted messaging system
- **Disputes**: Dispute resolution workflow

## 🛠️ Development

### Running Tests
```bash
python manage.py test
```

### Creating Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Debug Mode
Set `DEBUG=True` in `.env` for development.

## 🌐 Environment Variables

Key environment variables (see `.env.example`):

- `DJANGO_SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode (False for production)
- `ALLOWED_HOSTS`: Allowed hostnames including .onion
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `BITCOIND_RPC_*`: Bitcoin RPC settings
- `MONERO_*`: Monero wallet settings

## 📋 API Endpoints

- `/`: Homepage
- `/admin/`: Django admin panel
- `/accounts/`: User authentication
- `/products/`: Product catalog
- `/orders/`: Order management
- `/wallets/`: Wallet operations
- `/messaging/`: User messages
- `/disputes/`: Dispute system

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This software is provided for educational purposes. Users are responsible for ensuring compliance with local laws and regulations.

## 🔗 Links

- [Django Documentation](https://docs.djangoproject.com/)
- [Tor Project](https://www.torproject.org/)
- [Bitcoin Core](https://bitcoincore.org/)
- [Monero](https://www.getmonero.org/)

## 📞 Support

For support and questions, please use the GitHub issues system.

---

**⚡ Built with Django | 🧅 Tor Ready | 🔒 Privacy Focused**