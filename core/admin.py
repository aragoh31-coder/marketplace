import json

from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import path
from django.utils.html import format_html
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from datetime import timedelta

from .design_system import get_design_system
from .models import (
    BroadcastMessage, SystemSettings, SecurityLog, LoyaltyPoints, 
    LoyaltyTransaction, VendorAnalytics, ProductRecommendation, 
    PricePrediction, UserPreferenceProfile, SearchQuery, DisputeArbitration
)


@admin.register(admin.models.LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    # to disable the 'add' action
    def has_add_permission(self, request):
        return False

    # to disable the 'delete' action
    def has_delete_permission(self, request, obj=None):
        return False

    # to disable the 'change' action
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(BroadcastMessage)
class BroadcastMessageAdmin(admin.ModelAdmin):
    list_display = ['title', 'priority', 'target_audience', 'active', 'created_at', 'expires_at']
    list_filter = ['priority', 'target_audience', 'active', 'created_at']
    search_fields = ['title', 'content']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'description', 'updated_at']
    search_fields = ['key', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'user', 'ip_address', 'severity', 'timestamp']
    list_filter = ['severity', 'action', 'timestamp']
    search_fields = ['action', 'user__username', 'ip_address']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'


@admin.register(LoyaltyPoints)
class LoyaltyPointsAdmin(admin.ModelAdmin):
    list_display = ['user', 'level', 'points', 'total_earned', 'total_spent', 'last_activity']
    list_filter = ['level', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'last_activity']
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_type', 'points', 'reason', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['user__username', 'reason']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'order')


@admin.register(VendorAnalytics)
class VendorAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['vendor', 'data_type', 'period_start', 'period_end', 'created_at', 'is_expired_display']
    list_filter = ['data_type', 'created_at', 'period_start']
    search_fields = ['vendor__username', 'vendor__email']
    readonly_fields = ['created_at', 'expires_at']
    date_hierarchy = 'created_at'
    
    def is_expired_display(self, obj):
        if obj.is_expired():
            return format_html('<span style="color: red;">Expired</span>')
        return format_html('<span style="color: green;">Active</span>')
    is_expired_display.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('vendor')


@admin.register(ProductRecommendation)
class ProductRecommendationAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'recommendation_type', 'confidence_score', 'created_at', 'is_expired_display']
    list_filter = ['recommendation_type', 'created_at']
    search_fields = ['user__username', 'product__name']
    readonly_fields = ['created_at', 'expires_at']
    date_hierarchy = 'created_at'
    
    def is_expired_display(self, obj):
        if obj.is_expired():
            return format_html('<span style="color: red;">Expired</span>')
        return format_html('<span style="color: green;">Active</span>')
    is_expired_display.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'product')


@admin.register(PricePrediction)
class PricePredictionAdmin(admin.ModelAdmin):
    list_display = ['product', 'prediction_type', 'predicted_price', 'confidence_score', 'predicted_at', 'is_valid_display']
    list_filter = ['prediction_type', 'predicted_at']
    search_fields = ['product__name']
    readonly_fields = ['predicted_at']
    date_hierarchy = 'predicted_at'
    
    def is_valid_display(self, obj):
        if obj.is_valid():
            return format_html('<span style="color: green;">Valid</span>')
        return format_html('<span style="color: red;">Expired</span>')
    is_valid_display.short_description = 'Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')


@admin.register(UserPreferenceProfile)
class UserPreferenceProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'price_sensitivity', 'risk_profile', 'churn_risk', 'last_updated']
    list_filter = ['price_sensitivity', 'risk_profile', 'created_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'last_updated']
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ['query', 'user', 'results_count', 'ip_address', 'created_at']
    list_filter = ['created_at']
    search_fields = ['query', 'user__username', 'ip_address']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(DisputeArbitration)
class DisputeArbitrationAdmin(admin.ModelAdmin):
    list_display = ['dispute', 'decision', 'confidence_score', 'automated', 'created_at']
    list_filter = ['decision', 'automated', 'created_at']
    search_fields = ['dispute__id', 'arbitrator__username']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('dispute', 'arbitrator')


# Analytics Dashboard Admin
class AnalyticsDashboardAdmin(admin.ModelAdmin):
    """Custom admin interface for analytics dashboard."""
    change_list_template = "admin/analytics_dashboard_change_list.html"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("refresh-analytics/", self.refresh_analytics, name="refresh-analytics"),
            path("export-analytics/", self.export_analytics, name="export-analytics"),
        ]
        return custom_urls + urls
    
    def refresh_analytics(self, request):
        """Refresh analytics data."""
        try:
            # Trigger analytics refresh tasks
            from core.tasks import refresh_all_analytics
            refresh_all_analytics.delay()
            messages.success(request, "Analytics refresh initiated successfully!")
        except Exception as e:
            messages.error(request, f"Error refreshing analytics: {str(e)}")
        return HttpResponseRedirect("../")
    
    def export_analytics(self, request):
        """Export analytics data."""
        try:
            # Generate analytics export
            from core.tasks import export_analytics_data
            export_analytics_data.delay()
            messages.success(request, "Analytics export initiated successfully!")
        except Exception as e:
            messages.error(request, f"Error exporting analytics: {str(e)}")
        return HttpResponseRedirect("../")
    
    def changelist_view(self, request, extra_context=None):
        """Custom changelist view to show analytics dashboard."""
        # Get summary statistics
        extra_context = extra_context or {}
        
        # Loyalty statistics
        loyalty_stats = {
            'total_users': LoyaltyPoints.objects.count(),
            'total_points': LoyaltyPoints.objects.aggregate(Sum('points'))['points__sum'] or 0,
            'avg_points': LoyaltyPoints.objects.aggregate(Avg('points'))['points__avg'] or 0,
            'top_level': LoyaltyPoints.objects.values('level').annotate(count=Count('id')).order_by('-count').first()
        }
        
        # Search statistics
        search_stats = {
            'total_searches': SearchQuery.objects.count(),
            'today_searches': SearchQuery.objects.filter(
                created_at__date=timezone.now().date()
            ).count(),
            'avg_results': SearchQuery.objects.aggregate(Avg('results_count'))['results_count__avg'] or 0
        }
        
        # Recommendation statistics
        rec_stats = {
            'total_recommendations': ProductRecommendation.objects.count(),
            'active_recommendations': ProductRecommendation.objects.filter(
                expires_at__gt=timezone.now()
            ).count(),
            'avg_confidence': ProductRecommendation.objects.aggregate(
                Avg('confidence_score')
            )['confidence_score__avg'] or 0
        }
        
        # Dispute arbitration statistics
        dispute_stats = {
            'total_arbitrations': DisputeArbitration.objects.count(),
            'automated_decisions': DisputeArbitration.objects.filter(automated=True).count(),
            'avg_confidence': DisputeArbitration.objects.aggregate(
                Avg('confidence_score')
            )['confidence_score__avg'] or 0
        }
        
        extra_context.update({
            'loyalty_stats': loyalty_stats,
            'search_stats': search_stats,
            'rec_stats': rec_stats,
            'dispute_stats': dispute_stats,
        })
        
        return super().changelist_view(request, extra_context)


# Note: DesignSystemAdmin is not a model, so we don't register it directly
# It's used as a custom admin interface for the design system

# Note: All models are now registered using @admin.register decorators above
# No need for additional admin.site.register() calls
