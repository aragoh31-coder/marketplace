"""
Price Prediction Service
Analyzes historical data to predict future price trends and optimal pricing.
Designed for Tor-safe server-side processing without external dependencies.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.db.models import Avg, Max, Min, Count, Sum, Q, F
from django.utils import timezone
import statistics

from core.base_service import BaseService

logger = logging.getLogger(__name__)
User = get_user_model()


class PricePredictionService(BaseService):
    """Advanced price prediction and analysis service"""
    
    service_name = "price_prediction_service"
    version = "1.0.0"
    description = "Historical data analysis and price trend prediction"
    
    def __init__(self):
        super().__init__()
        self._prediction_cache = {}
        self._market_data_cache = {}
    
    def initialize(self):
        """Initialize the price prediction service"""
        try:
            logger.info("Price prediction service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize price prediction service: {e}")
            raise e
    
    def cleanup(self):
        """Clean up the price prediction service"""
        try:
            self._prediction_cache.clear()
            self._market_data_cache.clear()
            logger.info("Price prediction service cleaned up successfully")
        except Exception as e:
            logger.error(f"Failed to cleanup price prediction service: {e}")
    
    def predict_optimal_price(self, product_id: str) -> Dict[str, Any]:
        """Predict optimal pricing for a product based on market analysis"""
        try:
            from products.models import Product
            from orders.models import OrderItem
            
            cache_key = f"price_prediction:{product_id}"
            cached_prediction = self.get_cached(cache_key)
            if cached_prediction:
                return cached_prediction
            
            product = Product.objects.get(id=product_id)
            
            # Gather market data
            market_analysis = self._analyze_market_conditions(product)
            historical_performance = self._analyze_historical_performance(product)
            competitor_analysis = self._analyze_competitor_pricing(product)
            demand_analysis = self._analyze_demand_patterns(product)
            
            # Calculate optimal price recommendations
            price_recommendations = self._calculate_price_recommendations(
                product, market_analysis, historical_performance, 
                competitor_analysis, demand_analysis
            )
            
            # Generate price prediction forecast
            price_forecast = self._generate_price_forecast(product, market_analysis)
            
            prediction_result = {
                'product_id': product_id,
                'current_price_btc': float(product.price_btc),
                'current_price_xmr': float(product.price_xmr),
                'optimal_pricing': price_recommendations,
                'market_analysis': market_analysis,
                'historical_performance': historical_performance,
                'competitor_analysis': competitor_analysis,
                'demand_analysis': demand_analysis,
                'price_forecast': price_forecast,
                'confidence_score': self._calculate_confidence_score(
                    market_analysis, historical_performance, competitor_analysis
                ),
                'recommendations': self._generate_pricing_recommendations(
                    product, price_recommendations, market_analysis
                ),
                'generated_at': timezone.now(),
                'validity_hours': 24  # Predictions valid for 24 hours
            }
            
            # Cache for 6 hours
            self.set_cached(cache_key, prediction_result, timeout=21600)
            
            return prediction_result
            
        except Exception as e:
            logger.error(f"Failed to predict optimal price for product {product_id}: {e}")
            return {'error': str(e)}
    
    def analyze_category_trends(self, category_id: str, days: int = 90) -> Dict[str, Any]:
        """Analyze price trends for an entire product category"""
        try:
            from products.models import Product, Category
            from orders.models import OrderItem
            
            cache_key = f"category_trends:{category_id}:{days}"
            cached_analysis = self.get_cached(cache_key)
            if cached_analysis:
                return cached_analysis
            
            category = Category.objects.get(id=category_id)
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            # Get all products in category
            products = Product.objects.filter(category=category, is_available=True)
            
            # Analyze price distribution
            price_stats = products.aggregate(
                avg_price=Avg('price_btc'),
                min_price=Min('price_btc'),
                max_price=Max('price_btc'),
                product_count=Count('id')
            )
            
            # Analyze sales volume and trends
            sales_data = OrderItem.objects.filter(
                product__category=category,
                order__created_at__range=[start_date, end_date],
                order__status__in=['completed', 'shipped', 'delivered']
            ).aggregate(
                total_volume=Sum('quantity'),
                total_revenue=Sum(F('quantity') * F('price')),
                avg_price_sold=Avg('price')
            )
            
            # Weekly trend analysis
            weekly_trends = self._analyze_weekly_trends(category, start_date, end_date)
            
            # Price segments analysis
            price_segments = self._analyze_price_segments(products)
            
            # Market opportunities
            opportunities = self._identify_market_opportunities(category, price_stats, sales_data)
            
            analysis_result = {
                'category_id': category_id,
                'category_name': category.name,
                'price_statistics': {
                    'average_price': float(price_stats['avg_price'] or 0),
                    'minimum_price': float(price_stats['min_price'] or 0),
                    'maximum_price': float(price_stats['max_price'] or 0),
                    'price_range': float((price_stats['max_price'] or 0) - (price_stats['min_price'] or 0)),
                    'total_products': price_stats['product_count']
                },
                'sales_performance': {
                    'total_volume': sales_data['total_volume'] or 0,
                    'total_revenue': float(sales_data['total_revenue'] or 0),
                    'average_sale_price': float(sales_data['avg_price_sold'] or 0),
                    'period_days': days
                },
                'weekly_trends': weekly_trends,
                'price_segments': price_segments,
                'market_opportunities': opportunities,
                'trend_direction': self._calculate_category_trend_direction(weekly_trends),
                'generated_at': timezone.now()
            }
            
            # Cache for 4 hours
            self.set_cached(cache_key, analysis_result, timeout=14400)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Failed to analyze category trends for {category_id}: {e}")
            return {'error': str(e)}
    
    def get_market_insights(self, days: int = 30) -> Dict[str, Any]:
        """Get overall marketplace insights and trends"""
        try:
            cache_key = f"market_insights:{days}"
            cached_insights = self.get_cached(cache_key)
            if cached_insights:
                return cached_insights
            
            from products.models import Product, Category
            from orders.models import Order, OrderItem
            
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            # Overall market statistics
            market_stats = {
                'total_products': Product.objects.filter(is_available=True).count(),
                'total_categories': Category.objects.count(),
                'active_vendors': Product.objects.filter(is_available=True).values('vendor').distinct().count()
            }
            
            # Sales and revenue analysis
            sales_analysis = OrderItem.objects.filter(
                order__created_at__range=[start_date, end_date],
                order__status__in=['completed', 'shipped', 'delivered']
            ).aggregate(
                total_orders=Count('order', distinct=True),
                total_volume=Sum('quantity'),
                total_revenue=Sum(F('quantity') * F('price')),
                avg_order_value=Avg('order__total_amount')
            )
            
            # Price trends across categories
            category_trends = []
            for category in Category.objects.all():
                category_avg = Product.objects.filter(
                    category=category, is_available=True
                ).aggregate(avg_price=Avg('price_btc'))['avg_price']
                
                if category_avg:
                    category_trends.append({
                        'category': category.name,
                        'average_price': float(category_avg),
                        'product_count': Product.objects.filter(
                            category=category, is_available=True
                        ).count()
                    })
            
            # Top performing products
            top_products = OrderItem.objects.filter(
                order__created_at__range=[start_date, end_date],
                order__status__in=['completed', 'shipped', 'delivered']
            ).values(
                'product__name', 'product__category__name'
            ).annotate(
                total_sold=Sum('quantity'),
                total_revenue=Sum(F('quantity') * F('price'))
            ).order_by('-total_revenue')[:10]
            
            # Market volatility analysis
            volatility_score = self._calculate_market_volatility(days)
            
            insights = {
                'period_days': days,
                'market_statistics': market_stats,
                'sales_analysis': {
                    'total_orders': sales_analysis['total_orders'] or 0,
                    'total_volume': sales_analysis['total_volume'] or 0,
                    'total_revenue': float(sales_analysis['total_revenue'] or 0),
                    'average_order_value': float(sales_analysis['avg_order_value'] or 0)
                },
                'category_trends': sorted(category_trends, key=lambda x: x['average_price'], reverse=True),
                'top_performing_products': list(top_products),
                'market_volatility': volatility_score,
                'market_health': self._assess_market_health(sales_analysis, market_stats),
                'generated_at': timezone.now()
            }
            
            # Cache for 2 hours
            self.set_cached(cache_key, insights, timeout=7200)
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to get market insights: {e}")
            return {'error': str(e)}
    
    def _analyze_market_conditions(self, product) -> Dict[str, Any]:
        """Analyze current market conditions for the product"""
        try:
            from orders.models import OrderItem
            
            # Recent sales activity (last 30 days)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            
            recent_sales = OrderItem.objects.filter(
                product=product,
                order__created_at__gte=thirty_days_ago,
                order__status__in=['completed', 'shipped', 'delivered']
            ).aggregate(
                total_sold=Sum('quantity'),
                avg_price=Avg('price'),
                total_revenue=Sum(F('quantity') * F('price'))
            )
            
            # Category market activity
            category_activity = OrderItem.objects.filter(
                product__category=product.category,
                order__created_at__gte=thirty_days_ago,
                order__status__in=['completed', 'shipped', 'delivered']
            ).aggregate(
                category_volume=Sum('quantity'),
                category_revenue=Sum(F('quantity') * F('price'))
            )
            
            # Market share calculation
            product_revenue = float(recent_sales['total_revenue'] or 0)
            category_revenue = float(category_activity['category_revenue'] or 1)  # Avoid division by zero
            market_share = (product_revenue / category_revenue * 100) if category_revenue > 0 else 0
            
            return {
                'recent_sales_volume': recent_sales['total_sold'] or 0,
                'recent_average_price': float(recent_sales['avg_price'] or 0),
                'recent_revenue': product_revenue,
                'market_share_percentage': round(market_share, 2),
                'category_total_volume': category_activity['category_volume'] or 0,
                'sales_velocity': (recent_sales['total_sold'] or 0) / 30,  # Units per day
                'market_activity_level': self._assess_market_activity_level(recent_sales['total_sold'] or 0)
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze market conditions: {e}")
            return {}
    
    def _analyze_historical_performance(self, product) -> Dict[str, Any]:
        """Analyze historical sales performance of the product"""
        try:
            from orders.models import OrderItem
            
            # Get all historical sales
            all_sales = OrderItem.objects.filter(
                product=product,
                order__status__in=['completed', 'shipped', 'delivered']
            ).order_by('order__created_at')
            
            if not all_sales.exists():
                return {'no_sales_history': True}
            
            # Calculate performance metrics
            prices = [float(sale.price) for sale in all_sales]
            quantities = [sale.quantity for sale in all_sales]
            
            performance_data = {
                'total_sales': sum(quantities),
                'total_revenue': sum(float(sale.price) * sale.quantity for sale in all_sales),
                'average_price': statistics.mean(prices),
                'price_volatility': statistics.stdev(prices) if len(prices) > 1 else 0,
                'min_price': min(prices),
                'max_price': max(prices),
                'sales_consistency': statistics.stdev(quantities) if len(quantities) > 1 else 0,
                'first_sale_date': all_sales.first().order.created_at,
                'last_sale_date': all_sales.last().order.created_at,
                'total_orders': all_sales.count()
            }
            
            # Monthly performance trend
            monthly_performance = self._calculate_monthly_performance(all_sales)
            
            # Performance rating
            performance_rating = self._calculate_performance_rating(performance_data)
            
            return {
                'performance_metrics': performance_data,
                'monthly_trends': monthly_performance,
                'performance_rating': performance_rating,
                'price_stability': 'stable' if performance_data['price_volatility'] < 0.1 else 'volatile'
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze historical performance: {e}")
            return {}
    
    def _analyze_competitor_pricing(self, product) -> Dict[str, Any]:
        """Analyze pricing of similar products (competitors)"""
        try:
            from products.models import Product
            
            # Find similar products (same category, different vendor)
            competitors = Product.objects.filter(
                category=product.category,
                is_available=True
            ).exclude(
                vendor=product.vendor
            ).exclude(
                id=product.id
            )
            
            if not competitors.exists():
                return {'no_competitors': True}
            
            competitor_prices = [float(comp.price_btc) for comp in competitors]
            current_price = float(product.price_btc)
            
            analysis = {
                'competitor_count': len(competitor_prices),
                'average_competitor_price': statistics.mean(competitor_prices),
                'min_competitor_price': min(competitor_prices),
                'max_competitor_price': max(competitor_prices),
                'price_position': self._calculate_price_position(current_price, competitor_prices),
                'competitive_advantage': self._assess_competitive_advantage(current_price, competitor_prices),
                'price_gap_to_average': current_price - statistics.mean(competitor_prices),
                'underpriced_by': max(0, statistics.mean(competitor_prices) - current_price),
                'overpriced_by': max(0, current_price - statistics.mean(competitor_prices))
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze competitor pricing: {e}")
            return {}
    
    def _analyze_demand_patterns(self, product) -> Dict[str, Any]:
        """Analyze demand patterns and seasonality"""
        try:
            from orders.models import OrderItem
            
            # Get sales data for the last 6 months
            six_months_ago = timezone.now() - timedelta(days=180)
            
            sales_by_week = {}
            current_date = six_months_ago
            
            while current_date <= timezone.now():
                week_start = current_date
                week_end = current_date + timedelta(days=7)
                
                week_sales = OrderItem.objects.filter(
                    product=product,
                    order__created_at__range=[week_start, week_end],
                    order__status__in=['completed', 'shipped', 'delivered']
                ).aggregate(
                    volume=Sum('quantity'),
                    revenue=Sum(F('quantity') * F('price'))
                )
                
                week_key = week_start.strftime('%Y-%W')
                sales_by_week[week_key] = {
                    'volume': week_sales['volume'] or 0,
                    'revenue': float(week_sales['revenue'] or 0)
                }
                
                current_date += timedelta(days=7)
            
            # Calculate demand metrics
            weekly_volumes = [data['volume'] for data in sales_by_week.values()]
            demand_variability = statistics.stdev(weekly_volumes) if len(weekly_volumes) > 1 else 0
            average_weekly_demand = statistics.mean(weekly_volumes) if weekly_volumes else 0
            
            # Trend analysis
            recent_weeks = weekly_volumes[-4:] if len(weekly_volumes) >= 4 else weekly_volumes
            earlier_weeks = weekly_volumes[-8:-4] if len(weekly_volumes) >= 8 else []
            
            if recent_weeks and earlier_weeks:
                recent_avg = statistics.mean(recent_weeks)
                earlier_avg = statistics.mean(earlier_weeks)
                trend_direction = 'increasing' if recent_avg > earlier_avg * 1.1 else 'decreasing' if recent_avg < earlier_avg * 0.9 else 'stable'
            else:
                trend_direction = 'insufficient_data'
            
            return {
                'weekly_sales_data': sales_by_week,
                'average_weekly_demand': average_weekly_demand,
                'demand_variability': demand_variability,
                'demand_stability': 'stable' if demand_variability < average_weekly_demand * 0.5 else 'volatile',
                'trend_direction': trend_direction,
                'peak_demand_period': max(sales_by_week.items(), key=lambda x: x[1]['volume'])[0] if sales_by_week else None
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze demand patterns: {e}")
            return {}
    
    def _calculate_price_recommendations(self, product, market_analysis, historical_performance, 
                                       competitor_analysis, demand_analysis) -> Dict[str, Any]:
        """Calculate optimal price recommendations"""
        try:
            current_price = float(product.price_btc)
            recommendations = {}
            
            # Conservative recommendation (safe pricing)
            if competitor_analysis.get('average_competitor_price'):
                conservative_price = competitor_analysis['average_competitor_price'] * 0.95  # 5% below average
            else:
                conservative_price = current_price * 0.95
            
            # Aggressive recommendation (premium pricing)
            if historical_performance.get('performance_metrics', {}).get('average_price'):
                historical_avg = historical_performance['performance_metrics']['average_price']
                aggressive_price = max(current_price * 1.1, historical_avg * 1.05)
            else:
                aggressive_price = current_price * 1.1
            
            # Optimal recommendation (balanced approach)
            factors = []
            
            # Market share factor
            market_share = market_analysis.get('market_share_percentage', 0)
            if market_share > 10:  # High market share
                factors.append(current_price * 1.05)  # Slight premium
            elif market_share < 2:  # Low market share
                factors.append(current_price * 0.95)  # Slight discount
            else:
                factors.append(current_price)
            
            # Demand factor
            if demand_analysis.get('trend_direction') == 'increasing':
                factors.append(current_price * 1.08)
            elif demand_analysis.get('trend_direction') == 'decreasing':
                factors.append(current_price * 0.92)
            
            # Competitive factor
            if competitor_analysis.get('competitive_advantage') == 'underpriced':
                factors.append(current_price * 1.15)
            elif competitor_analysis.get('competitive_advantage') == 'overpriced':
                factors.append(current_price * 0.85)
            
            optimal_price = statistics.mean(factors) if factors else current_price
            
            recommendations = {
                'conservative': {
                    'price_btc': round(conservative_price, 8),
                    'price_xmr': round(conservative_price * 0.02, 6),  # Approximate BTC to XMR ratio
                    'strategy': 'Low risk, competitive pricing',
                    'expected_impact': 'Maintain market position, steady sales'
                },
                'optimal': {
                    'price_btc': round(optimal_price, 8),
                    'price_xmr': round(optimal_price * 0.02, 6),
                    'strategy': 'Balanced risk-reward approach',
                    'expected_impact': 'Optimize revenue while maintaining competitiveness'
                },
                'aggressive': {
                    'price_btc': round(aggressive_price, 8),
                    'price_xmr': round(aggressive_price * 0.02, 6),
                    'strategy': 'Premium positioning, higher margins',
                    'expected_impact': 'Higher profit per sale, potential volume reduction'
                }
            }
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to calculate price recommendations: {e}")
            return {}
    
    def _generate_price_forecast(self, product, market_analysis) -> Dict[str, Any]:
        """Generate price forecast for the next 30 days"""
        try:
            current_price = float(product.price_btc)
            
            # Simple linear trend projection based on market conditions
            market_activity = market_analysis.get('market_activity_level', 'medium')
            sales_velocity = market_analysis.get('sales_velocity', 0)
            
            # Base trend factor
            if market_activity == 'high' and sales_velocity > 1:
                trend_factor = 0.02  # 2% increase per week
            elif market_activity == 'low' or sales_velocity < 0.1:
                trend_factor = -0.01  # 1% decrease per week
            else:
                trend_factor = 0  # Stable
            
            # Generate weekly forecasts
            forecasts = []
            for week in range(1, 5):  # 4 weeks ahead
                predicted_price = current_price * (1 + trend_factor * week)
                
                # Add some randomness to simulate market volatility
                volatility = 0.05  # 5% volatility
                min_price = predicted_price * (1 - volatility)
                max_price = predicted_price * (1 + volatility)
                
                forecasts.append({
                    'week': week,
                    'date': (timezone.now() + timedelta(weeks=week)).strftime('%Y-%m-%d'),
                    'predicted_price': round(predicted_price, 8),
                    'min_price': round(min_price, 8),
                    'max_price': round(max_price, 8),
                    'confidence': 'high' if week <= 2 else 'medium' if week <= 3 else 'low'
                })
            
            return {
                'forecasts': forecasts,
                'trend_direction': 'upward' if trend_factor > 0 else 'downward' if trend_factor < 0 else 'stable',
                'volatility_expected': 'medium',
                'forecast_accuracy': 'Accuracy decreases with time horizon'
            }
            
        except Exception as e:
            logger.error(f"Failed to generate price forecast: {e}")
            return {}
    
    def _calculate_confidence_score(self, market_analysis, historical_performance, competitor_analysis) -> float:
        """Calculate confidence score for predictions"""
        try:
            confidence_factors = []
            
            # Historical data availability
            if historical_performance.get('performance_metrics', {}).get('total_orders', 0) > 10:
                confidence_factors.append(0.8)
            elif historical_performance.get('performance_metrics', {}).get('total_orders', 0) > 5:
                confidence_factors.append(0.6)
            else:
                confidence_factors.append(0.3)
            
            # Market data richness
            if market_analysis.get('recent_sales_volume', 0) > 5:
                confidence_factors.append(0.8)
            elif market_analysis.get('recent_sales_volume', 0) > 1:
                confidence_factors.append(0.6)
            else:
                confidence_factors.append(0.4)
            
            # Competitive data availability
            if competitor_analysis.get('competitor_count', 0) > 5:
                confidence_factors.append(0.9)
            elif competitor_analysis.get('competitor_count', 0) > 2:
                confidence_factors.append(0.7)
            else:
                confidence_factors.append(0.5)
            
            return round(statistics.mean(confidence_factors), 2) if confidence_factors else 0.5
            
        except Exception as e:
            logger.error(f"Failed to calculate confidence score: {e}")
            return 0.5
    
    def _generate_pricing_recommendations(self, product, price_recommendations, market_analysis) -> List[Dict[str, str]]:
        """Generate actionable pricing recommendations"""
        recommendations = []
        
        try:
            current_price = float(product.price_btc)
            
            # Current price analysis
            if market_analysis.get('market_share_percentage', 0) < 5:
                recommendations.append({
                    'type': 'market_share',
                    'title': 'Consider Competitive Pricing',
                    'description': 'Your market share is low. Consider pricing more competitively to gain market presence.',
                    'priority': 'high'
                })
            
            # Sales velocity analysis
            if market_analysis.get('sales_velocity', 0) < 0.5:
                recommendations.append({
                    'type': 'sales_velocity',
                    'title': 'Low Sales Velocity Detected',
                    'description': 'Consider reducing price or improving product positioning to increase sales.',
                    'priority': 'medium'
                })
            
            # Always include general recommendations
            recommendations.extend([
                {
                    'type': 'monitoring',
                    'title': 'Monitor Price Performance',
                    'description': 'Track sales performance after any price changes and adjust accordingly.',
                    'priority': 'medium'
                },
                {
                    'type': 'testing',
                    'title': 'Consider A/B Testing',
                    'description': 'Test different price points to find optimal pricing for your market.',
                    'priority': 'low'
                }
            ])
            
        except Exception as e:
            logger.error(f"Failed to generate pricing recommendations: {e}")
        
        return recommendations
    
    # Helper methods for internal calculations
    def _assess_market_activity_level(self, volume: int) -> str:
        """Assess market activity level based on sales volume"""
        if volume > 10:
            return 'high'
        elif volume > 3:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_price_position(self, current_price: float, competitor_prices: List[float]) -> str:
        """Calculate price position relative to competitors"""
        avg_price = statistics.mean(competitor_prices)
        
        if current_price < avg_price * 0.8:
            return 'significantly_below'
        elif current_price < avg_price * 0.95:
            return 'below'
        elif current_price > avg_price * 1.2:
            return 'significantly_above'
        elif current_price > avg_price * 1.05:
            return 'above'
        else:
            return 'competitive'
    
    def _assess_competitive_advantage(self, current_price: float, competitor_prices: List[float]) -> str:
        """Assess competitive pricing advantage"""
        avg_price = statistics.mean(competitor_prices)
        
        if current_price < avg_price * 0.9:
            return 'underpriced'  # Opportunity to increase
        elif current_price > avg_price * 1.1:
            return 'overpriced'  # Risk of losing customers
        else:
            return 'competitive'
    
    def _calculate_monthly_performance(self, sales_queryset) -> List[Dict[str, Any]]:
        """Calculate monthly performance trends"""
        monthly_data = {}
        
        for sale in sales_queryset:
            month_key = sale.order.created_at.strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = {'volume': 0, 'revenue': 0}
            
            monthly_data[month_key]['volume'] += sale.quantity
            monthly_data[month_key]['revenue'] += float(sale.price) * sale.quantity
        
        return [
            {
                'month': month,
                'volume': data['volume'],
                'revenue': data['revenue']
            }
            for month, data in sorted(monthly_data.items())
        ]
    
    def _calculate_performance_rating(self, performance_data: Dict[str, Any]) -> str:
        """Calculate overall performance rating"""
        total_sales = performance_data.get('total_sales', 0)
        total_revenue = performance_data.get('total_revenue', 0)
        
        if total_sales > 100 and total_revenue > 1000:
            return 'excellent'
        elif total_sales > 50 and total_revenue > 500:
            return 'good'
        elif total_sales > 10 and total_revenue > 100:
            return 'average'
        else:
            return 'needs_improvement'
    
    def _analyze_weekly_trends(self, category, start_date, end_date) -> List[Dict[str, Any]]:
        """Analyze weekly trends for a category"""
        from orders.models import OrderItem
        
        weekly_data = []
        current_date = start_date
        
        while current_date <= end_date:
            week_end = current_date + timedelta(days=7)
            
            week_stats = OrderItem.objects.filter(
                product__category=category,
                order__created_at__range=[current_date, week_end],
                order__status__in=['completed', 'shipped', 'delivered']
            ).aggregate(
                volume=Sum('quantity'),
                revenue=Sum(F('quantity') * F('price'))
            )
            
            weekly_data.append({
                'week_start': current_date.strftime('%Y-%m-%d'),
                'volume': week_stats['volume'] or 0,
                'revenue': float(week_stats['revenue'] or 0)
            })
            
            current_date = week_end
        
        return weekly_data
    
    def _analyze_price_segments(self, products) -> Dict[str, Any]:
        """Analyze price segments in product set"""
        prices = [float(p.price_btc) for p in products if p.price_btc]
        
        if not prices:
            return {}
        
        sorted_prices = sorted(prices)
        segments = {
            'budget': {'min': min(prices), 'max': sorted_prices[len(sorted_prices)//3], 'count': 0},
            'mid_range': {'min': sorted_prices[len(sorted_prices)//3], 'max': sorted_prices[2*len(sorted_prices)//3], 'count': 0},
            'premium': {'min': sorted_prices[2*len(sorted_prices)//3], 'max': max(prices), 'count': 0}
        }
        
        for price in prices:
            if price <= segments['budget']['max']:
                segments['budget']['count'] += 1
            elif price <= segments['mid_range']['max']:
                segments['mid_range']['count'] += 1
            else:
                segments['premium']['count'] += 1
        
        return segments
    
    def _identify_market_opportunities(self, category, price_stats, sales_data) -> List[Dict[str, str]]:
        """Identify market opportunities in a category"""
        opportunities = []
        
        avg_price = price_stats.get('avg_price', 0)
        total_revenue = sales_data.get('total_revenue', 0)
        
        if avg_price > 100:
            opportunities.append({
                'type': 'budget_segment',
                'title': 'Budget Segment Opportunity',
                'description': 'High average prices suggest opportunity for budget-friendly alternatives.'
            })
        
        if total_revenue > 10000:
            opportunities.append({
                'type': 'premium_segment',
                'title': 'Premium Market Active',
                'description': 'High revenue indicates active market with potential for premium offerings.'
            })
        
        return opportunities
    
    def _calculate_category_trend_direction(self, weekly_trends: List[Dict[str, Any]]) -> str:
        """Calculate overall trend direction for category"""
        if len(weekly_trends) < 4:
            return 'insufficient_data'
        
        recent_revenue = sum(week['revenue'] for week in weekly_trends[-4:])
        earlier_revenue = sum(week['revenue'] for week in weekly_trends[-8:-4]) if len(weekly_trends) >= 8 else 1
        
        if recent_revenue > earlier_revenue * 1.1:
            return 'growing'
        elif recent_revenue < earlier_revenue * 0.9:
            return 'declining'
        else:
            return 'stable'
    
    def _calculate_market_volatility(self, days: int) -> Dict[str, Any]:
        """Calculate market volatility score"""
        try:
            from orders.models import OrderItem
            
            # Get daily revenue data
            daily_revenues = []
            for i in range(days):
                date = timezone.now() - timedelta(days=i)
                day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)
                
                day_revenue = OrderItem.objects.filter(
                    order__created_at__range=[day_start, day_end],
                    order__status__in=['completed', 'shipped', 'delivered']
                ).aggregate(
                    revenue=Sum(F('quantity') * F('price'))
                )['revenue'] or 0
                
                daily_revenues.append(float(day_revenue))
            
            if len(daily_revenues) > 1:
                volatility = statistics.stdev(daily_revenues) / statistics.mean(daily_revenues) if statistics.mean(daily_revenues) > 0 else 0
                
                return {
                    'volatility_score': round(volatility, 3),
                    'volatility_level': 'high' if volatility > 0.5 else 'medium' if volatility > 0.2 else 'low',
                    'market_stability': 'stable' if volatility < 0.2 else 'volatile'
                }
            
            return {'volatility_score': 0, 'volatility_level': 'unknown', 'market_stability': 'unknown'}
            
        except Exception as e:
            logger.error(f"Failed to calculate market volatility: {e}")
            return {'error': str(e)}
    
    def _assess_market_health(self, sales_analysis: Dict[str, Any], market_stats: Dict[str, Any]) -> str:
        """Assess overall market health"""
        total_revenue = sales_analysis.get('total_revenue', 0)
        total_orders = sales_analysis.get('total_orders', 0)
        active_vendors = market_stats.get('active_vendors', 0)
        
        health_score = 0
        
        if total_revenue > 50000:
            health_score += 3
        elif total_revenue > 10000:
            health_score += 2
        elif total_revenue > 1000:
            health_score += 1
        
        if total_orders > 500:
            health_score += 2
        elif total_orders > 100:
            health_score += 1
        
        if active_vendors > 50:
            health_score += 2
        elif active_vendors > 10:
            health_score += 1
        
        if health_score >= 6:
            return 'excellent'
        elif health_score >= 4:
            return 'good'
        elif health_score >= 2:
            return 'fair'
        else:
            return 'poor'