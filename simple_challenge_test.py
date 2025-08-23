#!/usr/bin/env python3
"""
Simple Challenge Test
"""

import requests
from bs4 import BeautifulSoup

def test_challenge_step_by_step():
    """Test the challenge step by step"""
    
    base_url = "http://localhost:8000"
    session = requests.Session()
    
    print("🧪 Simple Challenge Test")
    print("=" * 40)
    
    # Step 1: Get the challenge page
    print("\n🛡️ Step 1: Get Challenge Page")
    response = session.get(f"{base_url}/security/challenge/")
    print(f"   Status: {response.status_code}")
    print(f"   URL: {response.url}")
    
    if "Security Challenge" in response.text:
        print("   ✅ Challenge page loaded")
        
        # Parse the page
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get form data
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        if csrf_token:
            csrf_value = csrf_token.get('value')
            print(f"   🔑 CSRF token: {csrf_value[:10]}...")
            
            # Check session data
            print(f"   🍪 Session ID: {session.cookies.get('sessionid', 'None')}")
            
            # Step 2: Submit the challenge
            print("\n✅ Step 2: Submit Challenge")
            form_data = {
                'challenge_answer': '4',
                'challenge_id': 'bot_challenge',
                'timestamp': '1234567890',
                'website': '',
                'email_address': ''
            }
            
            print(f"   📤 Submitting: {form_data}")
            submit_response = session.post(f"{base_url}/security/challenge/", data=form_data)
            
            print(f"   📥 Response status: {submit_response.status_code}")
            print(f"   📥 Response URL: {submit_response.url}")
            
            # Check if challenge was resolved
            if "Security Challenge" in submit_response.text:
                print("   ❌ Still showing challenge")
                
                # Check for error messages
                response_soup = BeautifulSoup(submit_response.text, 'html.parser')
                error_msg = response_soup.find('div', {'class': 'error-message'})
                if error_msg:
                    print(f"   ⚠️  Error: {error_msg.get_text(strip=True)}")
                else:
                    print("   🔍 No error message found")
                    
                # Check if we're still on challenge page
                if "/security/challenge/" in submit_response.url:
                    print("   📍 Still on challenge page")
                else:
                    print(f"   📍 Redirected to: {submit_response.url}")
            else:
                print("   ✅ Challenge resolved!")
                
                # Check where we are now
                if "Welcome to Secure Marketplace" in submit_response.text:
                    print("   🏠 Now on main page")
                elif "login" in submit_response.text.lower():
                    print("   🔑 Now on login page")
                else:
                    print(f"   📄 On different page: {submit_response.text[:100]}...")
        else:
            print("   ❌ CSRF token not found")
    else:
        print("   ❌ Challenge page not loaded")
        print(f"   📄 Content: {response.text[:200]}...")

if __name__ == "__main__":
    test_challenge_step_by_step()