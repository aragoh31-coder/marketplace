"""
Advanced Filtering Service
Provides sophisticated server-side filtering capabilities for marketplace data.
Designed for Tor-safe server-side processing without JavaScript dependencies.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Avg, Sum, Min, Max, F
from django.utils import timezone

from .base_service import BaseService

logger = logging.getLogger(__name__)
User = get_user_model()


class AdvancedFilteringService(BaseService):
    """Advanced filtering service for marketplace data"""
    
    service_name = "advanced_filtering_service"
    version = "1.0.0"
    description = "Sophisticated server-side filtering with smart suggestions"
    
    def __init__(self):
        super().__init__()
        self._filter_cache = {}
        self._suggestion_cache = {}
    
    def initialize(self):
        """Initialize the advanced filtering service"""
        try:
            logger.info("Advanced filtering service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize advanced filtering service: {e}")
            raise e
    
    def cleanup(self):
        """Clean up the advanced filtering service"""
        try:
            self._filter_cache.clear()
            self._suggestion_cache.clear()
            logger.info("Advanced filtering service cleaned up successfully")
        except Exception as e:
            logger.error(f"Failed to cleanup advanced filtering service: {e}")
    
    def apply_smart_filters(self, model_name: str, base_queryset, filters: Dict[str, Any], 
                           user_id: str = None) -> Tuple[Any, Dict[str, Any]]:
        """Apply intelligent filtering with optimization and suggestions"""
        try:
            # Apply basic filters first
            filtered_queryset = self._apply_basic_filters(base_queryset, filters, model_name)
            
            # Apply advanced filters
            filtered_queryset = self._apply_advanced_filters(filtered_queryset, filters, model_name)
            
            # Apply user-specific intelligent filters
            if user_id:
                filtered_queryset = self._apply_user_intelligent_filters(
                    filtered_queryset, filters, model_name, user_id
                )
            
            # Generate filter statistics and suggestions
            filter_stats = self._generate_filter_statistics(base_queryset, filtered_queryset, filters)
            filter_suggestions = self._generate_filter_suggestions(base_queryset, filters, model_name)
            
            # Apply result optimization
            optimized_queryset = self._optimize_queryset(filtered_queryset, model_name)
            
            filter_metadata = {
                'total_results': optimized_queryset.count() if hasattr(optimized_queryset, 'count') else len(optimized_queryset),
                'filter_statistics': filter_stats,
                'filter_suggestions': filter_suggestions,
                'applied_filters': self._get_applied_filters_summary(filters),
                'performance_metrics': self._get_filter_performance_metrics(filters)
            }
            
            return optimized_queryset, filter_metadata
            
        except Exception as e:
            logger.error(f"Failed to apply smart filters: {e}")
            return base_queryset, {'error': str(e)}
    
    def get_filter_suggestions(self, model_name: str, current_filters: Dict[str, Any], 
                              user_id: str = None) -> Dict[str, Any]:
        """Get intelligent filter suggestions based on current state"""
        try:
            cache_key = f"filter_suggestions:{model_name}:{hash(str(current_filters))}:{user_id}"
            cached_suggestions = self.get_cached(cache_key)
            if cached_suggestions:
                return cached_suggestions
            
            suggestions = {
                'recommended_filters': self._get_recommended_filters(model_name, current_filters, user_id),
                'popular_filters': self._get_popular_filters(model_name, user_id),
                'smart_combinations': self._get_smart_filter_combinations(model_name, current_filters),
                'value_suggestions': self._get_filter_value_suggestions(model_name, current_filters),
                'quick_filters': self._get_quick_filters(model_name, user_id)
            }
            
            # Cache for 30 minutes
            self.set_cached(cache_key, suggestions, timeout=1800)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Failed to get filter suggestions: {e}")
            return {}
    
    def analyze_filter_performance(self, model_name: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the performance and effectiveness of current filters"""
        try:
            from products.models import Product
            
            if model_name == 'product':
                base_queryset = Product.objects.filter(is_available=True)
            else:
                return {'error': 'Unsupported model for analysis'}
            
            # Apply filters and measure performance
            start_time = timezone.now()
            filtered_queryset = self._apply_all_filters(base_queryset, filters, model_name)
            filter_time = (timezone.now() - start_time).total_seconds()
            
            # Analyze filter effectiveness
            total_count = base_queryset.count()
            filtered_count = filtered_queryset.count()
            reduction_percentage = ((total_count - filtered_count) / total_count * 100) if total_count > 0 else 0
            
            # Analyze filter specificity
            specificity_score = self._calculate_filter_specificity(filters)
            
            # Generate optimization suggestions
            optimization_suggestions = self._get_filter_optimization_suggestions(
                filters, reduction_percentage, filter_time
            )
            
            analysis = {
                'performance_metrics': {
                    'filter_execution_time': round(filter_time, 3),
                    'total_results_before': total_count,
                    'total_results_after': filtered_count,
                    'reduction_percentage': round(reduction_percentage, 2),
                    'efficiency_score': self._calculate_efficiency_score(filter_time, reduction_percentage)
                },
                'filter_effectiveness': {
                    'specificity_score': specificity_score,
                    'selectivity': 'high' if reduction_percentage > 80 else 'medium' if reduction_percentage > 50 else 'low',
                    'filter_count': len([f for f in filters.values() if f not in [None, '', []]]),
                    'complexity_level': self._assess_filter_complexity(filters)
                },
                'optimization_suggestions': optimization_suggestions,
                'alternative_filters': self._suggest_alternative_filters(filters, model_name)
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze filter performance: {e}")
            return {'error': str(e)}
    
    def _apply_basic_filters(self, queryset, filters: Dict[str, Any], model_name: str):
        """Apply basic filtering logic"""
        try:
            if model_name == 'product':
                return self._apply_product_basic_filters(queryset, filters)
            elif model_name == 'order':
                return self._apply_order_basic_filters(queryset, filters)
            else:
                return queryset
        except Exception as e:
            logger.error(f"Failed to apply basic filters: {e}")
            return queryset
    
    def _apply_product_basic_filters(self, queryset, filters: Dict[str, Any]):
        """Apply basic product filters"""
        # Price range filters
        if filters.get('min_price'):
            try:
                min_price = float(filters['min_price'])
                queryset = queryset.filter(price_btc__gte=min_price)
            except (ValueError, TypeError):
                pass
        
        if filters.get('max_price'):
            try:
                max_price = float(filters['max_price'])
                queryset = queryset.filter(price_btc__lte=max_price)
            except (ValueError, TypeError):
                pass
        
        # Category filter
        if filters.get('category_id'):
            queryset = queryset.filter(category_id=filters['category_id'])
        
        if filters.get('categories'):
            category_list = filters['categories'] if isinstance(filters['categories'], list) else [filters['categories']]
            queryset = queryset.filter(category_id__in=category_list)
        
        # Vendor filter
        if filters.get('vendor_id'):
            queryset = queryset.filter(vendor_id=filters['vendor_id'])
        
        if filters.get('vendors'):
            vendor_list = filters['vendors'] if isinstance(filters['vendors'], list) else [filters['vendors']]
            queryset = queryset.filter(vendor_id__in=vendor_list)
        
        # Stock availability
        if filters.get('in_stock'):
            queryset = queryset.filter(stock_quantity__gt=0)
        
        if filters.get('out_of_stock'):
            queryset = queryset.filter(stock_quantity=0)
        
        # Text search
        if filters.get('search'):
            search_terms = filters['search'].split()
            search_q = Q()
            for term in search_terms:
                search_q |= (
                    Q(name__icontains=term) |
                    Q(description__icontains=term) |
                    Q(category__name__icontains=term)
                )
            queryset = queryset.filter(search_q)
        
        return queryset
    
    def _apply_advanced_filters(self, queryset, filters: Dict[str, Any], model_name: str):
        """Apply advanced filtering logic"""
        try:
            if model_name == 'product':
                return self._apply_product_advanced_filters(queryset, filters)
            else:
                return queryset
        except Exception as e:
            logger.error(f"Failed to apply advanced filters: {e}")
            return queryset
    
    def _apply_product_advanced_filters(self, queryset, filters: Dict[str, Any]):
        """Apply advanced product filters"""
        # Price percentile filters
        if filters.get('price_percentile'):
            try:
                percentile = int(filters['price_percentile'])
                if 0 <= percentile <= 100:
                    # Calculate price at given percentile
                    all_prices = queryset.values_list('price_btc', flat=True).order_by('price_btc')
                    if all_prices:
                        index = int((percentile / 100) * len(all_prices))
                        threshold_price = all_prices[min(index, len(all_prices) - 1)]
                        queryset = queryset.filter(price_btc__lte=threshold_price)
            except (ValueError, TypeError, IndexError):
                pass
        
        # Popularity filters
        if filters.get('min_popularity'):
            try:
                min_sales = int(filters['min_popularity'])
                queryset = queryset.annotate(
                    sales_count=Count('orderitem')
                ).filter(sales_count__gte=min_sales)
            except (ValueError, TypeError):
                pass
        
        # Rating filters (if you have ratings)
        if filters.get('min_rating'):
            try:
                min_rating = float(filters['min_rating'])
                # Assuming you have a rating field or related model
                # queryset = queryset.filter(average_rating__gte=min_rating)
            except (ValueError, TypeError):
                pass
        
        # Date range filters
        if filters.get('created_after'):
            try:
                if isinstance(filters['created_after'], str):
                    created_after = datetime.fromisoformat(filters['created_after'].replace('Z', '+00:00'))
                else:
                    created_after = filters['created_after']
                queryset = queryset.filter(created_at__gte=created_after)
            except (ValueError, TypeError):
                pass
        
        if filters.get('created_before'):
            try:
                if isinstance(filters['created_before'], str):
                    created_before = datetime.fromisoformat(filters['created_before'].replace('Z', '+00:00'))
                else:
                    created_before = filters['created_before']
                queryset = queryset.filter(created_at__lte=created_before)
            except (ValueError, TypeError):
                pass
        
        # Advanced text search with scoring
        if filters.get('advanced_search'):
            search_query = filters['advanced_search']
            # Implement weighted search scoring
            queryset = queryset.extra(
                select={
                    'search_rank': """
                        CASE 
                            WHEN LOWER(name) LIKE LOWER(%s) THEN 100
                            WHEN LOWER(name) LIKE LOWER(%s) THEN 80
                            WHEN LOWER(description) LIKE LOWER(%s) THEN 60
                            ELSE 0
                        END
                    """
                },
                select_params=[
                    f"{search_query}",  # Exact match
                    f"%{search_query}%",  # Contains
                    f"%{search_query}%"   # Description contains
                ]
            ).filter(
                Q(name__icontains=search_query) | Q(description__icontains=search_query)
            ).order_by('-search_rank', '-created_at')
        
        # Stock level filters
        if filters.get('stock_level'):
            stock_level = filters['stock_level']
            if stock_level == 'high':
                queryset = queryset.filter(stock_quantity__gte=50)
            elif stock_level == 'medium':
                queryset = queryset.filter(stock_quantity__range=[10, 49])
            elif stock_level == 'low':
                queryset = queryset.filter(stock_quantity__range=[1, 9])
            elif stock_level == 'out':
                queryset = queryset.filter(stock_quantity=0)
        
        # Vendor performance filters
        if filters.get('vendor_rating'):
            rating = filters['vendor_rating']
            if rating == 'top':
                # Top-rated vendors (low dispute rate)
                queryset = queryset.annotate(
                    vendor_disputes=Count('vendor__user__respondent_disputes')
                ).filter(vendor_disputes__lte=2)
            elif rating == 'established':
                # Established vendors (high product count)
                queryset = queryset.annotate(
                    vendor_products=Count('vendor__products')
                ).filter(vendor_products__gte=10)
        
        return queryset
    
    def _apply_user_intelligent_filters(self, queryset, filters: Dict[str, Any], 
                                       model_name: str, user_id: str):
        """Apply user-specific intelligent filters"""
        try:
            if model_name != 'product':
                return queryset
            
            user = User.objects.get(id=user_id)
            
            # Get user's purchase history for intelligent filtering
            from orders.models import OrderItem
            user_purchases = OrderItem.objects.filter(
                order__buyer=user,
                order__status__in=['completed', 'shipped', 'delivered']
            ).select_related('product')
            
            # Apply preference-based filtering if requested
            if filters.get('apply_preferences') and user_purchases.exists():
                # Analyze user's price preferences
                user_prices = [float(item.price) for item in user_purchases]
                if user_prices:
                    avg_price = sum(user_prices) / len(user_prices)
                    price_tolerance = avg_price * 0.5  # 50% tolerance
                    
                    if not filters.get('min_price') and not filters.get('max_price'):
                        queryset = queryset.filter(
                            price_btc__range=[
                                max(0, avg_price - price_tolerance),
                                avg_price + price_tolerance
                            ]
                        )
                
                # Prefer categories user has bought from
                user_categories = set(item.product.category_id for item in user_purchases)
                if user_categories and not filters.get('category_id'):
                    # Boost products from preferred categories in ordering
                    queryset = queryset.extra(
                        select={
                            'category_preference': f"""
                                CASE WHEN category_id IN ({','.join(map(str, user_categories))}) 
                                THEN 1 ELSE 0 END
                            """
                        }
                    ).order_by('-category_preference', '-created_at')
            
            # Hide products user already bought (if requested)
            if filters.get('hide_purchased'):
                purchased_product_ids = user_purchases.values_list('product_id', flat=True)
                queryset = queryset.exclude(id__in=purchased_product_ids)
            
            return queryset
            
        except Exception as e:
            logger.error(f"Failed to apply user intelligent filters: {e}")
            return queryset
    
    def _generate_filter_statistics(self, original_queryset, filtered_queryset, 
                                   filters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate statistics about the filtering operation"""
        try:
            original_count = original_queryset.count() if hasattr(original_queryset, 'count') else len(original_queryset)
            filtered_count = filtered_queryset.count() if hasattr(filtered_queryset, 'count') else len(filtered_queryset)
            
            stats = {
                'original_count': original_count,
                'filtered_count': filtered_count,
                'reduction_count': original_count - filtered_count,
                'reduction_percentage': round(
                    ((original_count - filtered_count) / original_count * 100) if original_count > 0 else 0, 2
                ),
                'active_filters': len([f for f in filters.values() if f not in [None, '', []]]),
                'filter_effectiveness': 'high' if filtered_count < original_count * 0.3 else 'medium' if filtered_count < original_count * 0.7 else 'low'
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to generate filter statistics: {e}")
            return {}
    
    def _generate_filter_suggestions(self, base_queryset, current_filters: Dict[str, Any], 
                                   model_name: str) -> List[Dict[str, Any]]:
        """Generate intelligent filter suggestions"""
        suggestions = []
        
        try:
            if model_name == 'product':
                # Suggest price range optimization
                if not current_filters.get('min_price') and not current_filters.get('max_price'):
                    price_stats = base_queryset.aggregate(
                        avg_price=Avg('price_btc'),
                        min_price=Min('price_btc'),
                        max_price=Max('price_btc')
                    )
                    
                    if price_stats['avg_price']:
                        suggestions.append({
                            'type': 'price_range',
                            'title': 'Set Price Range',
                            'description': f'Filter by price range (${float(price_stats["min_price"]):.2f} - ${float(price_stats["max_price"]):.2f})',
                            'filter_key': 'price_range',
                            'suggested_values': {
                                'budget': {'max_price': float(price_stats['avg_price']) * 0.7},
                                'mid_range': {
                                    'min_price': float(price_stats['avg_price']) * 0.7,
                                    'max_price': float(price_stats['avg_price']) * 1.3
                                },
                                'premium': {'min_price': float(price_stats['avg_price']) * 1.3}
                            }
                        })
                
                # Suggest category filtering if not applied
                if not current_filters.get('category_id'):
                    popular_categories = base_queryset.values(
                        'category__name', 'category__id'
                    ).annotate(
                        product_count=Count('id')
                    ).order_by('-product_count')[:5]
                    
                    if popular_categories:
                        suggestions.append({
                            'type': 'category',
                            'title': 'Filter by Category',
                            'description': 'Browse products in specific categories',
                            'filter_key': 'category_id',
                            'suggested_values': [
                                {
                                    'id': cat['category__id'],
                                    'name': cat['category__name'],
                                    'count': cat['product_count']
                                }
                                for cat in popular_categories
                            ]
                        })
                
                # Suggest stock availability filter
                if not current_filters.get('in_stock'):
                    in_stock_count = base_queryset.filter(stock_quantity__gt=0).count()
                    total_count = base_queryset.count()
                    
                    if in_stock_count < total_count:
                        suggestions.append({
                            'type': 'availability',
                            'title': 'Show Only Available Items',
                            'description': f'Hide out-of-stock items ({total_count - in_stock_count} items will be hidden)',
                            'filter_key': 'in_stock',
                            'suggested_values': True
                        })
            
        except Exception as e:
            logger.error(f"Failed to generate filter suggestions: {e}")
        
        return suggestions
    
    def _get_recommended_filters(self, model_name: str, current_filters: Dict[str, Any], 
                               user_id: str = None) -> List[Dict[str, Any]]:
        """Get personalized filter recommendations"""
        recommendations = []
        
        try:
            if model_name == 'product' and user_id:
                # Analyze user's behavior for recommendations
                from orders.models import OrderItem
                
                user_orders = OrderItem.objects.filter(
                    order__buyer_id=user_id,
                    order__status__in=['completed', 'shipped', 'delivered']
                ).select_related('product')
                
                if user_orders.exists():
                    # Recommend based on purchase history
                    user_categories = user_orders.values(
                        'product__category__name', 'product__category__id'
                    ).annotate(
                        purchase_count=Count('id')
                    ).order_by('-purchase_count')[:3]
                    
                    for cat in user_categories:
                        recommendations.append({
                            'type': 'personal_category',
                            'title': f'Browse {cat["product__category__name"]}',
                            'description': f'You\'ve purchased {cat["purchase_count"]} items from this category',
                            'filter_key': 'category_id',
                            'filter_value': cat['product__category__id'],
                            'confidence': 'high'
                        })
            
            # Add general recommendations
            recommendations.extend([
                {
                    'type': 'quick_filter',
                    'title': 'New Arrivals',
                    'description': 'Products added in the last 30 days',
                    'filter_key': 'created_after',
                    'filter_value': (timezone.now() - timedelta(days=30)).isoformat(),
                    'confidence': 'medium'
                },
                {
                    'type': 'quick_filter',
                    'title': 'Popular Items',
                    'description': 'Most frequently purchased products',
                    'filter_key': 'min_popularity',
                    'filter_value': 5,
                    'confidence': 'medium'
                }
            ])
            
        except Exception as e:
            logger.error(f"Failed to get recommended filters: {e}")
        
        return recommendations
    
    def _optimize_queryset(self, queryset, model_name: str):
        """Optimize queryset for better performance"""
        try:
            if model_name == 'product':
                # Add select_related and prefetch_related for common relationships
                queryset = queryset.select_related('category', 'vendor__user')
                
                # Add annotations for commonly needed data
                queryset = queryset.annotate(
                    sales_count=Count('orderitem')
                )
            
            return queryset
            
        except Exception as e:
            logger.error(f"Failed to optimize queryset: {e}")
            return queryset
    
    # Helper methods for analysis and suggestions
    def _calculate_filter_specificity(self, filters: Dict[str, Any]) -> float:
        """Calculate how specific the current filters are"""
        specificity_score = 0.0
        
        # Each filter type contributes to specificity
        if filters.get('min_price') or filters.get('max_price'):
            specificity_score += 0.2
        
        if filters.get('category_id') or filters.get('categories'):
            specificity_score += 0.3
        
        if filters.get('vendor_id') or filters.get('vendors'):
            specificity_score += 0.2
        
        if filters.get('search') or filters.get('advanced_search'):
            specificity_score += 0.3
        
        # Additional filters add to specificity
        additional_filters = [
            'in_stock', 'stock_level', 'vendor_rating', 'min_popularity',
            'created_after', 'created_before', 'price_percentile'
        ]
        
        for filter_key in additional_filters:
            if filters.get(filter_key):
                specificity_score += 0.1
        
        return min(specificity_score, 1.0)
    
    def _calculate_efficiency_score(self, filter_time: float, reduction_percentage: float) -> str:
        """Calculate overall filter efficiency score"""
        # Combine time and effectiveness metrics
        time_score = 1.0 if filter_time < 0.1 else 0.8 if filter_time < 0.5 else 0.6 if filter_time < 1.0 else 0.4
        effectiveness_score = reduction_percentage / 100
        
        combined_score = (time_score + effectiveness_score) / 2
        
        if combined_score > 0.8:
            return 'excellent'
        elif combined_score > 0.6:
            return 'good'
        elif combined_score > 0.4:
            return 'fair'
        else:
            return 'poor'
    
    def _assess_filter_complexity(self, filters: Dict[str, Any]) -> str:
        """Assess the complexity level of current filters"""
        active_filters = len([f for f in filters.values() if f not in [None, '', []]])
        
        if active_filters >= 5:
            return 'high'
        elif active_filters >= 3:
            return 'medium'
        else:
            return 'low'
    
    def _get_filter_optimization_suggestions(self, filters: Dict[str, Any], 
                                           reduction_percentage: float, 
                                           filter_time: float) -> List[Dict[str, str]]:
        """Generate optimization suggestions for current filters"""
        suggestions = []
        
        if filter_time > 1.0:
            suggestions.append({
                'type': 'performance',
                'title': 'Slow Filter Detected',
                'description': 'Consider simplifying your filters for better performance.',
                'priority': 'high'
            })
        
        if reduction_percentage < 10:
            suggestions.append({
                'type': 'effectiveness',
                'title': 'Filters Not Very Selective',
                'description': 'Your filters are not narrowing down results much. Consider adding more specific criteria.',
                'priority': 'medium'
            })
        
        if reduction_percentage > 95:
            suggestions.append({
                'type': 'over_filtering',
                'title': 'Filters May Be Too Restrictive',
                'description': 'Your filters are eliminating most results. Consider relaxing some criteria.',
                'priority': 'medium'
            })
        
        return suggestions
    
    def _suggest_alternative_filters(self, current_filters: Dict[str, Any], 
                                   model_name: str) -> List[Dict[str, Any]]:
        """Suggest alternative filter combinations"""
        alternatives = []
        
        try:
            # Suggest broader price ranges if price is filtered
            if current_filters.get('min_price') or current_filters.get('max_price'):
                alternatives.append({
                    'type': 'price_alternative',
                    'title': 'Broader Price Range',
                    'description': 'Expand your price range to see more options',
                    'changes': {
                        'action': 'modify',
                        'filter': 'price_range',
                        'suggestion': 'Increase range by 50%'
                    }
                })
            
            # Suggest removing least effective filters
            if len(current_filters) > 3:
                alternatives.append({
                    'type': 'simplification',
                    'title': 'Simplify Filters',
                    'description': 'Remove some filters to see more results',
                    'changes': {
                        'action': 'remove',
                        'suggestion': 'Keep only the most important 2-3 filters'
                    }
                })
            
        except Exception as e:
            logger.error(f"Failed to suggest alternative filters: {e}")
        
        return alternatives
    
    def _get_applied_filters_summary(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of currently applied filters"""
        summary = {
            'total_active': len([f for f in filters.values() if f not in [None, '', []]]),
            'categories': [],
            'price_range': {},
            'text_search': None,
            'other_filters': []
        }
        
        # Categorize filters
        for key, value in filters.items():
            if value not in [None, '', []]:
                if key in ['min_price', 'max_price']:
                    summary['price_range'][key] = value
                elif key in ['search', 'advanced_search']:
                    summary['text_search'] = value
                elif key in ['category_id', 'categories']:
                    summary['categories'].append({key: value})
                else:
                    summary['other_filters'].append({key: value})
        
        return summary
    
    def _get_filter_performance_metrics(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate performance metrics for the filter set"""
        return {
            'complexity_score': self._calculate_filter_specificity(filters),
            'estimated_selectivity': 'high' if len(filters) > 3 else 'medium' if len(filters) > 1 else 'low',
            'optimization_potential': 'high' if len(filters) > 5 else 'medium' if len(filters) > 3 else 'low'
        }
    
    def _apply_all_filters(self, queryset, filters: Dict[str, Any], model_name: str):
        """Apply all filters for performance testing"""
        queryset = self._apply_basic_filters(queryset, filters, model_name)
        queryset = self._apply_advanced_filters(queryset, filters, model_name)
        return queryset
    
    def _get_popular_filters(self, model_name: str, user_id: str = None) -> List[Dict[str, Any]]:
        """Get popular filter combinations used by other users"""
        # This would analyze filter usage patterns in a real implementation
        # For now, return some common filter suggestions
        popular = [
            {
                'name': 'Budget Friendly',
                'description': 'Products under average price',
                'filters': {'max_price': 50},
                'usage_count': 150
            },
            {
                'name': 'In Stock Only',
                'description': 'Only show available items',
                'filters': {'in_stock': True},
                'usage_count': 320
            },
            {
                'name': 'New This Week',
                'description': 'Recently added products',
                'filters': {'created_after': (timezone.now() - timedelta(days=7)).isoformat()},
                'usage_count': 85
            }
        ]
        
        return popular
    
    def _get_smart_filter_combinations(self, model_name: str, 
                                     current_filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get smart filter combinations that work well together"""
        combinations = []
        
        # If price is filtered, suggest complementary filters
        if current_filters.get('min_price') or current_filters.get('max_price'):
            combinations.append({
                'title': 'Price + Availability',
                'description': 'Combine price filtering with stock availability',
                'additional_filters': {'in_stock': True},
                'expected_results': 'More focused results with available items'
            })
        
        # If category is filtered, suggest vendor quality
        if current_filters.get('category_id'):
            combinations.append({
                'title': 'Category + Quality',
                'description': 'Add vendor quality filtering to your category',
                'additional_filters': {'vendor_rating': 'top'},
                'expected_results': 'Higher quality products in your chosen category'
            })
        
        return combinations
    
    def _get_filter_value_suggestions(self, model_name: str, 
                                    current_filters: Dict[str, Any]) -> Dict[str, List[Any]]:
        """Get suggested values for filter fields"""
        suggestions = {}
        
        if model_name == 'product':
            from products.models import Product, Category
            
            # Price suggestions based on actual data
            if not current_filters.get('min_price') and not current_filters.get('max_price'):
                price_quartiles = Product.objects.filter(is_available=True).aggregate(
                    q1=Avg('price_btc'),  # This would be actual quartile calculation
                    q2=Avg('price_btc'),
                    q3=Avg('price_btc')
                )
                
                suggestions['price_ranges'] = [
                    {'label': 'Budget', 'max_price': 25},
                    {'label': 'Mid-range', 'min_price': 25, 'max_price': 100},
                    {'label': 'Premium', 'min_price': 100}
                ]
            
            # Category suggestions
            if not current_filters.get('category_id'):
                popular_categories = Category.objects.annotate(
                    product_count=Count('products')
                ).filter(product_count__gt=0).order_by('-product_count')[:5]
                
                suggestions['categories'] = [
                    {'id': cat.id, 'name': cat.name}
                    for cat in popular_categories
                ]
        
        return suggestions
    
    def _get_quick_filters(self, model_name: str, user_id: str = None) -> List[Dict[str, Any]]:
        """Get quick filter presets for common use cases"""
        quick_filters = [
            {
                'name': 'Trending',
                'description': 'Popular products this week',
                'filters': {'min_popularity': 3},
                'icon': '📈'
            },
            {
                'name': 'New Arrivals',
                'description': 'Added in last 7 days',
                'filters': {'created_after': (timezone.now() - timedelta(days=7)).isoformat()},
                'icon': '🆕'
            },
            {
                'name': 'Best Value',
                'description': 'High quality, reasonable price',
                'filters': {'vendor_rating': 'top', 'max_price': 75},
                'icon': '💎'
            },
            {
                'name': 'Premium',
                'description': 'High-end products',
                'filters': {'min_price': 100, 'vendor_rating': 'top'},
                'icon': '⭐'
            }
        ]
        
        return quick_filters