from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.db.models import Prefetch, Count, Case, When, IntegerField, Q
from django.views.decorators.cache import cache_page
from django.db import models

from .models import Category, Product
from marketplace.cache_config import cache_page_tor_safe, CacheTimeouts


@cache_page_tor_safe(CacheTimeouts.PRODUCT_LIST)
def product_list(request):
    """Enhanced product list with intelligent search"""
    # Get search parameters
    search_query = request.GET.get('search', '').strip()
    category_filter = request.GET.get("category")
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    in_stock = request.GET.get('in_stock') == 'on'
    sort_by = request.GET.get('sort', '')
    
    # Prepare filters
    filters = {}
    if category_filter:
        filters['category_id'] = category_filter
    if min_price:
        try:
            filters['min_price'] = float(min_price)
        except ValueError:
            pass
    if max_price:
        try:
            filters['max_price'] = float(max_price)
        except ValueError:
            pass
    if in_stock:
        filters['in_stock'] = True
    
    # Use search service if query provided, otherwise basic filtering
    if search_query:
        from core.services.search_service import SearchService
        search_service = SearchService()
        
        user_id = str(request.user.id) if request.user.is_authenticated else None
        products = search_service.search_products(search_query, user_id, filters)
        
        # Convert to QuerySet for pagination
        product_ids = [p.id for p in products]
        products = Product.objects.filter(id__in=product_ids, is_available=True)
        
        # Preserve search order
        if product_ids:
            case = []
            for i, pid in enumerate(product_ids):
                case.append(models.When(pk=pid, then=i))
            products = products.annotate(
                search_order=models.Case(*case, output_field=models.IntegerField())
            ).order_by('search_order')
    else:
        # Basic filtering
        products = Product.objects.filter(is_available=True)
        
        if category_filter:
            products = products.filter(category_id=category_filter)
        
        if min_price:
            try:
                products = products.filter(price_btc__gte=float(min_price))
            except ValueError:
                pass
        
        if max_price:
            try:
                products = products.filter(price_btc__lte=float(max_price))
            except ValueError:
                pass
        
        if in_stock:
            products = products.filter(stock_quantity__gt=0)
    
    # Apply sorting
    if sort_by == 'price_low':
        products = products.order_by('price_btc')
    elif sort_by == 'price_high':
        products = products.order_by('-price_btc')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    elif sort_by == 'popular':
        # Order by order count (requires annotation)
        from django.db.models import Count
        products = products.annotate(
            order_count=Count('orderitem', distinct=True)
        ).order_by('-order_count')
    elif sort_by == 'rating':
        # Order by vendor trust level
        products = products.select_related('vendor').order_by('-vendor__trust_level')
    else:
        # Default ordering
        products = products.order_by('-created_at')
    
    # Include related data
    products = products.select_related('category', 'vendor')
    
    # Get categories with product count
    categories = Category.objects.annotate(
        product_count=Count('product', filter=models.Q(product__is_available=True))
    ).filter(product_count__gt=0).order_by('name')
    
    # Paginate
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'categories': categories,
        'search_query': search_query,
    }
    
    return render(request, 'products/list_advanced.html', context)


def product_detail(request, pk):
    # Optimized query to avoid N+1 queries
    product = get_object_or_404(
        Product.objects.select_related('vendor', 'vendor__user', 'category'),
        pk=pk,
        is_available=True
    )
    
    # Get related products efficiently
    related_products = Product.objects.filter(
        category=product.category,
        is_available=True
    ).exclude(
        pk=pk
    ).select_related(
        'vendor', 'category'
    )[:4]
    
    context = {
        "product": product,
        "related_products": related_products
    }
    return render(request, "products/detail.html", context)


def products_by_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    products = Product.objects.filter(category=category, is_available=True).order_by('-created_at')

    paginator = Paginator(products, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "products/list.html", {"page_obj": page_obj, "category": category})
