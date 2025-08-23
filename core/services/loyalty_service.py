"""
Loyalty Service
Handles loyalty points, rewards, and user incentives.
Designed for Tor-safe server-side processing without JavaScript.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count, Q
from django.utils import timezone

from core.base_service import BaseService

logger = logging.getLogger(__name__)
User = get_user_model()


class LoyaltyService(BaseService):
    """Loyalty system with points and rewards for Tor users"""
    
    service_name = "loyalty_service"
    version = "1.0.0"
    description = "Points-based loyalty system with rewards"
    
    # Points calculation constants
    POINTS_PER_DOLLAR = 10  # 10 points per dollar spent
    BONUS_DISPUTE_FREE = 50  # Bonus for dispute-free orders
    BONUS_REVIEW = 25  # Bonus for leaving reviews
    BONUS_REFERRAL = 100  # Bonus for successful referrals
    PENALTY_DISPUTE = -25  # Penalty for disputes (if user loses)
    
    def __init__(self):
        super().__init__()
        self._loyalty_cache = {}
    
    def initialize(self):
        """Initialize the loyalty service"""
        try:
            logger.info("Loyalty service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize loyalty service: {e}")
            raise e
    
    def cleanup(self):
        """Clean up the loyalty service"""
        try:
            self._loyalty_cache.clear()
            logger.info("Loyalty service cleaned up successfully")
        except Exception as e:
            logger.error(f"Failed to cleanup loyalty service: {e}")
    
    def calculate_user_points(self, user_id: str) -> Dict[str, Any]:
        """Calculate total loyalty points for a user"""
        try:
            from orders.models import Order
            from disputes.models import Dispute
            
            user = User.objects.get(id=user_id)
            
            # Cache check
            cache_key = f"loyalty_points:{user_id}"
            cached_points = self.get_cached(cache_key)
            if cached_points:
                return cached_points
            
            points_breakdown = {
                'total_points': 0,
                'purchase_points': 0,
                'bonus_points': 0,
                'penalty_points': 0,
                'available_points': 0,
                'lifetime_earned': 0,
                'points_spent': 0
            }
            
            # Points from completed orders
            completed_orders = Order.objects.filter(buyer=user, status="completed")
            total_spent = Decimal('0')
            
            for order in completed_orders:
                order_value = order.total_amount or Decimal('0')
                total_spent += order_value
                order_points = int(float(order_value) * self.POINTS_PER_DOLLAR)
                points_breakdown['purchase_points'] += order_points
                
                # Bonus for dispute-free orders
                if not hasattr(order, 'dispute'):
                    points_breakdown['bonus_points'] += self.BONUS_DISPUTE_FREE
            
            # Penalties from disputes (where user lost)
            lost_disputes = Dispute.objects.filter(
                complainant=user,
                status="RESOLVED"
            ).exclude(winner_id=user.id)
            
            points_breakdown['penalty_points'] = len(lost_disputes) * self.PENALTY_DISPUTE
            
            # Calculate totals
            points_breakdown['lifetime_earned'] = (
                points_breakdown['purchase_points'] + 
                points_breakdown['bonus_points']
            )
            
            points_breakdown['total_points'] = (
                points_breakdown['lifetime_earned'] + 
                points_breakdown['penalty_points']
            )
            
            # Get points spent on rewards
            points_breakdown['points_spent'] = self._get_points_spent(user_id)
            points_breakdown['available_points'] = max(0, 
                points_breakdown['total_points'] - points_breakdown['points_spent']
            )
            
            # Add user level
            points_breakdown['user_level'] = self._calculate_user_level(
                points_breakdown['lifetime_earned']
            )
            
            # Cache for 10 minutes
            self.set_cached(cache_key, points_breakdown, timeout=600)
            
            return points_breakdown
            
        except Exception as e:
            logger.error(f"Failed to calculate loyalty points for user {user_id}: {e}")
            return {'total_points': 0, 'available_points': 0, 'error': str(e)}
    
    def get_available_rewards(self, user_id: str) -> List[Dict[str, Any]]:
        """Get rewards available to user based on their points"""
        try:
            points_data = self.calculate_user_points(user_id)
            available_points = points_data.get('available_points', 0)
            user_level = points_data.get('user_level', 'Bronze')
            
            rewards = []
            
            # Basic rewards available to all
            basic_rewards = [
                {
                    'id': 'free_shipping',
                    'name': 'Free Shipping',
                    'description': 'Free shipping on your next order',
                    'cost': 1000,
                    'type': 'shipping',
                    'level_required': 'Bronze',
                    'expires_days': 30
                },
                {
                    'id': 'discount_5',
                    'name': '5% Discount',
                    'description': '5% discount on your next order',
                    'cost': 2500,
                    'type': 'discount',
                    'level_required': 'Bronze',
                    'expires_days': 30
                },
                {
                    'id': 'priority_support',
                    'name': 'Priority Support',
                    'description': 'Priority customer support for 30 days',
                    'cost': 1500,
                    'type': 'support',
                    'level_required': 'Silver',
                    'expires_days': 30
                }
            ]
            
            # Silver level rewards
            if user_level in ['Silver', 'Gold', 'Platinum']:
                basic_rewards.extend([
                    {
                        'id': 'discount_10',
                        'name': '10% Discount',
                        'description': '10% discount on your next order',
                        'cost': 5000,
                        'type': 'discount',
                        'level_required': 'Silver',
                        'expires_days': 30
                    },
                    {
                        'id': 'early_access',
                        'name': 'Early Access',
                        'description': 'Early access to new products for 7 days',
                        'cost': 3000,
                        'type': 'access',
                        'level_required': 'Silver',
                        'expires_days': 7
                    }
                ])
            
            # Gold level rewards
            if user_level in ['Gold', 'Platinum']:
                basic_rewards.extend([
                    {
                        'id': 'discount_15',
                        'name': '15% Discount',
                        'description': '15% discount on your next order',
                        'cost': 7500,
                        'type': 'discount',
                        'level_required': 'Gold',
                        'expires_days': 30
                    },
                    {
                        'id': 'vendor_priority',
                        'name': 'Vendor Priority',
                        'description': 'Priority processing from all vendors',
                        'cost': 6000,
                        'type': 'priority',
                        'level_required': 'Gold',
                        'expires_days': 60
                    }
                ])
            
            # Platinum level rewards
            if user_level == 'Platinum':
                basic_rewards.extend([
                    {
                        'id': 'discount_20',
                        'name': '20% Discount',
                        'description': '20% discount on your next order',
                        'cost': 10000,
                        'type': 'discount',
                        'level_required': 'Platinum',
                        'expires_days': 30
                    },
                    {
                        'id': 'concierge',
                        'name': 'Concierge Service',
                        'description': 'Personal shopping assistance',
                        'cost': 15000,
                        'type': 'concierge',
                        'level_required': 'Platinum',
                        'expires_days': 90
                    }
                ])
            
            # Filter rewards user can afford and has level for
            level_order = ['Bronze', 'Silver', 'Gold', 'Platinum']
            user_level_index = level_order.index(user_level)
            
            for reward in basic_rewards:
                reward_level_index = level_order.index(reward['level_required'])
                
                if (available_points >= reward['cost'] and 
                    user_level_index >= reward_level_index):
                    reward['affordable'] = True
                    reward['available'] = True
                else:
                    reward['affordable'] = available_points >= reward['cost']
                    reward['available'] = user_level_index >= reward_level_index
                
                rewards.append(reward)
            
            return rewards
            
        except Exception as e:
            logger.error(f"Failed to get available rewards for user {user_id}: {e}")
            return []
    
    def redeem_reward(self, user_id: str, reward_id: str) -> Tuple[bool, str]:
        """Redeem a reward for the user"""
        try:
            # Get user's available points
            points_data = self.calculate_user_points(user_id)
            available_points = points_data.get('available_points', 0)
            
            # Get reward details
            available_rewards = self.get_available_rewards(user_id)
            reward = None
            
            for r in available_rewards:
                if r['id'] == reward_id:
                    reward = r
                    break
            
            if not reward:
                return False, "Reward not found or not available"
            
            if not reward.get('affordable', False):
                return False, f"Insufficient points. Need {reward['cost']}, have {available_points}"
            
            if not reward.get('available', False):
                return False, f"Reward requires {reward['level_required']} level"
            
            # Create reward record
            reward_record = {
                'user_id': user_id,
                'reward_id': reward_id,
                'reward_name': reward['name'],
                'points_spent': reward['cost'],
                'redeemed_at': timezone.now(),
                'expires_at': timezone.now() + timedelta(days=reward.get('expires_days', 30)),
                'status': 'active'
            }
            
            # Store in cache (in production, this would be in database)
            user_rewards_key = f"user_rewards:{user_id}"
            user_rewards = self.get_cached(user_rewards_key, [])
            user_rewards.append(reward_record)
            self.set_cached(user_rewards_key, user_rewards, timeout=86400)  # 24 hours
            
            # Update points spent
            points_spent_key = f"points_spent:{user_id}"
            total_spent = self.get_cached(points_spent_key, 0)
            total_spent += reward['cost']
            self.set_cached(points_spent_key, total_spent, timeout=86400)
            
            # Clear points cache to force recalculation
            self.clear_cache(f"loyalty_points:{user_id}")
            
            logger.info(f"User {user_id} redeemed reward {reward_id} for {reward['cost']} points")
            
            return True, f"Successfully redeemed {reward['name']}!"
            
        except Exception as e:
            logger.error(f"Failed to redeem reward for user {user_id}: {e}")
            return False, f"Failed to redeem reward: {str(e)}"
    
    def get_user_rewards(self, user_id: str, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get user's redeemed rewards"""
        try:
            user_rewards_key = f"user_rewards:{user_id}"
            user_rewards = self.get_cached(user_rewards_key, [])
            
            if active_only:
                now = timezone.now()
                user_rewards = [
                    r for r in user_rewards 
                    if r.get('status') == 'active' and 
                    datetime.fromisoformat(r['expires_at'].isoformat()) > now
                ]
            
            return user_rewards
            
        except Exception as e:
            logger.error(f"Failed to get user rewards for {user_id}: {e}")
            return []
    
    def _get_points_spent(self, user_id: str) -> int:
        """Get total points spent by user"""
        points_spent_key = f"points_spent:{user_id}"
        return self.get_cached(points_spent_key, 0)
    
    def _calculate_user_level(self, lifetime_points: int) -> str:
        """Calculate user level based on lifetime points earned"""
        if lifetime_points >= 50000:
            return 'Platinum'
        elif lifetime_points >= 25000:
            return 'Gold'
        elif lifetime_points >= 10000:
            return 'Silver'
        else:
            return 'Bronze'
    
    def add_bonus_points(self, user_id: str, points: int, reason: str) -> bool:
        """Add bonus points to user (for special events, referrals, etc.)"""
        try:
            bonus_key = f"bonus_points:{user_id}"
            current_bonus = self.get_cached(bonus_key, 0)
            current_bonus += points
            self.set_cached(bonus_key, current_bonus, timeout=86400)
            
            # Clear points cache to force recalculation
            self.clear_cache(f"loyalty_points:{user_id}")
            
            logger.info(f"Added {points} bonus points to user {user_id}: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add bonus points to user {user_id}: {e}")
            return False
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top users by loyalty points (anonymized for privacy)"""
        try:
            # This would query all users and calculate their points
            # For now, return empty list as this requires significant computation
            return []
            
        except Exception as e:
            logger.error(f"Failed to get leaderboard: {e}")
            return []