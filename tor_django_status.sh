#!/bin/bash

echo "🔍 TOR & DJANGO STATUS CHECK"
echo "============================"

# Check Tor process
echo ""
echo "📡 TOR STATUS:"
TOR_PID=$(ps aux | grep "tor -f" | grep -v grep | awk '{print $2}' | head -1)
if [ ! -z "$TOR_PID" ]; then
    echo "   ✅ Tor Process: Running (PID: $TOR_PID)"
else
    echo "   ❌ Tor Process: NOT RUNNING"
fi

# Check onion address
echo ""
echo "🧅 ONION SERVICE:"
if sudo cat /var/lib/tor/marketplace/hostname 2>/dev/null; then
    ONION_ADDR=$(sudo cat /var/lib/tor/marketplace/hostname 2>/dev/null)
    echo "   ✅ Onion Address: $ONION_ADDR"
else
    echo "   ❌ Onion Address: NOT GENERATED"
fi

# Check Django
echo ""
echo "🐍 DJANGO STATUS:"
GUNICORN_COUNT=$(ps aux | grep "gunicorn.*marketplace" | grep -v grep | wc -l)
if [ $GUNICORN_COUNT -gt 0 ]; then
    echo "   ✅ Django/Gunicorn: Running ($GUNICORN_COUNT processes)"
else
    echo "   ❌ Django/Gunicorn: NOT RUNNING"
fi

# Check port 8000
echo ""
echo "🔌 PORT CHECK:"
if ss -tlnp | grep ":8000" > /dev/null; then
    echo "   ✅ Port 8000: Django listening"
else
    echo "   ❌ Port 8000: Nothing listening"
fi

# Test Django locally
echo ""
echo "🧪 LOCAL DJANGO TEST:"
if timeout 5 curl -s http://127.0.0.1:8000/ | grep -q "DOCTYPE"; then
    echo "   ✅ Django Response: Working"
else
    echo "   ❌ Django Response: Failed"
fi

# Test Tor SOCKS
echo ""
echo "🌐 TOR SOCKS TEST:"
if nc -z 127.0.0.1 9050 2>/dev/null; then
    echo "   ✅ SOCKS Port 9050: Available"
else
    echo "   ❌ SOCKS Port 9050: Not accessible"
fi

# Test onion service
echo ""
echo "🔗 ONION SERVICE TEST:"
if [ ! -z "$ONION_ADDR" ]; then
    echo "   Testing: $ONION_ADDR"
    if timeout 15 curl -x socks5h://127.0.0.1:9050 -s "http://$ONION_ADDR/" | grep -q "DOCTYPE"; then
        echo "   ✅ Onion Service: WORKING! 🎉"
    else
        echo "   ⚠️  Onion Service: Slow or not ready (may need more time)"
    fi
else
    echo "   ❌ Cannot test - no onion address"
fi

echo ""
echo "📋 SUMMARY:"
echo "==========="
if [ ! -z "$TOR_PID" ] && [ $GUNICORN_COUNT -gt 0 ]; then
    echo "🚀 Both Tor and Django are running!"
    echo "🌐 Your marketplace should be accessible at:"
    echo "   http://$ONION_ADDR/"
    echo ""
    echo "💡 If still not loading in Tor Browser:"
    echo "   1. Wait 2-3 minutes for network propagation"
    echo "   2. Try a new Tor circuit (Ctrl+Shift+L)"
    echo "   3. Clear Tor Browser cache"
    echo "   4. Check your internet connection"
else
    echo "❌ One or more services need attention"
fi