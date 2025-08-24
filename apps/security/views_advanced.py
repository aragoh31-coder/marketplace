"""
Advanced Security Views for Stateless Challenge Verification
"""
import json
import logging
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.contrib import messages

from core.antiddos_advanced import (
    AdvancedDDoSProtection, 
    HMACChallengeChain,
    BlindTokenBucket,
    ProofOfWork
)

logger = logging.getLogger('marketplace.security.views')


@csrf_protect
@require_http_methods(["GET", "POST"])
def advanced_challenge_verify(request):
    """Handle stateless challenge verification"""
    
    if request.method == "POST":
        # Get challenge data from form
        challenge_data = request.POST.get('challenge_data')
        challenge_hmac = request.POST.get('challenge_hmac')
        user_answer = request.POST.get('answer', '').strip()
        
        if not challenge_data or not challenge_hmac:
            messages.error(request, "Invalid challenge data")
            return redirect(request.session.get('ddos_redirect_after', '/'))
        
        try:
            # Parse challenge data
            challenge_dict = json.loads(challenge_data)
            
            # Verify challenge and get token
            is_valid, token = AdvancedDDoSProtection.verify_challenge_response(
                request,
                challenge_dict,
                challenge_hmac,
                user_answer
            )
            
            if is_valid and token:
                # Challenge passed! Store token for client
                messages.success(request, "Security verification completed!")
                
                # Redirect to original destination with token
                redirect_url = request.session.pop('ddos_redirect_after', '/')
                
                # Create response with token in header
                response = redirect(redirect_url)
                response['X-Auth-Token'] = token
                
                # Also set as cookie for convenience
                response.set_cookie(
                    'ddos_token',
                    token,
                    max_age=3600,  # 1 hour
                    httponly=True,
                    secure=True,
                    samesite='Strict'
                )
                
                return response
            else:
                messages.error(request, "Incorrect answer. Please try again.")
                # Fall through to regenerate challenge
                
        except Exception as e:
            logger.error(f"Challenge verification error: {e}")
            messages.error(request, "Challenge verification failed")
    
    # Generate new challenge
    challenge_data = AdvancedDDoSProtection.issue_challenge(request, 'math')
    
    return render(request, 'security/advanced_challenge.html', {
        'challenge': challenge_data
    })


@csrf_protect
@require_http_methods(["GET", "POST"])
def pow_challenge_verify(request):
    """Handle Proof of Work challenge verification"""
    
    if request.method == "POST":
        # Get PoW data
        challenge = request.POST.get('pow_challenge')
        signature = request.POST.get('pow_signature')
        nonce = request.POST.get('nonce', '').strip()
        
        if not challenge or not signature or not nonce:
            messages.error(request, "Invalid PoW data")
            return redirect(request.session.get('ddos_redirect_after', '/'))
        
        # Verify PoW solution
        if ProofOfWork.verify_solution(challenge, signature, nonce):
            # Generate token for successful PoW
            from core.antiddos_advanced import TorCircuitAwareness
            circuit_id = TorCircuitAwareness.get_circuit_id(request)
            session_id = request.session.session_key if hasattr(request, 'session') else circuit_id
            
            token = BlindTokenBucket.generate_token(
                session_id,
                metadata={'pow_completed': True}
            )
            
            messages.success(request, "Proof of Work completed successfully!")
            
            # Redirect with token
            redirect_url = request.session.pop('ddos_redirect_after', '/')
            response = redirect(redirect_url)
            response['X-Auth-Token'] = token
            response.set_cookie(
                'ddos_token',
                token,
                max_age=3600,
                httponly=True,
                secure=True,
                samesite='Strict'
            )
            
            return response
        else:
            messages.error(request, "Invalid Proof of Work solution")
    
    # Generate new PoW challenge
    challenge_data = AdvancedDDoSProtection.issue_challenge(request, 'pow')
    
    return render(request, 'security/pow_challenge.html', {
        'challenge': challenge_data,
        'difficulty': challenge_data['challenge'].get('pow_data', {}).get('difficulty', 4)
    })


