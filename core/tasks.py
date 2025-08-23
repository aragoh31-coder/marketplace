import json
import csv
from datetime import datetime, timedelta
from io import StringIO

from celery import shared_task
from django.utils import timezone
from django.db.models import Q, Sum, Count, Avg
from django.core.mail import send_mail
from django.conf import settings

from .models import (
    LoyaltyPoints, LoyaltyTransaction, VendorAnalytics, ProductRecommendation,
    PricePrediction, UserPreferenceProfile, SearchQuery, DisputeArbitration
)
from .services.loyalty_service import LoyaltyService
from .services.vendor_analytics_service import VendorAnalyticsService
from .services.recommendation_service import RecommendationService
from .services.price_prediction_service import PricePredictionService
from .services.user_preference_service import UserPreferenceService
from .services.search_service import SearchService
from .services.dispute_service import DisputeService


@shared_task
def refresh_all_analytics():
    """Refresh all analytics data for vendors."""
    try:
        analytics_service = VendorAnalyticsService()
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Get all vendor users
        vendors = User.objects.filter(is_staff=False, is_superuser=False)
        
        for vendor in vendors:
            try:
                # Generate fresh analytics
                dashboard_data = analytics_service.get_vendor_dashboard(vendor)
                
                # Store in database for caching
                for data_type, data in dashboard_data.items():
                    VendorAnalytics.objects.update_or_create(
                        vendor=vendor,
                        data_type=data_type,
                        period_start=timezone.now() - timedelta(days=30),
                        period_end=timezone.now(),
                        defaults={
                            'data': data,
                            'expires_at': timezone.now() + timedelta(hours=24)
                        }
                    )
                
                print(f"Refreshed analytics for vendor: {vendor.username}")
                
            except Exception as e:
                print(f"Error refreshing analytics for vendor {vendor.username}: {str(e)}")
                continue
        
        return f"Analytics refresh completed for {vendors.count()} vendors"
        
    except Exception as e:
        print(f"Error in refresh_all_analytics: {str(e)}")
        raise


