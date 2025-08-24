# Security Dropdown Removed

## Change Made
- Removed the "🔐 Security" option from the user dropdown menu in the navigation bar

## File Modified
- `/workspace/templates/base_tor_safe.html`

## Result
The dropdown menu now only shows:
1. 🔧 Profile Settings
2. 🏪 Vendor Dashboard (if user is a vendor)
3. --- divider ---
4. 🚪 Logout

The security settings can still be accessed through the profile page if needed.