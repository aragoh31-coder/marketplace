#!/usr/bin/env python3
import os
import sys
import django
from django.core.management import execute_from_command_line

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marketplace.settings')

# Simple test to see if we can at least start
try:
    django.setup()
    print("Django setup successful!")
    
    # Try to get installed apps
    from django.conf import settings
    print(f"Installed apps: {len(settings.INSTALLED_APPS)}")
    
    # Check database
    from django.db import connection
    print(f"Database engine: {connection.settings_dict['ENGINE']}")
    
except Exception as e:
    print(f"Error during setup: {e}")
    sys.exit(1)

print("\nTrying to run server...")
execute_from_command_line(['manage.py', 'check', '--deploy'])