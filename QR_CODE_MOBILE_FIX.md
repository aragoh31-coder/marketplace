# TOTP QR Code Mobile Fix

## Issue
The TOTP QR code was too large and didn't fit properly on mobile screens.

## Solution Implemented

### 1. Reduced QR Code Generation Parameters
**File**: `/workspace/accounts/totp_service.py`
- Changed `box_size` from 10 to 5
- Changed `border` from 4 to 2
- This reduces the physical size of the generated QR code image

### 2. Added Responsive CSS
**File**: `/workspace/templates/accounts/totp_setup.html`
- Added `qr-code-img` class with responsive sizing
- Desktop: max-width 200px
- Mobile (< 576px): max-width 150px
- Added proper padding adjustments for mobile
- Made manual entry code more mobile-friendly with smaller font and adjusted letter spacing

## Result
- QR code now fits properly on mobile screens
- Still scannable by authenticator apps
- Manual entry option remains available with improved mobile formatting
- Responsive design ensures good user experience across all devices

## Testing
To test the changes:
1. Navigate to the TOTP setup page
2. View on mobile device or use browser dev tools mobile view
3. QR code should fit within the screen without horizontal scrolling
4. Manual entry code should be readable and properly formatted