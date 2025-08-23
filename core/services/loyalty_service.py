"""
Loyalty Service
Handles user loyalty points, levels, and rewards.
"""

import logging
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any

from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.core.cache import cache

from .base_service import BaseService, performance_monitor

logger = logging.getLogger(__name__)

User = get_user_model()


class LoyaltyService(BaseService):
    """Service for managing user loyalty points and rewards."""
    
    service_name = "loyalty_service"
    description = "Manages user loyalty points, levels, and rewards"
    
    def __init__(self):
        super().__init__()
        self.points_per_dollar = 10  # 10 points per $1 spent
        self.bonus_multipliers = {
            'first_purchase': 2.0,  # Double points for first purchase
            'weekend_purchase': 1.5,  # 50% bonus for weekend purchases
            'bulk_purchase': 1.25,   # 25% bonus for bulk purchases
        }
    
    @performance_monitor
    def calculate_user_points(self, user: User) -> Tuple[int, str]:
        """Calculate total loyalty points and level for a user."""
        try:
            # Get user's order history
            from orders.models import Order
            orders = Order.objects.filter(buyer=user, status='completed')
            
            total_spent = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
            base_points = int(total_spent * self.points_per_dollar)
            
            # Apply bonuses
            bonus_points = self._calculate_bonus_points(user, orders)
            total_points = base_points + bonus_points
            
            # Calculate level
            level = self._calculate_user_level(total_points)
            
            return total_points, level
            
        except Exception as e:
            logger.error(f"Error calculating loyalty points for user {user.username}: {str(e)}")
            return 0, 'bronze'
    
    def _calculate_bonus_points(self, user: User, orders) -> int:
        """Calculate bonus points based on various factors."""
        bonus_points = 0
        
        try:
            # First purchase bonus
            if orders.count() == 1:
                first_order = orders.first()
                if first_order:
                    bonus_points += int(first_order.total_amount * self.points_per_dollar * 
                                     (self.bonus_multipliers['first_purchase'] - 1))
            
            # Weekend purchase bonus
            weekend_orders = orders.filter(created_at__week_day__in=[1, 7])  # Monday and Sunday
            for order in weekend_orders:
                bonus_points += int(order.total_amount * self.points_per_dollar * 
                                 (self.bonus_multipliers['weekend_purchase'] - 1))
            
            # Bulk purchase bonus (orders over $100)
            bulk_orders = orders.filter(total_amount__gte=100)
            for order in bulk_orders:
                bonus_points += int(order.total_amount * self.points_per_dollar * 
                                 (self.bonus_multipliers['bulk_purchase'] - 1))
            
            return bonus_points
            
        except Exception as e:
            logger.error(f"Error calculating bonus points for user {user.username}: {str(e)}")
            return 0
    
    def _calculate_user_level(self, points: int) -> str:
        """Calculate user loyalty level based on points."""
        if points >= 10000:
            return 'diamond'
        elif points >= 5000:
            return 'platinum'
        elif points >= 2500:
            return 'gold'
        elif points >= 1000:
            return 'silver'
        else:
            return 'bronze'
    
    @performance_monitor
    def get_available_rewards(self, user: User) -> List[Dict[str, Any]]:
        """Get available rewards for a user based on their level."""
        try:
            points, level = self.calculate_user_points(user)
            
            # Define rewards based on level
            rewards = {
                'bronze': [
                    {'id': 'discount_5', 'name': '5% Discount', 'points_cost': 100, 'type': 'discount'},
                    {'id': 'free_shipping', 'name': 'Free Shipping', 'points_cost': 200, 'type': 'shipping'},
                ],
                'silver': [
                    {'id': 'discount_10', 'name': '10% Discount', 'points_cost': 300, 'type': 'discount'},
                    {'id': 'free_shipping', 'name': 'Free Shipping', 'points_cost': 150, 'type': 'shipping'},
                    {'id': 'priority_support', 'name': 'Priority Support', 'points_cost': 400, 'type': 'service'},
                ],
                'gold': [
                    {'id': 'discount_15', 'name': '15% Discount', 'points_cost': 500, 'type': 'discount'},
                    {'id': 'free_shipping', 'name': 'Free Shipping', 'points_cost': 100, 'type': 'shipping'},
                    {'id': 'priority_support', 'name': 'Priority Support', 'points_cost': 300, 'type': 'service'},
                    {'id': 'early_access', 'name': 'Early Access to Sales', 'points_cost': 600, 'type': 'access'},
                ],
                'platinum': [
                    {'id': 'discount_20', 'name': '20% Discount', 'points_cost': 700, 'type': 'discount'},
                    {'id': 'free_shipping', 'name': 'Free Shipping', 'points_cost': 50, 'type': 'shipping'},
                    {'id': 'priority_support', 'name': 'Priority Support', 'points_cost': 200, 'type': 'service'},
                    {'id': 'early_access', 'name': 'Early Access to Sales', 'points_cost': 400, 'type': 'access'},
                    {'id': 'vip_event', 'name': 'VIP Event Access', 'points_cost': 1000, 'type': 'event'},
                ],
                'diamond': [
                    {'id': 'discount_25', 'name': '25% Discount', 'points_cost': 1000, 'type': 'discount'},
                    {'id': 'free_shipping', 'name': 'Free Shipping', 'points_cost': 0, 'type': 'shipping'},
                    {'id': 'priority_support', 'name': 'Priority Support', 'points_cost': 100, 'type': 'service'},
                    {'id': 'early_access', 'name': 'Early Access to Sales', 'points_cost': 200, 'type': 'access'},
                    {'id': 'vip_event', 'name': 'VIP Event Access', 'points_cost': 500, 'type': 'event'},
                    {'id': 'personal_concierge', 'name': 'Personal Concierge', 'points_cost': 2000, 'type': 'service'},
                ]
            }
            
            return rewards.get(level, [])
            
        except Exception as e:
            logger.error(f"Error getting available rewards for user {user.username}: {str(e)}")
            return []
    
    @performance_monitor
    def redeem_reward(self, user: User, reward_id: str) -> Dict[str, Any]:
        """Redeem a loyalty reward."""
        try:
            available_rewards = self.get_available_rewards(user)
            reward = next((r for r in available_rewards if r['id'] == reward_id), None)
            
            if not reward:
                return {'success': False, 'message': 'Reward not available'}
            
            points, level = self.calculate_user_points(user)
            if points < reward['points_cost']:
                return {'success': False, 'message': 'Insufficient points'}
            
            # Apply reward
            if reward['type'] == 'discount':
                # Store discount in user session or database
                cache.set(f"loyalty_discount_{user.id}", reward['name'], 3600)  # 1 hour
                message = f"Discount applied: {reward['name']}"
            elif reward['type'] == 'shipping':
                cache.set(f"loyalty_free_shipping_{user.id}", True, 3600)
                message = f"Free shipping applied for next order"
            elif reward['type'] == 'service':
                cache.set(f"loyalty_service_{user.id}_{reward_id}", True, 86400)  # 24 hours
                message = f"Service benefit applied: {reward['name']}"
            elif reward['type'] == 'access':
                cache.set(f"loyalty_access_{user.id}_{reward_id}", True, 86400)
                message = f"Access granted: {reward['name']}"
            elif reward['type'] == 'event':
                cache.set(f"loyalty_event_{user.id}_{reward_id}", True, 604800)  # 1 week
                message = f"Event access granted: {reward['name']}"
            else:
                message = f"Reward applied: {reward['name']}"
            
            # Deduct points (in a real system, this would update the database)
            # For now, we'll just return success
            
            return {
                'success': True,
                'message': message,
                'reward': reward,
                'points_deducted': reward['points_cost']
            }
            
        except Exception as e:
            logger.error(f"Error redeeming reward for user {user.username}: {str(e)}")
            return {'success': False, 'message': f'Error redeeming reward: {str(e)}'}
    
    @performance_monitor
    def get_user_loyalty_summary(self, user: User) -> Dict[str, Any]:
        """Get comprehensive loyalty summary for a user."""
        try:
            points, level = self.calculate_user_points(user)
            available_rewards = self.get_available_rewards(user)
            
            # Calculate progress to next level
            level_thresholds = {
                'bronze': 0,
                'silver': 1000,
                'gold': 2500,
                'platinum': 5000,
                'diamond': 10000
            }
            
            current_threshold = level_thresholds.get(level, 0)
            next_level = None
            progress_to_next = 0
            
            if level != 'diamond':
                for lvl, threshold in level_thresholds.items():
                    if threshold > current_threshold:
                        next_level = lvl
                        progress_to_next = ((points - current_threshold) / (threshold - current_threshold)) * 100
                        break
            
            return {
                'current_points': points,
                'current_level': level,
                'next_level': next_level,
                'progress_to_next': min(progress_to_next, 100),
                'available_rewards': available_rewards,
                'total_rewards_available': len(available_rewards),
                'level_benefits': self._get_level_benefits(level)
            }
            
        except Exception as e:
            logger.error(f"Error getting loyalty summary for user {user.username}: {str(e)}")
            return {}
    
    def _get_level_benefits(self, level: str) -> List[str]:
        """Get benefits for a specific loyalty level."""
        benefits = {
            'bronze': [
                'Basic rewards',
                'Standard support',
                'Email notifications'
            ],
            'silver': [
                'Enhanced rewards',
                'Priority support',
                'Exclusive offers',
                'Faster shipping'
            ],
            'gold': [
                'Premium rewards',
                'VIP support',
                'Early access to sales',
                'Special discounts',
                'Dedicated account manager'
            ],
            'platinum': [
                'Exclusive rewards',
                'Dedicated support',
                'VIP events access',
                'Premium discounts',
                'Personal shopping assistance'
            ],
            'diamond': [
                'Ultimate rewards',
                'Personal concierge',
                'Exclusive events',
                'Maximum discounts',
                'Custom services',
                'Priority everything'
            ]
        }
        
        return benefits.get(level, [])