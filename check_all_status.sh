#!/bin/bash

# Comprehensive Status Check Script
# Shows the current status of all services, monitoring scripts, and the marketplace

echo "=============================================="
echo "🔍 MARKETPLACE & SERVICES STATUS CHECK"
echo "=============================================="
echo "Timestamp: $(date)"
echo ""

# Function to check if process is running and show count
check_process() {
    local process_name="$1"
    local display_name="$2"
    local count=$(pgrep -cf "$process_name")
    
    if [ $count -gt 0 ]; then
        echo "✅ $display_name: Running ($count processes)"
        return 0
    else
        echo "❌ $display_name: Not running"
        return 1
    fi
}

# Function to test HTTP connectivity
test_http() {
    local url="$1"
    local name="$2"
    local response=$(curl -s -o /dev/null -w "%{http_code}" -H "Host: localhost" --max-time 5 "$url" 2>/dev/null)
    
    if [ "$response" = "200" ]; then
        echo "✅ $name: HTTP $response (OK)"
        return 0
    else
        echo "❌ $name: HTTP ${response:-timeout} (FAILED)"
        return 1
    fi
}

echo "📋 CORE SERVICES:"
echo "----------------"
check_process "tor -f /workspace/torrc" "Tor Hidden Service"
check_process "gunicorn.*marketplace.wsgi" "Django/Gunicorn"
check_process "redis-server" "Redis"
check_process "nginx" "Nginx"

echo ""
echo "🔧 MONITORING SCRIPTS:"
echo "---------------------"
check_process "keep_everything_alive_6hrs.sh" "Main 6-Hour Keepalive"
check_process "tor_watchdog.sh" "Tor Watchdog"
check_process "django_watchdog.sh" "Django Watchdog"

echo ""
echo "🌐 CONNECTIVITY TESTS:"
echo "---------------------"
test_http "http://127.0.0.1/" "Marketplace Homepage"
test_http "http://127.0.0.1/admin/" "Admin Panel"

echo ""
echo "🧅 TOR HIDDEN SERVICE:"
echo "---------------------"
if [ -f "/var/lib/tor/marketplace/hostname" ]; then
    onion_address=$(sudo cat /var/lib/tor/marketplace/hostname 2>/dev/null)
    if [ -n "$onion_address" ]; then
        echo "✅ Onion Address: $onion_address"
    else
        echo "❌ Cannot read onion address"
    fi
else
    echo "❌ Onion address file not found"
fi

echo ""
echo "💾 DATABASE STATUS:"
echo "------------------"
cd /workspace
export PATH="/home/ubuntu/.local/bin:$PATH"
if timeout 5 python3 manage.py check --database default >/dev/null 2>&1; then
    echo "✅ Database: Connected"
else
    echo "❌ Database: Connection failed"
fi

echo ""
echo "📊 SYSTEM RESOURCES:"
echo "-------------------"
echo "🖥️  Uptime: $(uptime | cut -d',' -f1)"
echo "💾 Memory: $(free -h | grep Mem | awk '{print $3"/"$2" ("int($3/$2*100)"% used)"}')"
echo "💿 Disk: $(df -h / | tail -1 | awk '{print $3"/"$2" ("$5" used)"}')"
echo "⚡ Load: $(uptime | awk -F'load average:' '{print $2}')"

echo ""
echo "📝 RECENT LOG ACTIVITY:"
echo "----------------------"
echo "🔧 Main Keepalive (last 3 lines):"
tail -3 /workspace/logs/keepalive.log 2>/dev/null || echo "No logs found"

echo ""
echo "🧅 Tor Watchdog (last 3 lines):"
tail -3 /workspace/logs/tor_watchdog.log 2>/dev/null || echo "No logs found"

echo ""
echo "🐍 Django Watchdog (last 3 lines):"
tail -3 /workspace/logs/django_watchdog.log 2>/dev/null || echo "No logs found"

echo ""
echo "⏰ KEEPALIVE TIME REMAINING:"
echo "---------------------------"
if [ -f "/workspace/keepalive.pid" ]; then
    keepalive_pid=$(cat /workspace/keepalive.pid)
    if ps -p $keepalive_pid > /dev/null 2>&1; then
        echo "✅ Keepalive script is running (PID: $keepalive_pid)"
        # Try to extract remaining time from the log
        last_heartbeat=$(grep "remaining" /workspace/logs/keepalive.log | tail -1)
        if [ -n "$last_heartbeat" ]; then
            echo "⏱️  $last_heartbeat"
        fi
    else
        echo "❌ Keepalive script not running"
    fi
else
    echo "❌ Keepalive PID file not found"
fi

echo ""
echo "=============================================="
echo "Status check completed at $(date)"
echo "=============================================="