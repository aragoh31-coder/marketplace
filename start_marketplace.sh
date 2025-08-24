#!/bin/bash

# Marketplace startup script

echo "Starting marketplace services..."

# Activate virtual environment
source /workspace/venv/bin/activate

# Start Redis if not running
if ! pgrep -x "redis-server" > /dev/null; then
    echo "Starting Redis..."
    redis-server --daemonize yes
    sleep 2
fi

# Start Tor if not running
if ! pgrep -x "tor" > /dev/null; then
    echo "Starting Tor..."
    tor -f /workspace/torrc &
    sleep 10
    echo "Tor hidden service address:"
    cat /workspace/tor-data/marketplace/hostname 2>/dev/null || echo "Hidden service not yet initialized"
fi

# Start Celery worker
echo "Starting Celery worker..."
celery -A marketplace worker -l info --detach

# Start Celery beat
echo "Starting Celery beat..."
celery -A marketplace beat -l info --detach

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Start Gunicorn
echo "Starting Gunicorn..."
gunicorn marketplace.wsgi:application \
    --bind 127.0.0.1:8000 \
    --workers 4 \
    --threads 2 \
    --worker-class sync \
    --worker-tmp-dir /dev/shm \
    --access-logfile /workspace/logs/gunicorn-access.log \
    --error-logfile /workspace/logs/gunicorn-error.log \
    --daemon

# Start Nginx
echo "Starting Nginx..."
sudo nginx -c /workspace/nginx.conf

echo "Marketplace services started!"
echo "Access the marketplace at: http://localhost"
echo "Tor hidden service address: $(cat /workspace/tor-data/marketplace/hostname 2>/dev/null || echo 'Not available')"