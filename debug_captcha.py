#!/usr/bin/env python
"""
Debug script to test the One-Click CAPTCHA functionality
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

# Create a session to maintain cookies
session = requests.Session()

# Step 1: Get the registration page
print("Step 1: Getting registration page...")
response = session.get('http://localhost:8000/accounts/register/')
print(f"Status: {response.status_code}")

# Parse the HTML
soup = BeautifulSoup(response.text, 'html.parser')

# Find the CSRF token
csrf_token = None
csrf_input = soup.find('input', {'name': 'csrfmiddlewaretoken'})
if csrf_input:
    csrf_token = csrf_input.get('value')
    print(f"CSRF Token: {csrf_token}")

# Find the captcha token
captcha_token = None
captcha_input = soup.find('input', {'name': 'captcha_token'})
if captcha_input:
    captcha_token = captcha_input.get('value')
    print(f"Captcha Token: {captcha_token}")

# Find the captcha image
captcha_img = soup.find('input', {'name': 'captcha', 'type': 'image'})
if captcha_img:
    captcha_src = captcha_img.get('src')
    print(f"Captcha Image URL: {captcha_src}")

# Step 2: Get the captcha image and save it
if captcha_src:
    img_response = session.get(f'http://localhost:8000{captcha_src}')
    with open('/workspace/test_captcha.png', 'wb') as f:
        f.write(img_response.content)
    print("Captcha image saved to test_captcha.png")

# Step 3: Check session data
print("\nChecking session data...")
from django.contrib.sessions.models import Session
from django.core.cache import caches

# Get session from cookies
session_key = session.cookies.get('sessionid')
print(f"Session ID from cookie: {session_key}")

if session_key:
    # Try to get session data from cache
    session_cache = caches['session']
    session_data = session_cache.get(f"session:{session_key}")
    print(f"Session data from cache: {session_data}")
    
    # Also check Django's session
    try:
        from django.contrib.sessions.backends.cache import SessionStore
        store = SessionStore(session_key=session_key)
        if store.exists(session_key):
            print(f"Django session data: {dict(store)}")
            
            # Look for captcha data
            for key, value in store.items():
                if 'captcha' in key:
                    print(f"  {key}: {value}")
    except Exception as e:
        print(f"Error accessing session: {e}")

print("\nInstructions:")
print("1. Open the saved test_captcha.png image")
print("2. Look for the circle with a missing slice (like Pac-Man)")
print("3. Note the approximate coordinates of that circle")
print("4. The validation expects clicks within the radius of that specific circle")