"""
Product Service
Handles all product-related business logic and operations.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import models, transaction
from django.utils import timezone

from .base_service import BaseService

logger = logging.getLogger(__name__)
User = get_user_model()


class ProductService(BaseService):
    """Service for managing products and product operations."""

    service_name = "product_service"
    version = "1.0.0"
    description = "Product management and operations service"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._product_cache = {}
        self._category_cache = {}

    def initialize(self) -> bool:
        """Initialize the product service."""
        try:
            # Set up any connections or validate configuration
            logger.info("Product service initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize product service: {e}")
            return False

    def cleanup(self) -> bool:
        """Clean up the product service."""
        try:
            # Clear caches
            self._product_cache.clear()
            self._category_cache.clear()
            logger.info("Product service cleaned up successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup product service: {e}")
            return False

    def get_required_config(self) -> List[str]:
        """Get required configuration keys."""
        return ["max_products_per_vendor", "product_approval_required"]

    def get_product_by_id(self, product_id: str) -> Optional[Any]:
        """Get product by ID with caching."""
        cache_key = f"product:{product_id}"

        # Try cache first
        cached_product = self.get_cached(cache_key)
        if cached_product:
            return cached_product

        try:
            from products.models import Product

            product = Product.objects.get(id=product_id)

            # Cache product for 5 minutes
            self.set_cached(cache_key, product, timeout=300)
            return product

        except Exception as e:
            logger.error(f"Failed to get product {product_id}: {e}")
            return None

    def get_products_by_vendor(self, vendor_id: str, **filters) -> List[Any]:
        """Get products by vendor with optional filters."""
        try:
            from products.models import Product

            queryset = Product.objects.filter(vendor_id=vendor_id)

            # Apply filters
            if filters.get("active_only", True):
                queryset = queryset.filter(is_active=True)

            if filters.get("category"):
                queryset = queryset.filter(category=filters["category"])

            if filters.get("min_price"):
                queryset = queryset.filter(price__gte=filters["min_price"])

            if filters.get("max_price"):
                queryset = queryset.filter(price__lte=filters["max_price"])

            if filters.get("in_stock", False):
                queryset = queryset.filter(stock_quantity__gt=0)

            # Order by creation date
            products = queryset.order_by("-created_at")

            # Apply limit if specified
            if filters.get("limit"):
                products = products[: filters["limit"]]

            return list(products)

        except Exception as e:
            logger.error(f"Failed to get products for vendor {vendor_id}: {e}")
            return []

    def create_product(self, vendor_id: str, product_data: dict) -> Tuple[Any, bool, str]:
        """Create a new product."""
        try:
            from products.models import Product

            with transaction.atomic():
                # Validate vendor exists and is approved
                from core.services.vendor_service import VendorService

                vendor_service = VendorService()
                vendor = vendor_service.get_vendor_by_user(vendor_id)

                if not vendor:
                    return None, False, "Vendor not found"

                if not vendor.is_approved:
                    return None, False, "Vendor must be approved to create products"

                # Check product limit
                existing_products = Product.objects.filter(vendor_id=vendor_id).count()
                max_products = self.get_config("max_products_per_vendor", 100)

                if existing_products >= max_products:
                    return None, False, f"Product limit reached. Maximum {max_products} products allowed."

                # Create product
                product = Product.objects.create(vendor_id=vendor_id, **product_data)

                # Clear vendor cache
                self.clear_cache(f"vendor_products:{vendor_id}")

                logger.info(f"Product created successfully: {product.name} by vendor {vendor_id}")
                return product, True, "Product created successfully"

        except Exception as e:
            logger.error(f"Failed to create product for vendor {vendor_id}: {e}")
            return None, False, str(e)

    def update_product(self, product_id: str, **kwargs) -> Tuple[Any, bool, str]:
        """Update product information."""
        try:
            product = self.get_product_by_id(product_id)
            if not product:
                return None, False, "Product not found"

            with transaction.atomic():
                # Update fields
                for field, value in kwargs.items():
                    if hasattr(product, field):
                        setattr(product, field, value)

                product.save()

                # Clear caches
                self.clear_cache(f"product:{product_id}")
                self.clear_cache(f"vendor_products:{product.vendor_id}")

                logger.info(f"Product updated successfully: {product.name}")
                return product, True, "Product updated successfully"

        except Exception as e:
            logger.error(f"Failed to update product {product_id}: {e}")
            return None, False, str(e)

    def delete_product(self, product_id: str) -> Tuple[bool, str]:
        """Delete a product."""
        try:
            product = self.get_product_by_id(product_id)
            if not product:
                return False, "Product not found"

            with transaction.atomic():
                vendor_id = product.vendor_id
                product_name = product.name
                product.delete()

                # Clear caches
                self.clear_cache(f"product:{product_id}")
                self.clear_cache(f"vendor_products:{vendor_id}")

                logger.info(f"Product deleted successfully: {product_name}")
                return True, "Product deleted successfully"

        except Exception as e:
            logger.error(f"Failed to delete product {product_id}: {e}")
            return False, str(e)

    def search_products(
        self,
        query: str = "",
        category: str = None,
        min_price: Decimal = None,
        max_price: Decimal = None,
        vendor_id: str = None,
        in_stock: bool = False,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search products with various filters."""
        try:
            from products.models import Product

            queryset = Product.objects.filter(is_active=True)

            # Apply search query
            if query:
                queryset = queryset.filter(
                    models.Q(name__icontains=query)
                    | models.Q(description__icontains=query)
                    | models.Q(category__icontains=query)
                )

            # Apply filters
            if category:
                queryset = queryset.filter(category=category)

            if min_price is not None:
                queryset = queryset.filter(price__gte=min_price)

            if max_price is not None:
                queryset = queryset.filter(price__lte=max_price)

            if vendor_id:
                queryset = queryset.filter(vendor_id=vendor_id)

            if in_stock:
                queryset = queryset.filter(stock_quantity__gt=0)

            # Order by relevance (could be enhanced with search ranking)
            products = queryset.order_by("-created_at")[:limit]

            return [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "description": p.description,
                    "price": float(p.price),
                    "currency": p.currency,
                    "category": p.category,
                    "stock_quantity": p.stock_quantity,
                    "vendor_id": str(p.vendor_id),
                    "is_active": p.is_active,
                    "created_at": p.created_at.isoformat(),
                    "updated_at": p.updated_at.isoformat() if hasattr(p, "updated_at") else None,
                }
                for p in products
            ]

        except Exception as e:
            logger.error(f"Product search failed: {e}")
            return []

    def get_product_categories(self) -> List[str]:
        """Get all available product categories."""
        try:
            from products.models import Product

            categories = Product.objects.filter(is_active=True).values_list("category", flat=True).distinct()

            return list(categories)

        except Exception as e:
            logger.error(f"Failed to get product categories: {e}")
            return []

    def update_product_stock(
        self, product_id: str, quantity_change: int, operation: str = "adjust"
    ) -> Tuple[bool, str]:
        """Update product stock quantity."""
        try:
            product = self.get_product_by_id(product_id)
            if not product:
                return False, "Product not found"

            with transaction.atomic():
                if operation == "adjust":
                    new_quantity = product.stock_quantity + quantity_change
                elif operation == "set":
                    new_quantity = quantity_change
                else:
                    return False, "Invalid operation. Use 'adjust' or 'set'"

                if new_quantity < 0:
                    return False, "Stock quantity cannot be negative"

                product.stock_quantity = new_quantity
                product.save()

                # Clear caches
                self.clear_cache(f"product:{product_id}")
                self.clear_cache(f"vendor_products:{product.vendor_id}")

                logger.info(f"Product stock updated: {product.name} - {operation} to {new_quantity}")
                return True, f"Stock updated to {new_quantity}"

        except Exception as e:
            logger.error(f"Failed to update product stock for {product_id}: {e}")
            return False, str(e)

    def check_product_availability(self, product_id: str, requested_quantity: int = 1) -> Tuple[bool, str]:
        """Check if a product is available in the requested quantity."""
        try:
            product = self.get_product_by_id(product_id)
            if not product:
                return False, "Product not found"

            if not product.is_active:
                return False, "Product is not active"

            if product.stock_quantity < requested_quantity:
                return (
                    False,
                    f"Insufficient stock. Available: {product.stock_quantity}, Requested: {requested_quantity}",
                )

            return True, "Product is available"

        except Exception as e:
            logger.error(f"Failed to check product availability for {product_id}: {e}")
            return False, str(e)

    def get_featured_products(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get featured products (could be based on sales, ratings, etc.)."""
        try:
            from products.models import Product

            # For now, get recently created products
            # This could be enhanced with sales data, ratings, etc.
            featured_products = Product.objects.filter(is_active=True, stock_quantity__gt=0).order_by("-created_at")[
                :limit
            ]

            return [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "description": p.description,
                    "price": float(p.price),
                    "currency": p.currency,
                    "category": p.category,
                    "vendor_id": str(p.vendor_id),
                    "created_at": p.created_at.isoformat(),
                }
                for p in featured_products
            ]

        except Exception as e:
            logger.error(f"Failed to get featured products: {e}")
            return []

    def get_products_by_category(self, category: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get products by category."""
        try:
            from products.models import Product

            products = Product.objects.filter(category=category, is_active=True).order_by("-created_at")[:limit]

            return [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "description": p.description,
                    "price": float(p.price),
                    "currency": p.currency,
                    "category": p.category,
                    "stock_quantity": p.stock_quantity,
                    "vendor_id": str(p.vendor_id),
                    "created_at": p.created_at.isoformat(),
                }
                for p in products
            ]

        except Exception as e:
            logger.error(f"Failed to get products by category {category}: {e}")
            return []

    def get_vendor_product_summary(self, vendor_id: str) -> Dict[str, Any]:
        """Get summary of vendor's products."""
        try:
            from products.models import Product

            products = Product.objects.filter(vendor_id=vendor_id)

            total_products = products.count()
            active_products = products.filter(is_active=True).count()
            out_of_stock = products.filter(stock_quantity=0).count()

            # Calculate total value
            total_value = sum(p.price * p.stock_quantity for p in products)

            # Get category distribution
            categories = {}
            for product in products:
                cat = product.category
                if cat not in categories:
                    categories[cat] = 0
                categories[cat] += 1

            return {
                "vendor_id": vendor_id,
                "total_products": total_products,
                "active_products": active_products,
                "out_of_stock": out_of_stock,
                "total_value": float(total_value),
                "category_distribution": categories,
                "recent_products": self._get_recent_products(vendor_id, 5),
            }

        except Exception as e:
            logger.error(f"Failed to get vendor product summary for {vendor_id}: {e}")
            return {}

    def _get_recent_products(self, vendor_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent products for a vendor."""
        try:
            from products.models import Product

            recent_products = Product.objects.filter(vendor_id=vendor_id).order_by("-created_at")[:limit]

            return [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "price": float(p.price),
                    "currency": p.currency,
                    "category": p.category,
                    "stock_quantity": p.stock_quantity,
                    "created_at": p.created_at.isoformat(),
                }
                for p in recent_products
            ]

        except Exception as e:
            logger.error(f"Failed to get recent products for vendor {vendor_id}: {e}")
            return []

    def get_service_health(self) -> Dict[str, Any]:
        """Get service health status."""
        try:
            from products.models import Product

            total_products = Product.objects.count()
            active_products = Product.objects.filter(is_active=True).count()
            out_of_stock = Product.objects.filter(stock_quantity=0).count()

            return {
                "total_products": total_products,
                "active_products": active_products,
                "out_of_stock": out_of_stock,
                "product_cache_size": len(self._product_cache),
                "category_cache_size": len(self._category_cache),
            }
        except Exception as e:
            logger.error(f"Failed to get service health: {e}")
            return {"error": str(e)}
