"""
Recommendation Service
Provides intelligent product recommendations using collaborative filtering and content-based approaches.
Designed for Tor-safe server-side processing without JavaScript.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict, Counter
from decimal import Decimal
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.db.models import Count, Avg, Sum, Q, F
from django.utils import timezone

from core.base_service import BaseService

logger = logging.getLogger(__name__)
User = get_user_model()


class RecommendationService(BaseService):
    """Intelligent product recommendation service for Tor users"""
    
    service_name = "recommendation_service"
    version = "1.0.0"
    description = "AI-powered product recommendations with collaborative and content-based filtering"
    
    def __init__(self):
        super().__init__()
        self._recommendation_cache = {}
        self._similarity_cache = {}
    
    def initialize(self):
        """Initialize the recommendation service"""
        try:
            logger.info("Recommendation service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize recommendation service: {e}")
            raise e
    
    def cleanup(self):
        """Clean up the recommendation service"""
        try:
            self._recommendation_cache.clear()
            self._similarity_cache.clear()
            logger.info("Recommendation service cleaned up successfully")
        except Exception as e:
            logger.error(f"Failed to cleanup recommendation service: {e}")
    
    def get_recommendations_for_user(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get personalized product recommendations for a user"""
        try:
            cache_key = f"user_recommendations:{user_id}:{limit}"
            cached_recommendations = self.get_cached(cache_key)
            if cached_recommendations:
                return cached_recommendations
            
            user = User.objects.get(id=user_id)
            
            # Get recommendations from multiple approaches
            collaborative_recs = self._get_collaborative_recommendations(user, limit // 2)
            content_based_recs = self._get_content_based_recommendations(user, limit // 2)
            trending_recs = self._get_trending_recommendations(user, limit // 4)
            
            # Combine and deduplicate recommendations
            all_recommendations = []
            seen_products = set()
            
            # Priority order: collaborative > content-based > trending
            for rec_list in [collaborative_recs, content_based_recs, trending_recs]:
                for rec in rec_list:
                    if rec['product_id'] not in seen_products:
                        all_recommendations.append(rec)
                        seen_products.add(rec['product_id'])
                        
                        if len(all_recommendations) >= limit:
                            break
                
                if len(all_recommendations) >= limit:
                    break
            
            # If we don't have enough recommendations, add popular products
            if len(all_recommendations) < limit:
                popular_recs = self._get_popular_recommendations(
                    user, limit - len(all_recommendations), exclude_ids=seen_products
                )
                all_recommendations.extend(popular_recs)
            
            # Add recommendation reasons and metadata
            final_recommendations = []
            for rec in all_recommendations[:limit]:
                enhanced_rec = self._enhance_recommendation(rec, user)
                final_recommendations.append(enhanced_rec)
            
            # Cache for 2 hours
            self.set_cached(cache_key, final_recommendations, timeout=7200)
            
            return final_recommendations
            
        except Exception as e:
            logger.error(f"Failed to get recommendations for user {user_id}: {e}")
            return []
    
    def get_similar_products(self, product_id: str, limit: int = 6) -> List[Dict[str, Any]]:
        """Get products similar to the given product"""
        try:
            from products.models import Product
            
            cache_key = f"similar_products:{product_id}:{limit}"
            cached_similar = self.get_cached(cache_key)
            if cached_similar:
                return cached_similar
            
            product = Product.objects.get(id=product_id, is_available=True)
            
            # Content-based similarity
            similar_products = []
            
            # 1. Same category products
            category_products = Product.objects.filter(
                category=product.category,
                is_available=True
            ).exclude(id=product_id).annotate(
                popularity=Count('orderitem')
            ).order_by('-popularity')[:limit * 2]
            
            for similar_product in category_products:
                similarity_score = self._calculate_product_similarity(product, similar_product)
                similar_products.append({
                    'product': similar_product,
                    'similarity_score': similarity_score,
                    'reason': f"Same category: {product.category.name}"
                })
            
            # 2. Same vendor products
            vendor_products = Product.objects.filter(
                vendor=product.vendor,
                is_available=True
            ).exclude(id=product_id).annotate(
                popularity=Count('orderitem')
            ).order_by('-popularity')[:limit]
            
            for vendor_product in vendor_products:
                # Check if not already included
                if not any(sp['product'].id == vendor_product.id for sp in similar_products):
                    similar_products.append({
                        'product': vendor_product,
                        'similarity_score': 0.7,  # High similarity for same vendor
                        'reason': f"Same vendor: {product.vendor.user.username}"
                    })
            
            # 3. Price-based similarity
            price_range_low = float(product.price_btc) * 0.7
            price_range_high = float(product.price_btc) * 1.3
            
            price_similar = Product.objects.filter(
                price_btc__range=[price_range_low, price_range_high],
                is_available=True
            ).exclude(id=product_id).annotate(
                popularity=Count('orderitem')
            ).order_by('-popularity')[:limit]
            
            for price_product in price_similar:
                if not any(sp['product'].id == price_product.id for sp in similar_products):
                    price_similarity = 1 - abs(float(product.price_btc) - float(price_product.price_btc)) / float(product.price_btc)
                    similar_products.append({
                        'product': price_product,
                        'similarity_score': price_similarity * 0.6,
                        'reason': "Similar price range"
                    })
            
            # Sort by similarity score and return top results
            similar_products.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            # Convert to response format
            result = []
            for item in similar_products[:limit]:
                product_data = self._product_to_dict(item['product'])
                product_data['similarity_reason'] = item['reason']
                product_data['similarity_score'] = round(item['similarity_score'], 2)
                result.append(product_data)
            
            # Cache for 4 hours
            self.set_cached(cache_key, result, timeout=14400)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get similar products for {product_id}: {e}")
            return []
    
    def _get_collaborative_recommendations(self, user, limit: int) -> List[Dict[str, Any]]:
        """Get recommendations based on similar users' purchases"""
        try:
            from orders.models import Order, OrderItem
            
            # Get user's purchase history
            user_purchases = set(
                OrderItem.objects.filter(
                    order__buyer=user,
                    order__status__in=['completed', 'shipped', 'delivered']
                ).values_list('product_id', flat=True)
            )
            
            if not user_purchases:
                return []
            
            # Find users with similar purchase patterns
            similar_users = defaultdict(int)
            
            for product_id in user_purchases:
                # Get other users who bought the same products
                other_buyers = OrderItem.objects.filter(
                    product_id=product_id,
                    order__status__in=['completed', 'shipped', 'delivered']
                ).exclude(
                    order__buyer=user
                ).values_list('order__buyer_id', flat=True).distinct()
                
                for buyer_id in other_buyers:
                    similar_users[buyer_id] += 1
            
            # Sort users by similarity (number of common purchases)
            similar_users = sorted(similar_users.items(), key=lambda x: x[1], reverse=True)[:20]
            
            # Get products bought by similar users that current user hasn't bought
            recommended_products = defaultdict(float)
            
            for similar_user_id, similarity_score in similar_users:
                similar_user_purchases = set(
                    OrderItem.objects.filter(
                        order__buyer_id=similar_user_id,
                        order__status__in=['completed', 'shipped', 'delivered']
                    ).values_list('product_id', flat=True)
                )
                
                # Products that similar user bought but current user hasn't
                new_products = similar_user_purchases - user_purchases
                
                for product_id in new_products:
                    # Weight by similarity and product popularity
                    weight = similarity_score / len(user_purchases)  # Normalize by user's purchase count
                    recommended_products[product_id] += weight
            
            # Sort by recommendation score
            sorted_recommendations = sorted(recommended_products.items(), key=lambda x: x[1], reverse=True)
            
            # Convert to product objects
            recommendations = []
            for product_id, score in sorted_recommendations[:limit]:
                try:
                    from products.models import Product
                    product = Product.objects.get(id=product_id, is_available=True)
                    recommendations.append({
                        'product_id': product_id,
                        'product': product,
                        'score': score,
                        'type': 'collaborative',
                        'reason': 'Users with similar purchases also bought this'
                    })
                except Product.DoesNotExist:
                    continue
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get collaborative recommendations: {e}")
            return []
    
    def _get_content_based_recommendations(self, user, limit: int) -> List[Dict[str, Any]]:
        """Get recommendations based on user's purchase history content"""
        try:
            from orders.models import OrderItem
            from products.models import Product
            
            # Analyze user's preferences from purchase history
            user_orders = OrderItem.objects.filter(
                order__buyer=user,
                order__status__in=['completed', 'shipped', 'delivered']
            ).select_related('product')
            
            if not user_orders.exists():
                return []
            
            # Analyze user preferences
            category_preferences = defaultdict(int)
            vendor_preferences = defaultdict(int)
            price_preferences = []
            
            for order_item in user_orders:
                product = order_item.product
                category_preferences[product.category_id] += order_item.quantity
                vendor_preferences[product.vendor_id] += order_item.quantity
                price_preferences.append(float(product.price_btc))
            
            # Calculate preferred price range
            if price_preferences:
                avg_price = sum(price_preferences) / len(price_preferences)
                price_range_low = avg_price * 0.5
                price_range_high = avg_price * 2.0
            else:
                price_range_low = 0
                price_range_high = float('inf')
            
            # Get preferred categories (top 3)
            top_categories = sorted(category_preferences.items(), key=lambda x: x[1], reverse=True)[:3]
            preferred_category_ids = [cat_id for cat_id, _ in top_categories]
            
            # Get preferred vendors (top 3)
            top_vendors = sorted(vendor_preferences.items(), key=lambda x: x[1], reverse=True)[:3]
            preferred_vendor_ids = [vendor_id for vendor_id, _ in top_vendors]
            
            # Find products matching user preferences
            candidate_products = Product.objects.filter(
                is_available=True,
                price_btc__range=[price_range_low, price_range_high]
            ).exclude(
                id__in=user_orders.values_list('product_id', flat=True)
            ).annotate(
                popularity=Count('orderitem')
            )
            
            # Score products based on preferences
            recommendations = []
            for product in candidate_products:
                score = 0.0
                reasons = []
                
                # Category preference
                if product.category_id in preferred_category_ids:
                    category_rank = preferred_category_ids.index(product.category_id)
                    category_score = (3 - category_rank) / 3  # Higher score for more preferred categories
                    score += category_score * 0.4
                    reasons.append(f"Matches your interest in {product.category.name}")
                
                # Vendor preference
                if product.vendor_id in preferred_vendor_ids:
                    vendor_rank = preferred_vendor_ids.index(product.vendor_id)
                    vendor_score = (3 - vendor_rank) / 3
                    score += vendor_score * 0.3
                    reasons.append(f"From vendor {product.vendor.user.username} you've bought from")
                
                # Price preference
                price_diff = abs(float(product.price_btc) - avg_price) / avg_price if avg_price > 0 else 0
                price_score = max(0, 1 - price_diff)
                score += price_score * 0.2
                
                # Popularity boost
                popularity_score = min(product.popularity / 10, 1.0)  # Normalize to 0-1
                score += popularity_score * 0.1
                
                if score > 0.1:  # Only include products with meaningful score
                    recommendations.append({
                        'product_id': product.id,
                        'product': product,
                        'score': score,
                        'type': 'content_based',
                        'reason': '; '.join(reasons) if reasons else 'Matches your preferences'
                    })
            
            # Sort by score and return top results
            recommendations.sort(key=lambda x: x['score'], reverse=True)
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get content-based recommendations: {e}")
            return []
    
    def _get_trending_recommendations(self, user, limit: int) -> List[Dict[str, Any]]:
        """Get trending/popular product recommendations"""
        try:
            from products.models import Product
            from orders.models import OrderItem
            
            # Get products that are trending (popular in last 7 days)
            week_ago = timezone.now() - timedelta(days=7)
            
            trending_products = Product.objects.filter(
                is_available=True
            ).annotate(
                recent_sales=Count(
                    'orderitem',
                    filter=Q(
                        orderitem__order__created_at__gte=week_ago,
                        orderitem__order__status__in=['completed', 'shipped', 'delivered']
                    )
                ),
                total_sales=Count('orderitem')
            ).filter(
                recent_sales__gt=0
            ).order_by('-recent_sales', '-total_sales')[:limit * 2]
            
            # Exclude products user already bought
            if user:
                user_purchases = set(
                    OrderItem.objects.filter(
                        order__buyer=user,
                        order__status__in=['completed', 'shipped', 'delivered']
                    ).values_list('product_id', flat=True)
                )
                trending_products = trending_products.exclude(id__in=user_purchases)
            
            recommendations = []
            for product in trending_products[:limit]:
                recommendations.append({
                    'product_id': product.id,
                    'product': product,
                    'score': product.recent_sales / max(product.total_sales, 1),
                    'type': 'trending',
                    'reason': f'Popular this week ({product.recent_sales} recent sales)'
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get trending recommendations: {e}")
            return []
    
    def _get_popular_recommendations(self, user, limit: int, exclude_ids: set = None) -> List[Dict[str, Any]]:
        """Get popular product recommendations as fallback"""
        try:
            from products.models import Product
            from orders.models import OrderItem
            
            exclude_ids = exclude_ids or set()
            
            # Get overall popular products
            popular_products = Product.objects.filter(
                is_available=True
            ).exclude(
                id__in=exclude_ids
            ).annotate(
                total_sales=Count('orderitem')
            ).filter(
                total_sales__gt=0
            ).order_by('-total_sales')[:limit]
            
            recommendations = []
            for product in popular_products:
                recommendations.append({
                    'product_id': product.id,
                    'product': product,
                    'score': product.total_sales / 100,  # Normalize
                    'type': 'popular',
                    'reason': f'Popular choice ({product.total_sales} total sales)'
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to get popular recommendations: {e}")
            return []
    
    def _calculate_product_similarity(self, product1, product2) -> float:
        """Calculate similarity score between two products"""
        try:
            similarity = 0.0
            
            # Category similarity
            if product1.category_id == product2.category_id:
                similarity += 0.4
            
            # Vendor similarity
            if product1.vendor_id == product2.vendor_id:
                similarity += 0.3
            
            # Price similarity
            price_diff = abs(float(product1.price_btc) - float(product2.price_btc))
            max_price = max(float(product1.price_btc), float(product2.price_btc))
            if max_price > 0:
                price_similarity = 1 - (price_diff / max_price)
                similarity += price_similarity * 0.3
            
            # Name/description similarity (simple keyword matching)
            product1_words = set(product1.name.lower().split() + product1.description.lower().split())
            product2_words = set(product2.name.lower().split() + product2.description.lower().split())
            
            if product1_words and product2_words:
                common_words = product1_words.intersection(product2_words)
                text_similarity = len(common_words) / max(len(product1_words), len(product2_words))
                similarity += text_similarity * 0.1
            
            return min(similarity, 1.0)
            
        except Exception as e:
            logger.error(f"Failed to calculate product similarity: {e}")
            return 0.0
    
    def _enhance_recommendation(self, recommendation: Dict[str, Any], user) -> Dict[str, Any]:
        """Add additional metadata to recommendation"""
        try:
            product = recommendation['product']
            
            enhanced = self._product_to_dict(product)
            enhanced.update({
                'recommendation_score': round(recommendation['score'], 3),
                'recommendation_type': recommendation['type'],
                'recommendation_reason': recommendation['reason'],
                'confidence': self._calculate_confidence(recommendation['score'], recommendation['type']),
                'why_recommended': self._generate_explanation(recommendation, user)
            })
            
            return enhanced
            
        except Exception as e:
            logger.error(f"Failed to enhance recommendation: {e}")
            return recommendation
    
    def _product_to_dict(self, product) -> Dict[str, Any]:
        """Convert product to dictionary representation"""
        return {
            'id': product.id,
            'name': product.name,
            'description': product.description[:200] + '...' if len(product.description) > 200 else product.description,
            'price_btc': float(product.price_btc),
            'price_xmr': float(product.price_xmr),
            'category': product.category.name,
            'vendor': product.vendor.user.username,
            'stock_quantity': product.stock_quantity,
            'image_url': product.image_url(),
            'thumbnail_url': product.thumbnail_url(),
        }
    
    def _calculate_confidence(self, score: float, rec_type: str) -> str:
        """Calculate confidence level for recommendation"""
        if rec_type == 'collaborative' and score > 0.5:
            return 'high'
        elif rec_type == 'content_based' and score > 0.7:
            return 'high'
        elif score > 0.3:
            return 'medium'
        else:
            return 'low'
    
    def _generate_explanation(self, recommendation: Dict[str, Any], user) -> str:
        """Generate human-readable explanation for recommendation"""
        rec_type = recommendation['type']
        
        explanations = {
            'collaborative': "Other users with similar purchase history also bought this item",
            'content_based': "This matches your previous purchases and preferences",
            'trending': "This item is currently popular among other users",
            'popular': "This is a well-reviewed and frequently purchased item"
        }
        
        return explanations.get(rec_type, "This item might interest you based on marketplace trends")