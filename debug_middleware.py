#!/usr/bin/env python3
"""
Debug Middleware and Form Submission
"""

import requests
from bs4 import BeautifulSoup

def debug_middleware():
    """Debug the middleware behavior"""
    
    base_url = "http://localhost:8000"
    session = requests.Session()
    
    print("🔍 Debugging Middleware and Form Submission")
    print("=" * 60)
    
    # Step 1: Get the challenge page
    print("\n🛡️ Step 1: Getting Challenge Page")
    response = session.get(f"{base_url}/")
    
    if "Security Challenge" in response.text:
        print("   ✅ Security challenge triggered")
        
        # Parse the page
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check the form action
        form = soup.find('form')
        if form:
            action = form.get('action', '')
            method = form.get('method', 'GET')
            print(f"   📝 Form action: '{action}'")
            print(f"   📝 Form method: '{method}'")
            
            # Check if there are multiple forms
            forms = soup.find_all('form')
            print(f"   📝 Number of forms: {len(forms)}")
            
            for i, f in enumerate(forms):
                print(f"   📝 Form {i+1}: action='{f.get('action', '')}' method='{f.get('method', 'GET')}'")
        
        # Check for challenge answer in the page
        challenge_question = soup.find('div', {'class': 'challenge-question'})
        if challenge_question:
            question_text = challenge_question.get_text(strip=True)
            print(f"   📝 Challenge question: {question_text}")
        
        # Check for error messages
        error_message = soup.find('div', {'class': 'error-message'})
        if error_message:
            print(f"   ⚠️  Error message: {error_message.get_text(strip=True)}")
        
        # Step 2: Submit the form
        print("\n✅ Step 2: Submitting Form")
        
        # Get form data
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        if csrf_token:
            csrf_value = csrf_token.get('value')
            print(f"   🔑 CSRF token: {csrf_value[:10]}...")
            
            # Submit the form
            form_data = {
                'challenge_answer': '4',
                'csrfmiddlewaretoken': csrf_value,
                'challenge_id': 'bot_challenge',
                'timestamp': '1234567890',
                'website': '',
                'email_address': ''
            }
            
            print(f"   📤 Submitting to: {base_url}/")
            print(f"   📤 Form data: {form_data}")
            
            submit_response = session.post(f"{base_url}/", data=form_data, allow_redirects=False)
            
            print(f"   📥 Response status: {submit_response.status_code}")
            print(f"   📥 Response headers: {dict(submit_response.headers)}")
            print(f"   📥 Response URL: {submit_response.url}")
            
            # Check response content
            if "Security Challenge" in submit_response.text:
                print("   ❌ Still showing security challenge")
                
                # Parse the response to see what's happening
                response_soup = BeautifulSoup(submit_response.text, 'html.parser')
                response_form = response_soup.find('form')
                if response_form:
                    print(f"   📝 Response form action: '{response_form.get('action', '')}'")
                
                # Check for any error messages
                response_error = response_soup.find('div', {'class': 'error-message'})
                if response_error:
                    print(f"   ⚠️  Response error: {response_error.get_text(strip=True)}")
            else:
                print("   ✅ Challenge resolved!")
                
        else:
            print("   ❌ CSRF token not found")
    else:
        print("   ❌ No security challenge triggered")

if __name__ == "__main__":
    debug_middleware()