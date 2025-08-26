#!/bin/bash

# Keep VM and services alive for 12 hours with monitoring
# Checks every 120 seconds and restarts services if needed

LOG_FILE="/workspace/logs/service_monitor.log"
DURATION_HOURS=12
CHECK_INTERVAL=120
TOTAL_SECONDS=$((DURATION_HOURS * 3600))
ELAPSED=0

# Onion address for health checks
ONION_ADDRESS="qeuueyrrxgksggiq3i4ejb3dritg5kl37ddtpa6woystvf2urtwfl5yd.onion"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to check if a service is running
check_service() {
    local service=$1
    if sudo service $service status >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to check if Gunicorn is running
check_gunicorn() {
    if pgrep -f "gunicorn.*marketplace.wsgi" >/dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to restart Tor
restart_tor() {
    log_message "Restarting Tor service..."
    sudo service tor restart
    sleep 5
}

# Function to restart Redis
restart_redis() {
    log_message "Restarting Redis service..."
    sudo service redis-server restart
    sleep 2
}

# Function to restart Nginx
restart_nginx() {
    log_message "Restarting Nginx service..."
    sudo service nginx restart
    sleep 2
}

# Function to restart Gunicorn
restart_gunicorn() {
    log_message "Restarting Gunicorn..."
    # Kill existing Gunicorn processes
    pkill -f "gunicorn.*marketplace.wsgi" 2>/dev/null
    sleep 2
    
    # Start Gunicorn in background
    cd /workspace
    source venv/bin/activate
    nohup gunicorn -c gunicorn_config.py marketplace.wsgi:application > /workspace/logs/gunicorn_restart.log 2>&1 &
    sleep 5
}

# Function to check Django health
check_django_health() {
    # Check local connection
    if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000 | grep -q "200"; then
        return 0
    else
        return 1
    fi
}

# Function to check Tor connectivity
check_tor_health() {
    # Check if we can reach the onion service
    if curl --socks5-hostname 127.0.0.1:9050 -s -o /dev/null -w "%{http_code}" -m 30 http://$ONION_ADDRESS | grep -q "200"; then
        return 0
    else
        return 1
    fi
}

# Function to perform health check and restart if needed
perform_health_check() {
    local all_healthy=true
    
    # Check Tor
    if ! check_service tor; then
        log_message "⚠️  Tor is not running!"
        restart_tor
        all_healthy=false
    fi
    
    # Check Redis
    if ! check_service redis-server; then
        log_message "⚠️  Redis is not running!"
        restart_redis
        all_healthy=false
    fi
    
    # Check Nginx
    if ! check_service nginx; then
        log_message "⚠️  Nginx is not running!"
        restart_nginx
        all_healthy=false
    fi
    
    # Check Gunicorn
    if ! check_gunicorn; then
        log_message "⚠️  Gunicorn is not running!"
        restart_gunicorn
        all_healthy=false
    fi
    
    # If all services are running, check Django health
    if [ "$all_healthy" = true ]; then
        if ! check_django_health; then
            log_message "⚠️  Django is not responding! Restarting Gunicorn..."
            restart_gunicorn
            all_healthy=false
        fi
    fi
    
    # Check Tor connectivity (only if services were healthy)
    if [ "$all_healthy" = true ]; then
        if ! check_tor_health; then
            log_message "⚠️  Onion service not accessible! Checking services..."
            # Don't immediately restart, could be temporary network issue
        else
            log_message "✅ All services healthy - Onion service accessible"
        fi
    fi
    
    return 0
}

# Function to keep VM alive
keep_vm_alive() {
    # Create a small file write to prevent VM suspension
    echo "$(date): Keeping VM alive" >> /workspace/logs/vm_heartbeat.log
    
    # Run a small CPU task
    timeout 1s find /workspace -name "*.pyc" -type f >/dev/null 2>&1 || true
}

# Main monitoring loop
main() {
    log_message "🚀 Starting 12-hour service monitoring for Django marketplace on Tor"
    log_message "Onion address: http://$ONION_ADDRESS"
    log_message "Check interval: $CHECK_INTERVAL seconds"
    
    # Initial health check
    log_message "Performing initial health check..."
    perform_health_check
    
    # Main loop
    while [ $ELAPSED -lt $TOTAL_SECONDS ]; do
        # Keep VM alive
        keep_vm_alive
        
        # Sleep for check interval
        sleep $CHECK_INTERVAL
        
        # Update elapsed time
        ELAPSED=$((ELAPSED + CHECK_INTERVAL))
        
        # Calculate remaining time
        REMAINING=$((TOTAL_SECONDS - ELAPSED))
        HOURS_LEFT=$((REMAINING / 3600))
        MINUTES_LEFT=$(((REMAINING % 3600) / 60))
        
        log_message "⏱️  Time remaining: ${HOURS_LEFT}h ${MINUTES_LEFT}m"
        
        # Perform health check
        perform_health_check
    done
    
    log_message "✅ 12-hour monitoring period completed successfully!"
}

# Ensure log directory exists
mkdir -p /workspace/logs

# Start monitoring
main