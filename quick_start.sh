#!/bin/bash

# Quick start script - no migrations needed!

echo "🚀 Quick Starting Marketplace..."

# Activate virtual environment
source /workspace/venv/bin/activate

# Initialize database if needed (very fast)
echo "Checking database..."
python /workspace/init_database.py

# Start Redis if not running
if ! pgrep -x "redis-server" > /dev/null; then
    echo "Starting Redis..."
    redis-server --daemonize yes
    sleep 1
fi

# Start Tor if not running
if ! pgrep -x "tor" > /dev/null; then
    echo "Starting Tor..."
    tor -f /workspace/torrc &
    sleep 3
fi

# Start Django
echo "Starting Django server..."
python manage.py runserver 0.0.0.0:8000 &

echo "✅ Marketplace started!"
echo "Local access: http://localhost:8000"
echo "Onion access: $(cat /workspace/tor-data/marketplace/hostname 2>/dev/null || echo 'Tor still initializing...')"