@csrf_protect
@require_http_methods(["GET", "POST"])
def dual_challenge_verify(request):
    """Handle dual challenge verification (math + visual)"""
    
    if request.method == "POST":
        # Check which challenges are completed
        math_completed = request.session.get('dual_math_completed', False)
        visual_completed = request.session.get('dual_visual_completed', False)
        
        # Handle math challenge
        if 'math_answer' in request.POST and not math_completed:
            challenge_data = request.POST.get('math_challenge_data')
            challenge_hmac = request.POST.get('math_challenge_hmac')
            user_answer = request.POST.get('math_answer', '').strip()
            
            if challenge_data and challenge_hmac:
                try:
                    challenge_dict = json.loads(challenge_data)
                    is_valid, _ = HMACChallengeChain.verify_challenge(
                        request.session.session_key,
                        challenge_dict,
                        challenge_hmac,
                        user_answer
                    )
                    
                    if is_valid:
                        request.session['dual_math_completed'] = True
                        math_completed = True
                        messages.success(request, "Math challenge completed!")
                except Exception as e:
                    logger.error(f"Math challenge error: {e}")
        
        # Handle visual (One-Click) challenge
        if 'captcha_x' in request.POST and not visual_completed:
            # Verify One-Click CAPTCHA
            from captcha.utils.captcha_generator import OneClickCaptcha
            
            captcha_x = request.POST.get('captcha_x')
            captcha_y = request.POST.get('captcha_y')
            captcha_token = request.POST.get('captcha_token')
            
            captcha = OneClickCaptcha()
            if captcha.validate(captcha_x, captcha_y, captcha_token, request):
                request.session['dual_visual_completed'] = True
                visual_completed = True
                messages.success(request, "Visual challenge completed!")
        
        # Check if both completed
        if math_completed and visual_completed:
            # Generate token
            from core.antiddos_advanced import TorCircuitAwareness
            circuit_id = TorCircuitAwareness.get_circuit_id(request)
            session_id = request.session.session_key if hasattr(request, 'session') else circuit_id
            
            token = BlindTokenBucket.generate_token(
                session_id,
                metadata={'dual_challenge_completed': True}
            )
            
            # Clear session flags
            request.session.pop('dual_math_completed', None)
            request.session.pop('dual_visual_completed', None)
            
            messages.success(request, "All challenges completed successfully!")
            
            # Redirect with token
            redirect_url = request.session.pop('ddos_redirect_after', '/')
            response = redirect(redirect_url)
            response['X-Auth-Token'] = token
            response.set_cookie(
                'ddos_token',
                token,
                max_age=3600,
                httponly=True,
                secure=True,
                samesite='Strict'
            )
            
            return response
    
    # Generate new challenges if needed
    math_challenge = None
    if not request.session.get('dual_math_completed', False):
        math_challenge = AdvancedDDoSProtection.issue_challenge(request, 'math')
    
    return render(request, 'security/challenge_required_dual_advanced.html', {
        'math_challenge': math_challenge,
        'math_completed': request.session.get('dual_math_completed', False),
        'visual_completed': request.session.get('dual_visual_completed', False),
    })


@require_http_methods(["GET"])
def get_auth_token(request):
    """API endpoint to get current auth token"""
    
    # Check for token in cookie
    token = request.COOKIES.get('ddos_token')
    
    if token:
        # Verify token is still valid
        is_valid, payload = BlindTokenBucket.verify_token(token)
        if is_valid:
            return JsonResponse({
                'token': token,
                'expires_at': payload.get('expires_at'),
                'metadata': payload.get('metadata', {})
            })
    
    return JsonResponse({'error': 'No valid token'}, status=401)


def token_usage_example(request):
    """Example view showing how to use tokens in requests"""
    
    # This view demonstrates how clients should include tokens
    
    example_code = """
    // JavaScript example (for reference - not used in Tor safe mode)
    fetch('/api/endpoint', {
        headers: {
            'Authorization': 'Bearer YOUR_TOKEN_HERE'
        }
    });
    
    // cURL example
    curl -H "Authorization: Bearer YOUR_TOKEN_HERE" https://marketplace.onion/api/endpoint
    
    // Python requests example
    import requests
    
    response = requests.get(
        'https://marketplace.onion/api/endpoint',
        headers={'Authorization': 'Bearer YOUR_TOKEN_HERE'}
    )
    """
    
    return render(request, 'security/token_usage.html', {
        'example_code': example_code
    })