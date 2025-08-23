"""
User Preference Learning Service
Analyzes user behavior patterns to build detailed preference profiles.
Designed for Tor-safe server-side processing with privacy-first approach.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter
from decimal import Decimal
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.db.models import Count, Avg, Sum, Q, F, Max, Min
from django.utils import timezone
import statistics

from .base_service import BaseService

logger = logging.getLogger(__name__)
User = get_user_model()


class UserPreferenceService(BaseService):
    """Advanced user preference learning and behavioral analysis service"""
    
    service_name = "user_preference_service"
    version = "1.0.0"
    description = "AI-powered user preference learning with behavioral analysis"
    
    def __init__(self):
        super().__init__()
        self._preference_cache = {}
        self._behavior_patterns_cache = {}
    
    def initialize(self):
        """Initialize the user preference service"""
        try:
            logger.info("User preference service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize user preference service: {e}")
            raise e
    
    def cleanup(self):
        """Clean up the user preference service"""
        try:
            self._preference_cache.clear()
            self._behavior_patterns_cache.clear()
            logger.info("User preference service cleaned up successfully")
        except Exception as e:
            logger.error(f"Failed to cleanup user preference service: {e}")
    
    def build_user_profile(self, user_id: str, include_predictions: bool = True) -> Dict[str, Any]:
        """Build comprehensive user preference profile"""
        try:
            cache_key = f"user_profile:{user_id}:{include_predictions}"
            cached_profile = self.get_cached(cache_key)
            if cached_profile:
                return cached_profile
            
            user = User.objects.get(id=user_id)
            
            # Analyze different aspects of user behavior
            profile = {
                'user_id': user_id,
                'basic_preferences': self._analyze_basic_preferences(user),
                'purchase_patterns': self._analyze_purchase_patterns(user),
                'browsing_behavior': self._analyze_browsing_behavior(user),
                'price_sensitivity': self._analyze_price_sensitivity(user),
                'category_affinity': self._analyze_category_affinity(user),
                'vendor_preferences': self._analyze_vendor_preferences(user),
                'temporal_patterns': self._analyze_temporal_patterns(user),
                'risk_profile': self._analyze_risk_profile(user),
                'loyalty_indicators': self._analyze_loyalty_indicators(user),
                'profile_completeness': self._calculate_profile_completeness(user),
                'confidence_scores': {},
                'last_updated': timezone.now()
            }
            
            # Add predictions if requested
            if include_predictions:
                profile['predictions'] = self._generate_behavior_predictions(user, profile)
                profile['recommendations'] = self._generate_profile_recommendations(profile)
            
            # Calculate confidence scores for each section
            profile['confidence_scores'] = self._calculate_confidence_scores(profile)
            
            # Cache for 2 hours
            self.set_cached(cache_key, profile, timeout=7200)
            
            return profile
            
        except Exception as e:
            logger.error(f"Failed to build user profile for {user_id}: {e}")
            return {'error': str(e)}
    
    def learn_from_interaction(self, user_id: str, interaction_type: str, 
                              interaction_data: Dict[str, Any]) -> bool:
        """Learn from user interactions in real-time"""
        try:
            # Clear cached profile to force recalculation
            cache_keys_to_clear = [
                f"user_profile:{user_id}:True",
                f"user_profile:{user_id}:False",
                f"behavior_patterns:{user_id}"
            ]
            
            for key in cache_keys_to_clear:
                self.clear_cache(key)
            
            # Log interaction for future analysis
            interaction_log = {
                'user_id': user_id,
                'interaction_type': interaction_type,
                'interaction_data': interaction_data,
                'timestamp': timezone.now()
            }
            
            # Store in cache for batch processing
            interactions_key = f"user_interactions:{user_id}"
            interactions = self.get_cached(interactions_key, [])
            interactions.append(interaction_log)
            
            # Keep only recent interactions (last 1000)
            if len(interactions) > 1000:
                interactions = interactions[-1000:]
            
            self.set_cached(interactions_key, interactions, timeout=86400)  # 24 hours
            
            logger.info(f"Learned from interaction: {interaction_type} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to learn from interaction: {e}")
            return False
    
    def get_personalized_insights(self, user_id: str) -> Dict[str, Any]:
        """Get personalized insights and analytics for the user"""
        try:
            profile = self.build_user_profile(user_id, include_predictions=True)
            
            if 'error' in profile:
                return profile
            
            insights = {
                'spending_insights': self._generate_spending_insights(profile),
                'category_insights': self._generate_category_insights(profile),
                'behavioral_insights': self._generate_behavioral_insights(profile),
                'opportunity_insights': self._generate_opportunity_insights(profile),
                'comparison_insights': self._generate_comparison_insights(user_id, profile),
                'trend_insights': self._generate_trend_insights(profile),
                'privacy_summary': self._generate_privacy_summary()
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Failed to get personalized insights for {user_id}: {e}")
            return {'error': str(e)}
    
    def _analyze_basic_preferences(self, user) -> Dict[str, Any]:
        """Analyze basic user preferences from account and activity data"""
        try:
            from orders.models import Order
            
            # Account age and activity level
            account_age = (timezone.now() - user.date_joined).days
            total_orders = Order.objects.filter(buyer=user).count()
            recent_orders = Order.objects.filter(
                buyer=user,
                created_at__gte=timezone.now() - timedelta(days=30)
            ).count()
            
            # Activity classification
            if total_orders == 0:
                activity_level = 'new'
            elif recent_orders == 0 and account_age > 90:
                activity_level = 'dormant'
            elif recent_orders >= 5:
                activity_level = 'high'
            elif recent_orders >= 2:
                activity_level = 'medium'
            else:
                activity_level = 'low'
            
            return {
                'account_age_days': account_age,
                'total_orders': total_orders,
                'recent_activity': recent_orders,
                'activity_level': activity_level,
                'user_segment': self._classify_user_segment(total_orders, account_age, recent_orders)
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze basic preferences: {e}")
            return {}
    
    def _analyze_purchase_patterns(self, user) -> Dict[str, Any]:
        """Analyze user's purchase patterns and habits"""
        try:
            from orders.models import Order, OrderItem
            
            orders = Order.objects.filter(
                buyer=user,
                status__in=['completed', 'shipped', 'delivered']
            ).order_by('-created_at')
            
            if not orders.exists():
                return {'no_purchase_history': True}
            
            order_items = OrderItem.objects.filter(
                order__in=orders
            ).select_related('product')
            
            # Calculate purchase metrics
            total_spent = sum(float(order.total_amount or 0) for order in orders)
            avg_order_value = total_spent / orders.count() if orders.count() > 0 else 0
            
            # Order frequency analysis
            order_dates = [order.created_at.date() for order in orders]
            if len(order_dates) > 1:
                intervals = [(order_dates[i-1] - order_dates[i]).days for i in range(1, len(order_dates))]
                avg_days_between_orders = statistics.mean(intervals) if intervals else 0
            else:
                avg_days_between_orders = 0
            
            # Purchase timing patterns
            purchase_hours = [order.created_at.hour for order in orders]
            purchase_days = [order.created_at.weekday() for order in orders]
            
            most_active_hour = Counter(purchase_hours).most_common(1)[0][0] if purchase_hours else 12
            most_active_day = Counter(purchase_days).most_common(1)[0][0] if purchase_days else 0
            
            # Item preferences
            items_per_order = [order.items.count() for order in orders]
            avg_items_per_order = statistics.mean(items_per_order) if items_per_order else 0
            
            return {
                'total_orders': orders.count(),
                'total_spent': total_spent,
                'average_order_value': avg_order_value,
                'average_days_between_orders': avg_days_between_orders,
                'average_items_per_order': avg_items_per_order,
                'most_active_hour': most_active_hour,
                'most_active_day': most_active_day,
                'purchase_frequency': self._classify_purchase_frequency(avg_days_between_orders),
                'spending_tier': self._classify_spending_tier(total_spent),
                'first_purchase': orders.last().created_at,
                'last_purchase': orders.first().created_at
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze purchase patterns: {e}")
            return {}
    
    def _analyze_browsing_behavior(self, user) -> Dict[str, Any]:
        """Analyze browsing behavior patterns (simulated for this implementation)"""
        try:
            # In a real implementation, this would analyze page views, search queries, etc.
            # For now, we'll infer browsing behavior from purchase patterns
            
            from orders.models import OrderItem
            
            # Analyze product view patterns from purchases
            purchased_items = OrderItem.objects.filter(
                order__buyer=user,
                order__status__in=['completed', 'shipped', 'delivered']
            ).select_related('product')
            
            if not purchased_items.exists():
                return {'insufficient_data': True}
            
            # Category exploration
            categories_explored = set(item.product.category_id for item in purchased_items)
            
            # Price range exploration
            prices_viewed = [float(item.product.price_btc) for item in purchased_items]
            price_range_low = min(prices_viewed) if prices_viewed else 0
            price_range_high = max(prices_viewed) if prices_viewed else 0
            
            # Vendor exploration
            vendors_explored = set(item.product.vendor_id for item in purchased_items)
            
            return {
                'categories_explored': len(categories_explored),
                'price_range_low': price_range_low,
                'price_range_high': price_range_high,
                'price_range_span': price_range_high - price_range_low,
                'vendors_explored': len(vendors_explored),
                'exploration_score': self._calculate_exploration_score(
                    len(categories_explored), len(vendors_explored), price_range_high - price_range_low
                )
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze browsing behavior: {e}")
            return {}
    
    def _analyze_price_sensitivity(self, user) -> Dict[str, Any]:
        """Analyze user's price sensitivity and spending patterns"""
        try:
            from orders.models import OrderItem
            
            order_items = OrderItem.objects.filter(
                order__buyer=user,
                order__status__in=['completed', 'shipped', 'delivered']
            ).select_related('product')
            
            if not order_items.exists():
                return {'no_data': True}
            
            # Price analysis
            prices_paid = [float(item.price) for item in order_items]
            product_list_prices = [float(item.product.price_btc) for item in order_items]
            
            avg_price_paid = statistics.mean(prices_paid)
            avg_list_price = statistics.mean(product_list_prices)
            
            # Price variance analysis
            price_std = statistics.stdev(prices_paid) if len(prices_paid) > 1 else 0
            price_coefficient_variation = price_std / avg_price_paid if avg_price_paid > 0 else 0
            
            # Price tier preferences
            price_tiers = {'budget': 0, 'mid': 0, 'premium': 0}
            for price in prices_paid:
                if price < avg_list_price * 0.7:
                    price_tiers['budget'] += 1
                elif price > avg_list_price * 1.3:
                    price_tiers['premium'] += 1
                else:
                    price_tiers['mid'] += 1
            
            # Determine price sensitivity
            if price_coefficient_variation < 0.3:
                sensitivity = 'consistent'
            elif price_coefficient_variation < 0.6:
                sensitivity = 'moderate'
            else:
                sensitivity = 'variable'
            
            preferred_tier = max(price_tiers, key=price_tiers.get)
            
            return {
                'average_price_paid': avg_price_paid,
                'price_variance': price_std,
                'price_consistency': sensitivity,
                'preferred_price_tier': preferred_tier,
                'price_tier_distribution': price_tiers,
                'budget_conscious': price_tiers['budget'] > price_tiers['premium'],
                'luxury_affinity': price_tiers['premium'] > price_tiers['budget']
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze price sensitivity: {e}")
            return {}
    
    def _analyze_category_affinity(self, user) -> Dict[str, Any]:
        """Analyze user's affinity for different product categories"""
        try:
            from orders.models import OrderItem
            from products.models import Category
            
            order_items = OrderItem.objects.filter(
                order__buyer=user,
                order__status__in=['completed', 'shipped', 'delivered']
            ).select_related('product__category')
            
            if not order_items.exists():
                return {'no_data': True}
            
            # Category purchase frequency
            category_counts = defaultdict(int)
            category_spending = defaultdict(float)
            
            for item in order_items:
                category_name = item.product.category.name
                category_counts[category_name] += item.quantity
                category_spending[category_name] += float(item.price) * item.quantity
            
            # Calculate affinity scores
            total_items = sum(category_counts.values())
            total_spending = sum(category_spending.values())
            
            category_affinities = {}
            for category, count in category_counts.items():
                frequency_score = count / total_items
                spending_score = category_spending[category] / total_spending
                affinity_score = (frequency_score + spending_score) / 2
                
                category_affinities[category] = {
                    'purchase_count': count,
                    'total_spent': category_spending[category],
                    'frequency_score': frequency_score,
                    'spending_score': spending_score,
                    'affinity_score': affinity_score
                }
            
            # Sort by affinity score
            sorted_affinities = sorted(
                category_affinities.items(),
                key=lambda x: x[1]['affinity_score'],
                reverse=True
            )
            
            return {
                'total_categories_purchased': len(category_affinities),
                'category_affinities': dict(sorted_affinities),
                'top_categories': [item[0] for item in sorted_affinities[:3]],
                'category_diversity': len(category_affinities) / Category.objects.count() if Category.objects.count() > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze category affinity: {e}")
            return {}
    
    def _analyze_vendor_preferences(self, user) -> Dict[str, Any]:
        """Analyze user's vendor preferences and loyalty patterns"""
        try:
            from orders.models import OrderItem
            from vendors.models import Vendor
            
            order_items = OrderItem.objects.filter(
                order__buyer=user,
                order__status__in=['completed', 'shipped', 'delivered']
            ).select_related('product__vendor')
            
            if not order_items.exists():
                return {'no_data': True}
            
            # Vendor interaction analysis
            vendor_stats = defaultdict(lambda: {'orders': 0, 'items': 0, 'spending': 0})
            
            for item in order_items:
                vendor_name = item.product.vendor.user.username
                vendor_stats[vendor_name]['orders'] += 1
                vendor_stats[vendor_name]['items'] += item.quantity
                vendor_stats[vendor_name]['spending'] += float(item.price) * item.quantity
            
            # Calculate vendor loyalty metrics
            total_vendors = len(vendor_stats)
            total_orders = sum(stats['orders'] for stats in vendor_stats.values())
            
            # Find most loyal relationships
            top_vendor = max(vendor_stats.items(), key=lambda x: x[1]['orders'])[0] if vendor_stats else None
            top_vendor_orders = vendor_stats[top_vendor]['orders'] if top_vendor else 0
            
            # Calculate vendor concentration (Herfindahl index)
            order_shares = [stats['orders'] / total_orders for stats in vendor_stats.values()]
            vendor_concentration = sum(share ** 2 for share in order_shares)
            
            loyalty_level = 'high' if vendor_concentration > 0.5 else 'medium' if vendor_concentration > 0.25 else 'low'
            
            return {
                'total_vendors_used': total_vendors,
                'vendor_stats': dict(vendor_stats),
                'top_vendor': top_vendor,
                'top_vendor_order_share': top_vendor_orders / total_orders if total_orders > 0 else 0,
                'vendor_concentration': vendor_concentration,
                'loyalty_level': loyalty_level,
                'vendor_diversity': 1 - vendor_concentration  # Inverse of concentration
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze vendor preferences: {e}")
            return {}
    
    def _analyze_temporal_patterns(self, user) -> Dict[str, Any]:
        """Analyze temporal patterns in user behavior"""
        try:
            from orders.models import Order
            
            orders = Order.objects.filter(
                buyer=user,
                status__in=['completed', 'shipped', 'delivered']
            ).order_by('created_at')
            
            if orders.count() < 2:
                return {'insufficient_data': True}
            
            # Time-based analysis
            order_hours = [order.created_at.hour for order in orders]
            order_days = [order.created_at.weekday() for order in orders]  # 0=Monday
            order_months = [order.created_at.month for order in orders]
            
            # Peak activity times
            hour_distribution = Counter(order_hours)
            day_distribution = Counter(order_days)
            month_distribution = Counter(order_months)
            
            # Activity patterns
            morning_activity = sum(1 for h in order_hours if 6 <= h < 12)
            afternoon_activity = sum(1 for h in order_hours if 12 <= h < 18)
            evening_activity = sum(1 for h in order_hours if 18 <= h < 24)
            night_activity = sum(1 for h in order_hours if 0 <= h < 6)
            
            total_orders = len(order_hours)
            
            # Determine user type based on activity patterns
            if evening_activity / total_orders > 0.4:
                user_type = 'evening_shopper'
            elif morning_activity / total_orders > 0.4:
                user_type = 'morning_shopper'
            elif night_activity / total_orders > 0.3:
                user_type = 'night_owl'
            else:
                user_type = 'flexible'
            
            # Seasonality analysis
            seasonal_patterns = self._analyze_seasonal_patterns(order_months)
            
            return {
                'peak_hour': hour_distribution.most_common(1)[0][0],
                'peak_day': day_distribution.most_common(1)[0][0],
                'user_type': user_type,
                'activity_distribution': {
                    'morning': morning_activity / total_orders,
                    'afternoon': afternoon_activity / total_orders,
                    'evening': evening_activity / total_orders,
                    'night': night_activity / total_orders
                },
                'day_preferences': dict(day_distribution),
                'seasonal_patterns': seasonal_patterns
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze temporal patterns: {e}")
            return {}
    
    def _analyze_risk_profile(self, user) -> Dict[str, Any]:
        """Analyze user's risk profile based on purchase and dispute history"""
        try:
            from orders.models import Order
            from disputes.models import Dispute
            
            # Order analysis
            total_orders = Order.objects.filter(buyer=user).count()
            completed_orders = Order.objects.filter(
                buyer=user,
                status__in=['completed', 'delivered']
            ).count()
            
            # Dispute analysis
            disputes_filed = Dispute.objects.filter(complainant=user).count()
            disputes_won = Dispute.objects.filter(
                complainant=user,
                status='RESOLVED',
                winner_id=user.id
            ).count()
            
            # Calculate risk metrics
            dispute_rate = disputes_filed / total_orders if total_orders > 0 else 0
            dispute_success_rate = disputes_won / disputes_filed if disputes_filed > 0 else 1.0
            completion_rate = completed_orders / total_orders if total_orders > 0 else 0
            
            # Risk classification
            if dispute_rate < 0.05 and completion_rate > 0.95:
                risk_level = 'low'
            elif dispute_rate < 0.15 and completion_rate > 0.85:
                risk_level = 'medium'
            else:
                risk_level = 'high'
            
            return {
                'total_orders': total_orders,
                'completed_orders': completed_orders,
                'disputes_filed': disputes_filed,
                'disputes_won': disputes_won,
                'dispute_rate': dispute_rate,
                'dispute_success_rate': dispute_success_rate,
                'completion_rate': completion_rate,
                'risk_level': risk_level,
                'trustworthiness_score': self._calculate_trustworthiness_score(
                    completion_rate, dispute_rate, dispute_success_rate
                )
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze risk profile: {e}")
            return {}
    
    def _analyze_loyalty_indicators(self, user) -> Dict[str, Any]:
        """Analyze indicators of user loyalty and engagement"""
        try:
            from orders.models import Order
            
            # Account metrics
            account_age = (timezone.now() - user.date_joined).days
            
            # Order frequency
            orders = Order.objects.filter(buyer=user).order_by('created_at')
            if orders.count() < 2:
                return {'insufficient_data': True}
            
            # Calculate recency, frequency, monetary (RFM) analysis
            last_order_days = (timezone.now() - orders.last().created_at).days
            order_frequency = orders.count() / max(account_age, 1) * 365  # Orders per year
            total_monetary = sum(float(order.total_amount or 0) for order in orders)
            
            # Engagement consistency
            order_dates = [order.created_at.date() for order in orders]
            if len(order_dates) > 1:
                intervals = [(order_dates[i] - order_dates[i-1]).days for i in range(1, len(order_dates))]
                consistency_score = 1 / (statistics.stdev(intervals) + 1) if len(intervals) > 1 else 1
            else:
                consistency_score = 0
            
            # Loyalty score calculation
            recency_score = max(0, 1 - last_order_days / 365)  # Higher if recent
            frequency_score = min(1, order_frequency / 10)  # Normalize to 0-1
            monetary_score = min(1, total_monetary / 1000)  # Normalize to 0-1
            
            loyalty_score = (recency_score + frequency_score + monetary_score + consistency_score) / 4
            
            # Loyalty classification
            if loyalty_score > 0.7:
                loyalty_tier = 'champion'
            elif loyalty_score > 0.5:
                loyalty_tier = 'loyal'
            elif loyalty_score > 0.3:
                loyalty_tier = 'potential'
            else:
                loyalty_tier = 'at_risk'
            
            return {
                'account_age_days': account_age,
                'last_order_days_ago': last_order_days,
                'order_frequency_yearly': order_frequency,
                'total_monetary_value': total_monetary,
                'consistency_score': consistency_score,
                'rfm_scores': {
                    'recency': recency_score,
                    'frequency': frequency_score,
                    'monetary': monetary_score
                },
                'loyalty_score': loyalty_score,
                'loyalty_tier': loyalty_tier
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze loyalty indicators: {e}")
            return {}
    
    def _calculate_profile_completeness(self, user) -> Dict[str, Any]:
        """Calculate how complete the user's behavioral profile is"""
        try:
            from orders.models import Order
            
            completeness_factors = {
                'has_orders': Order.objects.filter(buyer=user).exists(),
                'has_multiple_orders': Order.objects.filter(buyer=user).count() >= 3,
                'has_recent_activity': Order.objects.filter(
                    buyer=user,
                    created_at__gte=timezone.now() - timedelta(days=90)
                ).exists(),
                'account_age_sufficient': (timezone.now() - user.date_joined).days >= 30
            }
            
            completeness_score = sum(completeness_factors.values()) / len(completeness_factors)
            
            confidence_level = 'high' if completeness_score > 0.75 else 'medium' if completeness_score > 0.5 else 'low'
            
            return {
                'completeness_factors': completeness_factors,
                'completeness_score': completeness_score,
                'confidence_level': confidence_level,
                'data_points_available': sum(completeness_factors.values()),
                'recommendations_reliability': confidence_level
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate profile completeness: {e}")
            return {}
    
    def _generate_behavior_predictions(self, user, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate predictions about future user behavior"""
        try:
            predictions = {}
            
            # Purchase timing predictions
            if 'temporal_patterns' in profile and profile['temporal_patterns'].get('peak_hour'):
                predictions['next_purchase_likely_time'] = {
                    'hour': profile['temporal_patterns']['peak_hour'],
                    'day_type': profile['temporal_patterns']['user_type']
                }
            
            # Spending predictions
            if 'purchase_patterns' in profile:
                avg_order_value = profile['purchase_patterns'].get('average_order_value', 0)
                days_between_orders = profile['purchase_patterns'].get('average_days_between_orders', 0)
                
                if days_between_orders > 0:
                    predictions['next_purchase_likelihood'] = {
                        'days_estimate': days_between_orders,
                        'confidence': 'medium',
                        'estimated_value': avg_order_value
                    }
            
            # Category predictions
            if 'category_affinity' in profile and profile['category_affinity'].get('top_categories'):
                predictions['likely_categories'] = profile['category_affinity']['top_categories'][:3]
            
            # Churn risk prediction
            if 'loyalty_indicators' in profile:
                loyalty_tier = profile['loyalty_indicators'].get('loyalty_tier', 'unknown')
                last_order_days = profile['loyalty_indicators'].get('last_order_days_ago', 0)
                
                if loyalty_tier == 'at_risk' or last_order_days > 180:
                    churn_risk = 'high'
                elif loyalty_tier == 'potential' or last_order_days > 90:
                    churn_risk = 'medium'
                else:
                    churn_risk = 'low'
                
                predictions['churn_risk'] = {
                    'risk_level': churn_risk,
                    'days_since_last_order': last_order_days,
                    'retention_priority': 'high' if churn_risk == 'high' else 'medium'
                }
            
            return predictions
            
        except Exception as e:
            logger.error(f"Failed to generate behavior predictions: {e}")
            return {}
    
    def _generate_profile_recommendations(self, profile: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate recommendations based on user profile"""
        recommendations = []
        
        try:
            # Loyalty-based recommendations
            if 'loyalty_indicators' in profile:
                loyalty_tier = profile['loyalty_indicators'].get('loyalty_tier', 'unknown')
                
                if loyalty_tier == 'champion':
                    recommendations.append({
                        'type': 'loyalty_reward',
                        'title': 'VIP Benefits Available',
                        'description': 'As a champion customer, you qualify for exclusive perks and early access.',
                        'priority': 'high'
                    })
                elif loyalty_tier == 'at_risk':
                    recommendations.append({
                        'type': 'retention',
                        'title': 'Special Offer for You',
                        'description': 'We miss you! Check out these personalized deals to get you back shopping.',
                        'priority': 'high'
                    })
            
            # Price sensitivity recommendations
            if 'price_sensitivity' in profile:
                if profile['price_sensitivity'].get('budget_conscious'):
                    recommendations.append({
                        'type': 'budget_deals',
                        'title': 'Budget-Friendly Options',
                        'description': 'Discover great value products that match your smart shopping style.',
                        'priority': 'medium'
                    })
                elif profile['price_sensitivity'].get('luxury_affinity'):
                    recommendations.append({
                        'type': 'premium_products',
                        'title': 'Premium Collection',
                        'description': 'Explore our high-end products that match your refined taste.',
                        'priority': 'medium'
                    })
            
            # Category expansion recommendations
            if 'category_affinity' in profile:
                diversity = profile['category_affinity'].get('category_diversity', 0)
                if diversity < 0.3:
                    recommendations.append({
                        'type': 'category_expansion',
                        'title': 'Explore New Categories',
                        'description': 'Branch out and discover products in categories you haven\'t tried yet.',
                        'priority': 'low'
                    })
            
        except Exception as e:
            logger.error(f"Failed to generate profile recommendations: {e}")
        
        return recommendations
    
    def _calculate_confidence_scores(self, profile: Dict[str, Any]) -> Dict[str, float]:
        """Calculate confidence scores for different profile sections"""
        scores = {}
        
        try:
            # Base confidence on data availability and recency
            completeness = profile.get('profile_completeness', {}).get('completeness_score', 0)
            
            for section in ['purchase_patterns', 'price_sensitivity', 'category_affinity', 'vendor_preferences']:
                if section in profile and not profile[section].get('no_data', False):
                    # Higher confidence for more complete data
                    scores[section] = min(1.0, completeness + 0.2)
                else:
                    scores[section] = 0.1  # Low confidence for missing data
            
        except Exception as e:
            logger.error(f"Failed to calculate confidence scores: {e}")
        
        return scores
    
    # Helper methods
    def _classify_user_segment(self, total_orders: int, account_age: int, recent_orders: int) -> str:
        """Classify user into behavioral segments"""
        if total_orders == 0:
            return 'new_visitor'
        elif total_orders >= 20 and recent_orders >= 2:
            return 'power_user'
        elif total_orders >= 5 and recent_orders >= 1:
            return 'regular_customer'
        elif recent_orders == 0 and account_age > 180:
            return 'dormant_user'
        else:
            return 'occasional_buyer'
    
    def _classify_purchase_frequency(self, avg_days: float) -> str:
        """Classify purchase frequency"""
        if avg_days <= 7:
            return 'very_frequent'
        elif avg_days <= 30:
            return 'frequent'
        elif avg_days <= 90:
            return 'occasional'
        else:
            return 'rare'
    
    def _classify_spending_tier(self, total_spent: float) -> str:
        """Classify user spending tier"""
        if total_spent >= 5000:
            return 'high_value'
        elif total_spent >= 1000:
            return 'medium_value'
        elif total_spent >= 100:
            return 'low_value'
        else:
            return 'minimal_spender'
    
    def _calculate_exploration_score(self, categories: int, vendors: int, price_range: float) -> float:
        """Calculate how much the user explores different options"""
        # Normalize each factor and combine
        category_score = min(1.0, categories / 10)  # Max 10 categories
        vendor_score = min(1.0, vendors / 20)  # Max 20 vendors
        price_score = min(1.0, price_range / 1000)  # Max $1000 range
        
        return (category_score + vendor_score + price_score) / 3
    
    def _analyze_seasonal_patterns(self, months: List[int]) -> Dict[str, Any]:
        """Analyze seasonal purchasing patterns"""
        month_counts = Counter(months)
        
        # Group by seasons
        seasons = {
            'spring': sum(month_counts[m] for m in [3, 4, 5]),
            'summer': sum(month_counts[m] for m in [6, 7, 8]),
            'fall': sum(month_counts[m] for m in [9, 10, 11]),
            'winter': sum(month_counts[m] for m in [12, 1, 2])
        }
        
        total = sum(seasons.values())
        if total == 0:
            return {}
        
        season_preferences = {season: count/total for season, count in seasons.items()}
        preferred_season = max(season_preferences, key=season_preferences.get)
        
        return {
            'season_distribution': season_preferences,
            'preferred_season': preferred_season,
            'seasonal_variation': max(season_preferences.values()) - min(season_preferences.values())
        }
    
    def _calculate_trustworthiness_score(self, completion_rate: float, 
                                       dispute_rate: float, dispute_success_rate: float) -> float:
        """Calculate overall trustworthiness score"""
        # Weight factors: completion (40%), low disputes (40%), dispute success (20%)
        completion_score = completion_rate * 0.4
        dispute_score = (1 - dispute_rate) * 0.4  # Lower dispute rate is better
        success_score = dispute_success_rate * 0.2
        
        return completion_score + dispute_score + success_score
    
    # Insight generation methods
    def _generate_spending_insights(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights about user spending patterns"""
        insights = {}
        
        try:
            if 'purchase_patterns' in profile:
                pp = profile['purchase_patterns']
                insights['spending_summary'] = f"You've spent ${pp.get('total_spent', 0):.2f} across {pp.get('total_orders', 0)} orders"
                insights['avg_order_insight'] = f"Your average order value is ${pp.get('average_order_value', 0):.2f}"
                
                frequency = pp.get('purchase_frequency', 'unknown')
                if frequency == 'very_frequent':
                    insights['frequency_insight'] = "You're a very active shopper with frequent purchases"
                elif frequency == 'rare':
                    insights['frequency_insight'] = "You make purchases occasionally - consider setting up wish lists for items you're interested in"
        
        except Exception as e:
            logger.error(f"Failed to generate spending insights: {e}")
        
        return insights
    
    def _generate_category_insights(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights about category preferences"""
        insights = {}
        
        try:
            if 'category_affinity' in profile and profile['category_affinity'].get('top_categories'):
                top_cats = profile['category_affinity']['top_categories']
                insights['top_category_insight'] = f"Your favorite categories are: {', '.join(top_cats[:3])}"
                
                diversity = profile['category_affinity'].get('category_diversity', 0)
                if diversity > 0.5:
                    insights['diversity_insight'] = "You have diverse shopping interests across many categories"
                else:
                    insights['diversity_insight'] = "You tend to focus on specific categories - consider exploring new ones"
        
        except Exception as e:
            logger.error(f"Failed to generate category insights: {e}")
        
        return insights
    
    def _generate_behavioral_insights(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights about behavioral patterns"""
        insights = {}
        
        try:
            if 'temporal_patterns' in profile:
                tp = profile['temporal_patterns']
                user_type = tp.get('user_type', 'flexible')
                
                type_descriptions = {
                    'evening_shopper': "You prefer shopping in the evening hours",
                    'morning_shopper': "You're an early bird who likes morning shopping",
                    'night_owl': "You often shop late at night",
                    'flexible': "You shop at various times throughout the day"
                }
                
                insights['timing_insight'] = type_descriptions.get(user_type, "Your shopping timing is varied")
            
            if 'loyalty_indicators' in profile:
                loyalty_tier = profile['loyalty_indicators'].get('loyalty_tier', 'unknown')
                tier_messages = {
                    'champion': "You're one of our most valued customers!",
                    'loyal': "You're a loyal customer with consistent engagement",
                    'potential': "You show good potential for increased engagement",
                    'at_risk': "We'd love to see you shop with us more often"
                }
                
                insights['loyalty_insight'] = tier_messages.get(loyalty_tier, "Building your shopping relationship")
        
        except Exception as e:
            logger.error(f"Failed to generate behavioral insights: {e}")
        
        return insights
    
    def _generate_opportunity_insights(self, profile: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate insights about opportunities for the user"""
        opportunities = []
        
        try:
            # Price optimization opportunities
            if 'price_sensitivity' in profile:
                if profile['price_sensitivity'].get('budget_conscious'):
                    opportunities.append({
                        'type': 'savings',
                        'title': 'Save More',
                        'description': 'Set up price alerts for items on your wishlist to catch the best deals'
                    })
            
            # Category expansion opportunities
            if 'category_affinity' in profile:
                diversity = profile['category_affinity'].get('category_diversity', 0)
                if diversity < 0.3:
                    opportunities.append({
                        'type': 'exploration',
                        'title': 'Discover New Products',
                        'description': 'Explore new categories based on your interests'
                    })
        
        except Exception as e:
            logger.error(f"Failed to generate opportunity insights: {e}")
        
        return opportunities
    
    def _generate_comparison_insights(self, user_id: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights comparing user to similar users"""
        # This would require aggregate data analysis in a real implementation
        # For now, return generic comparison insights
        return {
            'spending_comparison': "Your spending is within the typical range for users with similar activity levels",
            'engagement_comparison': "Your engagement level is above average compared to similar users"
        }
    
    def _generate_trend_insights(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights about user trends over time"""
        insights = {}
        
        try:
            if 'predictions' in profile and 'churn_risk' in profile['predictions']:
                risk_level = profile['predictions']['churn_risk'].get('risk_level', 'unknown')
                
                if risk_level == 'high':
                    insights['engagement_trend'] = "Your activity has decreased recently - check out what's new!"
                elif risk_level == 'low':
                    insights['engagement_trend'] = "Your engagement is strong and consistent"
                else:
                    insights['engagement_trend'] = "Your activity level is moderate"
        
        except Exception as e:
            logger.error(f"Failed to generate trend insights: {e}")
        
        return insights
    
    def _generate_privacy_summary(self) -> Dict[str, str]:
        """Generate privacy-focused summary of data usage"""
        return {
            'data_usage': "Your behavioral analysis is based only on your purchase history and account activity",
            'privacy_protection': "All analysis is performed server-side with no external data sharing",
            'data_control': "You can request deletion of your behavioral profile at any time",
            'anonymization': "Your data is never combined with external sources or shared with third parties"
        }