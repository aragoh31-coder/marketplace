"""
Vendor Analytics Service
Provides comprehensive analytics dashboards for vendors.
Designed for Tor-safe server-side processing with static dashboards.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, Avg, Q, F, Min
from django.utils import timezone

from core.base_service import BaseService

logger = logging.getLogger(__name__)
User = get_user_model()


class VendorAnalyticsService(BaseService):
    """Comprehensive analytics service for vendors"""
    
    service_name = "vendor_analytics_service"
    version = "1.0.0"
    description = "Advanced analytics and insights for vendor performance"
    
    def __init__(self):
        super().__init__()
        self._analytics_cache = {}
    
    def initialize(self):
        """Initialize the vendor analytics service"""
        try:
            logger.info("Vendor analytics service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize vendor analytics service: {e}")
            raise e
    
    def cleanup(self):
        """Clean up the vendor analytics service"""
        try:
            self._analytics_cache.clear()
            logger.info("Vendor analytics service cleaned up successfully")
        except Exception as e:
            logger.error(f"Failed to cleanup vendor analytics service: {e}")
    
    def get_vendor_dashboard(self, vendor_id: str, days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive vendor dashboard data"""
        try:
            from vendors.models import Vendor
            from orders.models import Order
            from products.models import Product
            from disputes.models import Dispute
            
            vendor = Vendor.objects.get(id=vendor_id)
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            cache_key = f"vendor_dashboard:{vendor_id}:{days}"
            cached_data = self.get_cached(cache_key)
            if cached_data:
                return cached_data
            
            dashboard = {
                'summary': self._get_summary_metrics(vendor, start_date, end_date),
                'sales_performance': self._get_sales_performance(vendor, start_date, end_date),
                'product_performance': self._get_product_performance(vendor, start_date, end_date),
                'customer_insights': self._get_customer_insights(vendor, start_date, end_date),
                'quality_metrics': self._get_quality_metrics(vendor, start_date, end_date),
                'revenue_breakdown': self._get_revenue_breakdown(vendor, start_date, end_date),
                'geographic_data': self._get_geographic_insights(vendor, start_date, end_date),
                'trends': self._get_trend_analysis(vendor, days),
                'recommendations': self._get_vendor_recommendations(vendor),
                'period': f"Last {days} days",
                'generated_at': timezone.now()
            }
            
            # Cache for 1 hour
            self.set_cached(cache_key, dashboard, timeout=3600)
            
            return dashboard
            
        except Exception as e:
            logger.error(f"Failed to generate vendor dashboard for {vendor_id}: {e}")
            return {'error': str(e)}
    
    def _get_summary_metrics(self, vendor, start_date, end_date) -> Dict[str, Any]:
        """Get high-level summary metrics"""
        try:
            from orders.models import Order, OrderItem
            
            # Get orders in period
            orders = Order.objects.filter(
                items__product__vendor=vendor,
                created_at__range=[start_date, end_date],
                status__in=['completed', 'shipped', 'delivered']
            ).distinct()
            
            # Get all vendor orders for comparison
            all_orders = Order.objects.filter(
                items__product__vendor=vendor,
                status__in=['completed', 'shipped', 'delivered']
            ).distinct()
            
            # Calculate metrics
            total_revenue = orders.aggregate(
                total=Sum('total_amount')
            )['total'] or Decimal('0')
            
            total_orders = orders.count()
            unique_customers = orders.values('buyer').distinct().count()
            
            # Average order value
            avg_order_value = total_revenue / total_orders if total_orders > 0 else Decimal('0')
            
            # Customer retention rate
            previous_period_start = start_date - timedelta(days=(end_date - start_date).days)
            previous_customers = Order.objects.filter(
                items__product__vendor=vendor,
                created_at__range=[previous_period_start, start_date],
                status__in=['completed', 'shipped', 'delivered']
            ).values('buyer').distinct().count()
            
            retention_rate = (unique_customers / previous_customers * 100) if previous_customers > 0 else 0
            
            # Dispute rate
            disputes = Dispute.objects.filter(
                order__items__product__vendor=vendor,
                created_at__range=[start_date, end_date]
            ).count()
            
            dispute_rate = (disputes / total_orders * 100) if total_orders > 0 else 0
            
            return {
                'total_revenue': float(total_revenue),
                'total_orders': total_orders,
                'unique_customers': unique_customers,
                'average_order_value': float(avg_order_value),
                'customer_retention_rate': round(retention_rate, 2),
                'dispute_rate': round(dispute_rate, 2),
                'total_disputes': disputes,
                'lifetime_orders': all_orders.count(),
                'active_products': vendor.products.filter(is_active=True).count(),
                'total_products': vendor.products.count()
            }
            
        except Exception as e:
            logger.error(f"Failed to get summary metrics: {e}")
            return {}
    
    def _get_sales_performance(self, vendor, start_date, end_date) -> Dict[str, Any]:
        """Get detailed sales performance metrics"""
        try:
            from orders.models import Order
            
            # Daily sales data
            daily_sales = []
            current_date = start_date.date()
            end_date_only = end_date.date()
            
            while current_date <= end_date_only:
                day_start = timezone.make_aware(datetime.combine(current_date, datetime.min.time()))
                day_end = day_start + timedelta(days=1)
                
                day_orders = Order.objects.filter(
                    items__product__vendor=vendor,
                    created_at__range=[day_start, day_end],
                    status__in=['completed', 'shipped', 'delivered']
                ).distinct()
                
                day_revenue = day_orders.aggregate(
                    total=Sum('total_amount')
                )['total'] or Decimal('0')
                
                daily_sales.append({
                    'date': current_date.isoformat(),
                    'revenue': float(day_revenue),
                    'orders': day_orders.count()
                })
                
                current_date += timedelta(days=1)
            
            # Peak performance analysis
            best_day = max(daily_sales, key=lambda x: x['revenue']) if daily_sales else None
            
            # Weekly comparison
            weeks = self._group_by_week(daily_sales)
            
            return {
                'daily_sales': daily_sales,
                'best_day': best_day,
                'weekly_breakdown': weeks,
                'revenue_trend': self._calculate_trend([d['revenue'] for d in daily_sales]),
                'orders_trend': self._calculate_trend([d['orders'] for d in daily_sales])
            }
            
        except Exception as e:
            logger.error(f"Failed to get sales performance: {e}")
            return {}
    
    def _get_product_performance(self, vendor, start_date, end_date) -> Dict[str, Any]:
        """Get product-specific performance metrics"""
        try:
            from orders.models import OrderItem
            from products.models import Product
            
            # Top performing products
            product_stats = OrderItem.objects.filter(
                product__vendor=vendor,
                order__created_at__range=[start_date, end_date],
                order__status__in=['completed', 'shipped', 'delivered']
            ).values(
                'product__id', 'product__name'
            ).annotate(
                total_sold=Sum('quantity'),
                total_revenue=Sum(F('quantity') * F('price')),
                order_count=Count('order', distinct=True)
            ).order_by('-total_revenue')[:10]
            
            # Convert to list and add percentage
            products_list = list(product_stats)
            total_revenue = sum(p['total_revenue'] for p in products_list)
            
            for product in products_list:
                product['revenue_percentage'] = (
                    product['total_revenue'] / total_revenue * 100
                ) if total_revenue > 0 else 0
                product['total_revenue'] = float(product['total_revenue'])
            
            # Low performing products (need attention)
            low_performers = Product.objects.filter(
                vendor=vendor,
                is_active=True
            ).annotate(
                recent_sales=Count(
                    'orderitem',
                    filter=Q(
                        orderitem__order__created_at__range=[start_date, end_date],
                        orderitem__order__status__in=['completed', 'shipped', 'delivered']
                    )
                )
            ).filter(recent_sales=0)[:5]
            
            # Category performance
            category_stats = OrderItem.objects.filter(
                product__vendor=vendor,
                order__created_at__range=[start_date, end_date],
                order__status__in=['completed', 'shipped', 'delivered']
            ).values(
                'product__category__name'
            ).annotate(
                total_revenue=Sum(F('quantity') * F('price')),
                total_sold=Sum('quantity')
            ).order_by('-total_revenue')
            
            return {
                'top_products': products_list,
                'low_performers': [
                    {
                        'id': p.id,
                        'name': p.name,
                        'price_btc': float(p.price_btc),
                        'stock': p.stock_quantity
                    } for p in low_performers
                ],
                'category_performance': list(category_stats),
                'total_active_products': vendor.products.filter(is_active=True).count()
            }
            
        except Exception as e:
            logger.error(f"Failed to get product performance: {e}")
            return {}
    
    def _get_customer_insights(self, vendor, start_date, end_date) -> Dict[str, Any]:
        """Get customer behavior insights"""
        try:
            from orders.models import Order
            
            # Customer segments
            orders = Order.objects.filter(
                items__product__vendor=vendor,
                created_at__range=[start_date, end_date],
                status__in=['completed', 'shipped', 'delivered']
            ).distinct()
            
            # New vs returning customers
            all_customer_orders = Order.objects.filter(
                items__product__vendor=vendor,
                status__in=['completed', 'shipped', 'delivered']
            ).distinct().values('buyer').annotate(
                total_orders=Count('id'),
                total_spent=Sum('total_amount'),
                first_order=Min('created_at')
            )
            
            new_customers = 0
            returning_customers = 0
            high_value_customers = 0
            
            for customer in all_customer_orders:
                if customer['first_order'] >= start_date:
                    new_customers += 1
                else:
                    returning_customers += 1
                
                if customer['total_spent'] > 1000:  # High value threshold
                    high_value_customers += 1
            
            # Repeat purchase rate
            repeat_customers = all_customer_orders.filter(total_orders__gt=1).count()
            total_customers = all_customer_orders.count()
            repeat_rate = (repeat_customers / total_customers * 100) if total_customers > 0 else 0
            
            # Average customer lifetime value
            avg_clv = all_customer_orders.aggregate(
                avg_spent=Avg('total_spent')
            )['avg_spent'] or Decimal('0')
            
            return {
                'new_customers': new_customers,
                'returning_customers': returning_customers,
                'high_value_customers': high_value_customers,
                'repeat_purchase_rate': round(repeat_rate, 2),
                'average_customer_lifetime_value': float(avg_clv),
                'total_unique_customers': total_customers
            }
            
        except Exception as e:
            logger.error(f"Failed to get customer insights: {e}")
            return {}
    
    def _get_quality_metrics(self, vendor, start_date, end_date) -> Dict[str, Any]:
        """Get quality and satisfaction metrics"""
        try:
            from disputes.models import Dispute
            from orders.models import Order
            
            # Dispute analysis
            total_orders = Order.objects.filter(
                items__product__vendor=vendor,
                created_at__range=[start_date, end_date],
                status__in=['completed', 'shipped', 'delivered']
            ).distinct().count()
            
            disputes = Dispute.objects.filter(
                order__items__product__vendor=vendor,
                created_at__range=[start_date, end_date]
            )
            
            total_disputes = disputes.count()
            resolved_disputes = disputes.filter(status='RESOLVED').count()
            won_disputes = disputes.filter(status='RESOLVED', winner_id=vendor.user.id).count()
            
            # Quality scores
            dispute_rate = (total_disputes / total_orders * 100) if total_orders > 0 else 0
            resolution_rate = (resolved_disputes / total_disputes * 100) if total_disputes > 0 else 100
            win_rate = (won_disputes / resolved_disputes * 100) if resolved_disputes > 0 else 0
            
            # Response time analysis (placeholder - would need timestamps)
            avg_response_time = "< 24 hours"  # This would be calculated from actual data
            
            return {
                'dispute_rate': round(dispute_rate, 2),
                'resolution_rate': round(resolution_rate, 2),
                'dispute_win_rate': round(win_rate, 2),
                'total_disputes': total_disputes,
                'average_response_time': avg_response_time,
                'quality_score': round(100 - dispute_rate, 2)  # Simple quality score
            }
            
        except Exception as e:
            logger.error(f"Failed to get quality metrics: {e}")
            return {}
    
    def _get_revenue_breakdown(self, vendor, start_date, end_date) -> Dict[str, Any]:
        """Get detailed revenue breakdown"""
        try:
            from orders.models import OrderItem
            
            # Revenue by payment method
            btc_orders = OrderItem.objects.filter(
                product__vendor=vendor,
                order__created_at__range=[start_date, end_date],
                order__status__in=['completed', 'shipped', 'delivered'],
                order__payment_method='btc'
            ).aggregate(
                total=Sum(F('quantity') * F('price'))
            )['total'] or Decimal('0')
            
            xmr_orders = OrderItem.objects.filter(
                product__vendor=vendor,
                order__created_at__range=[start_date, end_date],
                order__status__in=['completed', 'shipped', 'delivered'],
                order__payment_method='xmr'
            ).aggregate(
                total=Sum(F('quantity') * F('price'))
            )['total'] or Decimal('0')
            
            total_revenue = btc_orders + xmr_orders
            
            # Revenue by category
            category_revenue = OrderItem.objects.filter(
                product__vendor=vendor,
                order__created_at__range=[start_date, end_date],
                order__status__in=['completed', 'shipped', 'delivered']
            ).values(
                'product__category__name'
            ).annotate(
                revenue=Sum(F('quantity') * F('price'))
            ).order_by('-revenue')
            
            return {
                'total_revenue': float(total_revenue),
                'btc_revenue': float(btc_orders),
                'xmr_revenue': float(xmr_orders),
                'btc_percentage': (float(btc_orders) / float(total_revenue) * 100) if total_revenue > 0 else 0,
                'xmr_percentage': (float(xmr_orders) / float(total_revenue) * 100) if total_revenue > 0 else 0,
                'category_breakdown': [
                    {
                        'category': item['product__category__name'],
                        'revenue': float(item['revenue']),
                        'percentage': (float(item['revenue']) / float(total_revenue) * 100) if total_revenue > 0 else 0
                    } for item in category_revenue
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to get revenue breakdown: {e}")
            return {}
    
    def _get_geographic_insights(self, vendor, start_date, end_date) -> Dict[str, Any]:
        """Get geographic insights (anonymized for privacy)"""
        try:
            # For privacy reasons, we'll provide general insights without specific locations
            from orders.models import Order
            
            orders = Order.objects.filter(
                items__product__vendor=vendor,
                created_at__range=[start_date, end_date],
                status__in=['completed', 'shipped', 'delivered']
            ).distinct()
            
            # Time zone analysis (very general)
            time_distribution = {}
            for order in orders:
                hour = order.created_at.hour
                if hour < 6:
                    period = "Night (00-06)"
                elif hour < 12:
                    period = "Morning (06-12)"
                elif hour < 18:
                    period = "Afternoon (12-18)"
                else:
                    period = "Evening (18-24)"
                
                time_distribution[period] = time_distribution.get(period, 0) + 1
            
            return {
                'order_time_distribution': time_distribution,
                'privacy_note': "Geographic data is anonymized to protect user privacy",
                'total_regions': "Multiple regions served"  # Intentionally vague
            }
            
        except Exception as e:
            logger.error(f"Failed to get geographic insights: {e}")
            return {}
    
    def _get_trend_analysis(self, vendor, days: int) -> Dict[str, Any]:
        """Get trend analysis and forecasting"""
        try:
            from orders.models import Order
            
            # Compare current period with previous period
            end_date = timezone.now()
            current_start = end_date - timedelta(days=days)
            previous_start = current_start - timedelta(days=days)
            
            current_revenue = Order.objects.filter(
                items__product__vendor=vendor,
                created_at__range=[current_start, end_date],
                status__in=['completed', 'shipped', 'delivered']
            ).distinct().aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
            
            previous_revenue = Order.objects.filter(
                items__product__vendor=vendor,
                created_at__range=[previous_start, current_start],
                status__in=['completed', 'shipped', 'delivered']
            ).distinct().aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
            
            # Calculate growth rate
            if previous_revenue > 0:
                growth_rate = ((current_revenue - previous_revenue) / previous_revenue * 100)
            else:
                growth_rate = 100 if current_revenue > 0 else 0
            
            # Simple trend direction
            trend_direction = "up" if growth_rate > 5 else "down" if growth_rate < -5 else "stable"
            
            return {
                'revenue_growth_rate': round(float(growth_rate), 2),
                'trend_direction': trend_direction,
                'current_period_revenue': float(current_revenue),
                'previous_period_revenue': float(previous_revenue),
                'forecast': self._generate_simple_forecast(vendor, float(current_revenue), float(growth_rate))
            }
            
        except Exception as e:
            logger.error(f"Failed to get trend analysis: {e}")
            return {}
    
    def _get_vendor_recommendations(self, vendor) -> List[Dict[str, str]]:
        """Get actionable recommendations for vendor"""
        recommendations = []
        
        try:
            # Basic recommendations based on simple metrics
            active_products = vendor.products.filter(is_active=True).count()
            total_products = vendor.products.count()
            
            if active_products < 5:
                recommendations.append({
                    'type': 'inventory',
                    'title': 'Expand Product Catalog',
                    'description': 'Consider adding more products to increase visibility and sales opportunities.',
                    'priority': 'medium'
                })
            
            if total_products > active_products * 1.5:
                recommendations.append({
                    'type': 'optimization',
                    'title': 'Review Inactive Products', 
                    'description': 'You have many inactive products. Consider reactivating or removing them.',
                    'priority': 'low'
                })
            
            # Always include these general recommendations
            recommendations.extend([
                {
                    'type': 'quality',
                    'title': 'Maintain Response Times',
                    'description': 'Keep responding to messages quickly to maintain customer satisfaction.',
                    'priority': 'high'
                },
                {
                    'type': 'security',
                    'title': 'Review Security Practices',
                    'description': 'Regularly update your security practices and use 2FA protection.',
                    'priority': 'high'
                },
                {
                    'type': 'pricing',
                    'title': 'Monitor Competitive Pricing',
                    'description': 'Regularly review your pricing to stay competitive in the market.',
                    'priority': 'medium'
                }
            ])
            
        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
        
        return recommendations
    
    def _group_by_week(self, daily_data: List[Dict]) -> List[Dict]:
        """Group daily data by week"""
        weeks = {}
        
        for day in daily_data:
            date_obj = datetime.fromisoformat(day['date'])
            week_start = date_obj - timedelta(days=date_obj.weekday())
            week_key = week_start.strftime("%Y-%m-%d")
            
            if week_key not in weeks:
                weeks[week_key] = {'revenue': 0, 'orders': 0, 'days': 0}
            
            weeks[week_key]['revenue'] += day['revenue']
            weeks[week_key]['orders'] += day['orders']
            weeks[week_key]['days'] += 1
        
        return [
            {
                'week_start': week,
                'revenue': data['revenue'],
                'orders': data['orders'],
                'avg_daily_revenue': data['revenue'] / data['days']
            }
            for week, data in sorted(weeks.items())
        ]
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from list of values"""
        if len(values) < 2:
            return "insufficient_data"
        
        # Simple linear trend
        first_half = sum(values[:len(values)//2]) / (len(values)//2)
        second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2)
        
        if second_half > first_half * 1.1:
            return "increasing"
        elif second_half < first_half * 0.9:
            return "decreasing"
        else:
            return "stable"
    
    def _generate_simple_forecast(self, vendor, current_revenue: float, growth_rate: float) -> Dict[str, Any]:
        """Generate simple revenue forecast"""
        try:
            # Simple linear projection
            monthly_projection = current_revenue * (1 + growth_rate / 100) * 30 / 30  # Normalize to monthly
            quarterly_projection = monthly_projection * 3
            
            return {
                'next_month_revenue': round(monthly_projection, 2),
                'next_quarter_revenue': round(quarterly_projection, 2),
                'confidence': "low" if abs(growth_rate) > 50 else "medium" if abs(growth_rate) > 20 else "high",
                'note': "Projections based on current trends and may vary significantly"
            }
        except Exception as e:
            logger.error(f"Failed to generate forecast: {e}")
            return {'error': 'Unable to generate forecast'}