from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.db.models import Prefetch, Count
from django.views.decorators.cache import cache_page

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
            from django.db.models import Case, When, IntegerField
            ordering = [When(pk=pid, then=pos) for pos, pid in enumerate(product_ids)]
            products = products.annotate(
                search_order=Case(*ordering, output_field=IntegerField())
            ).order_by('search_order')
    else:
        # Basic filtering without search - optimized query
        products = Product.objects.filter(is_available=True).select_related(
            "vendor", "vendor__user", "category"
        ).order_by('-created_at')
        
        if category_filter:
            products = products.filter(category_id=category_filter)
        if filters.get('min_price'):
            products = products.filter(price_btc__gte=filters['min_price'])
        if filters.get('max_price'):
            products = products.filter(price_btc__lte=filters['max_price'])
        if filters.get('in_stock'):
            products = products.filter(stock_quantity__gt=0)

    # Get all categories for filter dropdown
    categories = Category.objects.all()

    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj, 
        "categories": categories, 
        "selected_category": category_filter,
        "search_query": search_query,
        "filters": {
            'min_price': min_price,
            'max_price': max_price,
            'in_stock': in_stock,
        },
        "total_results": products.count() if hasattr(products, 'count') else len(products)
    }

    return render(request, "products/list.html", context)


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
