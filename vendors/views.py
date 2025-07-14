from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Vendor


def vendor_list(request):
    vendors = Vendor.objects.filter(is_approved=True, is_active=True)
    return render(request, 'vendors/list.html', {'vendors': vendors})


def vendor_detail(request, pk):
    vendor = get_object_or_404(Vendor, pk=pk, is_approved=True, is_active=True)
    return render(request, 'vendors/detail.html', {'vendor': vendor})


@login_required
def vendor_dashboard(request):
    try:
        vendor = request.user.vendor
    except Vendor.DoesNotExist:
        vendor = None
    return render(request, 'vendors/dashboard.html', {'vendor': vendor})


@login_required
def vendor_apply(request):
    return render(request, 'vendors/apply.html')
