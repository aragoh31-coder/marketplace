#!/bin/bash

# Django/Gunicorn Watchdog Script - Ensures Django Marketplace Stays Active
# This script continuously monitors Django and restarts it if needed

LOG_FILE="/workspace/logs/django_watchdog.log"
GUNICORN_CONFIG="/workspace/gunicorn.conf.py"
CHECK_INTERVAL=30  # Check every 30 seconds
MAX_RESTART_ATTEMPTS=3
RESTART_ATTEMPT_COUNT=0

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] DJANGO-WATCHDOG: $1" | tee -a "$LOG_FILE"
}

# Function to check if Gunicorn is running
is_gunicorn_running() {
    pgrep -f "gunicorn.*marketplace.wsgi" > /dev/null 2>&1
}

# Function to check Django application health
check_django_health() {
    local response=$(curl -s -o /dev/null -w "%{http_code}" -H "Host: localhost" --max-time 10 http://127.0.0.1/ 2>/dev/null)
    
    if [ "$response" = "200" ]; then
        log_message "Django health check: OK (HTTP 200)"
        return 0
    else
        log_message "Django health check: FAILED (HTTP ${response:-timeout})"
        return 1
    fi
}

# Function to check admin panel access
check_admin_access() {
    local response=$(curl -s -o /dev/null -w "%{http_code}" -H "Host: localhost" --max-time 10 http://127.0.0.1/admin/ 2>/dev/null)
    
    if [ "$response" = "200" ] || [ "$response" = "302" ]; then
        log_message "Admin panel check: OK (HTTP $response)"
        return 0
    else
        log_message "Admin panel check: FAILED (HTTP ${response:-timeout})"
        return 1
    fi
}

# Function to check database connectivity
check_database() {
    cd /workspace
    export PATH="/home/ubuntu/.local/bin:$PATH"
    
    local db_check=$(timeout 10 python3 manage.py check --database default 2>&1)
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        log_message "Database check: OK"
        return 0
    else
        log_message "Database check: FAILED - $db_check"
        return 1
    fi
}

# Function to restart Gunicorn
restart_gunicorn() {
    log_message "Restarting Gunicorn service (attempt $((RESTART_ATTEMPT_COUNT + 1))/$MAX_RESTART_ATTEMPTS)..."
    
    # Kill existing Gunicorn processes gracefully
    local gunicorn_pids=$(pgrep -f "gunicorn.*marketplace.wsgi")
    if [ -n "$gunicorn_pids" ]; then
        log_message "Stopping existing Gunicorn processes: $gunicorn_pids"
        pkill -TERM -f "gunicorn.*marketplace.wsgi" 2>/dev/null
        sleep 5
        
        # Force kill if still running
        if pgrep -f "gunicorn.*marketplace.wsgi" > /dev/null 2>&1; then
            log_message "Force killing remaining Gunicorn processes"
            pkill -KILL -f "gunicorn.*marketplace.wsgi" 2>/dev/null
            sleep 2
        fi
    fi
    
    # Ensure we're in the right directory
    cd /workspace
    export PATH="/home/ubuntu/.local/bin:$PATH"
    
    # Check if static files exist
    if [ ! -d "/workspace/staticfiles" ]; then
        log_message "Creating staticfiles directory"
        mkdir -p /workspace/staticfiles
    fi
    
    # Collect static files if needed
    if [ ! "$(ls -A /workspace/staticfiles 2>/dev/null)" ]; then
        log_message "Collecting static files..."
        python3 manage.py collectstatic --noinput --clear 2>/dev/null || log_message "Static files collection failed"
    fi
    
    # Start Gunicorn
    log_message "Starting Gunicorn with config: $GUNICORN_CONFIG"
    gunicorn --config "$GUNICORN_CONFIG" marketplace.wsgi:application &
    local gunicorn_pid=$!
    
    # Wait a moment and check if it started
    sleep 8
    
    if is_gunicorn_running; then
        log_message "Gunicorn restarted successfully"
        
        # Wait for Django to be ready
        local attempts=0
        while [ $attempts -lt 20 ]; do
            if check_django_health; then
                log_message "Django application is responding"
                RESTART_ATTEMPT_COUNT=0  # Reset counter on success
                return 0
            fi
            sleep 3
            attempts=$((attempts + 1))
        done
        
        log_message "WARNING: Django not responding after restart"
        RESTART_ATTEMPT_COUNT=$((RESTART_ATTEMPT_COUNT + 1))
        return 1
    else
        log_message "ERROR: Failed to restart Gunicorn"
        RESTART_ATTEMPT_COUNT=$((RESTART_ATTEMPT_COUNT + 1))
        return 1
    fi
}

# Function to restart associated services
restart_supporting_services() {
    log_message "Restarting supporting services..."
    
    # Restart Redis if not running
    if ! pgrep redis-server > /dev/null 2>&1; then
        log_message "Restarting Redis..."
        redis-server --daemonize yes
    fi
    
    # Reload Nginx
    if pgrep nginx > /dev/null 2>&1; then
        log_message "Reloading Nginx..."
        sudo nginx -s reload 2>/dev/null || log_message "Nginx reload failed"
    fi
}

# Function to perform comprehensive health check
comprehensive_health_check() {
    local health_score=0
    
    # Check if Gunicorn is running
    if is_gunicorn_running; then
        health_score=$((health_score + 1))
    else
        log_message "Health check: Gunicorn not running"
        return 1
    fi
    
    # Check Django application response
    if check_django_health; then
        health_score=$((health_score + 1))
    else
        log_message "Health check: Django not responding"
        return 1
    fi
    
    # Check admin panel
    if check_admin_access; then
        health_score=$((health_score + 1))
    else
        log_message "Health check: Admin panel not accessible"
    fi
    
    # Check database connectivity
    if check_database; then
        health_score=$((health_score + 1))
    else
        log_message "Health check: Database connectivity issues"
    fi
    
    log_message "Health check score: $health_score/4"
    
    # Consider healthy if at least 3/4 checks pass
    if [ $health_score -ge 3 ]; then
        return 0
    else
        return 1
    fi
}

# Main monitoring function
monitor_django() {
    log_message "Starting Django watchdog monitoring..."
    
    while true; do
        if comprehensive_health_check; then
            log_message "Django marketplace is healthy"
            RESTART_ATTEMPT_COUNT=0  # Reset on successful health check
        else
            log_message "Django marketplace health check failed"
            
            if [ $RESTART_ATTEMPT_COUNT -ge $MAX_RESTART_ATTEMPTS ]; then
                log_message "Max restart attempts reached. Trying supporting services restart..."
                restart_supporting_services
                RESTART_ATTEMPT_COUNT=0
                sleep 60  # Wait longer before next attempt
            else
                restart_gunicorn
            fi
        fi
        
        sleep "$CHECK_INTERVAL"
    done
}

# Signal handlers for graceful shutdown
cleanup() {
    log_message "Django watchdog shutting down..."
    exit 0
}

trap cleanup SIGTERM SIGINT

# Start monitoring
log_message "Django Watchdog starting..."
log_message "Monitoring interval: ${CHECK_INTERVAL} seconds"
log_message "Gunicorn config: $GUNICORN_CONFIG"
log_message "Max restart attempts: $MAX_RESTART_ATTEMPTS"

# Initial check and start if needed
if ! is_gunicorn_running; then
    log_message "Initial Gunicorn start required"
    restart_gunicorn
fi

# Start continuous monitoring
monitor_django