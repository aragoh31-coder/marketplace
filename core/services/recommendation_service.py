"""
Product Recommendation Service
Provides intelligent product recommendations based on user behavior.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import math

from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Avg, Sum, F
from django.utils import timezone
from django.core.cache import cache

from .base_service import BaseService, performance_monitor

logger = logging.getLogger(__name__)

User = get_user_model()


class RecommendationService(BaseService):
    """Service for providing intelligent product recommendations."""
    
    service_name = "recommendation_service"
    description = "Intelligent product recommendations based on user behavior"
    
    def __init__(self):
        super().__init__()
        self.cache_timeout = 1800  # 30 minutes cache for recommendations
    
    @performance_monitor
    def get_recommendations_for_user(self, user: User, limit: int = 20) -> List[Dict[str, Any]]:
        """Get personalized product recommendations for a user."""
        try:
            # Check cache first
            cache_key = f"user_recommendations:{user.id}"
            cached_recommendations = self.get_cached(cache_key)
            if cached_recommendations:
                return cached_recommendations[:limit]
            
            # Get different types of recommendations
            collaborative_recs = self._get_collaborative_recommendations(user, limit//3)
            content_based_recs = self._get_content_based_recommendations(user, limit//3)
            trending_recs = self._get_trending_recommendations(user, limit//3)
            
            # Combine and rank recommendations
            all_recommendations = collaborative_recs + content_based_recs + trending_recs
            
            # Remove duplicates and rank by confidence
            unique_recommendations = self._deduplicate_recommendations(all_recommendations)
            ranked_recommendations = self._rank_recommendations(unique_recommendations)
            
            # Cache the results
            self.set_cached(cache_key, ranked_recommendations, self.cache_timeout)
            
            return ranked_recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error getting recommendations for user {user.username}: {str(e)}")
            return []
    
    def _get_collaborative_recommendations(self, user: User, limit: int) -> List[Dict[str, Any]]:
        """Get recommendations based on similar users' behavior."""
        try:
            from orders.models import Order
            from products.models import Product
            
            # Get user's purchase history
            user_orders = Order.objects.filter(buyer=user, status='completed')
            user_products = set()
            for order in user_orders:
                user_products.update(order.products.all())
            
            if not user_products:
                return []
            
            # Find similar users (users who bought similar products)
            similar_users = self._find_similar_users(user, user_products)
            
            if not similar_users:
                return []
            
            # Get products that similar users bought but current user didn't
            recommendations = []
            for similar_user in similar_users:
                similar_user_orders = Order.objects.filter(
                    buyer=similar_user,
                    status='completed'
                )
                
                for order in similar_user_orders:
                    for product in order.products.all():
                        if product not in user_products and product.active:
                            # Calculate similarity score
                            similarity_score = self._calculate_user_similarity(user, similar_user)
                            
                            recommendations.append({
                                'product': product,
                                'type': 'collaborative',
                                'confidence': similarity_score * 0.8,  # Collaborative recommendations get 80% of similarity score
                                'explanation': f"Users similar to you also bought this product",
                                'source': 'collaborative_filtering'
                            })
            
            # Sort by confidence and return top results
            recommendations.sort(key=lambda x: x['confidence'], reverse=True)
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error getting collaborative recommendations for user {user.username}: {str(e)}")
            return []
    
    def _get_content_based_recommendations(self, user: User, limit: int) -> List[Dict[str, Any]]:
        """Get recommendations based on user's purchase history and preferences."""
        try:
            from orders.models import Order
            from products.models import Product, Category
            
            # Get user's purchase history
            user_orders = Order.objects.filter(buyer=user, status='completed')
            
            if not user_orders.exists():
                return []
            
            # Analyze user preferences
            category_preferences = {}
            price_range = {'min': float('inf'), 'max': 0}
            
            for order in user_orders:
                for product in order.products.all():
                    # Category preference
                    category = product.category
                    if category:
                        category_preferences[category.name] = category_preferences.get(category.name, 0) + 1
                    
                    # Price preference
                    price = float(product.price_btc or 0)
                    if price > 0:
                        price_range['min'] = min(price_range['min'], price)
                        price_range['max'] = max(price_range['max'], price)
            
            # Get recommendations based on preferences
            recommendations = []
            
            # Category-based recommendations
            if category_preferences:
                top_categories = sorted(category_preferences.items(), key=lambda x: x[1], reverse=True)[:3]
                
                for category_name, preference_score in top_categories:
                    try:
                        category = Category.objects.get(name=category_name)
                        category_products = Product.objects.filter(
                            category=category,
                            active=True
                        ).exclude(
                            id__in=[p.id for p in user_orders.values_list('products', flat=True)]
                        )[:5]
                        
                        for product in category_products:
                            # Calculate confidence based on category preference
                            confidence = min(0.9, preference_score / max(category_preferences.values()) * 0.8)
                            
                            recommendations.append({
                                'product': product,
                                'type': 'content_based',
                                'confidence': confidence,
                                'explanation': f"Based on your interest in {category_name}",
                                'source': 'category_preference'
                            })
                    except Category.DoesNotExist:
                        continue
            
            # Price-based recommendations
            if price_range['min'] != float('inf') and price_range['max'] > 0:
                avg_price = (price_range['min'] + price_range['max']) / 2
                price_tolerance = avg_price * 0.3  # 30% tolerance
                
                price_based_products = Product.objects.filter(
                    active=True,
                    price_btc__range=[avg_price - price_tolerance, avg_price + price_tolerance]
                ).exclude(
                    id__in=[p.id for p in user_orders.values_list('products', flat=True)]
                )[:5]
                
                for product in price_based_products:
                    price_diff = abs(float(product.price_btc or 0) - avg_price)
                    confidence = max(0.3, 0.8 - (price_diff / avg_price) * 0.5)
                    
                    recommendations.append({
                        'product': product,
                        'type': 'content_based',
                        'confidence': confidence,
                        'explanation': f"Similar to products in your price range",
                        'source': 'price_preference'
                    })
            
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error getting content-based recommendations for user {user.username}: {str(e)}")
            return []
    
    def _get_trending_recommendations(self, user: User, limit: int) -> List[Dict[str, Any]]:
        """Get recommendations based on trending products."""
        try:
            from products.models import Product
            from orders.models import Order
            
            # Get trending products (most ordered in last 30 days)
            thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
            
            trending_products = Product.objects.filter(
                active=True,
                orders__created_at__gte=thirty_days_ago
            ).annotate(
                recent_orders=Count('orders', filter=Q(orders__created_at__gte=thirty_days_ago))
            ).order_by('-recent_orders')[:limit*2]
            
            # Filter out products user already has
            user_products = set(Order.objects.filter(
                buyer=user,
                status='completed'
            ).values_list('products', flat=True))
            
            trending_recommendations = []
            for product in trending_products:
                if product.id not in user_products:
                    # Calculate trending confidence based on recent orders
                    confidence = min(0.9, product.recent_orders / max(p.recent_orders for p in trending_products) * 0.7)
                    
                    trending_recommendations.append({
                        'product': product,
                        'type': 'trending',
                        'confidence': confidence,
                        'explanation': f"Trending product with {product.recent_orders} recent orders",
                        'source': 'trending_analysis'
                    })
            
            return trending_recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error getting trending recommendations for user {user.username}: {str(e)}")
            return []
    
    def _find_similar_users(self, user: User, user_products: set) -> List[User]:
        """Find users with similar purchase patterns."""
        try:
            from orders.models import Order
            
            # Get users who bought similar products
            similar_users = []
            user_product_ids = [p.id for p in user_products]
            
            # Find users who bought at least 2 of the same products
            other_orders = Order.objects.filter(
                products__id__in=user_product_ids,
                buyer__isnull=False
            ).exclude(buyer=user)
            
            user_product_counts = {}
            for order in other_orders:
                buyer = order.buyer
                if buyer:
                    if buyer.id not in user_product_counts:
                        user_product_counts[buyer.id] = 0
                    user_product_counts[buyer.id] += 1
            
            # Get users with at least 2 similar products
            similar_user_ids = [uid for uid, count in user_product_counts.items() if count >= 2]
            similar_users = User.objects.filter(id__in=similar_user_ids)[:10]  # Limit to top 10
            
            return list(similar_users)
            
        except Exception as e:
            logger.error(f"Error finding similar users for {user.username}: {str(e)}")
            return []
    
    def _calculate_user_similarity(self, user1: User, user2: User) -> float:
        """Calculate similarity between two users based on purchase patterns."""
        try:
            from orders.models import Order
            
            # Get products for both users
            user1_products = set(Order.objects.filter(
                buyer=user1,
                status='completed'
            ).values_list('products', flat=True))
            
            user2_products = set(Order.objects.filter(
                buyer=user2,
                status='completed'
            ).values_list('products', flat=True))
            
            if not user1_products or not user2_products:
                return 0.0
            
            # Calculate Jaccard similarity
            intersection = len(user1_products.intersection(user2_products))
            union = len(user1_products.union(user2_products))
            
            similarity = intersection / union if union > 0 else 0.0
            
            return min(1.0, similarity)
            
        except Exception as e:
            logger.error(f"Error calculating user similarity: {str(e)}")
            return 0.0
    
    def _deduplicate_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate products from recommendations."""
        seen_products = set()
        unique_recommendations = []
        
        for rec in recommendations:
            product_id = rec['product'].id
            if product_id not in seen_products:
                seen_products.add(product_id)
                unique_recommendations.append(rec)
        
        return unique_recommendations
    
    def _rank_recommendations(self, recommendations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank recommendations by confidence and other factors."""
        try:
            # Sort by confidence first
            recommendations.sort(key=lambda x: x['confidence'], reverse=True)
            
            # Apply additional ranking factors
            for rec in recommendations:
                # Boost confidence for products with good ratings
                if hasattr(rec['product'], 'average_rating'):
                    rating_boost = min(0.2, (rec['product'].average_rating - 3) * 0.1)
                    rec['confidence'] = min(1.0, rec['confidence'] + rating_boost)
                
                # Boost confidence for products with good stock
                if hasattr(rec['product'], 'stock_quantity'):
                    stock_boost = min(0.1, rec['product'].stock_quantity / 100 * 0.1)
                    rec['confidence'] = min(1.0, rec['confidence'] + stock_boost)
            
            # Re-sort by final confidence
            recommendations.sort(key=lambda x: x['confidence'], reverse=True)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error ranking recommendations: {str(e)}")
            return recommendations
    
    @performance_monitor
    def get_similar_products(self, product, limit: int = 10) -> List[Dict[str, Any]]:
        """Get products similar to a given product."""
        try:
            from products.models import Product
            
            # Get products in the same category
            category_products = Product.objects.filter(
                category=product.category,
                active=True
            ).exclude(id=product.id)[:limit*2]
            
            similar_products = []
            for similar_product in category_products:
                # Calculate similarity score
                similarity_score = self._calculate_product_similarity(product, similar_product)
                
                if similarity_score > 0.3:  # Only include products with reasonable similarity
                    similar_products.append({
                        'product': similar_product,
                        'similarity_score': similarity_score,
                        'explanation': f"Similar category and characteristics to {product.name}"
                    })
            
            # Sort by similarity and return top results
            similar_products.sort(key=lambda x: x['similarity_score'], reverse=True)
            return similar_products[:limit]
            
        except Exception as e:
            logger.error(f"Error getting similar products for {product.name}: {str(e)}")
            return []
    
    def _calculate_product_similarity(self, product1, product2) -> float:
        """Calculate similarity between two products."""
        try:
            similarity_score = 0.0
            
            # Category similarity (40% weight)
            if product1.category == product2.category:
                similarity_score += 0.4
            
            # Price similarity (30% weight)
            price1 = float(product1.price_btc or 0)
            price2 = float(product2.price_btc or 0)
            
            if price1 > 0 and price2 > 0:
                price_diff = abs(price1 - price2) / max(price1, price2)
                price_similarity = max(0, 1 - price_diff)
                similarity_score += price_similarity * 0.3
            
            # Description similarity (20% weight)
            if product1.description and product2.description:
                # Simple keyword matching (in a real system, use more sophisticated NLP)
                desc1_words = set(product1.description.lower().split())
                desc2_words = set(product2.description.lower().split())
                
                if desc1_words and desc2_words:
                    word_similarity = len(desc1_words.intersection(desc2_words)) / len(desc1_words.union(desc2_words))
                    similarity_score += word_similarity * 0.2
            
            # Stock availability similarity (10% weight)
            if hasattr(product1, 'stock_quantity') and hasattr(product2, 'stock_quantity'):
                stock1 = product1.stock_quantity or 0
                stock2 = product2.stock_quantity or 0
                
                if stock1 > 0 and stock2 > 0:
                    stock_similarity = min(stock1, stock2) / max(stock1, stock2)
                    similarity_score += stock_similarity * 0.1
            
            return min(1.0, similarity_score)
            
        except Exception as e:
            logger.error(f"Error calculating product similarity: {str(e)}")
            return 0.0
    
    @performance_monitor
    def get_search_suggestions(self, query: str, limit: int = 5) -> List[str]:
        """Get search suggestions based on user query."""
        try:
            from products.models import Product
            
            # Simple search suggestions (in a real system, use more sophisticated search)
            suggestions = []
            
            # Get products that match the query
            matching_products = Product.objects.filter(
                Q(name__icontains=query) | Q(description__icontains=query),
                active=True
            )[:limit*2]
            
            # Extract suggestions from product names
            for product in matching_products:
                name_words = product.name.lower().split()
                for word in name_words:
                    if word.startswith(query.lower()) and len(word) > len(query):
                        suggestions.append(word.capitalize())
            
            # Get category suggestions
            from products.models import Category
            category_suggestions = Category.objects.filter(
                name__icontains=query
            ).values_list('name', flat=True)[:limit//2]
            
            suggestions.extend(category_suggestions)
            
            # Remove duplicates and return top suggestions
            unique_suggestions = list(dict.fromkeys(suggestions))
            return unique_suggestions[:limit]
            
        except Exception as e:
            logger.error(f"Error getting search suggestions for '{query}': {str(e)}")
            return []
    
    @performance_monitor
    def log_search(self, user: Optional[User], query: str, results_count: int, filters: Dict = None):
        """Log search activity for analytics and personalization."""
        try:
            # In a real system, this would log to a database
            # For now, we'll just log to the logger
            logger.info(f"Search logged - User: {user.username if user else 'Anonymous'}, "
                       f"Query: '{query}', Results: {results_count}, Filters: {filters}")
            
        except Exception as e:
            logger.error(f"Error logging search: {str(e)}")
    
    def get_recommendation_explanation(self, recommendation: Dict[str, Any]) -> str:
        """Get human-readable explanation for a recommendation."""
        try:
            base_explanation = recommendation.get('explanation', 'Recommended for you')
            
            # Add confidence level description
            confidence = recommendation.get('confidence', 0)
            if confidence >= 0.8:
                confidence_desc = "Highly recommended"
            elif confidence >= 0.6:
                confidence_desc = "Recommended"
            elif confidence >= 0.4:
                confidence_desc = "May interest you"
            else:
                confidence_desc = "Worth considering"
            
            return f"{confidence_desc}: {base_explanation}"
            
        except Exception as e:
            logger.error(f"Error getting recommendation explanation: {str(e)}")
            return "Recommended for you"