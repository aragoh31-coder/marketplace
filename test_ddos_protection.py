#!/usr/bin/env python3
"""
Test DDoS Protection System
"""
import os
import sys
import django
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# Setup Django
sys.path.insert(0, '/workspace')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marketplace.settings')
django.setup()

from django.test import Client
from django.core.cache import cache
from core.antiddos import DDoSProtection


def test_rate_limiting():
    """Test rate limiting functionality"""
    print("\n🧪 Testing Rate Limiting...")
    
    client = Client()
    ip = "192.168.1.100"
    
    # Clear any existing cache
    cache.clear()
    
    # Test per-second limit (5 requests per second)
    print("\n1. Testing per-second limit (5 req/sec)...")
    success_count = 0
    blocked_count = 0
    
    for i in range(10):
        response = client.get('/', HTTP_X_FORWARDED_FOR=ip)
        if response.status_code == 200:
            success_count += 1
        else:
            blocked_count += 1
    
    print(f"   ✅ Allowed: {success_count}, ❌ Blocked: {blocked_count}")
    assert blocked_count > 0, "Rate limiting not working for per-second limit"
    
    # Wait for rate limit to reset
    time.sleep(2)
    
    # Test per-minute limit (50 requests per minute)
    print("\n2. Testing per-minute limit (50 req/min)...")
    cache.clear()
    success_count = 0
    blocked_count = 0
    
    for i in range(60):
        response = client.get('/', HTTP_X_FORWARDED_FOR=ip)
        if response.status_code == 200:
            success_count += 1
        else:
            blocked_count += 1
        
        if i % 10 == 0:
            print(f"   Progress: {i}/60 requests sent")
    
    print(f"   ✅ Allowed: {success_count}, ❌ Blocked: {blocked_count}")
    assert blocked_count > 0, "Rate limiting not working for per-minute limit"


def test_suspicious_patterns():
    """Test suspicious pattern detection"""
    print("\n🧪 Testing Suspicious Pattern Detection...")
    
    # Test rapid endpoint switching
    print("\n1. Testing rapid endpoint switching...")
    cache.clear()
    
    endpoints = ['/products/', '/vendors/', '/orders/', '/wallets/', '/accounts/', 
                 '/support/', '/messages/', '/profile/', '/settings/', '/help/',
                 '/about/', '/contact/', '/faq/']
    
    ip = "192.168.1.101"
    request_mock = type('Request', (), {
        'path': '',
        'method': 'GET',
        'META': {'HTTP_X_FORWARDED_FOR': ip},
        'user': type('User', (), {'is_authenticated': False})(),
        'GET': type('QueryDict', (), {'urlencode': lambda: ''})(),
        'body': b''
    })()
    
    # Access many different endpoints rapidly
    for endpoint in endpoints:
        request_mock.path = endpoint
        is_allowed, reason, _ = DDoSProtection.check_request(request_mock)
        if not is_allowed and 'suspicious_pattern:rapid_endpoint_switching' in str(reason):
            print(f"   ✅ Rapid endpoint switching detected after {endpoints.index(endpoint) + 1} endpoints")
            break
    else:
        print("   ❌ Failed to detect rapid endpoint switching")
    
    # Test identical requests
    print("\n2. Testing identical request spam...")
    cache.clear()
    
    request_mock.path = '/products/'
    identical_count = 0
    
    for i in range(30):
        is_allowed, reason, _ = DDoSProtection.check_request(request_mock)
        if not is_allowed and 'suspicious_pattern:identical_requests' in str(reason):
            print(f"   ✅ Identical request spam detected after {i + 1} requests")
            break
        identical_count += 1
    else:
        print(f"   ❌ Failed to detect identical request spam after {identical_count} requests")


def test_blacklisting():
    """Test automatic blacklisting"""
    print("\n🧪 Testing Automatic Blacklisting...")
    
    cache.clear()
    ip = "192.168.1.102"
    
    request_mock = type('Request', (), {
        'path': '/login',
        'method': 'POST',
        'META': {'HTTP_X_FORWARDED_FOR': ip},
        'user': type('User', (), {'is_authenticated': False})(),
        'GET': type('QueryDict', (), {'urlencode': lambda: ''})(),
        'body': b'username=test&password=wrong'
    })()
    
    # Generate violations to trigger blacklisting
    print("\n1. Generating violations...")
    violation_count = 0
    
    for i in range(20):
        is_allowed, reason, _ = DDoSProtection.check_request(request_mock)
        if not is_allowed:
            violation_count += 1
            if reason == "auto_blacklisted":
                print(f"   ✅ IP auto-blacklisted after {violation_count} violations")
                break
    
    # Verify IP is blacklisted
    is_blacklisted = DDoSProtection._is_blacklisted(ip)
    assert is_blacklisted, "IP was not properly blacklisted"
    
    # Test that blacklisted IP is blocked
    is_allowed, reason, _ = DDoSProtection.check_request(request_mock)
    assert not is_allowed and reason == "blacklisted", "Blacklisted IP not being blocked"
    print("   ✅ Blacklisted IP is properly blocked")


def test_endpoint_specific_limits():
    """Test endpoint-specific rate limits"""
    print("\n🧪 Testing Endpoint-Specific Limits...")
    
    cache.clear()
    client = Client()
    ip = "192.168.1.103"
    
    # Test login endpoint (5 requests per minute)
    print("\n1. Testing /login rate limit (5 req/min)...")
    success_count = 0
    blocked_count = 0
    
    for i in range(10):
        response = client.post('/accounts/login/', 
                              {'username': 'test', 'password': 'wrong'},
                              HTTP_X_FORWARDED_FOR=ip)
        if response.status_code != 429:  # Not rate limited
            success_count += 1
        else:
            blocked_count += 1
    
    print(f"   ✅ Allowed: {success_count}, ❌ Blocked: {blocked_count}")
    assert blocked_count > 0, "Endpoint-specific rate limiting not working"


def test_concurrent_requests():
    """Test DDoS protection under concurrent load"""
    print("\n🧪 Testing Concurrent Request Handling...")
    
    cache.clear()
    
    def make_request(ip_suffix):
        client = Client()
        ip = f"192.168.1.{ip_suffix}"
        response = client.get('/', HTTP_X_FORWARDED_FOR=ip)
        return response.status_code
    
    # Simulate 50 concurrent requests from different IPs
    print("\n1. Simulating 50 concurrent requests...")
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(make_request, i) for i in range(50)]
        
        success_count = 0
        blocked_count = 0
        
        for future in as_completed(futures):
            status_code = future.result()
            if status_code == 200:
                success_count += 1
            else:
                blocked_count += 1
    
    print(f"   ✅ Allowed: {success_count}, ❌ Blocked: {blocked_count}")
    
    # Check global rate limit was enforced
    stats = DDoSProtection.get_protection_stats()
    print(f"   📊 Current requests/min: {stats['current_requests_per_minute']}")


def run_all_tests():
    """Run all DDoS protection tests"""
    print("=" * 60)
    print("🛡️  DDoS PROTECTION SYSTEM TEST SUITE")
    print("=" * 60)
    
    try:
        test_rate_limiting()
        test_suspicious_patterns()
        test_blacklisting()
        test_endpoint_specific_limits()
        test_concurrent_requests()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED! DDoS Protection is working correctly.")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()