#!/usr/bin/env python3
"""
Simple page testing script to verify all pages and design implementation
"""

import requests
from bs4 import BeautifulSoup
import sys

class SimplePageTester:
    def __init__(self):
        self.base_url = 'http://localhost:8000'
        self.session = requests.Session()
        self.results = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'redirects': 0,
            'design_issues': [],
            'js_found': [],
            'missing_css': []
        }
        
    def test_page(self, path, name):
        """Test a single page"""
        self.results['total'] += 1
        url = self.base_url + path
        
        print(f"\n📍 Testing: {name}")
        print(f"   URL: {url}")
        
        try:
            response = self.session.get(url, allow_redirects=False, timeout=5)
            status = response.status_code
            
            print(f"   Status: {status}")
            
            if status == 200:
                self.results['success'] += 1
                self.check_page_content(response.text, name)
            elif status in [301, 302]:
                self.results['redirects'] += 1
                print(f"   ↪️  Redirects to: {response.headers.get('Location', 'Unknown')}")
            else:
                self.results['failed'] += 1
                print(f"   ❌ Failed with status {status}")
                
        except Exception as e:
            self.results['failed'] += 1
            print(f"   ❌ Error: {str(e)}")
    
    def check_page_content(self, html, page_name):
        """Check page content for design elements and issues"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Check for JavaScript
        if '<script' in html or 'javascript:' in html:
            self.results['js_found'].append(page_name)
            print(f"   ⚠️  JavaScript detected!")
        
        # Check CSS files
        style_css = soup.find('link', {'href': '/static/css/style.css'})
        enhance_css = soup.find('link', {'href': '/static/css/enhancements.css'})
        
        if not style_css:
            self.results['missing_css'].append(f"{page_name}: Missing style.css")
            print(f"   ⚠️  Missing style.css")
        else:
            print(f"   ✅ style.css loaded")
            
        if not enhance_css:
            self.results['missing_css'].append(f"{page_name}: Missing enhancements.css")
            print(f"   ⚠️  Missing enhancements.css")
        else:
            print(f"   ✅ enhancements.css loaded")
        
        # Check for key design elements
        design_elements = {
            'toolbar': soup.find(class_=lambda x: x and 'toolbar' in x),
            'container': soup.find(class_=lambda x: x and 'container' in x),
            'box/card': soup.find(class_=lambda x: x and ('box' in x or 'card' in x)),
            'button': soup.find(class_=lambda x: x and 'btn' in x),
        }
        
        found_elements = [k for k, v in design_elements.items() if v]
        if found_elements:
            print(f"   ✅ Design elements: {', '.join(found_elements)}")
        
        # Check for enhanced UI elements
        enhanced_elements = {
            'breadcrumb': soup.find(class_='breadcrumb'),
            'security-badge': soup.find(class_='security-badge'),
            'tooltip': soup.find(class_='tooltip'),
            'accordion': soup.find(class_='accordion'),
            'empty-state': soup.find(class_='empty-state'),
        }
        
        found_enhanced = [k for k, v in enhanced_elements.items() if v]
        if found_enhanced:
            print(f"   ✨ Enhanced UI: {', '.join(found_enhanced)}")
        
        # Check forms for CSRF
        forms = soup.find_all('form', method='post')
        if forms:
            csrf_found = any('csrf' in str(form) for form in forms)
            if csrf_found:
                print(f"   ✅ CSRF protection found")
            else:
                print(f"   ❌ Missing CSRF token in forms")
                self.results['design_issues'].append(f"{page_name}: Missing CSRF")
    
    def run_tests(self):
        """Run all page tests"""
        print("🔍 Starting page tests...\n")
        print("="*60)
        
        # Define pages to test
        pages = [
            # Public pages
            ('/', 'Home'),
            ('/accounts/login/', 'Login'),
            ('/accounts/register/', 'Register'),
            ('/products/', 'Products'),
            ('/vendors/', 'Vendors'),
            ('/support/', 'Support'),
            ('/support/faq/', 'FAQ'),
            
            # Auth required pages (will redirect)
            ('/accounts/profile/', 'Profile'),
            ('/wallets/', 'Wallet'),
            ('/orders/', 'Orders'),
            ('/messaging/', 'Messages'),
            
            # Admin pages (will redirect)
            ('/adminpanel/', 'Admin Panel'),
            
            # Error pages
            ('/nonexistent/', '404 Page'),
        ]
        
        for path, name in pages:
            self.test_page(path, name)
        
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60)
        
        print(f"\nTotal pages tested: {self.results['total']}")
        print(f"✅ Successful (200): {self.results['success']}")
        print(f"↪️  Redirects (301/302): {self.results['redirects']}")
        print(f"❌ Failed: {self.results['failed']}")
        
        if self.results['js_found']:
            print(f"\n⚠️  JavaScript found in {len(self.results['js_found'])} pages:")
            for page in self.results['js_found']:
                print(f"   - {page}")
        
        if self.results['missing_css']:
            print(f"\n⚠️  CSS issues in {len(self.results['missing_css'])} pages:")
            for issue in self.results['missing_css']:
                print(f"   - {issue}")
        
        if self.results['design_issues']:
            print(f"\n⚠️  Design issues found:")
            for issue in self.results['design_issues']:
                print(f"   - {issue}")
        
        # Calculate score
        total_checks = self.results['total']
        issues = len(self.results['js_found']) + len(self.results['missing_css']) + len(self.results['design_issues'])
        
        if total_checks > 0:
            score = ((total_checks - issues) / total_checks) * 100
            print(f"\n🎯 Design Implementation Score: {score:.1f}%")
            
            if score >= 90:
                print("✨ Excellent! Pages are working well with good design.")
            elif score >= 70:
                print("👍 Good, but some improvements needed.")
            else:
                print("⚠️  Significant issues need attention.")

def main():
    """Run the tests"""
    tester = SimplePageTester()
    
    # Check if server is running
    try:
        response = requests.get('http://localhost:8000/', timeout=2)
        print("✅ Server is running\n")
    except:
        print("❌ Server is not running! Please start it with:")
        print("   python3 manage.py runserver 0.0.0.0:8000")
        sys.exit(1)
    
    tester.run_tests()

if __name__ == "__main__":
    main()