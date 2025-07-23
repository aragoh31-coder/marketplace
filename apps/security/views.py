from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from wallets.models import AuditLog
import random
import time
import hashlib


@login_required
def security_status(request):
    """Display user's security status and recent events"""
    user = request.user
    
    security_score = 0
    
    two_fa_enabled = hasattr(user, 'wallet') and user.wallet.two_fa_enabled
    if two_fa_enabled:
        security_score += 30
    
    pgp_key_set = bool(user.pgp_public_key)
    if pgp_key_set:
        security_score += 25
    
    account_age = (timezone.now().date() - user.date_joined.date()).days
    if account_age >= 90:
        security_score += 25
    elif account_age >= 30:
        security_score += 15
    elif account_age >= 7:
        security_score += 10
    
    if user.last_login:
        days_since_login = (timezone.now() - user.last_login).days
        if days_since_login <= 7:
            security_score += 20
        elif days_since_login <= 30:
            security_score += 10
    
    recent_events = AuditLog.objects.filter(
        user=user
    ).order_by('-created_at')[:20]
    
    security_info = {
        'security_score': min(security_score, 100),
        'two_fa_enabled': two_fa_enabled,
        'pgp_key_set': pgp_key_set,
        'account_age': account_age,
        'last_login': user.last_login,
    }
    
    return render(request, 'security/security_status.html', {
        'security_info': security_info,
        'recent_events': recent_events,
    })


def bot_challenge(request):
    """Handle bot challenge verification"""
    if request.method == 'POST':
        from apps.security.forms import BotChallengeForm
        
        expected_answer = request.session.get('bot_challenge_answer')
        
        form = BotChallengeForm(request.POST, expected_answer=expected_answer)
        
        if form.is_valid():
            request.session.pop('bot_challenge_answer', None)
            request.session.pop('bot_challenge_timestamp', None)
            
            request.session['bot_challenge_passed'] = True
            
            next_url = request.session.get('bot_challenge_next', '/')
            request.session.pop('bot_challenge_next', None)
            
            return redirect(next_url)
        else:
            messages.error(request, 'Challenge failed. Please try again.')
    
    num1 = random.randint(1, 20)
    num2 = random.randint(1, 20)
    operation = random.choice(['+', '-', '*'])
    
    if operation == '+':
        answer = num1 + num2
        question = f"{num1} + {num2}"
    elif operation == '-':
        answer = num1 - num2
        question = f"{num1} - {num2}"
    else:  # multiplication
        answer = num1 * num2
        question = f"{num1} × {num2}"
    
    request.session['bot_challenge_answer'] = answer
    request.session['bot_challenge_timestamp'] = time.time()
    
    form = BotChallengeForm(initial={
        'timestamp': time.time(),
        'challenge_id': f"challenge_{int(time.time())}"
    })
    
    return render(request, 'security/bot_challenge.html', {
        'form': form,
        'question': question,
        'challenge_id': f"challenge_{int(time.time())}"
    })


def captcha_challenge(request):
    """Handle CAPTCHA challenge"""
    if request.method == 'POST':
        user_answer = request.POST.get('captcha_answer', '').strip()
        expected_answer = request.session.get('captcha_answer', '')
        
        if request.POST.get('website') or request.POST.get('email_address'):
            messages.error(request, 'Bot detected. Access denied.')
            return redirect('security:captcha_challenge')
        
        if user_answer.lower() == expected_answer.lower():
            request.session['captcha_verified'] = True
            request.session.pop('captcha_answer', None)
            
            next_url = request.session.get('captcha_next', '/')
            request.session.pop('captcha_next', None)
            
            messages.success(request, 'Verification successful!')
            return redirect(next_url)
        else:
            messages.error(request, 'Incorrect CAPTCHA answer. Please try again.')
    
    words = ['SECURE', 'MARKET', 'CRYPTO', 'WALLET', 'TRADE', 'PRIVACY', 'SAFETY']
    captcha_word = random.choice(words)
    
    request.session['captcha_answer'] = captcha_word
    
    return render(request, 'security/captcha_challenge.html', {
        'captcha_word': captcha_word,
        'timestamp': time.time(),
        'form_hash': hashlib.sha256(f"{time.time()}:{captcha_word}".encode()).hexdigest()[:16]
    })


def rate_limited(request):
    """Display rate limit message"""
    return render(request, 'security/rate_limited.html', {
        'retry_after': 3600,  # 1 hour
        'limit_type': request.GET.get('type', 'general')
    })
