#!/usr/bin/env python3
"""Test registration with One-Click CAPTCHA"""

import requests
from bs4 import BeautifulSoup
import re

# Start a session to maintain cookies
session = requests.Session()

# Step 1: Get the registration page
print("1. Getting registration page...")
response = session.get('http://localhost:8000/accounts/register/')
print(f"   Status: {response.status_code}")

# Parse the page
soup = BeautifulSoup(response.text, 'html.parser')

# Extract CSRF token
csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})['value']
print(f"   CSRF Token: {csrf_token}")

# Extract CAPTCHA token
captcha_token_input = soup.find('input', {'name': 'captcha_token'})
captcha_token = captcha_token_input.get('value', '')
print(f"   CAPTCHA Token: {captcha_token}")

# Extract form data in the HTML
print("\n2. Form fields found:")
for input_field in soup.find_all('input'):
    name = input_field.get('name', 'unnamed')
    value = input_field.get('value', '')
    type_ = input_field.get('type', 'text')
    print(f"   - {name} ({type_}): {value[:20]}...")

# Step 2: Submit the form with test data
print("\n3. Submitting registration form...")
form_data = {
    'csrfmiddlewaretoken': csrf_token,
    'username': 'testuser123',
    'password1': 'TestPassword123!',
    'password2': 'TestPassword123!',
    'captcha.x': '50',  # Image input sends .x and .y
    'captcha.y': '50',
    'captcha_token': captcha_token,
    'captcha_x': '',
    'captcha_y': '',
}

print("   Form data:")
for key, value in form_data.items():
    print(f"   - {key}: {value}")

# Add headers to mimic browser request
headers = {
    'Referer': 'http://localhost:8000/accounts/register/',
    'Origin': 'http://localhost:8000',
}

response = session.post('http://localhost:8000/accounts/register/', data=form_data, headers=headers)
print(f"\n   Response status: {response.status_code}")

# Check for errors
soup = BeautifulSoup(response.text, 'html.parser')
errors = soup.find_all('div', class_='alert-danger')
if errors:
    print("\n   ERRORS found:")
    for error in errors:
        print(f"   - {error.get_text().strip()}")

# Check for non-field errors
non_field_errors = soup.find_all('p', class_='')
for p in non_field_errors:
    if 'Invalid CAPTCHA' in p.get_text() or 'Please click' in p.get_text():
        print(f"\n   CAPTCHA Error: {p.get_text().strip()}")

# Check if redirected to login (success)
if 'login' in response.url:
    print("\n   SUCCESS! Redirected to login page")
else:
    print(f"\n   Still on: {response.url}")
    
    # If 403, show the error
    if response.status_code == 403:
        print("\n   403 Forbidden - CSRF Error")
        if "CSRF" in response.text:
            # Extract CSRF error message
            import re
            csrf_msg = re.search(r'<p>([^<]*CSRF[^<]*)</p>', response.text)
            if csrf_msg:
                print(f"   Message: {csrf_msg.group(1)}")
    
print("\nDone!")