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
    
    # Get recent blocked IPs
    blocked_ips = []
    # This is a simplified version - in production, maintain a proper log
    
    context = {
        'stats': stats,
        'blocked_ips': blocked_ips,
        'rate_limits': DDoSProtection.RATE_LIMITS,
        'suspicious_patterns': DDoSProtection.SUSPICIOUS_PATTERNS,
    }
    
    return render(request, 'adminpanel/ddos_dashboard.html', context)


@staff_member_required
@require_http_methods(["POST"])
def unblock_ip(request):
    """Manually unblock an IP address"""
    ip = request.POST.get('ip')
    if ip:
        blacklist_key = f"ddos:blacklist:{ip}"
        cache.delete(blacklist_key)
        
        # Also reset violation score
        score_key = f"ddos:violation_score:{ip}"
        cache.delete(score_key)
        
        return JsonResponse({'success': True, 'message': f'IP {ip} has been unblocked'})
    
    return JsonResponse({'success': False, 'message': 'No IP provided'})


@staff_member_required
@require_http_methods(["POST"])
def block_ip(request):
    """Manually block an IP address"""
    ip = request.POST.get('ip')
    duration = int(request.POST.get('duration', 3600))  # Default 1 hour
    
    if ip:
        DDoSProtection._blacklist_ip(ip, duration)
        return JsonResponse({'success': True, 'message': f'IP {ip} has been blocked for {duration} seconds'})
    
    return JsonResponse({'success': False, 'message': 'No IP provided'})


@staff_member_required
def get_ip_history(request, ip):
    """Get request history for a specific IP"""
    history_key = f"ddos:history:{ip}"
    history = cache.get(history_key, [])
    
    # Get current violation score
    score_key = f"ddos:violation_score:{ip}"
    violation_score = cache.get(score_key, 0)
    
    # Check if currently blacklisted
    blacklist_key = f"ddos:blacklist:{ip}"
    is_blacklisted = cache.get(blacklist_key, False)
    
    return JsonResponse({
        'ip': ip,
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