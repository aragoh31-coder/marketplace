from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Count, Q, Avg, F
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.core.paginator import Paginator
from django.core.cache import cache
from django_ratelimit.decorators import ratelimit

from .models import Vendor
from .forms import VendorApplicationForm, ProductForm, VendorSettingsForm
from products.models import Product
from orders.models import Order, OrderItem
from adminpanel.utils import ChartGenerator


@ratelimit(key='ip', rate='10/m', method='GET')
def vendor_list(request):
    vendors = Vendor.objects.filter(
        is_active=True,
        user__is_active=True
    ).order_by('-trust_level')
    
    search = request.GET.get('q')
    if search:
        vendors = vendors.filter(
            Q(user__username__icontains=search) |
            Q(description__icontains=search)
        )
    
    paginator = Paginator(vendors, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'vendors/list.html', {'page_obj': page_obj})


@ratelimit(key='ip', rate='20/m', method='GET')
def vendor_detail(request, pk):
    vendor = get_object_or_404(Vendor, pk=pk, is_approved=True, is_active=True)
    return render(request, 'vendors/detail.html', {'vendor': vendor})


@login_required
@ratelimit(key='user', rate='30/m', method='GET')
def vendor_dashboard(request):
    if not hasattr(request.user, 'vendor'):
        messages.error(request, 'You are not registered as a vendor.')
        return redirect('vendors:apply')
    
    vendor = request.user.vendor
    
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    vendor_orders = Order.objects.filter(
        items__product__vendor=vendor
    ).distinct()
    
    total_sales = vendor_orders.filter(
        status='completed'
    ).count()
    
    week_sales = vendor_orders.filter(
        status='completed',
        created_at__date__gte=week_ago
    ).count()
    
    revenue_stats = vendor_orders.filter(
        status='completed'
    ).aggregate(
        total_btc=Sum('total_btc'),
        total_xmr=Sum('total_xmr')
    )
    
    total_revenue_btc = revenue_stats['total_btc'] or Decimal('0')
    total_revenue_xmr = revenue_stats['total_xmr'] or Decimal('0')
    
    week_revenue = vendor_orders.filter(
        status='completed',
        created_at__date__gte=week_ago
    ).aggregate(
        btc=Sum('total_btc'),
        xmr=Sum('total_xmr')
    )
    
    pending_orders = vendor_orders.filter(
        status__in=['paid', 'created']
    ).count()
    
    active_products = Product.objects.filter(
        vendor=vendor,
        is_active=True
    ).count()
    
    recent_orders = vendor_orders.order_by('-created_at')[:10]
    
    low_stock = Product.objects.filter(
        vendor=vendor,
        is_active=True,
        stock_quantity__lte=5
    ).order_by('stock_quantity')
    
    escrow_stats = vendor_orders.filter(
        status='shipped'
    ).aggregate(
        escrow_btc=Sum('total_btc'),
        escrow_xmr=Sum('total_xmr')
    )
    
    context = {
        'vendor': vendor,
        'total_sales': total_sales,
        'week_sales': week_sales,
        'total_revenue_btc': total_revenue_btc,
        'total_revenue_xmr': total_revenue_xmr,
        'week_revenue_btc': week_revenue['btc'] or Decimal('0'),
        'week_revenue_xmr': week_revenue['xmr'] or Decimal('0'),
        'pending_orders': pending_orders,
        'active_products': active_products,
        'recent_orders': recent_orders,
        'low_stock': low_stock,
        'escrow_btc': escrow_stats['escrow_btc'] or Decimal('0'),
        'escrow_xmr': escrow_stats['escrow_xmr'] or Decimal('0'),
    }
    
    return render(request, 'vendors/dashboard.html', context)


@login_required
def vendor_products(request):
    if not hasattr(request.user, 'vendor'):
        return redirect('vendors:apply')
    
    vendor = request.user.vendor
    products = Product.objects.filter(vendor=vendor).order_by('-created_at')
    
    category = request.GET.get('category')
    status = request.GET.get('status')
    search = request.GET.get('q')
    
    if category:
        products = products.filter(category=category)
    
    if status == 'active':
        products = products.filter(is_active=True)
    elif status == 'inactive':
        products = products.filter(is_active=False)
    
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'vendors/products.html', {
        'page_obj': page_obj,
        'vendor': vendor,
    })

@login_required
def create_product(request):
    if not hasattr(request.user, 'vendor'):
        return redirect('vendors:apply')
    
    vendor = request.user.vendor
    
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.vendor = vendor
            product.save()
            messages.success(request, 'Product created successfully!')
            return redirect('vendors:products')
    else:
        form = ProductForm()
    
    return render(request, 'vendors/create_product.html', {
        'form': form,
        'vendor': vendor,
    })

@login_required
def edit_product(request, product_id):
    if not hasattr(request.user, 'vendor'):
        return redirect('vendors:apply')
    
    vendor = request.user.vendor
    product = get_object_or_404(Product, id=product_id, vendor=vendor)
    
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated successfully!')
            return redirect('vendors:products')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'vendors/edit_product.html', {
        'form': form,
        'product': product,
        'vendor': vendor,
    })

