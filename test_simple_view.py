#!/usr/bin/env python3
"""
Test Simple View
"""

import requests

def test_simple_view():
    """Test if the view is working at all"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Simple View")
    print("=" * 30)
    
    # Test 1: GET request to challenge page
    print("\n🛡️ Test 1: GET Challenge Page")
    response = requests.get(f"{base_url}/security/challenge/")
    print(f"   Status: {response.status_code}")
    print(f"   Content length: {len(response.text)}")
    print(f"   Contains 'Security Challenge': {'Security Challenge' in response.text}")
    
    # Test 2: POST request with minimal data
    print("\n✅ Test 2: POST Challenge")
    form_data = {
        'challenge_answer': '4',
        'challenge_id': 'test',
        'timestamp': '123'
    }
    
    response = requests.post(f"{base_url}/security/challenge/", data=form_data)
    print(f"   Status: {response.status_code}")
    print(f"   Content length: {len(response.text)}")
    print(f"   Contains 'Security Challenge': {'Security Challenge' in response.text}")
    
    # Test 3: Check if we can access the main page
    print("\n🏠 Test 3: Access Main Page")
    response = requests.get(f"{base_url}/")
    print(f"   Status: {response.status_code}")
    print(f"   Contains 'Security Challenge': {'Security Challenge' in response.text}")

if __name__ == "__main__":
    test_simple_view()