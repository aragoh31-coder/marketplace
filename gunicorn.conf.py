# Gunicorn configuration for Django Marketplace
import multiprocessing

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# Logging
accesslog = "/workspace/logs/gunicorn_access.log"
errorlog = "/workspace/logs/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "marketplace_gunicorn"

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Environment
raw_env = [
    'DJANGO_SETTINGS_MODULE=marketplace.settings',
]

# Daemon settings (only if running as daemon)
# daemon = True
# pidfile = "/workspace/gunicorn.pid"
# user = "www-data"
# group = "www-data"

# Worker optimization
worker_tmp_dir = "/dev/shm"
tmp_upload_dir = None

# SSL (disabled for Tor)
# keyfile = None
# certfile = None