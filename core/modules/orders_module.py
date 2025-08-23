"""
Orders Module
Modular implementation of order management functionality.
"""

from typing import Dict, List, Any, Optional, Type
from ..architecture.base import BaseModule
from ..architecture.decorators import module, provides_models, provides_views, provides_templates
from ..architecture.interfaces import ModelInterface, ViewInterface, TemplateInterface
from ..services.order_service import OrderService
import logging

logger = logging.getLogger(__name__)


@module(
    name="orders",
    version="2.0.0",
    description="Order management and processing module",
    author="Marketplace Team",
    dependencies=["accounts", "vendors", "products", "wallets"],
    required_settings=["CACHES"]
)
@provides_templates("templates/orders")
@provides_views(
    order_list="orders.views.OrderListView",
    order_detail="orders.views.OrderDetailView",
    order_create="orders.views.OrderCreateView",
    order_track="orders.views.OrderTrackView"
)
class OrdersModule(BaseModule, ModelInterface, ViewInterface, TemplateInterface):
    """
    Modular orders system that provides order management capabilities.
    """

    def __init__(self, **kwargs):
        """Initialize the orders module."""
        super().__init__(**kwargs)
        self.order_service = OrderService(**kwargs)
        self._order_cache = {}

    def initialize(self) -> bool:
        """Initialize the orders module."""
        try:
            # Initialize the order service
            if not self.order_service.initialize():
                logger.error("Failed to initialize order service")
                return False

            # Register template tags
            self._register_template_tags()

            # Set up signal handlers
            self._setup_signals()

            logger.info(f"Orders module {self.name} initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize orders module: {e}")
            return False

    def cleanup(self) -> bool:
        """Clean up the orders module."""
        try:
            # Clean up order service
            self.order_service.cleanup()

            # Clear order cache
            self._order_cache.clear()

            # Clean up signal handlers
            self._cleanup_signals()

            logger.info(f"Orders module {self.name} cleaned up successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to cleanup orders module: {e}")
            return False

    def _register_template_tags(self):
        """Register template tags for the orders module."""
        # Template tags are automatically loaded by Django
        pass

    def _setup_signals(self):
        """Set up signal handlers for the orders module."""
        # Set up signals for order events
        pass

    def _cleanup_signals(self):
        """Clean up signal handlers."""
        # Disconnect signals
        pass

    def get_models(self) -> List[Type]:
        """Get models provided by this module."""
        try:
            from orders.models import Order, OrderItem, OrderStatusLog
            return [Order, OrderItem, OrderStatusLog]
        except ImportError:
            return []

    def get_admin_models(self) -> Dict[str, Type]:
        """Get admin models for this module."""
        try:
            from orders.admin import OrderAdmin, OrderItemAdmin
            return {
                'order': OrderAdmin,
                'order_item': OrderItemAdmin
            }
        except ImportError:
            return {}

    def get_signals(self) -> List:
        """Get signals provided by this module."""
        return []

    def get_urls(self) -> List:
        """Get URL patterns for this module."""
        from django.urls import path
        from orders.views import (
            OrderListView, OrderDetailView, OrderCreateView, OrderTrackView,
            order_history, vendor_orders
        )

        return [
            path('orders/', OrderListView.as_view(), name='order_list'),
            path('orders/<int:pk>/', OrderDetailView.as_view(), name='order_detail'),
            path('orders/create/', OrderCreateView.as_view(), name='order_create'),
            path('orders/<int:pk>/track/', OrderTrackView.as_view(), name='order_track'),
            path('orders/history/', order_history, name='order_history'),
            path('orders/vendor/', vendor_orders, name='vendor_orders'),
        ]

    def get_views(self) -> Dict[str, Type]:
        """Get views provided by this module."""
        try:
            from orders.views import (
                OrderListView, OrderDetailView, OrderCreateView, OrderTrackView,
                order_history, vendor_orders
            )

            return {
                'order_list': OrderListView,
                'order_detail': OrderDetailView,
                'order_create': OrderCreateView,
                'order_track': OrderTrackView,
                'order_history': order_history,
                'vendor_orders': vendor_orders,
            }
        except ImportError:
            return {}

    def get_permissions(self) -> Dict[str, List[str]]:
        """Get permissions required by this module."""
        return {
            'order_list': ['orders.view_order'],
            'order_detail': ['orders.view_order'],
            'order_create': ['orders.add_order'],
            'order_track': ['orders.view_order'],
        }

    def get_template_dirs(self) -> List[str]:
        """Get template directories for this module."""
        return ["templates/orders"]

    def get_context_processors(self) -> List[str]:
        """Get context processors for this module."""
        return []

    def get_template_tags(self) -> List[str]:
        """Get template tags for this module."""
        return []

    # Module-specific functionality using the order service
    def get_order_by_id(self, order_id: str) -> Any:
        """Get order by ID."""
        return self.order_service.get_order_by_id(order_id)

    def get_orders_by_user(self, user_id: str, **filters) -> List[Any]:
        """Get orders by user."""
        return self.order_service.get_orders_by_user(user_id, **filters)

    def get_orders_by_vendor(self, vendor_id: str, **filters) -> List[Any]:
        """Get orders by vendor."""
        return self.order_service.get_orders_by_vendor(vendor_id, **filters)

    def create_order(self, user_id: str, vendor_id: str, items: List[Dict], 
                    shipping_address: str, **kwargs) -> tuple:
        """Create a new order."""
        return self.order_service.create_order(user_id, vendor_id, items, shipping_address, **kwargs)

    def update_order_status(self, order_id: str, new_status: str, 
                          admin_user_id: str = None, notes: str = "") -> tuple:
        """Update order status."""
        return self.order_service.update_order_status(order_id, new_status, admin_user_id, notes)

    def get_order_summary(self, order_id: str) -> Dict[str, Any]:
        """Get order summary."""
        return self.order_service.get_order_summary(order_id)

    def get_user_order_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user order history."""
        return self.order_service.get_user_order_history(user_id, limit)

    def get_vendor_order_summary(self, vendor_id: str) -> Dict[str, Any]:
        """Get vendor order summary."""
        return self.order_service.get_vendor_order_summary(vendor_id)

    def cancel_order(self, order_id: str, user_id: str, reason: str = "") -> tuple:
        """Cancel an order."""
        return self.order_service.cancel_order(order_id, user_id, reason)

    def get_order_statistics(self, user_id: str = None, vendor_id: str = None) -> Dict[str, Any]:
        """Get order statistics."""
        return self.order_service.get_order_statistics(user_id, vendor_id)

    def get_module_health(self) -> Dict[str, Any]:
        """Get health status of this module."""
        return {
            'module_name': self.name,
            'version': self.version,
            'enabled': self.is_enabled(),
            'order_service_healthy': self.order_service.is_available(),
            'order_cache_size': len(self._order_cache),
            'last_activity': getattr(self, '_last_activity', None),
        }

    def get_module_metrics(self) -> Dict[str, Any]:
        """Get metrics for this module."""
        return {
            'orders_created': getattr(self, '_creation_count', 0),
            'orders_updated': getattr(self, '_update_count', 0),
            'orders_cancelled': getattr(self, '_cancellation_count', 0),
            'status_changes': getattr(self, '_status_change_count', 0),
        }

    def validate_configuration(self) -> bool:
        """Validate module configuration."""
        try:
            # Check if order service is available
            if not self.order_service.is_available():
                logger.error("Order service is not available")
                return False

            # Check if required models exist
            from django.apps import apps
            if not apps.is_installed('orders'):
                logger.error("Orders app is not installed")
                return False

            return True

        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False

    def get_configuration_schema(self) -> Dict[str, Any]:
        """Get configuration schema for this module."""
        return {
            'order_timeout_minutes': {
                'type': 'integer',
                'description': 'Order timeout in minutes',
                'default': 30,
                'required': False
            },
            'max_order_items': {
                'type': 'integer',
                'description': 'Maximum items per order',
                'default': 50,
                'required': False
            },
            'order_cache_timeout': {
                'type': 'integer',
                'description': 'Order cache timeout in seconds',
                'default': 300,
                'required': False
            }
        }

    def set_configuration(self, config: Dict[str, Any]) -> bool:
        """Set module configuration."""
        try:
            # Update order service configuration
            for key, value in config.items():
                if hasattr(self.order_service, key):
                    setattr(self.order_service, key, value)
                else:
                    logger.warning(f"Unknown configuration key: {key}")

            logger.info(f"Configuration updated for module {self.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to update configuration for module {self.name}: {e}")
            return False

    def get_order_analytics(self, user_id: str = None, vendor_id: str = None) -> Dict[str, Any]:
        """Get order analytics."""
        try:
            # Get order statistics
            order_stats = self.get_order_statistics(user_id, vendor_id)

            # Get recent orders
            if user_id:
                recent_orders = self.get_user_order_history(user_id, limit=10)
            elif vendor_id:
                recent_orders = self.get_orders_by_vendor(vendor_id, limit=10)
            else:
                recent_orders = []

            # Get order trends
            trends = self._get_order_trends(user_id, vendor_id)

            return {
                'order_statistics': order_stats,
                'recent_orders': recent_orders,
                'order_trends': trends,
                'performance_metrics': self._get_performance_metrics(user_id, vendor_id)
            }

        except Exception as e:
            logger.error(f"Failed to get order analytics: {e}")
            return {}

    def _get_order_trends(self, user_id: str = None, vendor_id: str = None) -> Dict[str, Any]:
        """Get order trends over time."""
        try:
            from orders.models import Order
            from django.utils import timezone
            from datetime import timedelta

            queryset = Order.objects.all()

            if user_id:
                queryset = queryset.filter(user_id=user_id)
            elif vendor_id:
                queryset = queryset.filter(vendor_id=vendor_id)

            # Daily trends for last 30 days
            daily_trends = {}
            for i in range(30):
                date = timezone.now().date() - timedelta(days=i)
                daily_orders = queryset.filter(created_at__date=date)
                
                daily_trends[date.isoformat()] = {
                    'count': daily_orders.count(),
                    'revenue': float(sum(o.total_amount for o in daily_orders if o.status == 'completed')),
                    'pending': daily_orders.filter(status='pending').count(),
                    'completed': daily_orders.filter(status='completed').count()
                }

            return {
                'daily_trends': daily_trends,
                'total_period_orders': queryset.filter(
                    created_at__gte=timezone.now() - timedelta(days=30)
                ).count()
            }

        except Exception as e:
            logger.error(f"Failed to get order trends: {e}")
            return {}

    def _get_performance_metrics(self, user_id: str = None, vendor_id: str = None) -> Dict[str, Any]:
        """Get performance metrics."""
        try:
            from orders.models import Order
            from django.utils import timezone
            from datetime import timedelta

            queryset = Order.objects.all()

            if user_id:
                queryset = queryset.filter(user_id=user_id)
            elif vendor_id:
                queryset = queryset.filter(vendor_id=vendor_id)

            # Calculate metrics for last 30 days
            cutoff_date = timezone.now() - timedelta(days=30)
            recent_orders = queryset.filter(created_at__gte=cutoff_date)

            total_orders = recent_orders.count()
            completed_orders = recent_orders.filter(status='completed').count()
            cancelled_orders = recent_orders.filter(status='cancelled').count()

            # Calculate completion rate
            completion_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0

            # Calculate average order value
            completed_order_amounts = recent_orders.filter(status='completed').values_list('total_amount', flat=True)
            avg_order_value = float(sum(completed_order_amounts) / len(completed_order_amounts)) if completed_order_amounts else 0

            # Calculate average processing time
            processing_times = []
            for order in recent_orders.filter(status='completed'):
                if hasattr(order, 'processing_started') and order.processing_started:
                    processing_time = (order.completed_at - order.processing_started).total_seconds() / 3600  # hours
                    processing_times.append(processing_time)

            avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0

            return {
                'total_orders_30d': total_orders,
                'completion_rate': round(completion_rate, 2),
                'cancellation_rate': round((cancelled_orders / total_orders * 100) if total_orders > 0 else 0, 2),
                'average_order_value': round(avg_order_value, 2),
                'average_processing_time_hours': round(avg_processing_time, 2),
                'revenue_30d': float(sum(o.total_amount for o in recent_orders.filter(status='completed')))
            }

        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {}

    def perform_order_maintenance(self) -> Dict[str, Any]:
        """Perform order maintenance tasks."""
        try:
            results = {
                'cleaned_expired': 0,
                'updated_statuses': 0,
                'processed_refunds': 0,
                'errors': []
            }

            # Clean up expired orders (older than 90 days)
            try:
                from orders.models import Order
                from django.utils import timezone
                from datetime import timedelta

                cutoff_date = timezone.now() - timedelta(days=90)
                expired_orders = Order.objects.filter(
                    status='pending',
                    created_at__lt=cutoff_date
                )
                
                for order in expired_orders:
                    try:
                        # Cancel expired orders
                        success, message = self.cancel_order(
                            str(order.id), 
                            str(order.user_id), 
                            "Order expired automatically"
                        )
                        if success:
                            results['cleaned_expired'] += 1
                    except Exception as e:
                        results['errors'].append(f"Failed to cancel expired order {order.id}: {e}")

            except Exception as e:
                results['errors'].append(f"Expired order cleanup failed: {e}")

            # Update order statuses
            try:
                from orders.models import Order
                from django.utils import timezone
                from datetime import timedelta

                # Auto-complete orders that have been shipped for more than 7 days
                shipped_cutoff = timezone.now() - timedelta(days=7)
                shipped_orders = Order.objects.filter(
                    status='shipped',
                    shipped_at__lt=shipped_cutoff
                )

                for order in shipped_orders:
                    try:
                        success, message = self.update_order_status(
                            str(order.id),
                            'completed',
                            notes="Auto-completed after shipping period"
                        )
                        if success:
                            results['updated_statuses'] += 1
                    except Exception as e:
                        results['errors'].append(f"Failed to auto-complete order {order.id}: {e}")

            except Exception as e:
                results['errors'].append(f"Status update failed: {e}")

            logger.info(f"Order maintenance completed: {results}")
            return results

        except Exception as e:
            logger.error(f"Order maintenance failed: {e}")
            return {'error': str(e)}

    def generate_order_report(self, start_date: str = None, end_date: str = None, 
                            user_id: str = None, vendor_id: str = None) -> Dict[str, Any]:
        """Generate order report for a date range."""
        try:
            from orders.models import Order
            from django.utils import timezone
            from datetime import datetime, timedelta

            # Parse dates
            if not start_date:
                start_date = (timezone.now() - timedelta(days=30)).date()
            else:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

            if not end_date:
                end_date = timezone.now().date()
            else:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

            # Get orders in date range
            queryset = Order.objects.filter(
                created_at__date__range=[start_date, end_date]
            )

            if user_id:
                queryset = queryset.filter(user_id=user_id)
            elif vendor_id:
                queryset = queryset.filter(vendor_id=vendor_id)

            # Calculate report data
            report_data = {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'total_orders': queryset.count(),
                'by_status': {},
                'by_currency': {},
                'daily_totals': {},
                'top_vendors': [],
                'top_users': []
            }

            # Group by status
            for status in ['pending', 'processing', 'shipped', 'completed', 'cancelled', 'disputed']:
                status_orders = queryset.filter(status=status)
                report_data['by_status'][status] = {
                    'count': status_orders.count(),
                    'total_value': float(sum(o.total_amount for o in status_orders))
                }

            # Group by currency
            for currency in queryset.values_list('currency', flat=True).distinct():
                currency_orders = queryset.filter(currency=currency)
                report_data['by_currency'][currency] = {
                    'count': currency_orders.count(),
                    'total_value': float(sum(o.total_amount for o in currency_orders))
                }

            # Daily totals
            current_date = start_date
            while current_date <= end_date:
                daily_orders = queryset.filter(created_at__date=current_date)
                daily_stats = {
                    'count': daily_orders.count(),
                    'total_value': float(sum(o.total_amount for o in daily_orders)),
                    'completed': daily_orders.filter(status='completed').count()
                }
                report_data['daily_totals'][current_date.isoformat()] = daily_stats
                current_date += timedelta(days=1)

            # Top vendors by order count
            vendor_stats = {}
            for order in queryset:
                vendor_id = str(order.vendor_id)
                if vendor_id not in vendor_stats:
                    vendor_stats[vendor_id] = {'count': 0, 'value': 0}
                vendor_stats[vendor_id]['count'] += 1
                vendor_stats[vendor_id]['value'] += float(order.total_amount)

            top_vendors = sorted(vendor_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:10]
            report_data['top_vendors'] = [
                {'vendor_id': vid, 'count': stats['count'], 'value': stats['value']}
                for vid, stats in top_vendors
            ]

            # Top users by order count
            user_stats = {}
            for order in queryset:
                user_id = str(order.user_id)
                if user_id not in user_stats:
                    user_stats[user_id] = {'count': 0, 'value': 0}
                user_stats[user_id]['count'] += 1
                user_stats[user_id]['value'] += float(order.total_amount)

            top_users = sorted(user_stats.items(), key=lambda x: x[1]['count'], reverse=True)[:10]
            report_data['top_users'] = [
                {'user_id': uid, 'count': stats['count'], 'value': stats['value']}
                for uid, stats in top_users
            ]

            return report_data

        except Exception as e:
            logger.error(f"Failed to generate order report: {e}")
            return {'error': str(e)}