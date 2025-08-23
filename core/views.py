import mimetypes
import os
from pathlib import Path
import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse
from django.views.decorators.cache import cache_control
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Q, Sum, Count, Avg, Case, When
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

# Import models from their respective apps
from products.models import Product, Category
from wallets.models import Wallet, Transaction
from .services.loyalty_service import LoyaltyService
from .services.vendor_analytics_service import VendorAnalyticsService
from .services.recommendation_service import RecommendationService
from .services.price_prediction_service import PricePredictionService
from .services.user_preference_service import UserPreferenceService
from .services.search_service import SearchService
from .services.dispute_service import DisputeService
from .models import (
    LoyaltyPoints, LoyaltyTransaction, VendorAnalytics, ProductRecommendation,
    PricePrediction, UserPreferenceProfile, SearchQuery
)
from orders.models import Order


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
    """Tor-safe home page."""
    products = Product.objects.filter(active=True).order_by('-created_at')[:8]
    context = {
        'products': products,
        'page_title': 'Welcome to the Marketplace'
    }
    return render(request, 'home_tor_safe.html', context)


def tor_safe_product_list(request):
    """Tor-safe product listing page."""
    products = Product.objects.filter(active=True).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'products': page_obj,
        'page_title': 'All Products'
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


@login_required
def loyalty_dashboard(request):
    """User loyalty dashboard showing points, level, and history."""
    try:
        # Get or create loyalty points
        loyalty_points, created = LoyaltyPoints.objects.get_or_create(
            user=request.user,
            defaults={'points': 0, 'level': 'bronze'}
        )
        
        # Get transaction history
        transactions = LoyaltyTransaction.objects.filter(user=request.user).order_by('-created_at')[:20]
        
        # Get available rewards
        loyalty_service = LoyaltyService()
        available_rewards = loyalty_service.get_available_rewards(request.user)
        
        context = {
            'loyalty_points': loyalty_points,
            'transactions': transactions,
            'available_rewards': available_rewards,
            'page_title': 'Loyalty Dashboard'
        }
        
        return render(request, 'core/loyalty_dashboard.html', context)
        
    except Exception as e:
        messages.error(request, f"Error loading loyalty dashboard: {str(e)}")
        return redirect('home')


@login_required
def vendor_analytics_dashboard(request):
    """Vendor analytics dashboard."""
    try:
        analytics_service = VendorAnalyticsService()
        dashboard_data = analytics_service.get_vendor_dashboard(request.user)
        
        # Store analytics in database for caching
        for data_type, data in dashboard_data.items():
            VendorAnalytics.objects.update_or_create(
                vendor=request.user,
                data_type=data_type,
                period_start=timezone.now() - timezone.timedelta(days=30),
                period_end=timezone.now(),
                defaults={
                    'data': data,
                    'expires_at': timezone.now() + timezone.timedelta(hours=24)
                }
            )
        
        context = {
            'dashboard_data': dashboard_data,
            'page_title': 'Vendor Analytics'
        }
        
        return render(request, 'core/vendor_analytics_dashboard.html', context)
        
    except Exception as e:
        messages.error(request, f"Error loading analytics dashboard: {str(e)}")
        return redirect('home')


@login_required
def product_recommendations(request):
    """User product recommendations page."""
    try:
        recommendation_service = RecommendationService()
        recommendations = recommendation_service.get_recommendations_for_user(request.user)
        
        # Store recommendations in database
        ProductRecommendation.objects.filter(user=request.user).delete()
        for rec in recommendations[:20]:
            ProductRecommendation.objects.create(
                user=request.user,
                product=rec['product'],
                recommendation_type=rec['type'],
                confidence_score=rec['confidence'],
                explanation=rec['explanation'],
                expires_at=timezone.now() + timezone.timedelta(days=7)
            )
        
        context = {
            'recommendations': recommendations,
            'page_title': 'Product Recommendations'
        }
        
        return render(request, 'core/product_recommendations.html', context)
        
    except Exception as e:
        messages.error(request, f"Error loading recommendations: {str(e)}")
        return redirect('home')


