#!/bin/bash

# Keep VM, Tor, and Django Services Alive for 6 Hours
# This script will run for 6 hours and continuously monitor/restart services

LOG_FILE="/workspace/logs/keepalive.log"
PID_FILE="/workspace/keepalive.pid"
DURATION=21600  # 6 hours in seconds
START_TIME=$(date +%s)
END_TIME=$((START_TIME + DURATION))

# Store PID for this script
echo $$ > "$PID_FILE"

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to check if a process is running
is_process_running() {
    local process_name="$1"
    pgrep -f "$process_name" > /dev/null 2>&1
}

# Function to keep VM alive with activity
keep_vm_alive() {
    # Create small file operations to show activity
    echo "$(date): VM keepalive heartbeat" >> /tmp/vm_heartbeat.log
    
    # Light CPU activity
    dd if=/dev/zero of=/tmp/keepalive_test bs=1M count=1 2>/dev/null
    rm -f /tmp/keepalive_test
    
    # Memory activity
    free -m > /tmp/memory_status.tmp
    rm -f /tmp/memory_status.tmp
    
    # Disk I/O activity
    sync
}

# Function to restart Tor if needed
restart_tor() {
    log_message "Restarting Tor service..."
    
    # Kill existing Tor processes
    sudo pkill -f "tor -f /workspace/torrc" 2>/dev/null
    sleep 2
    
    # Start Tor again
    sudo -u debian-tor tor -f /workspace/torrc &
    
    if [ $? -eq 0 ]; then
        log_message "Tor restarted successfully"
    else
        log_message "Failed to restart Tor"
    fi
}

# Function to restart Gunicorn if needed
restart_gunicorn() {
    log_message "Restarting Gunicorn service..."
    
    # Kill existing Gunicorn processes
    pkill -f "gunicorn.*marketplace.wsgi" 2>/dev/null
    sleep 3
    
    # Start Gunicorn again
    cd /workspace
    export PATH="/home/ubuntu/.local/bin:$PATH"
    gunicorn --config gunicorn.conf.py marketplace.wsgi:application &
    
    if [ $? -eq 0 ]; then
        log_message "Gunicorn restarted successfully"
    else
        log_message "Failed to restart Gunicorn"
    fi
}

# Function to restart Redis if needed
restart_redis() {
    log_message "Restarting Redis service..."
    
    # Kill existing Redis processes
    pkill redis-server 2>/dev/null
    sleep 2
    
    # Start Redis again
    redis-server --daemonize yes
    
    if [ $? -eq 0 ]; then
        log_message "Redis restarted successfully"
    else
        log_message "Failed to restart Redis"
    fi
}

# Function to restart Nginx if needed
restart_nginx() {
    log_message "Restarting Nginx service..."
    
    # Test nginx config first
    if sudo nginx -t 2>/dev/null; then
        sudo nginx -s reload 2>/dev/null || sudo nginx
        log_message "Nginx restarted successfully"
    else
        log_message "Nginx config test failed"
    fi
}

# Function to check and restart services
check_and_restart_services() {
    # Check Tor
    if ! is_process_running "tor -f /workspace/torrc"; then
        log_message "Tor is not running, restarting..."
        restart_tor
    else
        log_message "Tor is running - OK"
    fi
    
    # Check Gunicorn
    if ! is_process_running "gunicorn.*marketplace.wsgi"; then
        log_message "Gunicorn is not running, restarting..."
        restart_gunicorn
    else
        log_message "Gunicorn is running - OK"
    fi
    
    # Check Redis
    if ! is_process_running "redis-server"; then
        log_message "Redis is not running, restarting..."
        restart_redis
    else
        log_message "Redis is running - OK"
    fi
    
    # Check Nginx
    if ! is_process_running "nginx"; then
        log_message "Nginx is not running, restarting..."
        restart_nginx
    else
        log_message "Nginx is running - OK"
    fi
}

# Function to test marketplace connectivity
test_marketplace() {
    local response=$(curl -s -o /dev/null -w "%{http_code}" -H "Host: localhost" http://127.0.0.1/ 2>/dev/null)
    
    if [ "$response" = "200" ]; then
        log_message "Marketplace HTTP test: OK (200)"
        return 0
    else
        log_message "Marketplace HTTP test: FAILED (${response:-no response})"
        return 1
    fi
}

# Function to show system status
show_system_status() {
    log_message "=== SYSTEM STATUS ==="
    log_message "Uptime: $(uptime | cut -d',' -f1)"
    log_message "Memory: $(free -h | grep Mem | awk '{print $3"/"$2}')"
    log_message "Disk: $(df -h / | tail -1 | awk '{print $3"/"$2" ("$5" used)"}')"
    log_message "Load: $(uptime | awk -F'load average:' '{print $2}')"
    
    # Count running processes
    local tor_count=$(pgrep -cf "tor -f /workspace/torrc")
    local gunicorn_count=$(pgrep -cf "gunicorn.*marketplace.wsgi")
    local redis_count=$(pgrep -cf "redis-server")
    local nginx_count=$(pgrep -cf "nginx")
    
    log_message "Services: Tor($tor_count) Gunicorn($gunicorn_count) Redis($redis_count) Nginx($nginx_count)"
    log_message "===================="
}

# Main keepalive loop
log_message "Starting 6-hour keepalive script (PID: $$)"
log_message "Will run until: $(date -d @$END_TIME '+%Y-%m-%d %H:%M:%S')"

# Initial service check
check_and_restart_services
show_system_status

# Main monitoring loop
counter=0
while [ $(date +%s) -lt $END_TIME ]; do
    current_time=$(date +%s)
    remaining_time=$((END_TIME - current_time))
    hours_remaining=$((remaining_time / 3600))
    minutes_remaining=$(((remaining_time % 3600) / 60))
    
    # Keep VM alive with activity
    keep_vm_alive
    
    # Every minute: basic health check
    if [ $((counter % 12)) -eq 0 ]; then
        log_message "Keepalive heartbeat - ${hours_remaining}h ${minutes_remaining}m remaining"
        
        # Test marketplace connectivity
        if ! test_marketplace; then
            log_message "Marketplace connectivity failed, checking services..."
            check_and_restart_services
        fi
    fi
    
    # Every 5 minutes: detailed service check
    if [ $((counter % 60)) -eq 0 ]; then
        log_message "Performing detailed service check..."
        check_and_restart_services
    fi
    
    # Every 30 minutes: show system status
    if [ $((counter % 360)) -eq 0 ]; then
        show_system_status
    fi
    
    # Sleep for 5 seconds
    sleep 5
    counter=$((counter + 1))
done

log_message "6-hour keepalive period completed successfully!"
log_message "Final system status:"
show_system_status

# Clean up
rm -f "$PID_FILE"
rm -f /tmp/vm_heartbeat.log

log_message "Keepalive script finished"