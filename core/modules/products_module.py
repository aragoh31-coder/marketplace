"""
Products Module
Modular implementation of product management functionality.
"""

import logging
from typing import Any, Dict, List, Optional, Type

from ..architecture.base import BaseModule
from ..architecture.decorators import module, provides_models, provides_templates, provides_views
from ..architecture.interfaces import ModelInterface, TemplateInterface, ViewInterface
from ..services.product_service import ProductService

logger = logging.getLogger(__name__)


@module(
    name="products",
    version="2.0.0",
    description="Product management and catalog module",
    author="Marketplace Team",
    dependencies=["accounts", "vendors"],
    required_settings=["CACHES"],
)
@provides_templates("templates/products")
@provides_views(
    product_list="products.views.ProductListView",
    product_detail="products.views.ProductDetailView",
    product_create="products.views.ProductCreateView",
    product_edit="products.views.ProductEditView",
)
class ProductsModule(BaseModule, ModelInterface, ViewInterface, TemplateInterface):
    """
    Modular products system that provides product management capabilities.
    """

    def __init__(self, **kwargs):
        """Initialize the products module."""
        super().__init__(**kwargs)
        self.product_service = ProductService(**kwargs)
        self._product_cache = {}

    def initialize(self) -> bool:
        """Initialize the products module."""
        try:
            # Initialize the product service
            if not self.product_service.initialize():
                logger.error("Failed to initialize product service")
                return False

            # Register template tags
            self._register_template_tags()

            # Set up signal handlers
            self._setup_signals()

            logger.info(f"Products module {self.name} initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize products module: {e}")
            return False

    def cleanup(self) -> bool:
        """Clean up the products module."""
        try:
            # Clean up product service
            self.product_service.cleanup()

            # Clear product cache
            self._product_cache.clear()

            # Clean up signal handlers
            self._cleanup_signals()

            logger.info(f"Products module {self.name} cleaned up successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to cleanup products module: {e}")
            return False

    def _register_template_tags(self):
        """Register template tags for the products module."""
        # Template tags are automatically loaded by Django
        pass

    def _setup_signals(self):
        """Set up signal handlers for the products module."""
        # Set up signals for product events
        pass

    def _cleanup_signals(self):
        """Clean up signal handlers."""
        # Disconnect signals
        pass

    def get_models(self) -> List[Type]:
        """Get models provided by this module."""
        try:
            from products.models import Product, ProductCategory, ProductImage

            return [Product, ProductCategory, ProductImage]
        except ImportError:
            return []

    def get_admin_models(self) -> Dict[str, Type]:
        """Get admin models for this module."""
        try:
            from products.admin import ProductAdmin, ProductCategoryAdmin

            return {"product": ProductAdmin, "product_category": ProductCategoryAdmin}
        except ImportError:
            return {}

    def get_signals(self) -> List:
        """Get signals provided by this module."""
        return []

    def get_urls(self) -> List:
        """Get URL patterns for this module."""
        from django.urls import path

        from products.views import (
            ProductCreateView,
            ProductDetailView,
            ProductEditView,
            ProductListView,
            category_products,
            product_search,
        )

        return [
            path("products/", ProductListView.as_view(), name="product_list"),
            path("products/<int:pk>/", ProductDetailView.as_view(), name="product_detail"),
            path("products/create/", ProductCreateView.as_view(), name="product_create"),
            path("products/<int:pk>/edit/", ProductEditView.as_view(), name="product_edit"),
            path("products/search/", product_search, name="product_search"),
            path("products/category/<str:category>/", category_products, name="category_products"),
        ]

    def get_views(self) -> Dict[str, Type]:
        """Get views provided by this module."""
        try:
            from products.views import (
                ProductCreateView,
                ProductDetailView,
                ProductEditView,
                ProductListView,
                category_products,
                product_search,
            )

            return {
                "product_list": ProductListView,
                "product_detail": ProductDetailView,
                "product_create": ProductCreateView,
                "product_edit": ProductEditView,
                "product_search": product_search,
                "category_products": category_products,
            }
        except ImportError:
            return {}

    def get_permissions(self) -> Dict[str, List[str]]:
        """Get permissions required by this module."""
        return {
            "product_list": ["products.view_product"],
            "product_detail": ["products.view_product"],
            "product_create": ["products.add_product"],
            "product_edit": ["products.change_product"],
        }

    def get_template_dirs(self) -> List[str]:
        """Get template directories for this module."""
        return ["templates/products"]

    def get_context_processors(self) -> List[str]:
        """Get context processors for this module."""
        return []

    def get_template_tags(self) -> List[str]:
        """Get template tags for this module."""
        return []

    # Module-specific functionality using the product service
    def get_product_by_id(self, product_id: str) -> Any:
        """Get product by ID."""
        return self.product_service.get_product_by_id(product_id)

    def search_products(self, query: str = "", **filters) -> List[Dict[str, Any]]:
        """Search products."""
        return self.product_service.search_products(query, **filters)

    def get_products_by_vendor(self, vendor_id: str, **filters) -> List[Any]:
        """Get products by vendor."""
        return self.product_service.get_products_by_vendor(vendor_id, **filters)

    def create_product(self, vendor_id: str, product_data: dict) -> tuple:
        """Create a new product."""
        return self.product_service.create_product(vendor_id, product_data)

    def update_product(self, product_id: str, **kwargs) -> tuple:
        """Update product information."""
        return self.product_service.update_product(product_id, **kwargs)

    def delete_product(self, product_id: str) -> tuple:
        """Delete a product."""
        return self.product_service.delete_product(product_id)

    def get_product_categories(self) -> List[str]:
        """Get all product categories."""
        return self.product_service.get_product_categories()

    def get_featured_products(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get featured products."""
        return self.product_service.get_featured_products(limit)

    def get_products_by_category(self, category: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get products by category."""
        return self.product_service.get_products_by_category(category, limit)

    def get_vendor_product_summary(self, vendor_id: str) -> Dict[str, Any]:
        """Get vendor product summary."""
        return self.product_service.get_vendor_product_summary(vendor_id)

    def get_module_health(self) -> Dict[str, Any]:
        """Get health status of this module."""
        return {
            "module_name": self.name,
            "version": self.version,
            "enabled": self.is_enabled(),
            "product_service_healthy": self.product_service.is_available(),
            "product_cache_size": len(self._product_cache),
            "last_activity": getattr(self, "_last_activity", None),
        }

    def get_module_metrics(self) -> Dict[str, Any]:
        """Get metrics for this module."""
        return {
            "products_created": getattr(self, "_creation_count", 0),
            "products_updated": getattr(self, "_update_count", 0),
            "products_deleted": getattr(self, "_deletion_count", 0),
            "product_searches": getattr(self, "_search_count", 0),
        }

    def validate_configuration(self) -> bool:
        """Validate module configuration."""
        try:
            # Check if product service is available
            if not self.product_service.is_available():
                logger.error("Product service is not available")
                return False

            # Check if required models exist
            from django.apps import apps

            if not apps.is_installed("products"):
                logger.error("Products app is not installed")
                return False

            return True

        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False

    def get_configuration_schema(self) -> Dict[str, Any]:
        """Get configuration schema for this module."""
        return {
            "max_products_per_vendor": {
                "type": "integer",
                "description": "Maximum products a vendor can create",
                "default": 100,
                "required": False,
            },
            "product_approval_required": {
                "type": "boolean",
                "description": "Whether products require approval before going live",
                "default": True,
                "required": False,
            },
            "product_cache_timeout": {
                "type": "integer",
                "description": "Product cache timeout in seconds",
                "default": 300,
                "required": False,
            },
        }

    def set_configuration(self, config: Dict[str, Any]) -> bool:
        """Set module configuration."""
        try:
            # Update product service configuration
            for key, value in config.items():
                if hasattr(self.product_service, key):
                    setattr(self.product_service, key, value)
                else:
                    logger.warning(f"Unknown configuration key: {key}")

            logger.info(f"Configuration updated for module {self.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to update configuration for module {self.name}: {e}")
            return False

    def get_product_analytics(self, vendor_id: str = None) -> Dict[str, Any]:
        """Get product analytics."""
        try:
            # Get product statistics
            product_stats = self.product_service.get_service_health()

            # Get category distribution
            categories = self.get_product_categories()
            category_stats = {}
            for category in categories:
                products = self.get_products_by_category(category)
                category_stats[category] = len(products)

            # Get vendor statistics if specified
            vendor_stats = {}
            if vendor_id:
                vendor_stats = self.get_vendor_product_summary(vendor_id)

            return {
                "product_statistics": product_stats,
                "category_distribution": category_stats,
                "vendor_statistics": vendor_stats,
                "recent_activity": self._get_recent_product_activity(),
            }

        except Exception as e:
            logger.error(f"Failed to get product analytics: {e}")
            return {}

    def _get_recent_product_activity(self) -> List[Dict[str, Any]]:
        """Get recent product activity."""
        try:
            from datetime import timedelta

            from django.utils import timezone

            from products.models import Product

            cutoff_time = timezone.now() - timedelta(days=7)

            recent_products = Product.objects.filter(created_at__gte=cutoff_time).order_by("-created_at")[:10]

            return [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "vendor_id": str(p.vendor_id),
                    "category": p.category,
                    "price": float(p.price),
                    "created_at": p.created_at.isoformat(),
                }
                for p in recent_products
            ]

        except Exception as e:
            logger.error(f"Failed to get recent product activity: {e}")
            return []

    def perform_product_maintenance(self) -> Dict[str, Any]:
        """Perform product maintenance tasks."""
        try:
            results = {"cleaned_inactive": 0, "updated_categories": 0, "processed_images": 0, "errors": []}

            # Clean up inactive products (older than 90 days)
            try:
                from datetime import timedelta

                from django.utils import timezone

                from products.models import Product

                cutoff_date = timezone.now() - timedelta(days=90)
                inactive_products = Product.objects.filter(is_active=False, updated_at__lt=cutoff_date).delete()
                results["cleaned_inactive"] = inactive_products[0]

            except Exception as e:
                results["errors"].append(f"Product cleanup failed: {e}")

            # Update product categories
            try:
                from products.models import Product

                products = Product.objects.all()
                for product in products:
                    try:
                        # Update category if needed
                        if not product.category:
                            product.category = "uncategorized"
                            product.save()
                            results["updated_categories"] += 1
                    except Exception as e:
                        results["errors"].append(f"Failed to update product {product.id}: {e}")

            except Exception as e:
                results["errors"].append(f"Category update failed: {e}")

            logger.info(f"Product maintenance completed: {results}")
            return results

        except Exception as e:
            logger.error(f"Product maintenance failed: {e}")
            return {"error": str(e)}

    def generate_product_report(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Generate product report for a date range."""
        try:
            from datetime import datetime, timedelta

            from django.utils import timezone

            from products.models import Product

            # Parse dates
            if not start_date:
                start_date = (timezone.now() - timedelta(days=30)).date()
            else:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()

            if not end_date:
                end_date = timezone.now().date()
            else:
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()

            # Get products in date range
            products = Product.objects.filter(created_at__date__range=[start_date, end_date])

            # Calculate totals by category
            report_data = {
                "period": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
                "total_products": products.count(),
                "active_products": products.filter(is_active=True).count(),
                "by_category": {},
                "by_vendor": {},
                "daily_totals": {},
            }

            # Group by category
            for category in products.values_list("category", flat=True).distinct():
                category_products = products.filter(category=category)
                report_data["by_category"][category] = {
                    "count": category_products.count(),
                    "active": category_products.filter(is_active=True).count(),
                    "total_value": float(sum(p.price for p in category_products)),
                }

            # Group by vendor
            for vendor_id in products.values_list("vendor_id", flat=True).distinct():
                vendor_products = products.filter(vendor_id=vendor_id)
                report_data["by_vendor"][str(vendor_id)] = {
                    "count": vendor_products.count(),
                    "active": vendor_products.filter(is_active=True).count(),
                    "total_value": float(sum(p.price for p in vendor_products)),
                }

            # Daily totals
            current_date = start_date
            while current_date <= end_date:
                daily_products = products.filter(created_at__date=current_date)
                daily_stats = {
                    "count": daily_products.count(),
                    "active": daily_products.filter(is_active=True).count(),
                    "total_value": float(sum(p.price for p in daily_products)),
                }
                report_data["daily_totals"][current_date.isoformat()] = daily_stats
                current_date += timedelta(days=1)

            return report_data

        except Exception as e:
            logger.error(f"Failed to generate product report: {e}")
            return {"error": str(e)}
