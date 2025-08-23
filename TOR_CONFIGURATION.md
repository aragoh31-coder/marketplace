# 🔒 Tor Configuration Guide for Django Marketplace

This guide provides step-by-step instructions for configuring and deploying your Tor-safe Django marketplace.

## 🚀 **Quick Start**

### **1. Environment Setup**
```bash
# Clone the repository
git clone <your-repo-url>
cd marketplace

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Tor-specific dependencies
pip install django-csp  # Content Security Policy
```

### **2. Django Settings Configuration**
```python
# In marketplace/settings.py, ensure these are set:

# Tor Security Settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'no-referrer'
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000

# Content Security Policy - NO JavaScript
CSP_SCRIPT_SRC = ("'none'",)  # This blocks ALL JavaScript
CSP_DEFAULT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:")
CSP_FONT_SRC = ("'self'",)

# Disable external services
CELERY_BROKER_URL = None
CELERY_RESULT_BACKEND = None
```

### **3. Database Setup**
```bash
# Create database
python manage.py makemigrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic
```

### **4. Tor Configuration**
```bash
# Install Tor (Ubuntu/Debian)
sudo apt update
sudo apt install tor

# Install Tor (macOS)
brew install tor

# Install Tor (Windows)
# Download from https://www.torproject.org/
```

## 🛡️ **Security Configuration**

### **Django Security Headers**
```python
# Add to settings.py
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Tor security middleware
    'core.security.middleware.TorSecurityMiddleware',
]

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'no-referrer'
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

### **Content Security Policy**
```python
# Strict CSP for Tor
CSP_DEFAULT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_SCRIPT_SRC = ("'none'",)  # NO JavaScript
CSP_IMG_SRC = ("'self'", "data:")
CSP_FONT_SRC = ("'self'",)
CSP_CONNECT_SRC = ("'self'",)
CSP_FRAME_SRC = ("'none'",)
CSP_OBJECT_SRC = ("'none'",)
CSP_BASE_URI = ("'self'",)
CSP_FORM_ACTION = ("'self'",)
```

## 🌐 **Tor Hidden Service Configuration**

### **1. Tor Configuration File**
```bash
# Edit /etc/tor/torrc
sudo nano /etc/tor/torrc
```

### **2. Add Hidden Service Configuration**
```bash
# Add these lines to torrc
HiddenServiceDir /var/lib/tor/marketplace
HiddenServicePort 80 127.0.0.1:8000
HiddenServicePort 443 127.0.0.1:8000

# Optional: Add authentication
HiddenServiceAuthorizeClient auth marketplace
```

### **3. Restart Tor Service**
```bash
sudo systemctl restart tor
sudo systemctl enable tor

# Check status
sudo systemctl status tor
```

### **4. Get Hidden Service Address**
```bash
# View the hidden service address
sudo cat /var/lib/tor/marketplace/hostname
```

## 🚀 **Deployment Options**

### **Option 1: Development Server (Testing)**
```bash
# Run development server
python manage.py runserver 127.0.0.1:8000

# Access via Tor Browser
# Navigate to your hidden service address
```

### **Option 2: Gunicorn + Nginx (Production)**
```bash
# Install Gunicorn
pip install gunicorn

# Create Gunicorn config
cat > gunicorn.conf.py << EOF
bind = "127.0.0.1:8000"
workers = 4
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
EOF

# Run with Gunicorn
gunicorn -c gunicorn.conf.py marketplace.wsgi:application
```

### **Option 3: Docker Deployment**
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["gunicorn", "-c", "gunicorn.conf.py", "marketplace.wsgi:application"]
```

## 🔧 **Template Configuration**

### **Use Tor-Safe Templates**
```python
# In your views.py, use Tor-safe templates
def product_list(request):
    products = Product.objects.all()
    context = {'products': products}
    
    # Use Tor-safe template
    return render(request, 'products/product_list_tor_safe.html', context)

def login_view(request):
    form = LoginForm()
    context = {'form': form}
    
    # Use Tor-safe template
    return render(request, 'accounts/login_tor_safe.html', context)
```

