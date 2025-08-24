#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.insert(0, '/workspace')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marketplace.settings')
django.setup()

from django.test import Client
from django.contrib.sessions.models import Session
from django.core.cache import cache

# Create a test client
client = Client()

# Try to access the registration page
print("Testing registration page...")
response = client.get('/accounts/register/')
print(f"Status code: {response.status_code}")

# Check if session was created
if hasattr(client, 'session') and client.session:
    print(f"Session ID: {client.session.session_key}")
    print(f"Session data: {dict(client.session)}")
    
    # Check for math challenge in session
    if 'math_answer' in client.session:
        print(f"Math answer in session: {client.session['math_answer']}")
    else:
        print("No math answer in session!")
        
    if 'captcha_generated' in client.session:
        print(f"Captcha generated at: {client.session['captcha_generated']}")
    else:
        print("No captcha timestamp in session!")
else:
    print("No session created!")

# Check Redis connection
print("\nTesting Redis connection...")
try:
    cache.set('test_key', 'test_value', 60)
    value = cache.get('test_key')
    print(f"Redis test: {value}")
    cache.delete('test_key')
except Exception as e:
    print(f"Redis error: {e}")

# Try to check session cache
print("\nChecking session cache...")
from django.core.cache import caches
session_cache = caches['session']
try:
    session_cache.set('test_session', 'test', 60)
    value = session_cache.get('test_session')
    print(f"Session cache test: {value}")
    session_cache.delete('test_session')
except Exception as e:
    print(f"Session cache error: {e}")