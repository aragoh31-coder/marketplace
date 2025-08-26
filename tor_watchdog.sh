#!/bin/bash

# Tor Watchdog Script - Ensures Tor and Onion Service Stay Active
# This script continuously monitors Tor and restarts it if needed

LOG_FILE="/workspace/logs/tor_watchdog.log"
TOR_CONFIG="/workspace/torrc"
ONION_ADDRESS_FILE="/var/lib/tor/marketplace/hostname"
CHECK_INTERVAL=30  # Check every 30 seconds

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] TOR-WATCHDOG: $1" | tee -a "$LOG_FILE"
}

# Function to check if Tor is running
is_tor_running() {
    pgrep -f "tor -f /workspace/torrc" > /dev/null 2>&1
}

# Function to check if onion service is responsive
check_onion_service() {
    if [ -f "$ONION_ADDRESS_FILE" ]; then
        local onion_address=$(sudo cat "$ONION_ADDRESS_FILE" 2>/dev/null)
        if [ -n "$onion_address" ]; then
            log_message "Onion address: $onion_address"
            return 0
        else
            log_message "Could not read onion address file"
            return 1
        fi
    else
        log_message "Onion address file not found"
        return 1
    fi
}

# Function to restart Tor
restart_tor() {
    log_message "Restarting Tor service..."
    
    # Kill existing Tor processes
    sudo pkill -f "tor -f /workspace/torrc" 2>/dev/null
    sleep 3
    
    # Ensure permissions are correct
    sudo chown -R debian-tor:debian-tor /var/lib/tor/marketplace/ 2>/dev/null
    sudo chmod 700 /var/lib/tor/marketplace/ 2>/dev/null
    
    # Start Tor
    sudo -u debian-tor tor -f "$TOR_CONFIG" &
    local tor_pid=$!
    
    # Wait a moment and check if it started
    sleep 5
    
    if is_tor_running; then
        log_message "Tor restarted successfully (PID: $tor_pid)"
        
        # Wait for onion service to be ready
        local attempts=0
        while [ $attempts -lt 30 ]; do
            if check_onion_service; then
                log_message "Onion service is ready"
                return 0
            fi
            sleep 2
            attempts=$((attempts + 1))
        done
        
        log_message "WARNING: Onion service not ready after 60 seconds"
        return 1
    else
        log_message "ERROR: Failed to restart Tor"
        return 1
    fi
}

# Function to check Tor bootstrap status
check_tor_bootstrap() {
    if command -v tor >/dev/null 2>&1; then
        # Try to get bootstrap status via control port
        echo -e "AUTHENTICATE\r\nGETINFO status/bootstrap-phase\r\nQUIT\r\n" | \
        timeout 5 nc 127.0.0.1 9051 2>/dev/null | grep "BOOTSTRAP PROGRESS" | tail -1
    fi
}

# Main monitoring function
monitor_tor() {
    log_message "Starting Tor watchdog monitoring..."
    
    while true; do
        if is_tor_running; then
            # Check if onion service is working
            if check_onion_service; then
                log_message "Tor and onion service are running normally"
                
                # Check bootstrap status
                local bootstrap_status=$(check_tor_bootstrap)
                if [ -n "$bootstrap_status" ]; then
                    log_message "Bootstrap status: $bootstrap_status"
                fi
            else
                log_message "Onion service issue detected, restarting Tor..."
                restart_tor
            fi
        else
            log_message "Tor is not running, restarting..."
            restart_tor
        fi
        
        sleep "$CHECK_INTERVAL"
    done
}

# Signal handlers for graceful shutdown
cleanup() {
    log_message "Tor watchdog shutting down..."
    exit 0
}

trap cleanup SIGTERM SIGINT

# Start monitoring
log_message "Tor Watchdog starting..."
log_message "Monitoring interval: ${CHECK_INTERVAL} seconds"
log_message "Tor config: $TOR_CONFIG"
log_message "Onion address file: $ONION_ADDRESS_FILE"

# Initial check and restart if needed
if ! is_tor_running; then
    log_message "Initial Tor start required"
    restart_tor
fi

# Start continuous monitoring
monitor_tor