### **Template Inheritance**
```html
<!-- All templates should extend base_tor_safe.html -->
{% extends 'base_tor_safe.html' %}

{% block content %}
<!-- Your content here -->
{% endblock %}
```

## 🧪 **Testing Tor Compatibility**

### **1. Test with Tor Browser**
```bash
# Download Tor Browser from https://www.torproject.org/
# Set security level to "Safest"
# Navigate to your hidden service
# Verify all functionality works
```

### **2. Test with JavaScript Disabled**
```bash
# Open regular browser
# Disable JavaScript completely
# Navigate to your site
# Verify all functionality works
```

### **3. Test Security Headers**
```bash
# Use browser dev tools
# Check Network tab for security headers
# Verify CSP blocks JavaScript
# Check for external requests
```

## 📊 **Monitoring and Logging**

### **Django Logging Configuration**
```python
# In settings.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'tor_marketplace.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['file'],
        'level': 'INFO',
    },
}
```

### **Tor Log Monitoring**
```bash
# Monitor Tor logs
sudo tail -f /var/log/tor/log

# Monitor application logs
tail -f logs/tor_marketplace.log

# Check for security violations
grep -i "security\|blocked\|forbidden" logs/tor_marketplace.log
```

## 🚨 **Security Checklist**

### **Before Deployment**
- [ ] All JavaScript removed from templates
- [ ] All external CDN links removed
- [ ] Content Security Policy configured
- [ ] Security headers enabled
- [ ] Tor middleware active
- [ ] No external API calls
- [ ] All forms use CSRF tokens
- [ ] Database migrations applied
- [ ] Static files collected
- [ ] Logging configured

### **After Deployment**
- [ ] Tor hidden service accessible
- [ ] All functionality works without JavaScript
- [ ] Security headers present
- [ ] No external requests made
- [ ] CSP blocks JavaScript injection
- [ ] Forms submit correctly
- [ ] Navigation works properly
- [ ] Mobile compatibility verified
- [ ] Performance acceptable
- [ ] Logs show no errors

## 🔍 **Troubleshooting**

### **Common Issues**

#### **1. Template Not Found**
```bash
# Check template directory structure
ls -la templates/
ls -la templates/products/
ls -la templates/accounts/

# Verify template names match view calls
```

#### **2. Security Headers Missing**
```bash
# Check middleware order
# Ensure TorSecurityMiddleware is last
# Verify settings configuration
```

#### **3. JavaScript Still Working**
```bash
# Check CSP configuration
# Verify script-src is set to 'none'
# Clear browser cache
# Test in incognito/private mode
```

#### **4. External Requests**
```bash
# Check for hardcoded URLs
# Verify all resources are local
# Check static file configuration
# Monitor network requests
```

### **Debug Commands**
```bash
# Check Django configuration
python manage.py check --deploy

# Verify static files
python manage.py collectstatic --dry-run

# Test database connection
python manage.py dbshell

# Check installed apps
python manage.py shell
>>> from django.conf import settings
>>> print(settings.INSTALLED_APPS)
```

## 🎯 **Performance Optimization**

### **Static File Optimization**
```bash
# Compress CSS and JS (if any)
pip install django-compressor

# Optimize images
pip install Pillow

# Use local fonts instead of Google Fonts
# Host all resources locally
```

### **Database Optimization**
```bash
# Create database indexes
python manage.py makemigrations
python manage.py migrate

# Optimize queries
# Use select_related and prefetch_related
# Implement caching for frequently accessed data
```

## 🔒 **Final Security Notes**

1. **Never trust external resources** - Host everything locally
2. **Validate all user input** - Server-side validation only
3. **Use HTTPS in production** - Even behind Tor
4. **Regular security audits** - Check for new vulnerabilities
5. **Monitor access logs** - Watch for suspicious activity
6. **Keep Django updated** - Security patches are crucial
7. **Use strong passwords** - Enforce password policies
8. **Enable 2FA** - Additional security layer
9. **Regular backups** - Protect against data loss
10. **Test thoroughly** - Security is not optional

Your Tor-safe Django marketplace is now ready for secure deployment! 🎯