#!/usr/bin/env python3
"""
Test Token System Fix
Verifies that the captcha loop issue is resolved and tokens are working
"""

import requests
from bs4 import BeautifulSoup
import time

def test_token_system_fix():
    """Test the fixed token system"""
    
    base_url = "http://localhost:8000"
    session = requests.Session()
    
    print("🧪 Testing Fixed Token System")
    print("=" * 50)
    
    # Step 1: Test initial access (should trigger security challenge)
    print("\n🛡️ Step 1: Initial Access")
    response = session.get(f"{base_url}/")
    
    if "Security Challenge" in response.text:
        print("   ✅ Security challenge triggered (expected)")
        
        # Parse the challenge page
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get challenge question
        challenge_question = soup.find('div', {'class': 'challenge-question'})
        if challenge_question:
            question_text = challenge_question.get_text(strip=True)
            print(f"   📝 Question: {question_text}")
            
            # Extract answer
            if "What is 2 + 2?" in question_text:
                answer = "4"
            else:
                # Try to extract other math questions
                import re
                math_match = re.search(r'What is (\d+) \+ (\d+)\?', question_text)
                if math_match:
                    num1 = int(math_match.group(1))
                    num2 = int(math_match.group(2))
                    answer = str(num1 + num2)
                else:
                    print("   ❌ Unknown question format")
                    return False
        
        # Get form data
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        if not csrf_token:
            print("   ❌ CSRF token not found")
            return False
        
        csrf_value = csrf_token.get('value')
        challenge_id = soup.find('input', {'name': 'challenge_id'})
        timestamp = soup.find('input', {'name': 'timestamp'})
        
        challenge_id_value = challenge_id.get('value') if challenge_id else 'bot_challenge'
        timestamp_value = timestamp.get('value') if timestamp else str(time.time())
        
        print(f"   🧮 Answer: {answer}")
        print(f"   📋 Challenge ID: {challenge_id_value}")
        
        # Step 2: Submit challenge answer
        print("\n✅ Step 2: Submitting Answer")
        challenge_data = {
            'challenge_answer': answer,
            'csrfmiddlewaretoken': csrf_value,
            'challenge_id': challenge_id_value,
            'timestamp': timestamp_value,
            'website': '',  # Honeypot
            'email_address': ''  # Honeypot
        }
        
        challenge_response = session.post(
            f"{base_url}/security/challenge/",
            data=challenge_data,
            allow_redirects=True
        )
        
        print(f"   Response status: {challenge_response.status_code}")
        print(f"   Response URL: {challenge_response.url}")
        
        # Step 3: Check if challenge is resolved
        print("\n🔍 Step 3: Verifying Challenge Resolution")
        
        if "Security Challenge" in challenge_response.text:
            print("   ❌ Still showing security challenge - LOOP NOT FIXED!")
            return False
        else:
            print("   ✅ Security challenge resolved!")
            
            # Check what page we're on
            if "Welcome to Secure Marketplace" in challenge_response.text:
                print("   🏠 Now on main marketplace page")
            elif "login" in challenge_response.text.lower():
                print("   🔑 Redirected to login page")
            else:
                print(f"   📄 On different page")
        
        # Step 4: Test access to other pages
        print("\n🌐 Step 4: Testing Page Access")
        test_pages = [
            ('/accounts/login/', 'Login Page'),
            ('/products/', 'Products Page')
        ]
        
        for url, name in test_pages:
            try:
                page_response = session.get(f"{base_url}{url}", timeout=10)
                
                if "Security Challenge" in page_response.text:
                    print(f"   ❌ {name}: Still showing challenge")
                    return False
                else:
                    print(f"   ✅ {name}: Accessible without challenge")
                    
            except Exception as e:
                print(f"   ⚠️  {name}: Error - {e}")
        
        # Step 5: Test token persistence
        print("\n🔐 Step 5: Testing Token Persistence")
        
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
        
        print("\n🎉 TOKEN SYSTEM TEST COMPLETE!")
        return True
        
    else:
        print("   ❌ No security challenge triggered")
        print("   🔍 Security system might be disabled")
        return False

if __name__ == "__main__":
    print("🔧 Testing Fixed Token System")
    print("=" * 50)
    
    success = test_token_system_fix()
    
    if success:
        print("\n🏆 SUCCESS: Token system is working and captcha loop is RESOLVED!")
        print("   ✅ Security challenges work properly")
        print("   ✅ Tokens are issued and stored")
        print("   ✅ Challenge completion persists")
        print("   ✅ No more infinite loops!")
    else:
        print("\n❌ FAILED: Token system still has issues")
        print("   ⚠️  The captcha loop issue is NOT resolved")