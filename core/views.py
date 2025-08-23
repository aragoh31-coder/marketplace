import mimetypes
import os
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.views.decorators.cache import cache_control
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Q
from django.core.paginator import Paginator

# Import models from their respective apps
from products.models import Product, Category
from wallets.models import Wallet, Transaction


@cache_control(max_age=3600)  # Cache for 1 hour
def serve_secure_image(request, path):
    """
    Serve images from secure directory
    Only serves images, nothing else
    """
    if ".." in path or path.startswith("/"):
        raise Http404("Invalid path")

    full_path = settings.SECURE_UPLOAD_ROOT / path

    if not full_path.exists() or not full_path.is_file():
        raise Http404("Image not found")

    # Only serve .jpg files
    if not path.lower().endswith(".jpg"):
        raise Http404("Only JPEG images are served")

    try:
        with open(full_path, "rb") as f:
            content = f.read()

        content_type = "image/jpeg"

        response = HttpResponse(content, content_type=content_type)
        response["X-Content-Type-Options"] = "nosniff"
        response["Content-Security-Policy"] = "default-src 'none'; img-src 'self';"

        return response

    except Exception:
        raise Http404("Error serving image")


def home(request):
    """Regular home view."""
    context = {
        'tor_enabled': False,
        'javascript_disabled': False,
        'external_cdns_disabled': False,
        'analytics_disabled': False,
    }
    return render(request, 'home.html', context)


def tor_safe_home(request):
    """Tor-safe home view that uses Tor-safe templates."""
    context = {
        'tor_enabled': True,
        'javascript_disabled': True,
        'external_cdns_disabled': True,
        'analytics_disabled': True,
    }
    return render(request, 'home_tor_safe.html', context)


def tor_safe_product_list(request):
    """Tor-safe product list view."""
    products = Product.objects.all()
    categories = Category.objects.all()
    
    # Handle search
    search_query = request.GET.get('search', '')
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Handle category filter
    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'products': page_obj,
        'categories': categories,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
        'tor_enabled': True,
        'javascript_disabled': True,
    }
    
    return render(request, 'products/product_list_tor_safe.html', context)


def tor_safe_login(request):
    """Tor-safe login view."""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                next_url = request.POST.get('next', 'home')
                return redirect(next_url)
    else:
        form = AuthenticationForm()
    
    context = {
        'form': form,
        'next': request.GET.get('next', ''),
        'tor_enabled': True,
        'javascript_disabled': True,
    }
    
    return render(request, 'accounts/login_tor_safe.html', context)


def tor_safe_wallet_detail(request):
    """Tor-safe wallet detail view."""
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    
    try:
        wallet = Wallet.objects.get(user=request.user)
        recent_transactions = Transaction.objects.filter(wallet=wallet).order_by('-timestamp')[:10]
        
        # Calculate available balances
        available_btc = wallet.balance_btc - wallet.escrow_btc
        available_xmr = wallet.balance_xmr - wallet.escrow_xmr
        
        context = {
            'wallet': wallet,
            'recent_transactions': recent_transactions,
            'available_btc': available_btc,
            'available_xmr': available_xmr,
            'tor_enabled': True,
            'javascript_disabled': True,
        }
        
        return render(request, 'wallets/wallet_detail_tor_safe.html', context)
        
    except Wallet.DoesNotExist:
        # Create wallet if it doesn't exist
        wallet = Wallet.objects.create(user=request.user)
        return redirect('wallets:wallet_detail')
