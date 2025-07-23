from django.conf import settings
import secrets
import time


def captcha_data(request):
    """Context processor for CAPTCHA data"""
    if not hasattr(request, '_captcha_data'):
        num1 = secrets.randbelow(10) + 1
        num2 = secrets.randbelow(10) + 1
        answer = num1 + num2
        
        timestamp = time.time()
        
        form_hash = secrets.token_urlsafe(16)
        
        request._captcha_data = {
            'math_challenge': f"{num1} + {num2}",
            'math_answer': answer,
            'form_timestamp': timestamp,
            'form_hash': form_hash,
        }
        
        request.session['captcha_answer'] = answer
        request.session['captcha_timestamp'] = timestamp
        request.session['captcha_hash'] = form_hash
    
    return {
        'captcha_data': request._captcha_data
    }
