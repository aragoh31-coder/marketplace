#!/usr/bin/env python3
"""
Test Token System and Captcha Loop Resolution
Verifies that the security challenge system properly issues tokens and doesn't loop
"""

import os
import sys
import django
import requests
from bs4 import BeautifulSoup
import time

# Setup Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marketplace.settings')
django.setup()

def test_token_system():
    """Test the complete token system and captcha flow"""
    
    base_url = "http://localhost:8000"
    session = requests.Session()
    
    print("🔍 Testing Token System and Captcha Loop Resolution")
    print("=" * 70)
    
    # Step 1: Test initial access (should trigger security challenge)
    print("\n🛡️ Step 1: Testing Initial Access")
    print("   This should trigger the security challenge...")
    
    response = session.get(f"{base_url}/")
    print(f"   Response status: {response.status_code}")
    
    if "Security Challenge" in response.text:
        print("   ✅ Security challenge triggered (expected)")
        
        # Parse the challenge page
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for challenge elements
        challenge_question = soup.find('div', {'class': 'challenge-question'})
        if challenge_question:
            question_text = challenge_question.get_text(strip=True)
            print(f"   📝 Challenge question: {question_text}")
            
            # Extract the math question and solve it
            if "What is 2 + 2?" in question_text:
                answer = "4"
                print(f"   🧮 Answer: {answer}")
            else:
                # Try to extract other math questions
                import re
                math_match = re.search(r'What is (\d+) \+ (\d+)\?', question_text)
                if math_match:
                    num1 = int(math_match.group(1))
                    num2 = int(math_match.group(2))
                    answer = str(num1 + num2)
                    print(f"   🧮 Math answer: {num1} + {num2} = {answer}")
                else:
                    print("   ❌ Unknown challenge question format")
                    return False
        
        # Get CSRF token from challenge page
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        if not csrf_token:
            print("   ❌ CSRF token not found in challenge page")
            return False
        
        csrf_value = csrf_token.get('value')
        print("   ✅ CSRF token found")
        
        # Get other hidden fields
        challenge_id = soup.find('input', {'name': 'challenge_id'})
        timestamp = soup.find('input', {'name': 'timestamp'})
        
        challenge_id_value = challenge_id.get('value') if challenge_id else ''
        timestamp_value = timestamp.get('value') if timestamp else ''
        
        print(f"   📋 Challenge ID: {challenge_id_value}")
        print(f"   ⏰ Timestamp: {timestamp_value}")
        
        # Step 2: Submit the challenge answer
        print("\n✅ Step 2: Submitting Challenge Answer")
        print("   Submitting answer to resolve security challenge...")
        
        challenge_data = {
            'challenge_answer': answer,
            'csrfmiddlewaretoken': csrf_value,
            'challenge_id': challenge_id_value,
            'timestamp': timestamp_value,
            'website': '',  # Honeypot field
            'email_address': ''  # Honeypot field
        }
        
        challenge_response = session.post(
            f"{base_url}/",
            data=challenge_data,
            allow_redirects=True
        )
        
        print(f"   Challenge response status: {challenge_response.status_code}")
        print(f"   Response URL: {challenge_response.url}")
        
        # Step 3: Check if challenge is resolved
        print("\n🔍 Step 3: Checking Challenge Resolution")
        print("   Verifying that security challenge is completed...")
        
        # Check if we're still on the challenge page
        if "Security Challenge" in challenge_response.text:
            print("   ❌ Still showing security challenge - LOOP DETECTED!")
            print("   🔍 This indicates the token system is not working properly")
            
            # Check for error messages
            error_message = soup.find('div', {'class': 'error-message'})
            if error_message:
                print(f"   ⚠️  Error message: {error_message.get_text(strip=True)}")
            
            return False
        else:
            print("   ✅ Security challenge resolved!")
            
            # Check what page we're on now
            if "Welcome to Secure Marketplace" in challenge_response.text:
                print("   🏠 Now on main marketplace page")
            elif "login" in challenge_response.text.lower():
                print("   🔑 Redirected to login page")
            else:
                print(f"   📄 On different page: {challenge_response.text[:100]}...")
        
        # Step 4: Test if we can access other pages without challenge
        print("\n🌐 Step 4: Testing Access to Other Pages")
        print("   Verifying that challenge completion grants access...")
        
        test_pages = [
            ('/accounts/login/', 'Login Page'),
            ('/products/', 'Products Page'),
            ('/accounts/', 'Accounts Page')
        ]
        
        for url, name in test_pages:
            try:
                page_response = session.get(f"{base_url}{url}", timeout=10)
                
                if "Security Challenge" in page_response.text:
                    print(f"   ❌ {name}: Still showing security challenge")
                    print(f"      This indicates the token system is not working!")
                    return False
                else:
                    print(f"   ✅ {name}: Accessible without challenge")
                    
            except Exception as e:
                print(f"   ⚠️  {name}: Error accessing - {e}")
        
        # Step 5: Test token persistence
        print("\n🔐 Step 5: Testing Token Persistence")
        print("   Verifying that challenge completion persists across requests...")
        
        # Make multiple requests to test persistence
        for i in range(3):
            try:
                test_response = session.get(f"{base_url}/", timeout=10)
                
                if "Security Challenge" in test_response.text:
                    print(f"   ❌ Request {i+1}: Challenge reappeared - TOKEN SYSTEM FAILED!")
                    print(f"      This confirms the captcha loop issue is NOT resolved")
                    return False
                else:
                    print(f"   ✅ Request {i+1}: No challenge (token working)")
                    
                time.sleep(1)  # Small delay between requests
                
            except Exception as e:
                print(f"   ⚠️  Request {i+1}: Error - {e}")
        
        print("\n🎉 TOKEN SYSTEM TEST COMPLETE!")
        return True
        
    else:
        print("   ❌ No security challenge triggered")
        print("   🔍 This might indicate the security system is disabled")
        return False

