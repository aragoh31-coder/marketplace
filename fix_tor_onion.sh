#!/bin/bash

echo "🔧 Tor Onion Service Diagnostic & Fix Script"
echo "=============================================="

# Stop all existing Tor processes
echo "🛑 Stopping existing Tor processes..."
sudo pkill -f tor
sleep 3

# Clean up and recreate Tor directories with proper permissions
echo "📁 Setting up Tor directories..."
sudo rm -rf /var/lib/tor/marketplace/
sudo mkdir -p /var/lib/tor/marketplace/
sudo chown -R debian-tor:debian-tor /var/lib/tor/
sudo chmod 700 /var/lib/tor/marketplace/

# Create a working Tor configuration
echo "⚙️ Creating optimized Tor configuration..."
cat > /tmp/torrc_working << EOF
# Working Tor configuration for hidden service
DataDirectory /var/lib/tor
SocksPort 9050
ControlPort 9051
CookieAuthentication 1

# Hidden service
HiddenServiceDir /var/lib/tor/marketplace/
HiddenServicePort 80 127.0.0.1:8000
HiddenServiceVersion 3

# Logging for debugging
Log notice stdout
Log info stdout

# Basic security
ClientOnly 1
RunAsDaemon 0
EOF

sudo cp /tmp/torrc_working /workspace/torrc_working
sudo chown debian-tor:debian-tor /workspace/torrc_working

# Start Tor with the working configuration
echo "🚀 Starting Tor with working configuration..."
sudo -u debian-tor tor -f /workspace/torrc_working &
TOR_PID=$!

echo "⏳ Waiting for Tor to bootstrap (this may take 30-60 seconds)..."
sleep 10

# Check if Tor is running
if ps -p $TOR_PID > /dev/null 2>&1; then
    echo "✅ Tor process is running (PID: $TOR_PID)"
else
    echo "❌ Tor failed to start"
    exit 1
fi

# Wait for onion service to be ready
echo "🧅 Waiting for onion service to be ready..."
for i in {1..12}; do
    if [ -f "/var/lib/tor/marketplace/hostname" ]; then
        ONION_ADDRESS=$(sudo cat /var/lib/tor/marketplace/hostname)
        if [ -n "$ONION_ADDRESS" ]; then
            echo "✅ Onion service ready: $ONION_ADDRESS"
            break
        fi
    fi
    echo "   Attempt $i/12: Waiting for onion service..."
    sleep 5
done

# Test SOCKS proxy
echo "🔍 Testing Tor SOCKS proxy..."
if timeout 10 curl -x socks5h://127.0.0.1:9050 http://check.torproject.org/ 2>/dev/null | grep -q "Congratulations"; then
    echo "✅ Tor SOCKS proxy is working"
else
    echo "⚠️ Tor SOCKS proxy test failed (this might be normal initially)"
fi

# Test Django accessibility
echo "🌐 Testing Django application..."
if curl -H "Host: localhost" http://127.0.0.1:8000/ 2>/dev/null | head -1 | grep -q "DOCTYPE"; then
    echo "✅ Django is responding on port 8000"
else
    echo "❌ Django is not responding on port 8000"
fi

# Final status
echo ""
echo "📊 FINAL STATUS:"
echo "================"

if [ -f "/var/lib/tor/marketplace/hostname" ]; then
    FINAL_ONION=$(sudo cat /var/lib/tor/marketplace/hostname)
    echo "🧅 Onion Address: $FINAL_ONION"
    echo "🌐 Access URL: http://$FINAL_ONION/"
    echo "👤 Admin Panel: http://$FINAL_ONION/admin/"
    echo ""
    echo "✅ Setup complete! Your onion service should now be accessible."
    echo "⏳ Note: It may take a few minutes for the onion service to be fully propagated in the Tor network."
    echo "🔄 If it still doesn't work, wait 5-10 minutes and try again."
else
    echo "❌ Onion service setup failed"
    exit 1
fi

echo ""
echo "🛠️ Troubleshooting commands:"
echo "ps aux | grep tor | grep -v grep"
echo "sudo cat /var/lib/tor/marketplace/hostname"
echo "curl -x socks5h://127.0.0.1:9050 http://check.torproject.org/"