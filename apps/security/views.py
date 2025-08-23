import hashlib
import random
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from wallets.models import AuditLog


@login_required
def security_status(request):
    """Display user's security status and recent events"""
    user = request.user

    security_score = 0

    two_fa_enabled = hasattr(user, "wallet") and user.wallet.two_fa_enabled
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

    recent_events = AuditLog.objects.filter(user=user).order_by("-created_at")[:20]

    security_info = {
        "security_score": min(security_score, 100),
        "two_fa_enabled": two_fa_enabled,
        "pgp_key_set": pgp_key_set,
        "account_age": account_age,
        "last_login": user.last_login,
    }

    return render(
        request,
        "security/security_status.html",
        {
            "security_info": security_info,
            "recent_events": recent_events,
        },
    )


def bot_challenge(request):
    """Handle bot challenge verification"""
    if request.method == "POST":
        from apps.security.forms import BotChallengeForm

        expected_answer = request.session.get("bot_challenge_answer")

        form = BotChallengeForm(request.POST, expected_answer=expected_answer)

        if form.is_valid():
            request.session.pop("bot_challenge_answer", None)
            request.session.pop("bot_challenge_timestamp", None)

            request.session["bot_challenge_passed"] = True

            next_url = request.session.get("bot_challenge_next", "/")
            request.session.pop("bot_challenge_next", None)

            return redirect(next_url)
        else:
            messages.error(request, "Challenge failed. Please try again.")

    num1 = random.randint(1, 20)
    num2 = random.randint(1, 20)
    operation = random.choice(["+", "-", "*"])

    if operation == "+":
        answer = num1 + num2
        question = f"{num1} + {num2}"
    elif operation == "-":
        answer = num1 - num2
        question = f"{num1} - {num2}"
    else:  # multiplication
        answer = num1 * num2
        question = f"{num1} × {num2}"

    request.session["bot_challenge_answer"] = answer
    request.session["bot_challenge_timestamp"] = time.time()

    form = BotChallengeForm(initial={"timestamp": time.time(), "challenge_id": f"challenge_{int(time.time())}"})

    return render(
        request,
        "security/bot_challenge.html",
        {"form": form, "question": question, "challenge_id": f"challenge_{int(time.time())}"},
    )


def captcha_challenge(request):
    """Handle CAPTCHA challenge"""
    if request.method == "POST":
        user_answer = request.POST.get("captcha_answer", "").strip()
        expected_answer = request.session.get("captcha_answer", "")

        if request.POST.get("website") or request.POST.get("email_address"):
            messages.error(request, "Bot detected. Access denied.")
            return redirect("security:captcha_challenge")

        if user_answer.lower() == expected_answer.lower():
            request.session["captcha_verified"] = True
            request.session.pop("captcha_answer", None)

            next_url = request.session.get("captcha_next", "/")
            request.session.pop("captcha_next", None)

            messages.success(request, "Verification successful!")
            return redirect(next_url)
        else:
            messages.error(request, "Incorrect CAPTCHA answer. Please try again.")

    words = ["SECURE", "MARKET", "CRYPTO", "WALLET", "TRADE", "PRIVACY", "SAFETY"]
    captcha_word = random.choice(words)

    request.session["captcha_answer"] = captcha_word

    return render(
        request,
        "security/captcha_challenge.html",
        {
            "captcha_word": captcha_word,
            "timestamp": time.time(),
            "form_hash": hashlib.sha256(f"{time.time()}:{captcha_word}".encode()).hexdigest()[:16],
        },
    )


@require_http_methods(["POST"])
def security_challenge_completion(request):
    """Handle security challenge completion and issue tokens"""
    
    # Check if this is a security challenge submission
    challenge_answer = request.POST.get('challenge_answer')
    challenge_id = request.POST.get('challenge_id')
    timestamp = request.POST.get('timestamp')
    
    if not challenge_answer or not challenge_id:
        messages.error(request, "Invalid challenge submission")
        return redirect('/')
    
    # Validate the challenge answer
    expected_answer = request.session.get('bot_challenge_answer')
    if not expected_answer:
        messages.error(request, "Challenge expired or invalid")
        return redirect('/')
    
    try:
        user_answer = int(challenge_answer)
        if user_answer == expected_answer:
            # Challenge completed successfully - issue token
            current_time = time.time()
            
            # Store challenge completion in session
            request.session['security_challenge_completed'] = True
            request.session['security_challenge_timestamp'] = current_time
            request.session['security_challenge_id'] = challenge_id
            
            # Clear the challenge answer
            request.session.pop('bot_challenge_answer', None)
            request.session.pop('bot_challenge_timestamp', None)
            
            # Set challenge completion expiry (24 hours)
            request.session['security_challenge_expires'] = current_time + (24 * 60 * 60)
            
            # Log successful completion
            # logger.info(f"Security challenge completed successfully for IP: {request.META.get('REMOTE_ADDR')}") # logger is not defined
            
            messages.success(request, "Security verification completed successfully!")
            return redirect('/')
        else:
            messages.error(request, "Incorrect answer. Please try again.")
            return redirect('/')
            
    except (ValueError, TypeError):
        messages.error(request, "Invalid answer format")
        return redirect('/')


def rate_limited(request):
    """Display rate limit exceeded message"""
    return render(request, "security/rate_limited.html", {"retry_after": 60})


def security_verification(request):
    """Display security verification page"""
    return render(request, "security/security_verification.html")