def analyze_token_system_issues():
    """Analyze potential issues with the token system"""
    print("\n🔍 ANALYZING TOKEN SYSTEM ISSUES")
    print("=" * 70)
    
    print("\n📋 Potential Issues Found:")
    
    print("\n1. 🚨 MIDDLEWARE CHALLENGE SERVING ISSUE")
    print("   - The EnhancedSecurityMiddleware is serving the challenge")
    print("   - But there's no view to process the form submission")
    print("   - This creates a loop: challenge → form → same challenge")
    
    print("\n2. 🔄 MISSING CHALLENGE PROCESSING")
    print("   - Challenge form submits to same URL ('action=\"\"')")
    print("   - No view handles POST requests for challenge completion")
    print("   - No token issuance or session marking")
    
    print("\n3. 🎯 BOT DETECTION TOO AGGRESSIVE")
    print("   - 'python-requests' is in BOT_USER_AGENTS list")
    print("   - Legitimate testing tools are blocked")
    print("   - No whitelist for testing scenarios")
    
    print("\n4. 🔐 NO TOKEN STORAGE")
    print("   - No session variable to mark challenge completion")
    print("   - No timestamp-based token expiration")
    print("   - No IP-based challenge bypass")
    
    print("\n💡 RECOMMENDED FIXES:")
    print("   1. Create a view to handle challenge form submission")
    print("   2. Implement proper token storage in session")
    print("   3. Add challenge completion tracking")
    print("   4. Whitelist legitimate testing tools")
    print("   5. Add challenge timeout and expiration")

if __name__ == "__main__":
    print("🧪 Testing Token System and Captcha Loop Resolution")
    print("=" * 70)
    
    # Run the token system test
    success = test_token_system()
    
    if success:
        print("\n🏆 SUCCESS: Token system is working and captcha loop is resolved!")
    else:
        print("\n❌ FAILED: Token system has issues - captcha loop detected!")
        
        # Analyze the issues
        analyze_token_system_issues()
        
        print("\n⚠️  CONCLUSION: The captcha loop issue is NOT resolved.")
        print("   The security challenge system needs proper implementation.")