"""
Vendor Service
Handles all vendor-related business logic and operations.
"""

from typing import Dict, List, Any, Optional, Tuple
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache
from .base_service import BaseService
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)
User = get_user_model()


class VendorService(BaseService):
    """Service for managing vendors and vendor operations."""
    
    service_name = "vendor_service"
    version = "1.0.0"
    description = "Vendor management and operations service"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._vendor_cache = {}
        self._rating_cache = {}
    
    def initialize(self) -> bool:
        """Initialize the vendor service."""
        try:
            # Set up any connections or validate configuration
            logger.info("Vendor service initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize vendor service: {e}")
            return False
    
    def cleanup(self) -> bool:
        """Clean up the vendor service."""
        try:
            # Clear caches
            self._vendor_cache.clear()
            self._rating_cache.clear()
            logger.info("Vendor service cleaned up successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup vendor service: {e}")
            return False
    
    def get_required_config(self) -> List[str]:
        """Get required configuration keys."""
        return ['min_bond_amount', 'approval_threshold']
    
    def get_vendor_by_user(self, user_id: str) -> Optional[Any]:
        """Get vendor profile for a specific user with caching."""
        cache_key = f"vendor:{user_id}"
        
        # Try cache first
        cached_vendor = self.get_cached(cache_key)
        if cached_vendor:
            return cached_vendor
        
        try:
            from vendors.models import Vendor
            vendor = Vendor.objects.get(user_id=user_id)
            
            # Cache vendor for 5 minutes
            self.set_cached(cache_key, vendor, timeout=300)
            return vendor
            
        except Exception as e:
            logger.error(f"Failed to get vendor for user {user_id}: {e}")
            return None
    
    def get_vendor_by_name(self, vendor_name: str) -> Optional[Any]:
        """Get vendor by vendor name."""
        try:
            from vendors.models import Vendor
            return Vendor.objects.get(vendor_name=vendor_name)
        except Exception as e:
            logger.error(f"Failed to get vendor by name {vendor_name}: {e}")
            return None
    
    def create_vendor_profile(self, user_id: str, vendor_name: str, description: str = "", 
                            **kwargs) -> Tuple[Any, bool, str]:
        """Create a new vendor profile."""
        try:
            from vendors.models import Vendor
            
            with transaction.atomic():
                # Check if vendor name already exists
                if Vendor.objects.filter(vendor_name=vendor_name).exists():
                    return None, False, "Vendor name already exists"
                
                # Check if user already has a vendor profile
                if Vendor.objects.filter(user_id=user_id).exists():
                    return None, False, "User already has a vendor profile"
                
                # Create vendor profile
                vendor = Vendor.objects.create(
                    user_id=user_id,
                    vendor_name=vendor_name,
                    description=description,
                    **kwargs
                )
                
                # Clear cache
                self.clear_cache(f"vendor:{user_id}")
                
                logger.info(f"Vendor profile created successfully for user {user_id}: {vendor_name}")
                return vendor, True, "Vendor profile created successfully"
                
        except Exception as e:
            logger.error(f"Failed to create vendor profile for user {user_id}: {e}")
            return None, False, str(e)
    
    def update_vendor_profile(self, user_id: str, **kwargs) -> Tuple[Any, bool, str]:
        """Update vendor profile information."""
        try:
            vendor = self.get_vendor_by_user(user_id)
            if not vendor:
                return None, False, "Vendor profile not found"
            
            with transaction.atomic():
                # Update fields
                for field, value in kwargs.items():
                    if hasattr(vendor, field):
                        setattr(vendor, field, value)
                
                vendor.save()
                
                # Clear cache
                self.clear_cache(f"vendor:{user_id}")
                
                logger.info(f"Vendor profile updated successfully for user {user_id}")
                return vendor, True, "Vendor profile updated successfully"
                
        except Exception as e:
            logger.error(f"Failed to update vendor profile for user {user_id}: {e}")
            return None, False, str(e)
    
    def delete_vendor_profile(self, user_id: str) -> Tuple[bool, str]:
        """Delete a vendor profile."""
        try:
            vendor = self.get_vendor_by_user(user_id)
            if not vendor:
                return False, "Vendor profile not found"
            
            with transaction.atomic():
                vendor_name = vendor.vendor_name
                vendor.delete()
                
                # Clear cache
                self.clear_cache(f"vendor:{user_id}")
                
                logger.info(f"Vendor profile deleted successfully for user {user_id}: {vendor_name}")
                return True, "Vendor profile deleted successfully"
                
        except Exception as e:
            logger.error(f"Failed to delete vendor profile for user {user_id}: {e}")
            return False, str(e)
    
    def approve_vendor(self, user_id: str, admin_user_id: str) -> Tuple[bool, str]:
        """Approve a vendor profile."""
        try:
            vendor = self.get_vendor_by_user(user_id)
            if not vendor:
                return False, "Vendor profile not found"
            
            if vendor.is_approved:
                return False, "Vendor is already approved"
            
            with transaction.atomic():
                vendor.is_approved = True
                vendor.save()
                
                # Log approval
                self._log_vendor_action(user_id, "approved", admin_user_id)
                
                # Clear cache
                self.clear_cache(f"vendor:{user_id}")
                
                logger.info(f"Vendor approved successfully: {vendor.vendor_name}")
                return True, "Vendor approved successfully"
                
        except Exception as e:
            logger.error(f"Failed to approve vendor {user_id}: {e}")
            return False, str(e)
    
    def suspend_vendor(self, user_id: str, admin_user_id: str, reason: str = "") -> Tuple[bool, str]:
        """Suspend a vendor profile."""
        try:
            vendor = self.get_vendor_by_user(user_id)
            if not vendor:
                return False, "Vendor profile not found"
            
            if not vendor.is_active:
                return False, "Vendor is already suspended"
            
            with transaction.atomic():
                vendor.is_active = False
                vendor.save()
                
                # Log suspension
                self._log_vendor_action(user_id, "suspended", admin_user_id, reason)
                
                # Clear cache
                self.clear_cache(f"vendor:{user_id}")
                
                logger.info(f"Vendor suspended: {vendor.vendor_name}, Reason: {reason}")
                return True, "Vendor suspended successfully"
                
        except Exception as e:
            logger.error(f"Failed to suspend vendor {user_id}: {e}")
            return False, str(e)
    
    def activate_vendor(self, user_id: str, admin_user_id: str) -> Tuple[bool, str]:
        """Activate a suspended vendor profile."""
        try:
            vendor = self.get_vendor_by_user(user_id)
            if not vendor:
                return False, "Vendor profile not found"
            
            if vendor.is_active:
                return False, "Vendor is already active"
            
            with transaction.atomic():
                vendor.is_active = True
                vendor.save()
                
                # Log activation
                self._log_vendor_action(user_id, "activated", admin_user_id)
                
                # Clear cache
                self.clear_cache(f"vendor:{user_id}")
                
                logger.info(f"Vendor activated: {vendor.vendor_name}")
                return True, "Vendor activated successfully"
                
        except Exception as e:
            logger.error(f"Failed to activate vendor {user_id}: {e}")
            return False, str(e)
    
    def update_vendor_rating(self, vendor_user_id: str, user_id: str, rating: int, 
                           comment: str = "") -> Tuple[bool, str]:
        """Update vendor rating and comment."""
        try:
            if not 1 <= rating <= 5:
                return False, "Rating must be between 1 and 5"
            
            vendor = self.get_vendor_by_user(vendor_user_id)
            if not vendor:
                return False, "Vendor not found"
            
            with transaction.atomic():
                from vendors.models import VendorRating
                
                # Update or create rating
                rating_obj, created = VendorRating.objects.update_or_create(
                    vendor=vendor,
                    user_id=user_id,
                    defaults={
                        'rating': rating,
                        'comment': comment
                    }
                )
                
                # Recalculate vendor's average rating
                self._recalculate_vendor_rating(vendor)
                
                # Clear caches
                self.clear_cache(f"vendor:{vendor_user_id}")
                self.clear_cache(f"rating:{vendor_user_id}")
                
                action = "created" if created else "updated"
                logger.info(f"Vendor rating {action} for {vendor.vendor_name}: {rating}/5")
                return True, f"Rating {action} successfully"
                
        except Exception as e:
            logger.error(f"Failed to update vendor rating: {e}")
            return False, str(e)
    
    def _recalculate_vendor_rating(self, vendor: Any) -> None:
        """Recalculate vendor's average rating."""
        try:
            from vendors.models import VendorRating
            
            ratings = VendorRating.objects.filter(vendor=vendor)
            if ratings.exists():
                avg_rating = sum(r.rating for r in ratings) / ratings.count()
                vendor.rating = round(avg_rating, 2)
                vendor.save(update_fields=['rating'])
            
        except Exception as e:
            logger.error(f"Failed to recalculate vendor rating: {e}")
    
    def get_vendor_ratings(self, vendor_user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get ratings for a specific vendor."""
        try:
            from vendors.models import VendorRating
            
            ratings = VendorRating.objects.filter(
                vendor__user_id=vendor_user_id
            ).select_related('user').order_by('-id')[:limit]
            
            return [
                {
                    'id': str(r.id),
                    'rating': r.rating,
                    'comment': r.comment,
                    'user_username': r.user.username,
                    'created_at': r.created_at.isoformat() if hasattr(r, 'created_at') else None
                }
                for r in ratings
            ]
            
        except Exception as e:
            logger.error(f"Failed to get vendor ratings for {vendor_user_id}: {e}")
            return []
    
    def search_vendors(self, query: str = "", trust_level: str = None, 
                      is_approved: bool = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Search vendors with filters."""
        try:
            from vendors.models import Vendor
            
            queryset = Vendor.objects.all()
            
            # Apply filters
            if query:
                queryset = queryset.filter(
                    models.Q(vendor_name__icontains=query) |
                    models.Q(description__icontains=query)
                )
            
            if trust_level:
                queryset = queryset.filter(trust_level=trust_level)
            
            if is_approved is not None:
                queryset = queryset.filter(is_approved=is_approved)
            
            # Only show active vendors
            queryset = queryset.filter(is_active=True)
            
            # Order by rating and total sales
            vendors = queryset.order_by('-rating', '-total_sales')[:limit]
            
            return [
                {
                    'id': str(v.id),
                    'vendor_name': v.vendor_name,
                    'description': v.description,
                    'trust_level': v.trust_level,
                    'rating': float(v.rating),
                    'total_sales': float(v.total_sales),
                    'is_approved': v.is_approved,
                    'is_active': v.is_active,
                    'vacation_mode': v.is_on_vacation,
                    'response_time': str(v.response_time) if v.response_time else None,
                    'user_id': str(v.user_id)
                }
                for v in vendors
            ]
            
        except Exception as e:
            logger.error(f"Vendor search failed: {e}")
            return []
    
    def get_top_vendors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top-rated vendors."""
        try:
            from vendors.models import Vendor
            
            vendors = Vendor.objects.filter(
                is_approved=True,
                is_active=True
            ).order_by('-rating', '-total_sales')[:limit]
            
            return [
                {
                    'id': str(v.id),
                    'vendor_name': v.vendor_name,
                    'rating': float(v.rating),
                    'total_sales': float(v.total_sales),
                    'trust_level': v.trust_level,
                    'response_time': str(v.response_time) if v.response_time else None
                }
                for v in vendors
            ]
            
        except Exception as e:
            logger.error(f"Failed to get top vendors: {e}")
            return []
    
    def activate_vacation_mode(self, user_id: str, message: str = "", ends_at: str = None) -> Tuple[bool, str]:
        """Activate vacation mode for a vendor."""
        try:
            vendor = self.get_vendor_by_user(user_id)
            if not vendor:
                return False, "Vendor profile not found"
            
            if vendor.vacation_mode:
                return False, "Vacation mode is already active"
            
            with transaction.atomic():
                vendor.activate_vacation_mode(message, ends_at)
                
                # Clear cache
                self.clear_cache(f"vendor:{user_id}")
                
                logger.info(f"Vacation mode activated for vendor: {vendor.vendor_name}")
                return True, "Vacation mode activated successfully"
                
        except Exception as e:
            logger.error(f"Failed to activate vacation mode for vendor {user_id}: {e}")
            return False, str(e)
    
    def deactivate_vacation_mode(self, user_id: str) -> Tuple[bool, str]:
        """Deactivate vacation mode for a vendor."""
        try:
            vendor = self.get_vendor_by_user(user_id)
            if not vendor:
                return False, "Vendor profile not found"
            
            if not vendor.vacation_mode:
                return False, "Vacation mode is not active"
            
            with transaction.atomic():
                vendor.deactivate_vacation_mode()
                
                # Clear cache
                self.clear_cache(f"vendor:{user_id}")
                
                logger.info(f"Vacation mode deactivated for vendor: {vendor.vendor_name}")
                return True, "Vacation mode deactivated successfully"
                
        except Exception as e:
            logger.error(f"Failed to deactivate vacation mode for vendor {user_id}: {e}")
            return False, str(e)
    
    def update_vendor_trust_level(self, user_id: str, new_trust_level: str) -> Tuple[bool, str]:
        """Update vendor trust level."""
        try:
            vendor = self.get_vendor_by_user(user_id)
            if not vendor:
                return False, "Vendor profile not found"
            
            valid_levels = [choice[0] for choice in vendor.TRUST_LEVELS]
            if new_trust_level not in valid_levels:
                return False, f"Invalid trust level. Must be one of: {', '.join(valid_levels)}"
            
            with transaction.atomic():
                vendor.trust_level = new_trust_level
                vendor.save(update_fields=['trust_level'])
                
                # Clear cache
                self.clear_cache(f"vendor:{user_id}")
                
                logger.info(f"Trust level updated for vendor {vendor.vendor_name}: {new_trust_level}")
                return True, f"Trust level updated to {new_trust_level}"
                
        except Exception as e:
            logger.error(f"Failed to update trust level for vendor {user_id}: {e}")
            return False, str(e)
    
    def _log_vendor_action(self, vendor_user_id: str, action: str, admin_user_id: str, 
                          details: str = "") -> None:
        """Log vendor administrative actions."""
        try:
            from vendors.models import VendorActionLog
            
            VendorActionLog.objects.create(
                vendor_id=vendor_user_id,
                admin_user_id=admin_user_id,
                action=action,
                details=details,
                timestamp=timezone.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to log vendor action: {e}")
    
    def get_vendor_statistics(self, vendor_user_id: str) -> Dict[str, Any]:
        """Get comprehensive vendor statistics."""
        try:
            vendor = self.get_vendor_by_user(vendor_user_id)
            if not vendor:
                return {}
            
            # Get rating statistics
            ratings = self.get_vendor_ratings(vendor_user_id, limit=1000)
            rating_counts = {}
            for i in range(1, 6):
                rating_counts[str(i)] = len([r for r in ratings if r['rating'] == i])
            
            return {
                'vendor_name': vendor.vendor_name,
                'trust_level': vendor.trust_level,
                'rating': float(vendor.rating),
                'total_sales': float(vendor.total_sales),
                'is_approved': vendor.is_approved,
                'is_active': vendor.is_active,
                'vacation_mode': vendor.is_on_vacation,
                'response_time': str(vendor.response_time) if vendor.response_time else None,
                'bond_paid': vendor.bond_paid,
                'bond_amount': float(vendor.bond_amount) if vendor.bond_amount else 0,
                'bond_currency': vendor.bond_currency,
                'rating_distribution': rating_counts,
                'total_ratings': len(ratings),
                'low_stock_threshold': vendor.low_stock_threshold,
                'account_created': vendor.created_at.isoformat() if hasattr(vendor, 'created_at') else None,
                'last_updated': vendor.updated_at.isoformat() if hasattr(vendor, 'updated_at') else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get vendor statistics for {vendor_user_id}: {e}")
            return {}
    
    def get_service_health(self) -> Dict[str, Any]:
        """Get service health status."""
        try:
            from vendors.models import Vendor, VendorRating
            
            total_vendors = Vendor.objects.count()
            approved_vendors = Vendor.objects.filter(is_approved=True).count()
            active_vendors = Vendor.objects.filter(is_active=True).count()
            total_ratings = VendorRating.objects.count()
            
            return {
                'total_vendors': total_vendors,
                'approved_vendors': approved_vendors,
                'active_vendors': active_vendors,
                'total_ratings': total_ratings,
                'vendor_cache_size': len(self._vendor_cache),
                'rating_cache_size': len(self._rating_cache),
            }
        except Exception as e:
            logger.error(f"Failed to get service health: {e}")
            return {'error': str(e)}