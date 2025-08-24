# Captcha Troubleshooting Guide

## Issue: "Captcha is wrong" Error

The marketplace uses a **One-Click CAPTCHA** system that requires you to click on a specific shape in an image.

### How the Captcha Works

1. **Image Display**: The captcha shows multiple circles
2. **Target Circle**: One circle has a missing slice (looks like Pac-Man)
3. **Required Action**: You must click **inside** the Pac-Man circle
4. **Validation**: The system checks if your click is within the radius of the target circle

### Common Issues and Solutions

#### Issue 1: Clicking the Wrong Circle
- **Problem**: Clicking on a complete circle instead of the Pac-Man circle
- **Solution**: Look carefully for the circle with a missing wedge/slice

#### Issue 2: Clicking Outside the Target
- **Problem**: Clicking near but not inside the Pac-Man circle
- **Solution**: Click directly in the center of the Pac-Man shape

#### Issue 3: Session/Cookie Issues
- **Problem**: Session data not being maintained between page load and form submission
- **Solution**: 
  - Ensure cookies are enabled in your browser
  - Don't use private/incognito mode as it may affect session handling
  - Try clearing cookies and starting fresh

#### Issue 4: Form Expiration
- **Problem**: Taking too long to complete the form (>10 minutes)
- **Solution**: Refresh the page and try again quickly

### Technical Details

The captcha validation checks:
1. Click coordinates (x, y) against the target circle center
2. Distance formula: `sqrt((click_x - center_x)² + (click_y - center_y)²) <= radius + 2`
3. Allows 2-pixel margin of error for usability

### Visual Example

```
Normal Circle:     Pac-Man Circle (TARGET):
    ⚪                   🟡
                      (missing slice)
```

### Tips for Success

1. **Look for the Pac-Man**: Find the circle with a pie-slice cut out
2. **Click the Center**: Aim for the middle of the Pac-Man circle
3. **Don't Rush**: The form requires at least 3 seconds to complete (anti-bot measure)
4. **Single Click**: The form auto-submits when you click the captcha image

### If Problems Persist

1. **Check Browser Console**: Look for JavaScript errors (though the system works without JS)
2. **Try Different Browser**: Some browsers handle image inputs differently
3. **Clear Cache**: Browser cache issues can sometimes interfere
4. **Check Tor Browser Settings**: If using Tor, ensure security settings aren't too restrictive

### Alternative Registration

If the One-Click CAPTCHA continues to fail, you can:
1. Contact an admin to create an account
2. Use the API endpoint (if available)
3. Try during off-peak hours when server load is lower

---

**Note**: The captcha is designed to be accessible and work without JavaScript, making it compatible with Tor Browser's highest security settings.