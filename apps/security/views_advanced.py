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
    """Handle Proof of Work challenge verification with dedicated launcher"""
    
    if request.method == "POST":
        # Get PoW data
        challenge_id = request.POST.get('challenge_id')
        nonce = request.POST.get('nonce', '').strip()
        
        if not challenge_id or not nonce:
            messages.error(request, "Invalid PoW data")
            return redirect(request.session.get('ddos_redirect_after', '/'))
        
        # Import the PoW service
        from core.pow_launcher import TorPoWService
        
        # Verify PoW solution using the service
        if TorPoWService.verify_solution(challenge_id, nonce):
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
    
    # Generate new PoW challenge using the launcher service
    from core.pow_launcher import TorPoWService
    from core.antiddos_advanced import TorCircuitAwareness
    
    circuit_id = TorCircuitAwareness.get_circuit_id(request)
    session_id = request.session.session_key if hasattr(request, 'session') else circuit_id
    
    # Issue challenge with launcher
    challenge_data = TorPoWService.issue_challenge(session_id, 'rate_limit')
    
    return render(request, 'security/pow_challenge_launcher.html', {
        'challenge': challenge_data,
        'challenge_id': challenge_data['challenge_id'],
        'difficulty': challenge_data['difficulty'],
        'launcher_url': challenge_data['launcher_url'],
        'download_url': challenge_data.get('download_url'),
        'expires': challenge_data.get('expires', 0)
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


@require_http_methods(["GET"])
def pow_launcher(request, challenge_id):
    """Display PoW launcher page"""
    from core.pow_launcher import TorPoWLauncher, TorPoWService
    
    # Get challenge data
    time_window = int(time.time() // 300)
    challenge_data = {
        'challenge_id': challenge_id,
        'time_window': time_window,
        'difficulty': 4,
        'expires': (time_window + 1) * 300
    }
    
    # Generate launcher HTML
    launcher_html = TorPoWLauncher.create_web_launcher(challenge_data)
    
    return HttpResponse(launcher_html, content_type='text/html')


@require_http_methods(["GET"])
def pow_download_solver(request, challenge_id):
    """Download PoW solver script"""
    from core.pow_launcher import TorPoWLauncher
    
    # Generate solver script
    script = TorPoWLauncher.get_launcher_script(challenge_id)
    
    response = HttpResponse(script, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="pow_solver_{challenge_id}.py"'
    
    return response


@require_http_methods(["GET"])
def pow_get_solution(request, challenge_id):
    """Get pre-computed solution if available"""
    from django.core.cache import cache
    
    solution_key = f"pow:solution:{challenge_id}"
    solution = cache.get(solution_key)
    
    if solution:
        return JsonResponse({
            'status': 'ready',
            'challenge_id': challenge_id,
            'nonce': solution['nonce'],
            'hash': solution['hash'],
            'computed_at': solution['computed_at']
        })
    else:
        # Try to compute it now
        from core.pow_launcher import TorPoWLauncher
        
        time_window = int(time.time() // 300)
        solution = TorPoWLauncher._compute_solution(challenge_id, time_window, 4)
        
        if solution:
            return JsonResponse({
                'status': 'computed',
                'challenge_id': challenge_id,
                'nonce': solution['nonce'],
                'hash': solution['hash']
            })
        else:
            return JsonResponse({
                'status': 'pending',
                'message': 'Solution not yet available. Please use the solver.'
            }, status=202)


@require_http_methods(["GET"])
def pow_solve_endpoint(request, challenge_id):
    """Endpoint that returns a solver script for curl|python3"""
    from core.pow_launcher import TorPoWLauncher
    
    # Return a minimal solver that outputs just the nonce
    script = f"""
import hashlib
challenge_id = "{challenge_id}"
time_window = {int(time.time() // 300)}
difficulty = 4
challenge = f"{{challenge_id}}:{{time_window}}:{{difficulty}}"
target = '0' * difficulty
nonce = 0
while True:
    solution = f"{{challenge}}:{{nonce}}"
    if hashlib.sha256(solution.encode()).hexdigest().startswith(target):
        print(nonce)
        break
    nonce += 1
"""
    
    return HttpResponse(script, content_type='text/plain')