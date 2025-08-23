#!/usr/bin/env python3
"""
Test Challenge Storage
"""

import requests
from bs4 import BeautifulSoup

def test_challenge_storage():
    """Test if challenge completion is being stored correctly"""
    
    base_url = "http://localhost:8000"
    session = requests.Session()
    
    print("🧪 Testing Challenge Storage")
    print("=" * 40)
    
    # Step 1: Get the challenge page
    print("\n🛡️ Step 1: Get Challenge Page")
    response = session.get(f"{base_url}/security/challenge/")
    print(f"   Status: {response.status_code}")
    
    if "Security Challenge" in response.text:
        print("   ✅ Challenge page loaded")
        
        # Parse the page
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get form data
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        if csrf_token:
            csrf_value = csrf_token.get('value')
            print(f"   🔑 CSRF token: {csrf_value[:10]}...")
            
            # Step 2: Submit the challenge
            print("\n✅ Step 2: Submit Challenge")
            form_data = {
                'challenge_answer': '4',
                'csrfmiddlewaretoken': csrf_value,
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
            else:
                print("   ✅ Challenge resolved!")
                
                # Step 3: Test if we can access the main page
                print("\n🏠 Step 3: Test Main Page Access")
                main_response = session.get(f"{base_url}/")
                print(f"   Main page status: {main_response.status_code}")
                
                if "Security Challenge" in main_response.text:
                    print("   ❌ Main page still showing challenge")
                else:
                    print("   ✅ Main page accessible!")
                    
        else:
            print("   ❌ CSRF token not found")
    else:
        print("   ❌ Challenge page not loaded")

if __name__ == "__main__":
    test_challenge_storage()