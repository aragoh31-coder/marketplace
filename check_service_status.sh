#!/bin/bash

# Quick status check for all services

echo "=== Django Marketplace Service Status ==="
echo "Time: $(date)"
echo ""

# Check Tor
echo -n "Tor Service: "
if sudo service tor status >/dev/null 2>&1; then
    echo "✅ Running"
else
    echo "❌ Stopped"
fi

# Check Redis
echo -n "Redis Service: "
if sudo service redis-server status >/dev/null 2>&1; then
    echo "✅ Running"
else
    echo "❌ Stopped"
fi

# Check Nginx
echo -n "Nginx Service: "
if sudo service nginx status >/dev/null 2>&1; then
    echo "✅ Running"
else
    echo "❌ Stopped"
fi

# Check Gunicorn
echo -n "Gunicorn: "
if pgrep -f "gunicorn.*marketplace.wsgi" >/dev/null; then
    COUNT=$(pgrep -f "gunicorn.*marketplace.wsgi" | wc -l)
    echo "✅ Running ($COUNT processes)"
else
    echo "❌ Stopped"
fi

# Check Django health
echo -n "Django App: "
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000 2>/dev/null)
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Responding (HTTP $HTTP_CODE)"
else
    echo "❌ Not responding (HTTP $HTTP_CODE)"
fi

# Check monitoring script
echo -n "Monitoring Script: "
if pgrep -f "keep_services_alive_12hrs.sh" >/dev/null; then
    PID=$(pgrep -f "keep_services_alive_12hrs.sh")
    echo "✅ Running (PID: $PID)"
else
    echo "❌ Not running"
fi

echo ""
echo "=== Onion Service ==="
echo "Address: http://qeuueyrrxgksggiq3i4ejb3dritg5kl37ddtpa6woystvf2urtwfl5yd.onion"
echo -n "Status: "
if curl --socks5-hostname 127.0.0.1:9050 -s -o /dev/null -w "%{http_code}" -m 10 http://qeuueyrrxgksggiq3i4ejb3dritg5kl37ddtpa6woystvf2urtwfl5yd.onion 2>/dev/null | grep -q "200"; then
    echo "✅ Accessible via Tor"
else
    echo "⚠️  Not accessible (may be temporary)"
fi

echo ""
echo "=== Recent Monitor Log ==="
if [ -f /workspace/logs/service_monitor.log ]; then
    tail -n 5 /workspace/logs/service_monitor.log
else
    echo "No monitor log found"
fi