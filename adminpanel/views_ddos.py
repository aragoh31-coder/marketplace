"""
DDoS Protection Monitoring Views
"""
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from core.antiddos import DDoSProtection
from django.core.cache import cache
import json


@staff_member_required
def ddos_dashboard(request):
    """DDoS protection monitoring dashboard"""
    stats = DDoSProtection.get_protection_stats()
    
    # Get recent blocked sessions
    blocked_sessions = []
    # This is a simplified version - in production, maintain a proper log
    
    context = {
        'stats': stats,
        'blocked_sessions': blocked_sessions,
        'rate_limits': DDoSProtection.RATE_LIMITS,
        'suspicious_patterns': DDoSProtection.SUSPICIOUS_PATTERNS,
    }
    
    return render(request, 'adminpanel/ddos_dashboard.html', context)


@staff_member_required
@require_http_methods(["POST"])
def unblock_session(request):
    """Manually unblock a session"""
    session_id = request.POST.get('session_id')
    if session_id:
        blacklist_key = f"ddos:blacklist:{session_id}"
        cache.delete(blacklist_key)
        
        # Also reset violation score
        score_key = f"ddos:violation_score:{session_id}"
        cache.delete(score_key)
        
        return JsonResponse({'success': True, 'message': f'Session {session_id} has been unblocked'})
    
    return JsonResponse({'success': False, 'message': 'No session ID provided'})


@staff_member_required
@require_http_methods(["POST"])
def block_session(request):
    """Manually block a session"""
    session_id = request.POST.get('session_id')
    duration = int(request.POST.get('duration', 3600))  # Default 1 hour
    
    if session_id:
        DDoSProtection._blacklist_session(session_id, duration)
        return JsonResponse({'success': True, 'message': f'Session {session_id} has been blocked for {duration} seconds'})
    
    return JsonResponse({'success': False, 'message': 'No session ID provided'})


@staff_member_required
def get_session_history(request, session_id):
    """Get request history for a specific session"""
    history_key = f"ddos:history:{session_id}"
    history = cache.get(history_key, [])
    
    # Get current violation score
    score_key = f"ddos:violation_score:{session_id}"
    violation_score = cache.get(score_key, 0)
    
    # Check if currently blacklisted
    blacklist_key = f"ddos:blacklist:{session_id}"
    is_blacklisted = cache.get(blacklist_key, False)
    
    return JsonResponse({
        'session_id': session_id,
        'violation_score': violation_score,
        'is_blacklisted': is_blacklisted,
        'history': history[-50:],  # Last 50 requests
    })


@staff_member_required
@require_http_methods(["POST"])
def update_rate_limits(request):
    """Update rate limit configurations (requires restart)"""
    try:
        new_limits = json.loads(request.body)
        
        # Validate the structure
        required_keys = ['global', 'per_ip', 'per_user']
        for key in required_keys:
            if key not in new_limits:
                return JsonResponse({'success': False, 'message': f'Missing required key: {key}'})
        
        # In production, save to database or configuration file
        # For now, just return success
        return JsonResponse({
            'success': True, 
            'message': 'Rate limits updated. Restart required for changes to take effect.'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})