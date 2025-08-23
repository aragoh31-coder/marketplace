"""
Search Service
Handles intelligent search with personalization and semantic understanding.
Designed for Tor-safe server-side processing without JavaScript.
"""

import logging
from typing import Dict, List, Optional, Any
from django.db.models import Q, Count, Avg
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from core.base_service import BaseService

logger = logging.getLogger(__name__)
User = get_user_model()


class SearchService(BaseService):
    """Advanced search service with personalization for Tor safety"""
    
    service_name = "search_service"
    version = "1.0.0"
    description = "Intelligent search with personalization and semantic understanding"
    
    def __init__(self):
        super().__init__()
        self._search_cache = {}
        self._user_preferences = {}
    
    def initialize(self):
        """Initialize the search service"""
        try:
            logger.info("Search service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize search service: {e}")
            raise e
    
    def cleanup(self):
        """Clean up the search service"""
        try:
            self._search_cache.clear()
            self._user_preferences.clear()
            logger.info("Search service cleaned up successfully")
        except Exception as e:
            logger.error(f"Failed to cleanup search service: {e}")
    
    def search_products(self, query: str, user_id: str = None, filters: Dict = None) -> List[Any]:
        """
        Intelligent product search with personalization
        
        Args:
            query: Search query string
            user_id: Optional user ID for personalization
            filters: Optional filters (category, price_range, etc.)
        """
        try:
            from products.models import Product
            
            # Start with basic search
            products = Product.objects.filter(is_available=True)
            
            if query.strip():
                # Enhanced search with semantic understanding
                search_terms = self._extract_search_terms(query)
                search_q = self._build_search_query(search_terms)
                products = products.filter(search_q)
            
            # Apply filters
            if filters:
                products = self._apply_filters(products, filters)
            
            # Apply personalization if user provided
            if user_id:
                products = self._personalize_results(products, user_id)
            
            # Order results by relevance
            products = self._order_by_relevance(products, query, user_id)
            
            # Cache results for performance
            cache_key = f"search:{hash(query)}:{user_id}:{hash(str(filters))}"
            self.set_cached(cache_key, list(products[:50]), timeout=300)  # 5 minutes
            
            return products[:50]  # Limit to 50 results
            
        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return []
    
    def _extract_search_terms(self, query: str) -> Dict[str, List[str]]:
        """Extract and categorize search terms from query"""
        terms = {
            'keywords': [],
            'categories': [],
            'price_indicators': [],
            'quality_indicators': []
        }
        
        # Clean and split query
        words = query.lower().replace(',', ' ').split()
        
        # Category keywords
        category_keywords = {
            'electronics': ['phone', 'laptop', 'computer', 'tech', 'device'],
            'books': ['book', 'ebook', 'pdf', 'manual', 'guide'],
            'digital': ['software', 'app', 'code', 'script', 'digital'],
            'services': ['service', 'consulting', 'help', 'support']
        }
        
        # Price indicators
        price_keywords = ['cheap', 'expensive', 'premium', 'budget', 'affordable']
        
        # Quality indicators
        quality_keywords = ['high-quality', 'premium', 'professional', 'reliable', 'trusted']
        
        for word in words:
            # Check category keywords
            for category, keywords in category_keywords.items():
                if word in keywords:
                    terms['categories'].append(category)
            
            # Check price indicators
            if word in price_keywords:
                terms['price_indicators'].append(word)
            
            # Check quality indicators
            if word in quality_keywords:
                terms['quality_indicators'].append(word)
            
            # Add as general keyword
            if len(word) > 2:  # Ignore very short words
                terms['keywords'].append(word)
        
        return terms
    
    def _build_search_query(self, search_terms: Dict[str, List[str]]) -> Q:
        """Build Django Q object for database search"""
        query = Q()
        
        # Search in product fields
        for keyword in search_terms['keywords']:
            keyword_q = (
                Q(name__icontains=keyword) |
                Q(description__icontains=keyword) |
                Q(category__name__icontains=keyword) |
                Q(vendor__user__username__icontains=keyword)
            )
            query |= keyword_q
        
        # Category-specific search
        for category in search_terms['categories']:
            query |= Q(category__name__icontains=category)
        
        return query if query else Q(pk__isnull=False)  # Return all if no specific terms
    
    def _apply_filters(self, queryset, filters: Dict) -> Any:
        """Apply additional filters to the queryset"""
        if 'category_id' in filters and filters['category_id']:
            queryset = queryset.filter(category_id=filters['category_id'])
        
        if 'min_price' in filters and filters['min_price']:
            queryset = queryset.filter(price_btc__gte=filters['min_price'])
        
        if 'max_price' in filters and filters['max_price']:
            queryset = queryset.filter(price_btc__lte=filters['max_price'])
        
        if 'vendor_id' in filters and filters['vendor_id']:
            queryset = queryset.filter(vendor_id=filters['vendor_id'])
        
        if 'in_stock' in filters and filters['in_stock']:
            queryset = queryset.filter(stock_quantity__gt=0)
        
        return queryset
    
    def _personalize_results(self, queryset, user_id: str) -> Any:
        """Apply personalization based on user behavior"""
        try:
            user = User.objects.get(id=user_id)
            preferences = self._get_user_preferences(user)
            
            # Boost products from preferred categories
            if preferences.get('preferred_categories'):
                preferred_ids = []
                other_ids = []
                
                for product in queryset:
                    if product.category_id in preferences['preferred_categories']:
                        preferred_ids.append(product.id)
                    else:
                        other_ids.append(product.id)
                
                # Reorder to put preferred categories first
                from django.db.models import Case, When, IntegerField
                ordering = []
                for i, pid in enumerate(preferred_ids + other_ids):
                    ordering.append(When(pk=pid, then=i))
                
                if ordering:
                    queryset = queryset.annotate(
                        preference_order=Case(*ordering, output_field=IntegerField())
                    ).order_by('preference_order')
            
            # Boost products from trusted vendors
            if preferences.get('trusted_vendors'):
                trusted_q = Q(vendor_id__in=preferences['trusted_vendors'])
                # This would require a more complex ordering in a real implementation
                
        except Exception as e:
            logger.error(f"Personalization failed for user {user_id}: {e}")
        
        return queryset
    
    def _get_user_preferences(self, user) -> Dict[str, Any]:
        """Get or compute user preferences based on purchase history"""
        cache_key = f"user_preferences:{user.id}"
        preferences = self.get_cached(cache_key)
        
        if preferences:
            return preferences
        
        try:
            from orders.models import Order
            from vendors.models import Vendor
            
            # Analyze user's order history
            user_orders = Order.objects.filter(buyer=user, status="completed")
            
            # Get preferred categories
            category_counts = {}
            vendor_ratings = {}
            
            for order in user_orders:
                for item in order.items.all():
                    # Count category preferences
                    cat_id = item.product.category_id
                    category_counts[cat_id] = category_counts.get(cat_id, 0) + 1
                    
                    # Track vendor performance
                    vendor_id = item.product.vendor_id
                    if vendor_id not in vendor_ratings:
                        vendor_ratings[vendor_id] = {'orders': 0, 'disputes': 0}
                    vendor_ratings[vendor_id]['orders'] += 1
            
            # Get dispute counts for vendors
            from disputes.models import Dispute
            for vendor_id in vendor_ratings:
                dispute_count = Dispute.objects.filter(
                    order__items__product__vendor_id=vendor_id,
                    complainant=user
                ).count()
                vendor_ratings[vendor_id]['disputes'] = dispute_count
            
            # Determine preferred categories (top 3)
            preferred_categories = sorted(
                category_counts.keys(), 
                key=lambda x: category_counts[x], 
                reverse=True
            )[:3]
            
            # Determine trusted vendors (low dispute rate)
            trusted_vendors = [
                vendor_id for vendor_id, stats in vendor_ratings.items()
                if stats['orders'] >= 2 and stats['disputes'] == 0
            ]
            
            preferences = {
                'preferred_categories': preferred_categories,
                'trusted_vendors': trusted_vendors,
                'total_orders': user_orders.count()
            }
            
            # Cache for 1 hour
            self.set_cached(cache_key, preferences, timeout=3600)
            
            return preferences
            
        except Exception as e:
            logger.error(f"Failed to compute user preferences for {user.id}: {e}")
            return {}
    
    def _order_by_relevance(self, queryset, query: str, user_id: str = None) -> Any:
        """Order results by relevance score"""
        try:
            # If no specific query, order by popularity/rating
            if not query.strip():
                return queryset.order_by('-created_at')  # Newest first
            
            # For specific queries, we could implement TF-IDF or similar
            # For now, use simple relevance indicators
            return queryset.order_by(
                '-vendor__trust_level',  # Trusted vendors first
                '-created_at'  # Then by recency
            )
            
        except Exception as e:
            logger.error(f"Failed to order results by relevance: {e}")
            return queryset.order_by('-created_at')
    
    def get_search_suggestions(self, partial_query: str, limit: int = 10) -> List[str]:
        """Get search suggestions based on partial query (server-side)"""
        try:
            from products.models import Product
            
            if len(partial_query) < 2:
                return []
            
            # Get product names that match partial query
            products = Product.objects.filter(
                name__icontains=partial_query,
                is_available=True
            ).values_list('name', flat=True)[:limit]
            
            suggestions = list(set(products))  # Remove duplicates
            return sorted(suggestions)[:limit]
            
        except Exception as e:
            logger.error(f"Failed to get search suggestions: {e}")
            return []
    
    def log_search(self, user_id: str, query: str, results_count: int):
        """Log search for analytics and improvement"""
        try:
            search_data = {
                'user_id': user_id,
                'query': query,
                'results_count': results_count,
                'timestamp': timezone.now().isoformat()
            }
            
            logger.info(f"Search logged: {search_data}")
            
        except Exception as e:
            logger.error(f"Failed to log search: {e}")