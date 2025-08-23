#!/usr/bin/env python3
"""
Test authenticated pages with login
"""

import os
import sys
import django
import requests
from bs4 import BeautifulSoup

# Django setup
sys.path.append('/workspace')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marketplace.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

class AuthenticatedPageTester:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = 'http://localhost:8000'
        self.username = 'testuser'
        self.password = 'testpass123'
        
    def create_test_user(self):
        """Create or get test user"""
        try:
            self.user = User.objects.create_user(
                username=self.username,
                password=self.password,
                email='test@example.com'
            )
            print(f"✅ Created test user: {self.username}")
        except:
            self.user = User.objects.get(username=self.username)
            self.user.set_password(self.password)
            self.user.save()
            print(f"✅ Using existing test user: {self.username}")
    
    def login(self):
        """Login via the web interface"""
        # Get login page
        login_url = f"{self.base_url}/accounts/login/"
        response = self.session.get(login_url)
        
        if response.status_code != 200:
            print(f"❌ Failed to get login page: {response.status_code}")
            return False
        
        # Extract CSRF token
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrfmiddlewaretoken'})
        
        if not csrf_token:
            print("❌ No CSRF token found")
            return False
        
        # Login
        login_data = {
            'csrfmiddlewaretoken': csrf_token['value'],
            'username': self.username,
            'password': self.password,
        }
        
        # Check if there's a math challenge
        math_challenge = soup.find('input', {'name': 'math_challenge'})
        if math_challenge:
            # Look for the math question
            label = soup.find('label', {'for': 'id_math_challenge'})
            if label:
                question = label.text.strip()
                print(f"📐 Solving math challenge: {question}")
                
                # Extract numbers from question like "What is 5 + 3?"
                import re
                numbers = re.findall(r'\d+', question)
                if len(numbers) >= 2:
                    # Assume it's addition for now
                    answer = int(numbers[0]) + int(numbers[1])
                    login_data['math_challenge'] = str(answer)
                    print(f"   Answer: {answer}")
        
        response = self.session.post(login_url, data=login_data, allow_redirects=False)
        
        if response.status_code == 302:
            print("✅ Login successful!")
            return True
        else:
            print(f"❌ Login failed: {response.status_code}")
            return False
    
    def test_page(self, path, name):
        """Test an authenticated page"""
        url = self.base_url + path
        print(f"\n📍 Testing: {name}")
        print(f"   URL: {url}")
        
        response = self.session.get(url, allow_redirects=False)
        
        if response.status_code == 200:
            print(f"   ✅ Status: 200 OK")
            self.check_design(response.text, name)
        elif response.status_code == 302:
            print(f"   ↪️  Redirected to: {response.headers.get('Location', 'Unknown')}")
        else:
            print(f"   ❌ Status: {response.status_code}")
    
    def check_design(self, html, page_name):
        """Check design implementation"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check CSS files
        style_css = soup.find('link', {'href': '/static/css/style.css'})
        enhance_css = soup.find('link', {'href': '/static/css/enhancements.css'})
        
        if style_css and enhance_css:
            print("   ✅ CSS files loaded correctly")
        else:
            if not style_css:
                print("   ⚠️  Missing style.css")
            if not enhance_css:
                print("   ⚠️  Missing enhancements.css")
        
        # Check for JavaScript
        if '<script' in html or 'javascript:' in html:
            print("   ⚠️  JavaScript detected!")
        else:
            print("   ✅ No JavaScript found")
        
        # Check design elements
        elements = {
            'toolbar': soup.find(class_=lambda x: x and 'toolbar' in x),
            'container': soup.find(class_=lambda x: x and 'container' in x),
            'box/card': soup.find(class_=lambda x: x and ('box' in x or 'card' in x)),
            'button': soup.find(class_=lambda x: x and 'btn' in x),
        }
        
        found = [k for k, v in elements.items() if v]
        if found:
            print(f"   ✅ Design elements: {', '.join(found)}")
    
    def run_tests(self):
        """Run all tests"""
        print("🔍 Testing Authenticated Pages\n")
        print("="*60)
        
        # Create user and login
        self.create_test_user()
        
        if not self.login():
            print("\n❌ Failed to login, cannot test authenticated pages")
            return
        
        # Test authenticated pages
        pages = [
            ('/accounts/profile/', 'User Profile'),
            ('/accounts/profile/settings/', 'Profile Settings'),
            ('/wallets/', 'Wallet Dashboard'),
            ('/wallets/transactions/', 'Transaction History'),
            ('/wallets/deposit/', 'Deposit'),
            ('/wallets/withdraw/', 'Withdraw'),
            ('/orders/', 'My Orders'),
            ('/orders/cart/', 'Shopping Cart'),
            ('/messaging/', 'Messages'),
            ('/vendors/dashboard/', 'Vendor Dashboard'),
        ]
        
        for path, name in pages:
            self.test_page(path, name)
        
        print("\n" + "="*60)
        print("✅ Authenticated page testing complete!")

def main():
    tester = AuthenticatedPageTester()
    tester.run_tests()

if __name__ == "__main__":
    main()