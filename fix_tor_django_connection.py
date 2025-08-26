#!/usr/bin/env python3
"""
Script to test and fix Tor-Django connection issues
"""

import subprocess
import time
import os
import sys

def run_command(cmd):
    """Run a command and return the result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def test_django_response(host_header):
    """Test Django response with specific host header"""
    cmd = f'curl -s -H "Host: {host_header}" http://127.0.0.1:8000/'
    success, stdout, stderr = run_command(cmd)
    
    if success and "<!DOCTYPE html>" in stdout:
        print(f"✅ Django responds to Host: {host_header}")
        return True
    else:
        print(f"❌ Django not responding to Host: {host_header}")
        if stderr:
            print(f"   Error: {stderr}")
        return False

def check_static_files():
    """Check if static files are being served"""
    cmd = 'curl -s -H "Host: p4y5gtlfyq4ftfpxqo6mamtcmquo6azvpwlnrj7jxkn743jjwk3ya5id.onion" http://127.0.0.1:8000/static/admin/css/base.css | head -1'
    success, stdout, stderr = run_command(cmd)
    
    if success and ("body" in stdout or "css" in stdout.lower()):
        print("✅ Static files are being served")
        return True
    else:
        print("❌ Static files not being served properly")
        return False

def main():
    print("🔍 Tor-Django Connection Diagnostic")
    print("==================================")
    
    # Test with different host headers
    onion_address = "p4y5gtlfyq4ftfpxqo6mamtcmquo6azvpwlnrj7jxkn743jjwk3ya5id.onion"
    
    hosts_to_test = [
        "localhost",
        "127.0.0.1",
        onion_address
    ]
    
    print("\n📊 Testing Django responses:")
    all_good = True
    for host in hosts_to_test:
        if not test_django_response(host):
            all_good = False
    
    print(f"\n🔧 Testing static files:")
    static_ok = check_static_files()
    
    print(f"\n📋 DIAGNOSIS:")
    print(f"   Django Core: {'✅ Working' if all_good else '❌ Issues'}")
    print(f"   Static Files: {'✅ Working' if static_ok else '❌ Issues'}")
    
    if all_good and static_ok:
        print(f"\n🎉 EVERYTHING LOOKS GOOD!")
        print(f"   Your marketplace should be accessible at:")
        print(f"   http://{onion_address}/")
        
        print(f"\n💡 If Tor Browser shows issues:")
        print(f"   1. Clear Tor Browser cache")
        print(f"   2. Try a new Tor circuit (Ctrl+Shift+L)")
        print(f"   3. Wait 2-3 minutes for Tor network propagation")
        print(f"   4. Ensure you're using the exact address: {onion_address}")
    else:
        print(f"\n🔧 FIXES NEEDED:")
        if not all_good:
            print(f"   - Django configuration issues detected")
        if not static_ok:
            print(f"   - Static files not serving properly")
    
    # Additional Tor-specific checks
    print(f"\n🧅 Tor Service Status:")
    success, stdout, stderr = run_command("ps aux | grep 'tor -f' | grep -v grep")
    if success and stdout.strip():
        print(f"   ✅ Tor process running")
    else:
        print(f"   ❌ Tor process not found")
    
    # Check onion address
    success, stdout, stderr = run_command("sudo cat /var/lib/tor/marketplace/hostname")
    if success and stdout.strip():
        current_onion = stdout.strip()
        print(f"   ✅ Onion address: {current_onion}")
        if current_onion != onion_address:
            print(f"   ⚠️  WARNING: Address mismatch!")
            print(f"      Expected: {onion_address}")
            print(f"      Current:  {current_onion}")
    else:
        print(f"   ❌ Cannot read onion address")

if __name__ == "__main__":
    main()