@login_required
def price_predictions(request):
    """Price predictions for products."""
    try:
        price_service = PricePredictionService()
        
        # Get user's products if vendor, or all products if buyer
        if hasattr(request.user, 'vendor_profile'):
            products = Product.objects.filter(vendor=request.user, active=True)
        else:
            products = Product.objects.filter(active=True)[:20]  # Limit for buyers
        
        predictions = []
        for product in products:
            try:
                prediction_data = price_service.predict_optimal_price(product)
                predictions.append({
                    'product': product,
                    'prediction': prediction_data
                })
                
                # Store prediction in database
                PricePrediction.objects.update_or_create(
                    product=product,
                    prediction_type='optimal',
                    predicted_at=timezone.now(),
                    defaults={
                        'predicted_price': prediction_data['optimal_price'],
                        'confidence_score': prediction_data['confidence_score'],
                        'market_conditions': prediction_data.get('market_conditions', {}),
                        'factors': prediction_data.get('factors', {}),
                        'valid_until': timezone.now() + timezone.timedelta(days=30)
                    }
                )
                
            except Exception as e:
                print(f"Error predicting price for product {product.name}: {str(e)}")
                continue
        
        context = {
            'predictions': predictions,
            'page_title': 'Price Predictions'
        }
        
        return render(request, 'core/price_predictions.html', context)
        
    except Exception as e:
        messages.error(request, f"Error loading price predictions: {str(e)}")
        return redirect('home')


@login_required
def user_preferences(request):
    """User preference profile and insights."""
    try:
        preference_service = UserPreferenceService()
        profile_data = preference_service.build_user_profile(request.user)
        
        # Get or create preference profile
        profile, created = UserPreferenceProfile.objects.get_or_create(
            user=request.user,
            defaults={
                'purchase_patterns': profile_data.get('purchase_patterns', {}),
                'price_sensitivity': profile_data.get('price_sensitivity', 'medium'),
                'category_affinity': profile_data.get('category_affinity', {}),
                'vendor_preferences': profile_data.get('vendor_preferences', {}),
                'temporal_patterns': profile_data.get('temporal_patterns', {}),
                'risk_profile': profile_data.get('risk_profile', 'moderate'),
                'loyalty_indicators': profile_data.get('loyalty_indicators', {}),
                'churn_risk': profile_data.get('churn_risk', 0.5)
            }
        )
        
        if not created:
            profile.purchase_patterns = profile_data.get('purchase_patterns', {})
            profile.price_sensitivity = profile_data.get('price_sensitivity', 'medium')
            profile.category_affinity = profile_data.get('category_affinity', {})
            profile.vendor_preferences = profile_data.get('vendor_preferences', {})
            profile.temporal_patterns = profile_data.get('temporal_patterns', {})
            profile.risk_profile = profile_data.get('risk_profile', 'moderate')
            profile.loyalty_indicators = profile_data.get('loyalty_indicators', {})
            profile.churn_risk = profile_data.get('churn_risk', 0.5)
            profile.save()
        
        # Get personalized insights
        insights = preference_service.get_personalized_insights(request.user)
        
        context = {
            'profile': profile,
            'profile_data': profile_data,
            'insights': insights,
            'page_title': 'User Preferences'
        }
        
        return render(request, 'core/user_preferences.html', context)
        
    except Exception as e:
        messages.error(request, f"Error loading user preferences: {str(e)}")
        return redirect('home')


@login_required
def advanced_search(request):
    """Advanced search with filters and personalization."""
    try:
        search_service = SearchService()
        
        # Get search parameters
        query = request.GET.get('q', '')
        category = request.GET.get('category', '')
        min_price = request.GET.get('min_price', '')
        max_price = request.GET.get('max_price', '')
        sort_by = request.GET.get('sort', 'relevance')
        
        # Build filters
        filters = {}
        if category:
            filters['category'] = category
        if min_price:
            filters['min_price'] = float(min_price)
        if max_price:
            filters['max_price'] = float(max_price)
        
        # Perform search
        if query:
            search_results = search_service.search_products(
                query=query,
                filters=filters,
                user=request.user if request.user.is_authenticated else None,
                sort_by=sort_by
            )
            
            # Log search query
            SearchQuery.objects.create(
                user=request.user if request.user.is_authenticated else None,
                query=query,
                filters=filters,
                results_count=len(search_results),
                session_id=request.session.session_key or '',
                ip_address=request.session.session_key if hasattr(request, 'session') and request.session.session_key else 'no-session',  # Using session ID
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Convert to QuerySet for pagination
            product_ids = [result['product'].id for result in search_results]
            products = Product.objects.filter(id__in=product_ids).order_by('-created_at')
            
            # Preserve search order
            preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(product_ids)])
            products = products.order_by(preserved)
            
        else:
            products = Product.objects.filter(active=True).order_by('-created_at')
            search_results = []
        
        # Pagination
        paginator = Paginator(products, 12)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Get search suggestions
        suggestions = search_service.get_search_suggestions(query) if query else []
        
        context = {
            'products': page_obj,
            'search_results': search_results,
            'query': query,
            'filters': filters,
            'suggestions': suggestions,
            'sort_by': sort_by,
            'page_title': f'Search Results for "{query}"' if query else 'Advanced Search'
        }
        
        return render(request, 'core/advanced_search.html', context)
        
    except Exception as e:
        messages.error(request, f"Error performing search: {str(e)}")
        return redirect('home')


