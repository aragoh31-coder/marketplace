from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.core.cache import cache
from django.db.models import Count, Avg, Sum
from django.utils import timezone
from django_ratelimit.decorators import ratelimit
from datetime import timedelta

from .models import Vendor, VendorNotification, Feedback, Promotion
from products.models import Product
from orders.models import Order
from adminpanel.utils import ChartGenerator


@ratelimit(key='ip', rate='10/m', method='GET')
def vendor_list(request):
    vendors = Vendor.objects.filter(is_approved=True, is_active=True)
    return render(request, 'vendors/list.html', {'vendors': vendors})


@ratelimit(key='ip', rate='20/m', method='GET')
def vendor_detail(request, pk):
    vendor = get_object_or_404(Vendor, pk=pk, is_approved=True, is_active=True)
    return render(request, 'vendors/detail.html', {'vendor': vendor})


@login_required
@ratelimit(key='user', rate='30/m', method='GET')
def vendor_dashboard(request):
    try:
        vendor = request.user.vendor
    except Vendor.DoesNotExist:
        vendor = None
        return render(request, 'vendors/dashboard.html', {'vendor': vendor})
    
    cache_key = f'vendor_metrics_{vendor.id}'
    metrics = cache.get(cache_key)
    
    if not metrics:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        orders_data = Order.objects.filter(
            items__product__vendor=vendor,
            created_at__date__range=[start_date, end_date]
        ).values('created_at__date').annotate(
            count=Count('id'),
            revenue=Sum('total')
        ).order_by('created_at__date')
        
        metrics = {
            'total_products': vendor.products.filter(is_available=True).count(),
            'total_orders': Order.objects.filter(items__product__vendor=vendor).count(),
            'average_rating': vendor.rating,
            'total_sales': vendor.total_sales,
            'orders_data': list(orders_data),
        }
        
        cache.set(cache_key, metrics, 3600)  # Cache for 1 hour
    
    orders_chart = ChartGenerator.generate_chart(
        metrics['orders_data'], 'count', 'Orders Over Time', 'line'
    )
    revenue_chart = ChartGenerator.generate_chart(
        metrics['orders_data'], 'revenue', 'Revenue Over Time', 'bar'
    )
    
    notifications = vendor.notifications.filter(is_read=False)[:5]
    
    low_stock_products = vendor.products.filter(
        stock_quantity__lte=vendor.low_stock_threshold,
        is_available=True
    )
    
    context = {
        'vendor': vendor,
        'metrics': metrics,
        'orders_chart': orders_chart,
        'revenue_chart': revenue_chart,
        'notifications': notifications,
        'low_stock_products': low_stock_products,
    }
    
    return render(request, 'vendors/dashboard.html', context)


@login_required
@ratelimit(key='user', rate='20/m', method='GET')
def vendor_notifications(request):
    try:
        vendor = request.user.vendor
    except Vendor.DoesNotExist:
        messages.error(request, 'You must be a vendor to access this page.')
        return redirect('home')
    
    notifications = vendor.notifications.all()
    
    if request.GET.get('mark_read'):
        notification_id = request.GET.get('mark_read')
        try:
            notification = notifications.get(id=notification_id)
            notification.mark_as_read()
            messages.success(request, 'Notification marked as read.')
        except VendorNotification.DoesNotExist:
            messages.error(request, 'Notification not found.')
        return redirect('vendors:notifications')
    
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    stats = {
        'total': notifications.count(),
        'unread': notifications.filter(is_read=False).count(),
        'low_stock': notifications.filter(notification_type='low_stock').count(),
        'new_orders': notifications.filter(notification_type='new_order').count(),
    }
    
    return render(request, 'vendors/notifications.html', {
        'vendor': vendor,
        'page_obj': page_obj,
        'stats': stats,
    })


@login_required
@ratelimit(key='user', rate='15/m', method='GET')
def vendor_feedback(request):
    try:
        vendor = request.user.vendor
    except Vendor.DoesNotExist:
        messages.error(request, 'You must be a vendor to access this page.')
        return redirect('home')
    
    feedback_list = vendor.feedback.all().order_by('-created_at')
    
    paginator = Paginator(feedback_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    stats = {
        'total': feedback_list.count(),
        'average_rating': feedback_list.aggregate(avg=Avg('rating'))['avg'] or 0,
        'pending_response': feedback_list.filter(vendor_response='').count(),
    }
    
    return render(request, 'vendors/feedback.html', {
        'vendor': vendor,
        'page_obj': page_obj,
        'stats': stats,
    })


@login_required
@ratelimit(key='user', rate='10/m', method='POST')
def respond_feedback(request, feedback_id):
    try:
        vendor = request.user.vendor
        feedback = get_object_or_404(Feedback, id=feedback_id, vendor=vendor)
        
        if request.method == 'POST':
            response = request.POST.get('response', '').strip()
            if response:
                feedback.vendor_response = response
                feedback.response_date = timezone.now()
                feedback.save()
                messages.success(request, 'Response added successfully.')
            else:
                messages.error(request, 'Response cannot be empty.')
        
        return redirect('vendors:feedback')
        
    except Vendor.DoesNotExist:
        messages.error(request, 'You must be a vendor to access this page.')
        return redirect('home')


@login_required
def vendor_apply(request):
    return render(request, 'vendors/apply.html')