@login_required
def delete_product(request, product_id):
    if not hasattr(request.user, 'vendor'):
        return redirect('vendors:apply')
    
    vendor = request.user.vendor
    product = get_object_or_404(Product, id=product_id, vendor=vendor)
    
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully!')
        return redirect('vendors:products')
    
    return render(request, 'vendors/delete_product.html', {
        'product': product,
        'vendor': vendor,
    })

@login_required
def toggle_product(request, product_id):
    if not hasattr(request.user, 'vendor'):
        return redirect('vendors:apply')
    
    vendor = request.user.vendor
    product = get_object_or_404(Product, id=product_id, vendor=vendor)
    
    product.is_active = not product.is_active
    product.save()
    
    status = 'activated' if product.is_active else 'deactivated'
    messages.success(request, f'Product {status} successfully!')
    
    return redirect('vendors:products')

@login_required
def vendor_orders(request):
    if not hasattr(request.user, 'vendor'):
        return redirect('vendors:apply')
    
    vendor = request.user.vendor
    
    orders = Order.objects.filter(
        items__product__vendor=vendor
    ).distinct().order_by('-created_at')
    
    status = request.GET.get('status')
    if status:
        orders = orders.filter(status=status)
    
    paginator = Paginator(orders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'vendors/orders.html', {
        'page_obj': page_obj,
        'vendor': vendor,
    })

@login_required
def order_detail(request, order_id):
    if not hasattr(request.user, 'vendor'):
        return redirect('vendors:apply')
    
    vendor = request.user.vendor
    order = get_object_or_404(Order, id=order_id)
    
    vendor_items = order.items.filter(product__vendor=vendor)
    
    if not vendor_items.exists():
        messages.error(request, 'You do not have access to this order.')
        return redirect('vendors:orders')
    
    return render(request, 'vendors/order_detail.html', {
        'order': order,
        'vendor_items': vendor_items,
        'vendor': vendor,
    })

@login_required
def ship_order(request, order_id):
    if not hasattr(request.user, 'vendor'):
        return redirect('vendors:apply')
    
    vendor = request.user.vendor
    order = get_object_or_404(Order, id=order_id)
    
    if not order.items.filter(product__vendor=vendor).exists():
        messages.error(request, 'You do not have access to this order.')
        return redirect('vendors:orders')
    
    if request.method == 'POST':
        with transaction.atomic():
            order.status = 'shipped'
            order.shipped_at = timezone.now()
            order.save()
            
            messages.success(request, 'Order marked as shipped!')
    
    return redirect('vendors:order_detail', order_id=order.id)

@login_required
def cancel_order(request, order_id):
    if not hasattr(request.user, 'vendor'):
        return redirect('vendors:apply')
    
    vendor = request.user.vendor
    order = get_object_or_404(Order, id=order_id)
    
    if not order.items.filter(product__vendor=vendor).exists():
        messages.error(request, 'You do not have access to this order.')
        return redirect('vendors:orders')
    
    if order.status in ['created', 'paid']:
        with transaction.atomic():
            order.status = 'cancelled'
            order.save()
            
            for item in order.items.filter(product__vendor=vendor):
                item.product.stock_quantity += item.quantity
                item.product.save()
            
            messages.success(request, 'Order cancelled successfully!')
    else:
        messages.error(request, 'Cannot cancel order in current status.')
    
    return redirect('vendors:orders')

@login_required
def vendor_settings(request):
    if not hasattr(request.user, 'vendor'):
        return redirect('vendors:apply')
    
    vendor = request.user.vendor
    
    if request.method == 'POST':
        form = VendorSettingsForm(request.POST, instance=vendor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Settings updated successfully!')
            return redirect('vendors:dashboard')
    else:
        form = VendorSettingsForm(instance=vendor)
    
    return render(request, 'vendors/settings.html', {
        'form': form,
        'vendor': vendor,
    })

@login_required
def vendor_apply(request):
    if hasattr(request.user, 'vendor'):
        messages.info(request, 'You are already a vendor.')
        return redirect('vendors:dashboard')
    
    if request.method == 'POST':
        form = VendorApplicationForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                vendor = form.save(commit=False)
                vendor.user = request.user
                vendor.save()
                
                request.user.is_vendor = True
                request.user.save()
                
                messages.success(request, 'Vendor application submitted! Your account is now active.')
                return redirect('vendors:dashboard')
    else:
        form = VendorApplicationForm()
    
    return render(request, 'vendors/apply.html', {'form': form})


def vendor_profile(request, vendor_id):
    vendor = get_object_or_404(Vendor, id=vendor_id, is_active=True)
    
    products = Product.objects.filter(
        vendor=vendor,
        is_active=True
    ).order_by('-created_at')
    
    paginator = Paginator(products, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    total_sales = Order.objects.filter(
        items__product__vendor=vendor,
        status='completed'
    ).distinct().count()
    
    return render(request, 'vendors/profile.html', {
        'vendor': vendor,
        'page_obj': page_obj,
        'total_sales': total_sales,
    })
