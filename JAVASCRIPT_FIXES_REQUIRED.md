# 🚨 JavaScript Fixes Required for Tor Compatibility

This document lists all JavaScript code that must be removed or replaced for the marketplace to work in Tor Browser's safest mode.

## 1. Copy to Clipboard Functions

### Issue: `onclick` handlers for copying text
**Files affected:**
- `templates/accounts/pgp_verify.html` (line 66)
- `templates/accounts/pgp_challenge.html` (line 30)

**Current code:**
```html
<button onclick="copyMessage()" class="btn btn-secondary">
    📋 Copy Message
</button>
```

**Fix:** Remove the button entirely or replace with instructions:
```html
<p class="help-text">Select the text above and copy it manually (Ctrl+C or Cmd+C)</p>
```

## 2. JavaScript History Navigation

### Issue: `javascript:history.back()`
**File:** `templates/security/captcha_failed.html` (line 77)

**Current code:**
```html
<a href="javascript:history.back()" class="btn">🔙 Try Again</a>
```

**Fix:** Replace with proper URL:
```html
<a href="{{ request.META.HTTP_REFERER|default:'/' }}" class="btn">🔙 Try Again</a>
```

## 3. Confirmation Dialogs

### Issue: `onclick` confirmation dialogs
**Files affected:**
- `templates/adminpanel/user_detail.html` (multiple instances)
- `templates/adminpanel/user_detail_enhanced.html` (multiple instances)
- `templates/adminpanel/withdrawal_detail.html`
- `templates/wallets/withdrawal_status.html`

**Current code:**
```html
<button type="submit" name="action" value="ban" class="btn btn-danger" 
        onclick="return confirm('Are you sure you want to ban this user?')">
    🚫 Ban User
</button>
```

**Fix:** Create separate confirmation pages:
```html
<!-- Replace button with link to confirmation page -->
<a href="{% url 'adminpanel:confirm_ban' user.username %}" class="btn btn-danger">
    🚫 Ban User
</a>

<!-- Create new confirmation template: confirm_ban.html -->
<form method="post" action="{% url 'adminpanel:user_action' user.username %}">
    {% csrf_token %}
    <h2>Confirm Action</h2>
    <p>Are you sure you want to ban user {{ user.username }}?</p>
    <input type="hidden" name="action" value="ban">
    <button type="submit" class="btn btn-danger">Yes, Ban User</button>
    <a href="{% url 'adminpanel:user_detail' user.username %}" class="btn">Cancel</a>
</form>
```

## 4. Script Tags for Functions

### Issue: JavaScript functions in script tags
**Files affected:**
- `templates/accounts/pgp_verify.html` (lines 385-408)
- `templates/accounts/pgp_challenge.html` (lines 401-490)
- `templates/accounts/pgp_settings.html` (lines 321-333)

**Current code example:**
```html
<script>
    function copyMessage() {
        const textarea = document.getElementById('encrypted-message');
        textarea.select();
        document.execCommand('copy');
        alert('Message copied to clipboard!');
    }
</script>
```

**Fix:** Remove entire script blocks and related functionality

## 5. Form Handlers

### Issue: Dynamic form validation and submission
**Files affected:**
- `templates/wallets/dashboard_final_enhanced.html`
- `templates/wallets/dashboard_enhanced.html`

**Fix:** Remove all JavaScript validation and rely on server-side validation with proper error messages

## 6. Dynamic UI Updates

### Issue: JavaScript for showing/hiding elements
**Files affected:**
- `templates/admin/design_system_change_list.html`
- `templates/base_design_system.html`

**Fix:** Use CSS-only solutions or server-side rendering:
```css
/* Use CSS :target pseudo-class for simple show/hide */
.hidden-section {
    display: none;
}
.hidden-section:target {
    display: block;
}
```

## Required Actions for Each File:

### 1. `templates/accounts/pgp_verify.html`
- Remove lines 385-408 (script block)
- Remove line 66 (onclick handler)
- Add manual copy instructions

### 2. `templates/accounts/pgp_challenge.html`
- Remove lines 401-490 (script block)
- Remove line 30 (onclick handler)
- Remove lines 66, 69 (onclick handlers)

### 3. `templates/accounts/pgp_settings.html`
- Remove lines 321-333 (script block)
- Remove line 26 (onclick handler)
- Remove line 32 (onclick handler)
- Implement server-side confirmation

### 4. `templates/adminpanel/user_detail.html`
- Replace all onclick confirmations (lines 13, 23, 27, 32)
- Create confirmation pages for each action

### 5. `templates/adminpanel/user_detail_enhanced.html`
- Replace all onclick confirmations (lines 308, 312, 318, 324, 328)
- Create confirmation pages for each action

### 6. `templates/security/captcha_failed.html`
- Replace line 77 javascript:history.back()

### 7. `templates/wallets/withdrawal_status.html`
- Replace line 261 onclick confirmation

### 8. `templates/admin/design_system_change_list.html`
- Remove lines 375-390 (script block)
- Replace line 370 onclick confirmation

### 9. `templates/base_design_system.html`
- Remove lines 109-145 (script block)
- Remove this template entirely if not needed

### 10. `templates/wallets/dashboard_final_enhanced.html`
- Remove lines 291-324 (script block)

### 11. `templates/security/rate_limited_enhanced.html`
- Remove lines 151-187 (script block)

## Testing Checklist After Fixes:

- [ ] All forms submit without JavaScript
- [ ] All confirmations work via separate pages
- [ ] No console errors in browser
- [ ] All functionality works in Tor Browser safest mode
- [ ] No external requests are made
- [ ] Page navigation works without JavaScript
- [ ] Error messages display properly
- [ ] CSRF tokens are present in all forms