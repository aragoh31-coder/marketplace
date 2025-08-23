"""
Security views with dual CAPTCHA support
"""
import random
import time
import logging
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages

from apps.security.forms_oneclick import DualCaptchaSecurityForm
from captcha.utils.captcha_generator import OneClickCaptcha

logger = logging.getLogger(__name__)


@csrf_protect
@require_http_methods(["GET", "POST"])
def security_challenge_dual(request):
    """Handle security challenge with dual CAPTCHA (math + one-click)"""
    
    # Ensure session exists
    if not request.session.session_key:
        request.session.create()
    
    session_id = request.session.session_key
    logger.info(f"Security Challenge - Session ID: {session_id}")
    
    if request.method == 'POST':
        # Check if this is from image input (One-Click CAPTCHA)
        if 'captcha.x' in request.POST and 'captcha.y' in request.POST:
            # Handle One-Click CAPTCHA validation along with math
            form = DualCaptchaSecurityForm(request.POST, request=request)
        else:
            form = DualCaptchaSecurityForm(request.POST, request=request)
        
        if form.is_valid():
            logger.info("Both challenges completed successfully!")
            
            # Mark challenge as completed
            request.session['security_challenge_completed'] = True
            request.session['challenge_completed_at'] = time.time()
            request.session['challenge_expires_at'] = time.time() + (24 * 60 * 60)  # 24 hours
            
            # Clear challenge data
            request.session.pop('challenge_token', None)
            request.session.pop('challenge_answer', None)
            request.session.pop('math_answer', None)
            request.session.pop('security_math_answer', None)
            
            # Force session save
            request.session.modified = True
            
            messages.success(request, "Security verification completed successfully!")
            
            # Redirect to originally requested page or home
            next_url = request.POST.get('next', request.GET.get('next', '/'))
            return redirect(next_url)
        else:
            # Form validation failed
            logger.warning("Challenge validation failed")
            messages.error(request, "Verification failed. Please complete both challenges correctly.")
    else:
        # GET request - generate new challenges
        form = DualCaptchaSecurityForm(request=request)
    
    # Generate math challenge for display
    challenge_question = _generate_math_question(request)
    
    # Generate unique challenge ID
    challenge_id = f"challenge_{int(time.time())}_{random.randint(1000, 9999)}"
    request.session['challenge_id'] = challenge_id
    
    # Get reason from DDoS protection
    reason = request.GET.get('reason', 'Security verification required')
    
    return render(request, 'security/challenge_required_dual.html', {
        'form': form,
        'challenge_question': challenge_question,
        'challenge_id': challenge_id,
        'reason': reason,
    })


def _generate_math_question(request):
    """Generate a math challenge question and store answer in session"""
    num1 = random.randint(5, 20)
    num2 = random.randint(1, 10)
    
    operations = [
        ('+', lambda a, b: a + b),
        ('-', lambda a, b: a - b),
        ('×', lambda a, b: a * b),
    ]
    
    op_symbol, op_func = random.choice(operations)
    
    # For subtraction, ensure positive result
    if op_symbol == '-' and num2 > num1:
        num1, num2 = num2, num1
    
    answer = op_func(num1, num2)
    question = f"What is {num1} {op_symbol} {num2}?"
    
    # Store in session
    request.session['challenge_answer'] = str(answer)
    request.session['math_answer'] = str(answer)
    request.session['challenge_created_at'] = time.time()
    
    return question


@require_http_methods(["GET"])
def check_challenge_status(request):
    """Check if security challenge is completed and valid"""
    
    if not request.session.session_key:
        return JsonResponse({'completed': False})
    
    completed = request.session.get('security_challenge_completed', False)
    expires_at = request.session.get('challenge_expires_at', 0)
    
    if completed and time.time() < expires_at:
        return JsonResponse({
            'completed': True,
            'expires_in': int(expires_at - time.time())
        })
    else:
        return JsonResponse({'completed': False})


@require_http_methods(["POST"])
def clear_challenge(request):
    """Clear security challenge status (admin use)"""
    
    # Check if user is admin
    if not request.user.is_authenticated or not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Clear challenge data
    request.session.pop('security_challenge_completed', None)
    request.session.pop('challenge_completed_at', None)
    request.session.pop('challenge_expires_at', None)
    request.session.pop('challenge_token', None)
    request.session.pop('challenge_answer', None)
    request.session.pop('math_answer', None)
    
    request.session.modified = True
    
    return JsonResponse({'status': 'cleared'})


# Backward compatibility
security_challenge = security_challenge_dual