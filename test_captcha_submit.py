#!/usr/bin/env python
"""
Test submitting a registration form with correct captcha coordinates
"""
import os
import sys
import django
import requests
from bs4 import BeautifulSoup

# Setup Django
sys.path.insert(0, '/workspace')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marketplace.settings')
django.setup()

# Create a session
session = requests.Session()

# Get the registration page
print("Getting registration page...")
response = session.get('http://localhost:8000/accounts/register/')

# Parse the HTML
soup = BeautifulSoup(response.text, 'html.parser')

# Get form data
csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
captcha_token = soup.find('input', {'name': 'captcha_token'})['value']
form_timestamp = soup.find('input', {'name': 'form_timestamp'})['value']
form_hash = soup.find('input', {'name': 'form_hash'})['value']

print(f"CSRF Token: {csrf_token}")
print(f"Captcha Token: {captcha_token}")

# Get the captcha solution from session
from django.contrib.sessions.backends.cache import SessionStore
session_key = session.cookies.get('sessionid')
store = SessionStore(session_key=session_key)
captcha_data = store.get(f'captcha_{captcha_token}')

if captcha_data:
    print(f"\nCaptcha solution: x={captcha_data['x']}, y={captcha_data['y']}, r={captcha_data['r']}")
    
    # Prepare form data
    form_data = {
        'csrfmiddlewaretoken': csrf_token,
        'username': 'testuser123',
        'email': 'test@example.com',
        'password1': 'ComplexPass123!',
        'password2': 'ComplexPass123!',
        'terms_accepted': 'on',
        
        # Captcha data - simulating an image input click
        'captcha.x': str(captcha_data['x']),  # Click at exact center
        'captcha.y': str(captcha_data['y']),
        'captcha_token': captcha_token,
        
        # Hidden fields
        'form_timestamp': form_timestamp,
        'form_hash': form_hash,
        'website': '',  # Honeypot - should be empty
        'email_address': '',  # Honeypot - should be empty
    }
    
    print("\nSubmitting registration with captcha click...")
    print(f"Click coordinates: ({captcha_data['x']}, {captcha_data['y']})")
    
    # Submit the form
    submit_response = session.post('http://localhost:8000/accounts/register/', data=form_data)
    
    print(f"\nResponse status: {submit_response.status_code}")
    
    # Check for errors
    if submit_response.status_code == 200:
        # Parse response to check for errors
        result_soup = BeautifulSoup(submit_response.text, 'html.parser')
        
        # Check for error messages
        errors = result_soup.find_all(class_='alert-danger')
        if errors:
            print("\nErrors found:")
            for error in errors:
                print(f"  - {error.get_text().strip()}")
        
        # Check for field errors
        field_errors = result_soup.find_all(class_='text-danger')
        if field_errors:
            print("\nField errors:")
            for error in field_errors:
                print(f"  - {error.get_text().strip()}")
        
        # Check if redirected (success)
        if 'login' in submit_response.url:
            print("\nSuccess! Registration completed and redirected to login page.")
        else:
            print(f"\nStill on registration page. URL: {submit_response.url}")
            
            # Check for success messages
            messages = result_soup.find_all(class_='alert-success')
            for msg in messages:
                print(f"Success: {msg.get_text().strip()}")
    
else:
    print("No captcha data found in session!")