@login_required
def user_security_dashboard(request):
    """Display user security dashboard"""
    user = request.user
    
    # Get security statistics
    security_stats = {
        'two_fa_enabled': hasattr(user, 'wallet') and user.wallet.two_fa_enabled,
        'pgp_key_set': bool(user.pgp_public_key),
        'last_login': user.last_login,
        'account_age': (timezone.now().date() - user.date_joined.date()).days,
    }
    
    return render(request, "security/user_dashboard.html", {"security_stats": security_stats})


@login_required
def security_settings(request):
    """Display and handle security settings"""
    if request.method == "POST":
        # Handle security setting updates
        if 'enable_2fa' in request.POST:
            # Enable 2FA logic
            pass
        elif 'update_pgp' in request.POST:
            # Update PGP key logic
            pass
    
    return render(request, "security/settings.html")


def security_status_api(request):
    """API endpoint for security status"""
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    security_data = {
        'challenge_completed': request.session.get('security_challenge_completed', False),
        'challenge_expires': request.session.get('security_challenge_expires', 0),
        'timestamp': time.time()
    }
    
    return JsonResponse(security_data)


def ip_change_detected(request):
    """Handle IP change detection"""
    return render(request, "security/ip_change.html")


def session_expired(request):
    """Handle session expiration"""
    return render(request, "security/session_expired.html")


def generate_challenge_token(session_id):
    """Generate a unique challenge token"""
    timestamp = str(int(time.time()))
    token_data = f"{session_id}:{timestamp}:challenge"
    return hashlib.sha256(token_data.encode()).hexdigest()[:16]

def security_challenge(request):
    """Handle security challenge with proper token system"""
    
    # Ensure session exists
    if not request.session.session_key:
        request.session.create()
    
    session_id = request.session.session_key
    print(f"🔍 Security Challenge - Session ID: {session_id}")
    
    if request.method == 'POST':
        print("🔍 Processing POST request")
        
        # Get form data
        challenge_answer = request.POST.get('challenge_answer')
        challenge_token = request.POST.get('challenge_token')
        
        print(f"🔍 Challenge answer: {challenge_answer}")
        print(f"🔍 Challenge token: {challenge_token}")
        
        # Validate challenge token
        expected_token = request.session.get('challenge_token')
        if not expected_token or challenge_token != expected_token:
            print("🔍 Invalid or expired challenge token")
            # Generate new challenge
            return generate_new_challenge(request, session_id)
        
        # Validate answer
        expected_answer = request.session.get('challenge_answer')
        if not expected_answer:
            print("🔍 No expected answer in session")
            return generate_new_challenge(request, session_id)
        
        try:
            user_answer = int(challenge_answer)
            if user_answer == expected_answer:
                print("🔍 Challenge completed successfully!")
                
                # Mark challenge as completed
                request.session['security_challenge_completed'] = True
                request.session['challenge_completed_at'] = time.time()
                request.session['challenge_expires_at'] = time.time() + (24 * 60 * 60)  # 24 hours
                
                # Clear challenge data
                request.session.pop('challenge_token', None)
                request.session.pop('challenge_answer', None)
                request.session.pop('challenge_created_at', None)
                
                # Force session save
                request.session.modified = True
                
                print("🔍 Session updated, redirecting to home")
                return redirect('/')
            else:
                print(f"🔍 Incorrect answer: {user_answer} != {expected_answer}")
                return generate_new_challenge(request, session_id, error="Incorrect answer. Please try again.")
                
        except (ValueError, TypeError):
            print("🔍 Invalid answer format")
            return generate_new_challenge(request, session_id, error="Invalid answer format. Please enter a number.")
    
    else:
        print("🔍 Processing GET request")
        return generate_new_challenge(request, session_id)

def generate_new_challenge(request, session_id, error=None):
    """Generate a new security challenge"""
    print(f"🔍 Generating new challenge for session: {session_id}")
    
    # Generate challenge data
    num1 = 2
    num2 = 2
    answer = num1 + num2
    question = f"What is {num1} + {num2}?"
    
    # Generate challenge token
    challenge_token = generate_challenge_token(session_id)
    
    # Store challenge data in session
    request.session['challenge_answer'] = answer
    request.session['challenge_token'] = challenge_token
    request.session['challenge_created_at'] = time.time()
    request.session.modified = True
    
    print(f"🔍 Challenge data stored - Answer: {answer}, Token: {challenge_token}")
    
    # Render challenge page
    context = {
        'question': question,
        'challenge_token': challenge_token,
        'error_message': error,
        'timestamp': time.time(),
    }
    
    return render(request, 'security/bot_challenge.html', context)

def test_session(request):
    """Test if sessions are working"""
    if request.method == 'POST':
        # Set a test session variable
        request.session['test_var'] = 'test_value'
        request.session.modified = True
        return HttpResponse(f"Session set: {dict(request.session)}")
    else:
        # Get the test session variable
        test_var = request.session.get('test_var', 'not_set')
        return HttpResponse(f"Session test_var: {test_var}, All session: {dict(request.session)}")

def test_view(request):
    """Simple test view to verify routing"""
    return HttpResponse("Test view working!")

def challenge_status(request):
    """Check challenge completion status"""
    session_id = request.session.session_key
    completed = request.session.get('security_challenge_completed', False)
    expires_at = request.session.get('challenge_expires_at', 0)
    
    status = {
        'session_id': session_id,
        'completed': completed,
        'expires_at': expires_at,
        'current_time': time.time(),
        'valid': completed and time.time() < expires_at
    }
    
    return HttpResponse(f"Challenge Status: {status}")

def reset_challenge(request):
    """Reset challenge completion (for testing)"""
    request.session.pop('security_challenge_completed', None)
    request.session.pop('challenge_completed_at', None)
    request.session.pop('challenge_expires_at', None)
    request.session.modified = True
    return HttpResponse("Challenge reset successfully")
