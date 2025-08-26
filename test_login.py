#!/usr/bin/env python3
"""
Test script to verify login functionality works
"""

import requests
import re

def test_login():
    base_url = "http://127.0.0.1:8000"
    headers = {
        'Host': 'p4y5gtlfyq4ftfpxqo6mamtcmquo6azvpwlnrj7jxkn743jjwk3ya5id.onion',
        'User-Agent': 'curl/8.12.1'  # Whitelisted user agent
    }
    
    session = requests.Session()
    session.headers.update(headers)
    
    print("🔍 Testing Login Process...")
    
    try:
        # Get login page
        print("1. Getting login page...")
        login_page = session.get(f"{base_url}/accounts/login/")
        print(f"   Status: {login_page.status_code}")
        
        if login_page.status_code != 200:
            print(f"❌ Failed to get login page")
            return False
        
        # Extract CSRF token
        csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', login_page.text)
        if not csrf_match:
            print("❌ Could not find CSRF token")
            return False
        
        csrf_token = csrf_match.group(1)
        print(f"   ✅ CSRF token found")
        
        # Attempt login
        print("2. Attempting login...")
        login_data = {
            'username': 'admin',
            'password': 'admin123',
            'csrfmiddlewaretoken': csrf_token
        }
        
        login_response = session.post(f"{base_url}/accounts/login/", data=login_data)
        print(f"   Status: {login_response.status_code}")
        
        # Check if login was successful (should redirect or show dashboard)
        if login_response.status_code in [200, 302]:
            if 'login' not in login_response.url and login_response.status_code == 302:
                print("   ✅ Login successful (redirect detected)")
                return True
            elif login_response.status_code == 200 and 'dashboard' in login_response.text.lower():
                print("   ✅ Login successful (dashboard detected)")
                return True
            else:
                print("   ⚠️  Login response unclear")
                print(f"   URL: {login_response.url}")
                return False
        else:
            print(f"   ❌ Login failed with status {login_response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error during login test: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Django Login Test")
    print("===================")
    
    success = test_login()
    
    if success:
        print("\n🎉 LOGIN TEST PASSED!")
        print("✅ The 500 error after login should be fixed")
    else:
        print("\n❌ LOGIN TEST FAILED!")
        print("The 500 error may still exist")