@login_required
def loyalty_rewards(request):
    """Loyalty rewards redemption page."""
    try:
        loyalty_service = LoyaltyService()
        available_rewards = loyalty_service.get_available_rewards(request.user)
        
        if request.method == 'POST':
            reward_id = request.POST.get('reward_id')
            if reward_id:
                try:
                    result = loyalty_service.redeem_reward(request.user, reward_id)
                    if result['success']:
                        messages.success(request, f"Reward redeemed successfully! {result['message']}")
                    else:
                        messages.error(request, f"Failed to redeem reward: {result['message']}")
                except Exception as e:
                    messages.error(request, f"Error redeeming reward: {str(e)}")
                
                return redirect('loyalty_rewards')
        
        context = {
            'available_rewards': available_rewards,
            'page_title': 'Loyalty Rewards'
        }
        
        return render(request, 'core/loyalty_rewards.html', context)
        
    except Exception as e:
        messages.error(request, f"Error loading loyalty rewards: {str(e)}")
        return redirect('home')


@login_required
def dispute_management(request):
    """User dispute management page."""
    try:
        from disputes.models import Dispute
        
        # Get user's disputes
        if hasattr(request.user, 'vendor_profile'):
            disputes = Dispute.objects.filter(vendor=request.user).order_by('-created_at')
        else:
            disputes = Dispute.objects.filter(buyer=request.user).order_by('-created_at')
        
        # Get dispute service for automated resolution
        dispute_service = DisputeService()
        
        context = {
            'disputes': disputes,
            'page_title': 'Dispute Management'
        }
        
        return render(request, 'core/dispute_management.html', context)
        
    except Exception as e:
        messages.error(request, f"Error loading dispute management: {str(e)}")
        return redirect('home')


@login_required
def system_insights(request):
    """System insights and analytics for users."""
    try:
        # Get user's activity summary
        user_orders = Order.objects.filter(buyer=request.user)
        total_spent = user_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        order_count = user_orders.count()
        
        # Get loyalty status
        loyalty_points = LoyaltyPoints.objects.filter(user=request.user).first()
        
        # Get recent recommendations
        recent_recommendations = ProductRecommendation.objects.filter(
            user=request.user,
            expires_at__gt=timezone.now()
        ).order_by('-confidence_score')[:5]
        
        # Get search history
        search_history = SearchQuery.objects.filter(
            user=request.user
        ).order_by('-created_at')[:10]
        
        context = {
            'total_spent': total_spent,
            'order_count': order_count,
            'loyalty_points': loyalty_points,
            'recent_recommendations': recent_recommendations,
            'search_history': search_history,
            'page_title': 'System Insights'
        }
        
        return render(request, 'core/system_insights.html', context)
        
    except Exception as e:
        messages.error(request, f"Error loading system insights: {str(e)}")
        return redirect('home')


# API endpoints for AJAX requests (if needed in future)
@csrf_exempt
@require_http_methods(["POST"])
def update_user_preferences(request):
    """Update user preferences via AJAX."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        data = json.loads(request.body)
        
        # Update preference profile
        profile, created = UserPreferenceProfile.objects.get_or_create(user=request.user)
        
        if 'price_sensitivity' in data:
            profile.price_sensitivity = data['price_sensitivity']
        if 'risk_profile' in data:
            profile.risk_profile = data['risk_profile']
        
        profile.save()
        
        return JsonResponse({'success': True, 'message': 'Preferences updated'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def refresh_recommendations(request):
    """Refresh user recommendations via AJAX."""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        recommendation_service = RecommendationService()
        recommendations = recommendation_service.get_recommendations_for_user(request.user)
        
        return JsonResponse({
            'success': True,
            'recommendations': [
                {
                    'product_name': rec['product'].name,
                    'product_url': rec['product'].get_absolute_url(),
                    'confidence': rec['confidence'],
                    'explanation': rec['explanation']
                }
                for rec in recommendations[:10]
            ]
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
