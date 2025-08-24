"""
Two-Factor Authentication views for both PGP and TOTP
"""
import logging
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from .forms import PGPKeyForm, TOTPVerificationForm
from .models import User, LoginHistory
from .pgp_service import PGPService
from .totp_service import TOTPService

logger = logging.getLogger('accounts')


@csrf_protect
@never_cache
def two_factor_verify(request):
    """Unified 2FA verification for both PGP and TOTP"""
    # Check if user is in 2FA flow
    if '2fa_user_id' not in request.session:
        return redirect('accounts:login')
    
    try:
        user = User.objects.get(id=request.session['2fa_user_id'])
    except User.DoesNotExist:
        del request.session['2fa_user_id']
        return redirect('accounts:login')
    
    # Determine which 2FA methods are required
    requires_pgp = user.pgp_login_enabled
    requires_totp = user.totp_enabled
    
    # Vendor requirement check
    if user.is_vendor and (not requires_pgp or not requires_totp):
        messages.error(request, "Vendors must have both PGP and TOTP enabled for security.")
        return redirect('accounts:login')
    
    # Track verification status
    pgp_verified = request.session.get('2fa_pgp_verified', False) if requires_pgp else True
    totp_verified = request.session.get('2fa_totp_verified', False) if requires_totp else True
    
    # If all required methods are verified, complete login
    if pgp_verified and totp_verified:
        # Complete the login
        login(request, user)
        
        # Log successful login
        LoginHistory.objects.create(
            user=user,
            success=True,
            method='2FA'
        )
        
        # Clean up session
        session_keys_to_remove = ['2fa_user_id', '2fa_pgp_verified', '2fa_totp_verified', 'pgp_challenge']
        for key in session_keys_to_remove:
            request.session.pop(key, None)
        
        messages.success(request, f'Welcome back, {user.username}!')
        
        # Redirect to next URL or home
        next_url = request.session.pop('2fa_next_url', '/')
        return redirect(next_url)
    
    # Initialize forms
    pgp_form = None
    totp_form = None
    
    # Handle PGP verification
    if requires_pgp and not pgp_verified:
        if request.method == 'POST' and 'pgp_response' in request.POST:
            pgp_form = PGPKeyForm(request.POST)
            if pgp_form.is_valid():
                decrypted_response = pgp_form.cleaned_data['pgp_response']
                expected_challenge = request.session.get('pgp_challenge', '')
                
                if decrypted_response.strip() == expected_challenge.strip():
                    request.session['2fa_pgp_verified'] = True
                    pgp_verified = True
                    messages.success(request, "PGP verification successful!")
                    
                    # Reload page to show next step or complete login
                    return redirect('accounts:2fa_verify')
                else:
                    messages.error(request, "Invalid PGP response. Please try again.")
        else:
            # Generate PGP challenge if not exists
            if 'pgp_challenge' not in request.session:
                challenge = PGPService.generate_challenge()
                request.session['pgp_challenge'] = challenge
                
                # Encrypt challenge with user's public key
                encrypted_challenge = PGPService.encrypt_message(challenge, user.pgp_public_key)
                request.session['encrypted_challenge'] = encrypted_challenge
            
            pgp_form = PGPKeyForm()
    
    # Handle TOTP verification
    if requires_totp and not totp_verified:
        if request.method == 'POST' and ('token' in request.POST or 'backup_code' in request.POST):
            totp_form = TOTPVerificationForm(request.POST)
            if totp_form.is_valid():
                token = totp_form.cleaned_data.get('token')
                backup_code = totp_form.cleaned_data.get('backup_code')
                
                verified = False
                if token:
                    # Verify TOTP token
                    verified = TOTPService.verify_token(user.totp_secret, token)
                    if verified:
                        messages.success(request, "TOTP verification successful!")
                elif backup_code:
                    # Verify backup code
                    verified = TOTPService.verify_backup_code(user, backup_code)
                    if verified:
                        messages.success(request, "Backup code verified successfully!")
                        messages.warning(request, "This backup code has been used and is no longer valid.")
                
                if verified:
                    request.session['2fa_totp_verified'] = True
                    totp_verified = True
                    
                    # Reload page to show next step or complete login
                    return redirect('accounts:2fa_verify')
                else:
                    messages.error(request, "Invalid verification code. Please try again.")
        else:
            totp_form = TOTPVerificationForm()
    
    context = {
        'user': user,
        'requires_pgp': requires_pgp,
        'requires_totp': requires_totp,
        'pgp_verified': pgp_verified,
        'totp_verified': totp_verified,
        'pgp_form': pgp_form,
        'totp_form': totp_form,
        'encrypted_challenge': request.session.get('encrypted_challenge', '') if requires_pgp and not pgp_verified else None,
        'is_vendor': user.is_vendor
    }
    
    return render(request, 'accounts/2fa_verify.html', context)