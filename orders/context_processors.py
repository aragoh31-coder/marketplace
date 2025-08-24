from django.db import models

def cart_context(request):
    """Add cart information to template context"""
    if request.user.is_authenticated:
        from .models import Cart
        try:
            cart = Cart.objects.get(user=request.user)
            cart_count = cart.items.aggregate(total=models.Sum('quantity'))['total'] or 0
        except Cart.DoesNotExist:
            cart_count = 0
    else:
        cart_count = 0
    
    return {
        'cart_count': cart_count
    }