#!/usr/bin/env python3
"""
Test Fixed Token System
Verifies that the captcha loop issue is resolved
"""

import requests
from bs4 import BeautifulSoup
import time

def test_fixed_token_system():
    """Test the completely fixed token system"""
    
    base_url = "http://localhost:8000"
    session = requests.Session()
    
    print("🧪 Testing Fixed Token System")
    print("=" * 60)
    
    # Step 1: Test if we can access the challenge page directly
    print("\n🛡️ Step 1: Direct Challenge Access")
    response = session.get(f"{base_url}/security/challenge/")
    print(f"   Status: {response.status_code}")
    print(f"   URL: {response.url}")
    
    if "Security Challenge" in response.text:
        print("   ✅ Challenge page accessible directly")
        
        # Parse the challenge page
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get challenge question
        challenge_question = soup.find('div', {'class': 'challenge-question'})
        if challenge_question:
            question_text = challenge_question.get_text(strip=True)
            print(f"   📝 Question: {question_text}")
        
        # Get challenge token
        challenge_token = soup.find('input', {'name': 'challenge_token'})
        if challenge_token:
            token_value = challenge_token.get('value')
            print(f"   🔑 Challenge token: {token_value}")
        else:
            print("   ❌ Challenge token not found")
            return False
        
        # Get CSRF token
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        if csrf_token:
            csrf_value = csrf_token.get('value')
            print(f"   🛡️ CSRF token: {csrf_value[:10]}...")
        else:
            print("   ❌ CSRF token not found")
            return False
        
        # Step 2: Submit the challenge answer
        print("\n✅ Step 2: Submit Challenge Answer")
        form_data = {
            'challenge_answer': '4',
            'challenge_token': token_value,
            'csrfmiddlewaretoken': csrf_value,
            'website': '',
            'email_address': ''
        }
        
        print(f"   📤 Submitting: {form_data}")
        submit_response = session.post(f"{base_url}/security/challenge/", data=form_data)
        
        print(f"   📥 Response status: {submit_response.status_code}")
        print(f"   📥 Response URL: {submit_response.url}")
        
        # Check if challenge was resolved
        if "Security Challenge" in submit_response.text:
            print("   ❌ Still showing security challenge - LOOP NOT FIXED!")
            
            # Check for error messages
            response_soup = BeautifulSoup(submit_response.text, 'html.parser')
            error_msg = response_soup.find('div', {'class': 'error-message'})
            if error_msg:
                print(f"   ⚠️  Error: {error_msg.get_text(strip=True)}")
            
            return False
        else:
            print("   ✅ Security challenge resolved!")
            
            # Check what page we're on now
            if "Welcome to Secure Marketplace" in submit_response.text:
                print("   🏠 Now on main marketplace page")
            elif "login" in submit_response.text.lower():
                print("   🔑 Redirected to login page")
            else:
                print(f"   📄 On different page")
        
        # Step 3: Test access to main page
        print("\n🏠 Step 3: Test Main Page Access")
        main_response = session.get(f"{base_url}/")
        print(f"   Main page status: {main_response.status_code}")
        
        if "Security Challenge" in main_response.text:
            print("   ❌ Main page still showing challenge")
            return False
        else:
            print("   ✅ Main page accessible without challenge!")
        
        # Step 4: Test token persistence
        print("\n🔐 Step 4: Test Token Persistence")
        
        for i in range(3):
            try:
                test_response = session.get(f"{base_url}/", timeout=10)
                
                if "Security Challenge" in test_response.text:
                    print(f"   ❌ Request {i+1}: Challenge reappeared - TOKEN SYSTEM FAILED!")
                    return False
                else:
                    print(f"   ✅ Request {i+1}: No challenge (token working)")
                    
                time.sleep(1)
                
            except Exception as e:
                print(f"   ⚠️  Request {i+1}: Error - {e}")
        
        # Step 5: Test challenge status endpoint
        print("\n📊 Step 5: Test Challenge Status")
        try:
            status_response = session.get(f"{base_url}/security/challenge-status/")
            print(f"   Status endpoint: {status_response.status_code}")
            print(f"   Status content: {status_response.text[:200]}...")
        except Exception as e:
            print(f"   ⚠️  Status endpoint error: {e}")
        
        print("\n🎉 TOKEN SYSTEM TEST COMPLETE!")
        return True
        
    else:
        print("   ❌ Challenge page not accessible")
        print(f"   📄 Content: {response.text[:200]}...")
        return False

def test_session_functionality():
    """Test if sessions are working properly"""
    print("\n🔍 Testing Session Functionality")
    print("=" * 40)
    
    base_url = "http://localhost:8000"
    session = requests.Session()
    
    # Test 1: Set session variable
    print("\n📝 Test 1: Set Session Variable")
    response = session.post(f"{base_url}/security/test-session/")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text[:100]}...")
    
    # Test 2: Get session variable
    print("\n📖 Test 2: Get Session Variable")
    response = session.get(f"{base_url}/security/test-session/")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text[:100]}...")
    
    # Test 3: Check if session persists
    print("\n🔄 Test 3: Session Persistence")
    response = session.get(f"{base_url}/security/test-session/")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.text[:100]}...")

if __name__ == "__main__":
    print("🔧 Testing Fixed Token System")
    print("=" * 60)
    
    # Test session functionality first
    test_session_functionality()
    
    # Test the main token system
    success = test_fixed_token_system()
    
    if success:
        print("\n🏆 SUCCESS: Token system is working and captcha loop is RESOLVED!")
        print("   ✅ Security challenges work properly")
        print("   ✅ Tokens are issued and stored")
        print("   ✅ Challenge completion persists")
        print("   ✅ No more infinite loops!")
        print("   🎉 The captcha loop issue is FIXED!")
    else:
        print("\n❌ FAILED: Token system still has issues")
        print("   ⚠️  The captcha loop issue is NOT resolved")
        print("   🔧 Additional debugging needed")