@shared_task
def export_analytics_data():
    """Export analytics data to CSV format."""
    try:
        # Create CSV data
        csv_data = StringIO()
        writer = csv.writer(csv_data)
        
        # Write headers
        writer.writerow([
            'Data Type', 'Vendor', 'Period Start', 'Period End', 'Data Summary'
        ])
        
        # Export vendor analytics
        analytics = VendorAnalytics.objects.all().select_related('vendor')
        for analytic in analytics:
            data_summary = str(analytic.data)[:100] + "..." if len(str(analytic.data)) > 100 else str(analytic.data)
            writer.writerow([
                analytic.data_type,
                analytic.vendor.username,
                analytic.period_start.strftime('%Y-%m-%d %H:%M:%S'),
                analytic.period_end.strftime('%Y-%m-%d %H:%M:%S'),
                data_summary
            ])
        
        # Export loyalty data
        writer.writerow([])
        writer.writerow(['LOYALTY DATA'])
        writer.writerow(['User', 'Level', 'Points', 'Total Earned', 'Total Spent'])
        
        loyalty_data = LoyaltyPoints.objects.all().select_related('user')
        for loyalty in loyalty_data:
            writer.writerow([
                loyalty.user.username,
                loyalty.level,
                loyalty.points,
                loyalty.total_earned,
                loyalty.total_spent
            ])
        
        # Export search data
        writer.writerow([])
        writer.writerow(['SEARCH DATA'])
        writer.writerow(['Query', 'User', 'Results Count', 'Date'])
        
        search_data = SearchQuery.objects.all().select_related('user')[:1000]  # Limit to last 1000
        for search in search_data:
            writer.writerow([
                search.query,
                search.user.username if search.user else 'Anonymous',
                search.results_count,
                search.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        # Save to file or send via email
        csv_content = csv_data.getvalue()
        csv_data.close()
        
        # For now, just print the content (in production, save to file or send via email)
        print("Analytics export completed")
        print(f"Total records exported: {analytics.count() + loyalty_data.count() + search_data.count()}")
        
        return f"Analytics export completed with {analytics.count() + loyalty_data.count() + search_data.count()} records"
        
    except Exception as e:
        print(f"Error in export_analytics_data: {str(e)}")
        raise


@shared_task
def calculate_loyalty_points_for_user(user_id):
    """Calculate and update loyalty points for a specific user."""
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.get(id=user_id)
        loyalty_service = LoyaltyService()
        
        # Calculate points
        points, level = loyalty_service.calculate_user_points(user)
        
        # Update or create loyalty record
        loyalty_points, created = LoyaltyPoints.objects.get_or_create(
            user=user,
            defaults={
                'points': points,
                'level': level,
                'total_earned': points,
                'total_spent': 0
            }
        )
        
        if not created:
            loyalty_points.points = points
            loyalty_points.level = level
            loyalty_points.save()
        
        print(f"Updated loyalty points for {user.username}: {points} points, {level} level")
        return f"Loyalty points updated for {user.username}"
        
    except Exception as e:
        print(f"Error calculating loyalty points for user {user_id}: {str(e)}")
        raise


@shared_task
def refresh_user_recommendations(user_id=None):
    """Refresh product recommendations for users."""
    try:
        recommendation_service = RecommendationService()
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if user_id:
            users = User.objects.filter(id=user_id)
        else:
            # Get active users (have made purchases in last 90 days)
            users = User.objects.filter(
                orders__created_at__gte=timezone.now() - timedelta(days=90)
            ).distinct()
        
        for user in users:
            try:
                # Get recommendations
                recommendations = recommendation_service.get_recommendations_for_user(user)
                
                # Clear old recommendations
                ProductRecommendation.objects.filter(user=user).delete()
                
                # Store new recommendations
                for rec in recommendations[:20]:  # Store top 20
                    ProductRecommendation.objects.create(
                        user=user,
                        product=rec['product'],
                        recommendation_type=rec['type'],
                        confidence_score=rec['confidence'],
                        explanation=rec['explanation'],
                        expires_at=timezone.now() + timedelta(days=7)
                    )
                
                print(f"Refreshed recommendations for user: {user.username}")
                
            except Exception as e:
                print(f"Error refreshing recommendations for user {user.username}: {str(e)}")
                continue
        
        return f"Recommendations refresh completed for {users.count()} users"
        
    except Exception as e:
        print(f"Error in refresh_user_recommendations: {str(e)}")
        raise


@shared_task
def update_price_predictions():
    """Update price predictions for all products."""
    try:
        price_service = PricePredictionService()
        from products.models import Product
        
        products = Product.objects.filter(active=True)
        
        for product in products:
            try:
                # Get price prediction
                prediction_data = price_service.predict_optimal_price(product)
                
                # Store prediction
                PricePrediction.objects.create(
                    product=product,
                    predicted_price=prediction_data['optimal_price'],
                    confidence_score=prediction_data['confidence_score'],
                    prediction_type='optimal',
                    market_conditions=prediction_data.get('market_conditions', {}),
                    factors=prediction_data.get('factors', {}),
                    valid_until=timezone.now() + timedelta(days=30)
                )
                
                print(f"Updated price prediction for product: {product.name}")
                
            except Exception as e:
                print(f"Error updating price prediction for product {product.name}: {str(e)}")
                continue
        
        return f"Price predictions updated for {products.count()} products"
        
    except Exception as e:
        print(f"Error in update_price_predictions: {str(e)}")
        raise


@shared_task
def build_user_preference_profiles():
    """Build or update user preference profiles."""
    try:
        preference_service = UserPreferenceService()
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Get users with activity
        users = User.objects.filter(
            orders__created_at__gte=timezone.now() - timedelta(days=365)
        ).distinct()
        
        for user in users:
            try:
                # Build profile
                profile_data = preference_service.build_user_profile(user)
                
                # Update or create profile
                profile, created = UserPreferenceProfile.objects.get_or_create(
                    user=user,
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
                
                print(f"Updated preference profile for user: {user.username}")
                
            except Exception as e:
                print(f"Error updating preference profile for user {user.username}: {str(e)}")
                continue
        
        return f"Preference profiles updated for {users.count()} users"
        
    except Exception as e:
        print(f"Error in build_user_preference_profiles: {str(e)}")
        raise


@shared_task
def process_pending_disputes():
    """Process pending disputes with automated arbitration."""
    try:
        dispute_service = DisputeService()
        from disputes.models import Dispute
        
        # Get pending disputes
        pending_disputes = Dispute.objects.filter(
            status='pending',
            created_at__lte=timezone.now() - timedelta(days=3)  # Wait 3 days
        )
        
        processed_count = 0
        
        for dispute in pending_disputes:
            try:
                # Attempt automated resolution
                result = dispute_service.auto_resolve_dispute(dispute)
                
                if result['resolved']:
                    processed_count += 1
                    print(f"Automatically resolved dispute {dispute.id}")
                else:
                    print(f"Dispute {dispute.id} requires manual review: {result['reason']}")
                
            except Exception as e:
                print(f"Error processing dispute {dispute.id}: {str(e)}")
                continue
        
        return f"Processed {processed_count} disputes automatically"
        
    except Exception as e:
        print(f"Error in process_pending_disputes: {str(e)}")
        raise


@shared_task
def cleanup_expired_data():
    """Clean up expired data from various models."""
    try:
        now = timezone.now()
        
        # Clean up expired vendor analytics
        expired_analytics = VendorAnalytics.objects.filter(expires_at__lt=now)
        analytics_count = expired_analytics.count()
        expired_analytics.delete()
        
        # Clean up expired product recommendations
        expired_recommendations = ProductRecommendation.objects.filter(expires_at__lt=now)
        recommendations_count = expired_recommendations.count()
        expired_recommendations.delete()
        
        # Clean up expired price predictions
        expired_predictions = PricePrediction.objects.filter(valid_until__lt=now)
        predictions_count = expired_predictions.count()
        expired_predictions.delete()
        
        # Clean up old search queries (keep last 30 days)
        old_searches = SearchQuery.objects.filter(
            created_at__lt=now - timedelta(days=30)
        )
        searches_count = old_searches.count()
        old_searches.delete()
        
        print(f"Cleanup completed: {analytics_count} analytics, {recommendations_count} recommendations, "
              f"{predictions_count} predictions, {searches_count} searches")
        
        return f"Cleanup completed: {analytics_count + recommendations_count + predictions_count + searches_count} records removed"
        
    except Exception as e:
        print(f"Error in cleanup_expired_data: {str(e)}")
        raise


@shared_task
def daily_maintenance():
    """Daily maintenance tasks."""
    try:
        # Run all maintenance tasks
        refresh_all_analytics.delay()
        refresh_user_recommendations.delay()
        update_price_predictions.delay()
        build_user_preference_profiles.delay()
        process_pending_disputes.delay()
        cleanup_expired_data.delay()
        
        print("Daily maintenance tasks scheduled")
        return "Daily maintenance tasks scheduled successfully"
        
    except Exception as e:
        print(f"Error in daily_maintenance: {str(e)}")
        raise


@shared_task
def weekly_analytics_report():
    """Generate and send weekly analytics report."""
    try:
        # Generate report data
        report_data = {
            'loyalty_summary': {
                'total_users': LoyaltyPoints.objects.count(),
                'total_points': LoyaltyPoints.objects.aggregate(Sum('points'))['points__sum'] or 0,
                'new_users_this_week': LoyaltyPoints.objects.filter(
                    created_at__gte=timezone.now() - timedelta(days=7)
                ).count()
            },
            'search_summary': {
                'total_searches': SearchQuery.objects.count(),
                'searches_this_week': SearchQuery.objects.filter(
                    created_at__gte=timezone.now() - timedelta(days=7)
                ).count(),
                'avg_results': SearchQuery.objects.aggregate(Avg('results_count'))['results_count__avg'] or 0
            },
            'recommendations_summary': {
                'total_recommendations': ProductRecommendation.objects.count(),
                'active_recommendations': ProductRecommendation.objects.filter(
                    expires_at__gt=timezone.now()
                ).count()
            },
            'disputes_summary': {
                'total_arbitrations': DisputeArbitration.objects.count(),
                'automated_resolutions': DisputeArbitration.objects.filter(automated=True).count()
            }
        }
        
        # Convert to JSON for storage or email
        report_json = json.dumps(report_data, indent=2, default=str)
        
        print("Weekly analytics report generated")
        print(report_json)
        
        return "Weekly analytics report generated successfully"
        
    except Exception as e:
        print(f"Error in weekly_analytics_report: {str(e)}")
        raise


# Task scheduling helpers
def schedule_daily_maintenance():
    """Schedule daily maintenance tasks."""
    from celery.schedules import crontab
    
    # This would be configured in Celery beat schedule
    # daily_maintenance.apply_async(countdown=60)  # Run in 1 minute
    
    return "Daily maintenance scheduled"


def schedule_weekly_report():
    """Schedule weekly analytics report."""
    from celery.schedules import crontab
    
    # This would be configured in Celery beat schedule
    # weekly_analytics_report.apply_async(countdown=60)  # Run in 1 minute
    
    return "Weekly report scheduled"