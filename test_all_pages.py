#!/usr/bin/env python3
"""
Comprehensive test script to verify all pages, URLs, and design implementation
"""

import os
import sys
import django
import requests
from urllib.parse import urljoin
from bs4 import BeautifulSoup

# Django setup
sys.path.append('/workspace')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marketplace.settings')
django.setup()

from django.urls import reverse
from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()

class PageTester:
    def __init__(self):
        self.client = Client()
        self.base_url = 'http://localhost:8000'
        self.results = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'design_issues': [],
            'missing_elements': [],
            'js_found': []
        }
        
        # Design elements to check for
        self.required_design_elements = [
            'toolbar',
            'box',
            'card',
            'btn',
            'form-input',
            'container'
        ]
        
        self.enhanced_elements = [
            'breadcrumb',
            'security-badge',
            'tooltip',
            'accordion',
            'progress-steps',
            'empty-state',
            'section-divider'
        ]
        
    def setup_test_user(self):
        """Create test user for authenticated pages"""
        try:
            self.user = User.objects.create_user(
                username='testuser',
                password='testpass123',
                email='test@example.com'
            )
        except:
            self.user = User.objects.get(username='testuser')
    
    def check_page(self, url, name, requires_auth=False):
        """Test individual page"""
        print(f"\n📍 Testing: {name} ({url})")
        self.results['total'] += 1
        
        try:
            if requires_auth:
                self.client.login(username='testuser', password='testpass123')
            
            response = self.client.get(url, follow=True)
            
            if response.status_code in [200, 301, 302]:
                print(f"  ✅ Status: {response.status_code}")
                self.results['success'] += 1
                
                # Check design elements
                if response.status_code == 200:
                    content = response.content.decode('utf-8')
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Check for JavaScript
                    if '<script' in content or 'javascript:' in content:
                        print(f"  ⚠️  JavaScript found!")
                        self.results['js_found'].append(name)
                    
                    # Check base template usage
                    if 'base_tor_safe.html' not in content and 'extends' in content:
                        print(f"  ⚠️  Not using base_tor_safe.html")
                        self.results['design_issues'].append(f"{name}: Not using Tor-safe base")
                    
                    # Check CSS includes
                    if not soup.find('link', {'href': '/static/css/style.css'}):
                        print(f"  ⚠️  Missing style.css")
                        self.results['missing_elements'].append(f"{name}: Missing style.css")
                    
                    if not soup.find('link', {'href': '/static/css/enhancements.css'}):
                        print(f"  ⚠️  Missing enhancements.css")
                        self.results['missing_elements'].append(f"{name}: Missing enhancements.css")
                    
                    # Check for design elements
                    design_found = []
                    for element in self.required_design_elements:
                        if soup.find(class_=lambda x: x and element in x):
                            design_found.append(element)
                    
                    if design_found:
                        print(f"  ✅ Design elements: {', '.join(design_found)}")
                    
                    # Check for enhanced elements
                    enhanced_found = []
                    for element in self.enhanced_elements:
                        if soup.find(class_=lambda x: x and element in x):
                            enhanced_found.append(element)
                    
                    if enhanced_found:
                        print(f"  ✨ Enhanced elements: {', '.join(enhanced_found)}")
                    
                    # Check for CSRF token in forms
                    forms = soup.find_all('form', method='post')
                    if forms:
                        csrf_found = any('csrf' in str(form) for form in forms)
                        if csrf_found:
                            print(f"  ✅ CSRF protection: Yes")
                        else:
                            print(f"  ❌ CSRF protection: Missing")
                            self.results['design_issues'].append(f"{name}: Missing CSRF token")
                    
                else:
                    print(f"  ℹ️  Redirected")
                    
            else:
                print(f"  ❌ Status: {response.status_code}")
                self.results['failed'] += 1
                self.results['design_issues'].append(f"{name}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            self.results['failed'] += 1
            self.results['design_issues'].append(f"{name}: {str(e)}")
    
    def test_all_pages(self):
        """Test all defined URLs"""
        print("🔍 Starting comprehensive page testing...\n")
        
        self.setup_test_user()
        
        # Public pages
        public_pages = [
            ('/', 'Home'),
            ('/accounts/login/', 'Login'),
            ('/accounts/register/', 'Register'),
            ('/products/', 'Products List'),
            ('/vendors/', 'Vendors List'),
            ('/support/', 'Support'),
            ('/support/faq/', 'FAQ'),
        ]
        
        # Authenticated pages
        auth_pages = [
            ('/accounts/profile/', 'User Profile'),
            ('/accounts/profile/settings/', 'Profile Settings'),
            ('/wallets/', 'Wallet Dashboard'),
            ('/wallets/transactions/', 'Transaction History'),
            ('/wallets/deposit/', 'Deposit'),
            ('/wallets/withdraw/', 'Withdraw'),
            ('/orders/', 'Orders'),
            ('/orders/cart/', 'Shopping Cart'),
            ('/messaging/', 'Messages'),
            ('/messaging/compose/', 'Compose Message'),
            ('/disputes/', 'Disputes'),
            ('/vendors/dashboard/', 'Vendor Dashboard'),
            ('/vendors/products/', 'Vendor Products'),
            ('/vendors/orders/', 'Vendor Orders'),
            ('/vendors/settings/', 'Vendor Settings'),
        ]
        
        # Admin pages
        admin_pages = [
            ('/adminpanel/', 'Admin Dashboard'),
            ('/adminpanel/users/', 'Admin Users'),
            ('/adminpanel/vendors/', 'Admin Vendors'),
            ('/adminpanel/products/', 'Admin Products'),
            ('/adminpanel/orders/', 'Admin Orders'),
            ('/adminpanel/withdrawals/', 'Admin Withdrawals'),
            ('/adminpanel/logs/', 'Admin Logs'),
            ('/adminpanel/ddos/', 'DDoS Dashboard'),
        ]
        
        # Security pages
        security_pages = [
            ('/security/status/', 'Security Status'),
            ('/security/dashboard/', 'Security Dashboard'),
            ('/security/settings/', 'Security Settings'),
        ]
        
        # Test public pages
        print("="*50)
        print("📄 Testing Public Pages")
        print("="*50)
        for url, name in public_pages:
            self.check_page(url, name)
        
        # Test authenticated pages
        print("\n" + "="*50)
        print("🔐 Testing Authenticated Pages")
        print("="*50)
        for url, name in auth_pages:
            self.check_page(url, name, requires_auth=True)
        
        # Test admin pages (will redirect to login)
        print("\n" + "="*50)
        print("👮 Testing Admin Pages")
        print("="*50)
        for url, name in admin_pages:
            self.check_page(url, name)
        
        # Test security pages
        print("\n" + "="*50)
        print("🛡️ Testing Security Pages")
        print("="*50)
        for url, name in security_pages:
            self.check_page(url, name, requires_auth=True)
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*70)
        print("📊 TEST SUMMARY")
        print("="*70)
        
        print(f"\nTotal pages tested: {self.results['total']}")
        print(f"✅ Successful: {self.results['success']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['js_found']:
            print(f"\n⚠️  JavaScript found in {len(self.results['js_found'])} pages:")
            for page in self.results['js_found']:
                print(f"   - {page}")
        
        if self.results['design_issues']:
            print(f"\n🎨 Design issues found ({len(self.results['design_issues'])}):")
            for issue in self.results['design_issues']:
                print(f"   - {issue}")
        
        if self.results['missing_elements']:
            print(f"\n📦 Missing elements ({len(self.results['missing_elements'])}):")
            for element in self.results['missing_elements']:
                print(f"   - {element}")
        
        success_rate = (self.results['success'] / self.results['total'] * 100) if self.results['total'] > 0 else 0
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 90 and not self.results['js_found']:
            print("\n✨ Excellent! All pages are working well with proper design implementation!")
        elif success_rate >= 70:
            print("\n⚠️  Good progress, but some pages need attention.")
        else:
            print("\n❌ Significant issues found. Pages need major fixes.")

def main():
    """Run the comprehensive page test"""
    tester = PageTester()
    
    try:
        tester.test_all_pages()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {str(e)}")
    finally:
        tester.print_summary()

if __name__ == "__main__":
    main()