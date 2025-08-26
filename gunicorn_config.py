import multiprocessing
import os

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
worker_connections = 1000
timeout = 300
keepalive = 2

# Restart workers after this many requests, to help prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = '/workspace/logs/gunicorn-access.log'
errorlog = '/workspace/logs/gunicorn-error.log'
loglevel = 'info'
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = 'django_marketplace'

# Server mechanics
daemon = False
pidfile = '/workspace/gunicorn.pid'
user = None
group = None
tmp_upload_dir = None

# SSL/TLS - Not needed for Tor hidden service as Tor provides encryption
# keyfile = None
# certfile = None