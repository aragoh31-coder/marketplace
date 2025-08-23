"""
Vendor Analytics Service
Provides comprehensive analytics and insights for vendors.
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from django.core.cache import cache

from .base_service import BaseService, performance_monitor

logger = logging.getLogger(__name__)

User = get_user_model()


class VendorAnalyticsService(BaseService):
    """Service for providing vendor analytics and insights."""
    
    service_name = "vendor_analytics_service"
    description = "Comprehensive vendor analytics and business insights"
    
    def __init__(self):
        super().__init__()
        self.cache_timeout = 3600  # 1 hour cache for analytics
    
    @performance_monitor
    def get_vendor_dashboard(self, vendor: User) -> Dict[str, Any]:
        """Get comprehensive vendor dashboard data."""
        try:
            # Check cache first
            cache_key = f"vendor_dashboard:{vendor.id}"
            cached_data = self.get_cached(cache_key)
            if cached_data:
                return cached_data
            
            dashboard_data = {
                'summary_metrics': self._get_summary_metrics(vendor),
                'sales_performance': self._get_sales_performance(vendor),
                'product_performance': self._get_product_performance(vendor),
                'customer_insights': self._get_customer_insights(vendor),
                'quality_metrics': self._get_quality_metrics(vendor),
                'revenue_breakdown': self._get_revenue_breakdown(vendor),
                'geographic_insights': self._get_geographic_insights(vendor),
                'trend_analysis': self._get_trend_analysis(vendor),
                'recommendations': self._get_actionable_recommendations(vendor)
            }
            
            # Cache the dashboard data
            self.set_cached(cache_key, dashboard_data, self.cache_timeout)
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error getting vendor dashboard for {vendor.username}: {str(e)}")
            return {}
    
    def _get_summary_metrics(self, vendor: User) -> Dict[str, Any]:
        """Get summary metrics for the vendor."""
        try:
            from orders.models import Order
            from products.models import Product
            
            # Get date range (last 30 days)
            end_date = timezone.now()
            start_date = end_date - timedelta(days=30)
            previous_start = start_date - timedelta(days=30)
            
            # Current period metrics
            current_orders = Order.objects.filter(
                vendor=vendor,
                created_at__gte=start_date,
                created_at__lte=end_date
            )
            
            current_revenue = current_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
            current_order_count = current_orders.count()
            current_customers = current_orders.values('buyer').distinct().count()
            
            # Previous period metrics
            previous_orders = Order.objects.filter(
                vendor=vendor,
                created_at__gte=previous_start,
                created_at__lt=start_date
            )
            
            previous_revenue = previous_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
            previous_order_count = previous_orders.count()
            previous_customers = previous_orders.values('buyer').distinct().count()
            
            # Calculate growth percentages
            revenue_growth = self._calculate_growth(current_revenue, previous_revenue)
            order_growth = self._calculate_growth(current_order_count, previous_order_count)
            customer_growth = self._calculate_growth(current_customers, previous_customers)
            
            # Get average rating
            from reviews.models import Review
            reviews = Review.objects.filter(product__vendor=vendor)
            avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0.0
            
            # Calculate rating change (simplified)
            rating_change = 0.0  # In a real system, compare with previous period
            
            return {
                'total_revenue': float(current_revenue),
                'revenue_growth': revenue_growth,
                'total_orders': current_order_count,
                'order_growth': order_growth,
                'active_customers': current_customers,
                'customer_growth': customer_growth,
                'average_rating': avg_rating,
                'rating_change': rating_change,
                'total_products': Product.objects.filter(vendor=vendor, active=True).count()
            }
            
        except Exception as e:
            logger.error(f"Error getting summary metrics for vendor {vendor.username}: {str(e)}")
            return {}
    
    def _get_sales_performance(self, vendor: User) -> Dict[str, Any]:
        """Get sales performance data."""
        try:
            from orders.models import Order
            
            # Daily sales for last 7 days
            daily_sales = {}
            for i in range(7):
                date = timezone.now() - timedelta(days=i)
                day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)
                
                day_revenue = Order.objects.filter(
                    vendor=vendor,
                    created_at__gte=day_start,
                    created_at__lt=day_end
                ).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
                
                daily_sales[date.strftime('%a')] = float(day_revenue)
            
            # Weekly sales for last 4 weeks
            weekly_sales = {}
            for i in range(4):
                week_start = timezone.now() - timedelta(weeks=i+1)
                week_end = week_start + timedelta(weeks=1)
                
                week_revenue = Order.objects.filter(
                    vendor=vendor,
                    created_at__gte=week_start,
                    created_at__lt=week_end
                ).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
                
                weekly_sales[f"Week {i+1}"] = float(week_revenue)
            
            return {
                'daily_sales': daily_sales,
                'weekly_sales': weekly_sales,
                'total_sales_period': '30 days'
            }
            
        except Exception as e:
            logger.error(f"Error getting sales performance for vendor {vendor.username}: {str(e)}")
            return {}
    
    def _get_product_performance(self, vendor: User) -> Dict[str, Any]:
        """Get product performance data."""
        try:
            from orders.models import Order
            from products.models import Product
            
            # Get top performing products
            top_products = []
            products = Product.objects.filter(vendor=vendor, active=True)
            
            for product in products:
                product_orders = Order.objects.filter(
                    vendor=vendor,
                    products=product
                )
                
                sales_count = product_orders.count()
                revenue = product_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
                
                if sales_count > 0:
                    top_products.append({
                        'name': product.name,
                        'sales_count': sales_count,
                        'revenue': float(revenue),
                        'avg_price': float(revenue / sales_count)
                    })
            
            # Sort by revenue
            top_products.sort(key=lambda x: x['revenue'], reverse=True)
            
            return {
                'top_products': top_products[:10],
                'total_products': len(top_products),
                'avg_product_revenue': sum(p['revenue'] for p in top_products) / len(top_products) if top_products else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting product performance for vendor {vendor.username}: {str(e)}")
            return {}
    
    def _get_customer_insights(self, vendor: User) -> Dict[str, Any]:
        """Get customer insights and segmentation."""
        try:
            from orders.models import Order
            
            # Get all customers
            customers = Order.objects.filter(vendor=vendor).values('buyer').distinct()
            
            # Segment customers by order value
            segments = {
                'high_value': {'count': 0, 'percentage': 0.0},
                'medium_value': {'count': 0, 'percentage': 0.0},
                'low_value': {'count': 0, 'percentage': 0.0}
            }
            
            total_customers = customers.count()
            
            for customer_data in customers:
                customer = customer_data['buyer']
                total_spent = Order.objects.filter(
                    vendor=vendor,
                    buyer=customer
                ).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
                
                if total_spent >= 500:
                    segments['high_value']['count'] += 1
                elif total_spent >= 100:
                    segments['medium_value']['count'] += 1
                else:
                    segments['low_value']['count'] += 1
            
            # Calculate percentages
            for segment in segments.values():
                segment['percentage'] = (segment['count'] / total_customers * 100) if total_customers > 0 else 0
            
            return {
                'segments': [
                    {'name': 'High Value ($500+)', 'count': segments['high_value']['count'], 'percentage': segments['high_value']['percentage']},
                    {'name': 'Medium Value ($100-$499)', 'count': segments['medium_value']['count'], 'percentage': segments['medium_value']['percentage']},
                    {'name': 'Low Value (<$100)', 'count': segments['low_value']['count'], 'percentage': segments['low_value']['percentage']}
                ],
                'total_customers': total_customers,
                'repeat_customers': self._get_repeat_customer_count(vendor)
            }
            
        except Exception as e:
            logger.error(f"Error getting customer insights for vendor {vendor.username}: {str(e)}")
            return {}
    
    def _get_quality_metrics(self, vendor: User) -> Dict[str, Any]:
        """Get quality and dispute metrics."""
        try:
            from disputes.models import Dispute
            from orders.models import Order
            
            # Get total orders
            total_orders = Order.objects.filter(vendor=vendor).count()
            
            # Get disputes
            disputes = Dispute.objects.filter(vendor=vendor)
            total_disputes = disputes.count()
            resolved_disputes = disputes.filter(status='resolved').count()
            
            # Calculate metrics
            dispute_rate = (total_disputes / total_orders * 100) if total_orders > 0 else 0
            
            # Average resolution time (simplified)
            avg_resolution_time = 2.5  # In a real system, calculate from actual data
            
            # Customer satisfaction (simplified)
            satisfaction_score = 8.5  # In a real system, calculate from reviews
            
            # Return rate (simplified)
            return_rate = 1.2  # In a real system, calculate from actual returns
            
            return {
                'dispute_rate': dispute_rate,
                'avg_resolution_time': avg_resolution_time,
                'satisfaction_score': satisfaction_score,
                'return_rate': return_rate,
                'total_disputes': total_disputes,
                'resolved_disputes': resolved_disputes
            }
            
        except Exception as e:
            logger.error(f"Error getting quality metrics for vendor {vendor.username}: {str(e)}")
            return {}
    
    def _get_revenue_breakdown(self, vendor: User) -> Dict[str, Any]:
        """Get revenue breakdown by category and time."""
        try:
            from orders.models import Order
            from products.models import Product, Category
            
            # Revenue by category
            category_revenue = {}
            categories = Category.objects.all()
            
            for category in categories:
                category_products = Product.objects.filter(
                    vendor=vendor,
                    category=category,
                    active=True
                )
                
                if category_products.exists():
                    category_orders = Order.objects.filter(
                        vendor=vendor,
                        products__in=category_products
                    )
                    
                    revenue = category_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
                    if revenue > 0:
                        category_revenue[category.name] = float(revenue)
            
            # Revenue by time of day
            time_revenue = {
                'morning': 0.0,
                'afternoon': 0.0,
                'evening': 0.0,
                'night': 0.0
            }
            
            orders = Order.objects.filter(vendor=vendor)
            for order in orders:
                hour = order.created_at.hour
                if 6 <= hour < 12:
                    time_revenue['morning'] += float(order.total_amount or 0)
                elif 12 <= hour < 17:
                    time_revenue['afternoon'] += float(order.total_amount or 0)
                elif 17 <= hour < 22:
                    time_revenue['evening'] += float(order.total_amount or 0)
                else:
                    time_revenue['night'] += float(order.total_amount or 0)
            
            return {
                'by_category': category_revenue,
                'by_time': time_revenue,
                'total_revenue': sum(category_revenue.values())
            }
            
        except Exception as e:
            logger.error(f"Error getting revenue breakdown for vendor {vendor.username}: {str(e)}")
            return {}
    
    def _get_geographic_insights(self, vendor: User) -> Dict[str, Any]:
        """Get geographic insights (anonymized for privacy)."""
        try:
            from orders.models import Order
            
            # Get orders with shipping addresses
            orders = Order.objects.filter(vendor=vendor)
            
            # Simplified geographic data (in real system, analyze shipping addresses)
            locations = [
                {'name': 'North America', 'orders': 45, 'revenue': 1250.00},
                {'name': 'Europe', 'orders': 32, 'revenue': 890.00},
                {'name': 'Asia', 'orders': 28, 'revenue': 720.00},
                {'name': 'Other', 'orders': 15, 'revenue': 340.00}
            ]
            
            return {
                'top_locations': locations,
                'total_locations': len(locations),
                'international_orders': sum(1 for loc in locations if loc['name'] != 'North America')
            }
            
        except Exception as e:
            logger.error(f"Error getting geographic insights for vendor {vendor.username}: {str(e)}")
            return {}
    
    def _get_trend_analysis(self, vendor: User) -> Dict[str, Any]:
        """Get trend analysis and predictions."""
        try:
            from orders.models import Order
            
            # Analyze recent trends
            recent_orders = Order.objects.filter(
                vendor=vendor,
                created_at__gte=timezone.now() - timedelta(days=7)
            )
            
            previous_week_orders = Order.objects.filter(
                vendor=vendor,
                created_at__gte=timezone.now() - timedelta(days=14),
                created_at__lt=timezone.now() - timedelta(days=7)
            )
            
            recent_revenue = recent_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
            previous_revenue = previous_week_orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
            
            # Determine trends
            if recent_revenue > previous_revenue * 1.1:
                revenue_trend = 'increasing'
            elif recent_revenue < previous_revenue * 0.9:
                revenue_trend = 'decreasing'
            else:
                revenue_trend = 'stable'
            
            # Customer behavior trends
            recent_customers = recent_orders.values('buyer').distinct().count()
            previous_customers = previous_week_orders.values('buyer').distinct().count()
            
            if recent_customers > previous_customers * 1.05:
                customer_trend = 'growing'
            elif recent_customers < previous_customers * 0.95:
                customer_trend = 'declining'
            else:
                customer_trend = 'stable'
            
            return {
                'revenue_trend': revenue_trend,
                'revenue_factors': [
                    'Seasonal demand changes',
                    'Product availability',
                    'Pricing strategy adjustments'
                ],
                'customer_trend': customer_trend,
                'customer_factors': [
                    'Marketing effectiveness',
                    'Customer satisfaction',
                    'Competitive landscape'
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting trend analysis for vendor {vendor.username}: {str(e)}")
            return {}
    
    def _get_actionable_recommendations(self, vendor: User) -> List[Dict[str, Any]]:
        """Get actionable recommendations for the vendor."""
        try:
            recommendations = []
            
            # Analyze current performance
            summary = self._get_summary_metrics(vendor)
            quality = self._get_quality_metrics(vendor)
            
            # Revenue optimization recommendations
            if summary.get('revenue_growth', 0) < 5:
                recommendations.append({
                    'priority': 'high',
                    'title': 'Optimize Pricing Strategy',
                    'description': 'Consider adjusting prices based on market analysis and competitor pricing.',
                    'expected_impact': 'Potential 10-15% revenue increase'
                })
            
            # Customer retention recommendations
            if summary.get('customer_growth', 0) < 0:
                recommendations.append({
                    'priority': 'high',
                    'title': 'Improve Customer Retention',
                    'description': 'Focus on customer satisfaction and loyalty programs to reduce churn.',
                    'expected_impact': 'Stabilize customer base and improve lifetime value'
                })
            
            # Quality improvement recommendations
            if quality.get('dispute_rate', 0) > 5:
                recommendations.append({
                    'priority': 'medium',
                    'title': 'Reduce Dispute Rate',
                    'description': 'Improve product descriptions, shipping accuracy, and customer communication.',
                    'expected_impact': 'Lower dispute rate and improved customer satisfaction'
                })
            
            # Product performance recommendations
            product_perf = self._get_product_performance(vendor)
            if product_perf.get('total_products', 0) > 20:
                recommendations.append({
                    'priority': 'medium',
                    'title': 'Product Portfolio Optimization',
                    'description': 'Consider discontinuing low-performing products to focus on winners.',
                    'expected_impact': 'Improved efficiency and higher margins'
                })
            
            # Add general recommendations
            recommendations.extend([
                {
                    'priority': 'low',
                    'title': 'Expand Marketing Channels',
                    'description': 'Explore additional marketing channels to reach new customers.',
                    'expected_impact': 'Increased market reach and customer acquisition'
                },
                {
                    'priority': 'low',
                    'title': 'Customer Feedback Analysis',
                    'description': 'Analyze customer feedback to identify improvement opportunities.',
                    'expected_impact': 'Better product-market fit and customer satisfaction'
                }
            ])
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting recommendations for vendor {vendor.username}: {str(e)}")
            return []
    
    def _calculate_growth(self, current: float, previous: float) -> float:
        """Calculate growth percentage between two values."""
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return ((current - previous) / previous) * 100
    
    def _get_repeat_customer_count(self, vendor: User) -> int:
        """Get count of repeat customers."""
        try:
            from orders.models import Order
            
            # Get customers with multiple orders
            customer_order_counts = Order.objects.filter(
                vendor=vendor
            ).values('buyer').annotate(
                order_count=Count('id')
            ).filter(order_count__gt=1)
            
            return customer_order_counts.count()
            
        except Exception as e:
            logger.error(f"Error getting repeat customer count for vendor {vendor.username}: {str(e)}")
            return 0