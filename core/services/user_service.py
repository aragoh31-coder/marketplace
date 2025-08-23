"""
User Service
Handles all user-related business logic and operations.
"""

import logging
import secrets
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple
from functools import lru_cache

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import models, transaction
from django.db.models import Q, Prefetch, Count, F
from django.utils import timezone

from .base_service import BaseService, performance_monitor, cache_result

logger = logging.getLogger(__name__)
User = get_user_model()


class UserService(BaseService):
    """
    Service for managing user operations with optimized queries and caching.
    """

    service_name = "user_service"
    version = "2.0.0"
    description = "Optimized user management service"

    # Cache timeouts
    USER_CACHE_TIMEOUT = 300  # 5 minutes
    BULK_CACHE_TIMEOUT = 600  # 10 minutes
    STATS_CACHE_TIMEOUT = 1800  # 30 minutes

    def initialize(self) -> bool:
        """Initialize the user service."""
        try:
            # Warm up frequently accessed data
            self._warm_cache()
            return True
        except Exception as e:
            logger.error(f"Failed to initialize user service: {e}")
            return False

    def cleanup(self) -> bool:
        """Clean up the user service."""
        try:
            # Clear service-specific caches
            self.clear_cache()
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup user service: {e}")
            return False

    def get_required_config(self) -> List[str]:
        """Get required configuration keys."""
        return ["max_login_attempts", "lockout_duration"]

    def _warm_cache(self):
        """Warm up frequently accessed cache data."""
        try:
            # Cache user count
            self.get_user_count()
            # Cache active users count
            self.get_active_users_count()
        except Exception as e:
            logger.warning(f"Cache warming failed: {e}")

    @performance_monitor
    @cache_result(timeout=USER_CACHE_TIMEOUT, key_func=lambda user_id: user_id)
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID with optimized caching."""
        try:
            return User.objects.select_related().get(id=user_id)
        except User.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            return None

    @performance_monitor
    @cache_result(timeout=USER_CACHE_TIMEOUT, key_func=lambda username: f"username:{username}")
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username with optimized caching."""
        try:
            return User.objects.select_related().get(username=username)
        except User.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error fetching user by username {username}: {e}")
            return None

    @performance_monitor
    def get_users_by_ids(self, user_ids: List[str]) -> List[User]:
        """Bulk fetch users by IDs with optimized query."""
        if not user_ids:
            return []

        # Check cache first for individual users
        cached_users = {}
        uncached_ids = []
        
        for user_id in user_ids:
            cached_user = self.get_cached(f"user:{user_id}")
            if cached_user:
                cached_users[user_id] = cached_user
            else:
                uncached_ids.append(user_id)

        # Fetch uncached users in bulk
        db_users = []
        if uncached_ids:
            db_users = list(User.objects.filter(id__in=uncached_ids).select_related())
            
            # Cache the fetched users
            for user in db_users:
                self.set_cached(f"user:{user.id}", user, self.USER_CACHE_TIMEOUT)

        # Combine results
        all_users = list(cached_users.values()) + db_users
        return sorted(all_users, key=lambda u: user_ids.index(str(u.id)))

    @performance_monitor
    def get_user_by_pgp_fingerprint(self, fingerprint: str) -> Optional[User]:
        """Get user by PGP fingerprint."""
        cache_key = f"pgp:{fingerprint}"
        cached_user = self.get_cached(cache_key)
        if cached_user:
            return cached_user

        try:
            user = User.objects.select_related().get(pgp_fingerprint=fingerprint)
            self.set_cached(cache_key, user, self.USER_CACHE_TIMEOUT)
            return user
        except User.DoesNotExist:
            return None

    @performance_monitor
    def create_user(self, username: str, email: str, password: str, **kwargs) -> Tuple[User, bool, str]:
        """Create a new user with validation and optimized queries."""
        try:
            with transaction.atomic():
                # Check if username or email already exists in single query
                existing = User.objects.filter(
                    Q(username=username) | Q(email=email)
                ).values_list('username', 'email')
                
                existing_usernames = {u[0] for u in existing}
                existing_emails = {u[1] for u in existing}
                
                if username in existing_usernames:
                    return None, False, "Username already exists"
                
                if email in existing_emails:
                    return None, False, "Email already exists"

                # Create user
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    **kwargs
                )

                # Clear related caches
                self._invalidate_user_caches(user.id, username)

                # Invalidate count caches
                self.clear_cache("user_count")
                self.clear_cache("active_users_count")

                logger.info(f"User created successfully: {username}")
                return user, True, "User created successfully"

        except Exception as e:
            logger.error(f"Failed to create user {username}: {e}")
            return None, False, str(e)

    @performance_monitor
    def update_user(self, user_id: str, **kwargs) -> Tuple[User, bool, str]:
        """Update user information with cache invalidation."""
        try:
            with transaction.atomic():
                user = User.objects.select_for_update().get(id=user_id)
                
                # Track changed fields for cache invalidation
                changed_fields = []
                for field, value in kwargs.items():
                    if hasattr(user, field) and getattr(user, field) != value:
                        setattr(user, field, value)
                        changed_fields.append(field)

                if changed_fields:
                    user.save(update_fields=changed_fields)
                    
                    # Invalidate caches
                    self._invalidate_user_caches(user_id, user.username)

                    logger.info(f"User updated successfully: {user.username}, fields: {changed_fields}")
                    return user, True, "User updated successfully"
                else:
                    return user, True, "No changes detected"

        except User.DoesNotExist:
            return None, False, "User not found"
        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {e}")
            return None, False, str(e)

    @performance_monitor
    def delete_user(self, user_id: str) -> Tuple[bool, str]:
        """Delete user with cache cleanup."""
        try:
            with transaction.atomic():
                user = User.objects.get(id=user_id)
                username = user.username
                
                user.delete()
                
                # Clear caches
                self._invalidate_user_caches(user_id, username)
                self.clear_cache("user_count")
                self.clear_cache("active_users_count")

                logger.info(f"User deleted successfully: {username}")
                return True, "User deleted successfully"

        except User.DoesNotExist:
            return False, "User not found"
        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            return False, str(e)

    def _invalidate_user_caches(self, user_id: str, username: str):
        """Invalidate all caches related to a user."""
        cache_keys = [
            f"user:{user_id}",
            f"username:{username}",
            f"user_profile:{user_id}",
            f"user_stats:{user_id}"
        ]
        for key in cache_keys:
            self.clear_cache(key)

    @performance_monitor
    def authenticate_user(self, username: str, password: str) -> Tuple[Optional[User], bool, str]:
        """Authenticate user with rate limiting and optimized queries."""
        try:
            # Check if user is locked out
            lockout_key = f"lockout:{username}"
            if self.get_cached(lockout_key):
                return None, False, "Account temporarily locked due to too many failed attempts"

            # Get user with optimized query
            user = self.get_user_by_username(username)
            if not user:
                self._record_failed_attempt(username)
                return None, False, "Invalid username or password"

            # Check password
            if user.check_password(password):
                # Clear failed attempts on successful login
                self.clear_cache(f"failed_attempts:{username}")
                
                # Update last login timestamp
                user.last_login = timezone.now()
                user.save(update_fields=['last_login'])
                
                # Invalidate user cache to reflect login time update
                self._invalidate_user_caches(str(user.id), username)
                
                return user, True, "Authentication successful"
            else:
                self._record_failed_attempt(username)
                return None, False, "Invalid username or password"

        except Exception as e:
            logger.error(f"Authentication error for user {username}: {e}")
            return None, False, "Authentication failed"

    def _record_failed_attempt(self, username: str):
        """Record failed login attempt with rate limiting."""
        failed_attempts_key = f"failed_attempts:{username}"
        failed_attempts = self.get_cached(failed_attempts_key, 0)
        failed_attempts += 1
        
        max_attempts = self.get_config('max_login_attempts', 5)
        lockout_duration = self.get_config('lockout_duration', 900)  # 15 minutes
        
        self.set_cached(failed_attempts_key, failed_attempts, lockout_duration)
        
        if failed_attempts >= max_attempts:
            lockout_key = f"lockout:{username}"
            self.set_cached(lockout_key, True, lockout_duration)
            logger.warning(f"User {username} locked out after {failed_attempts} failed attempts")

    @performance_monitor
    @cache_result(timeout=STATS_CACHE_TIMEOUT)
    def get_user_count(self) -> int:
        """Get total user count with caching."""
        return User.objects.count()

    @performance_monitor
    @cache_result(timeout=STATS_CACHE_TIMEOUT)
    def get_active_users_count(self) -> int:
        """Get active users count (logged in within last 30 days)."""
        cutoff_date = timezone.now() - timedelta(days=30)
        return User.objects.filter(last_login__gte=cutoff_date).count()

    @performance_monitor
    def search_users(self, query: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Search users with optimized query and pagination."""
        if not query or len(query) < 2:
            return []

        cache_key = f"search:{query}:{limit}:{offset}"
        cached_result = self.get_cached(cache_key)
        if cached_result:
            return cached_result

        try:
            # Optimized search query
            users = User.objects.filter(
                Q(username__icontains=query) |
                Q(email__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query)
            ).select_related().values(
                'id', 'username', 'email', 'first_name', 'last_name',
                'date_joined', 'last_login', 'is_active'
            )[offset:offset + limit]

            result = list(users)
            self.set_cached(cache_key, result, 300)  # Cache for 5 minutes
            return result

        except Exception as e:
            logger.error(f"User search failed for query '{query}': {e}")
            return []

    @performance_monitor
    @cache_result(timeout=STATS_CACHE_TIMEOUT, key_func=lambda days: f"stats:{days}")
    def get_user_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get user statistics with optimized aggregation queries."""
        try:
            cutoff_date = timezone.now() - timedelta(days=days)
            
            # Single query with multiple aggregations
            stats = User.objects.aggregate(
                total_users=Count('id'),
                active_users=Count('id', filter=Q(last_login__gte=cutoff_date)),
                new_users=Count('id', filter=Q(date_joined__gte=cutoff_date)),
                inactive_users=Count('id', filter=Q(last_login__lt=cutoff_date) | Q(last_login__isnull=True))
            )

            # Add calculated fields
            stats['active_percentage'] = (
                (stats['active_users'] / stats['total_users'] * 100) 
                if stats['total_users'] > 0 else 0
            )
            
            return stats

        except Exception as e:
            logger.error(f"Failed to get user statistics: {e}")
            return {}

    @performance_monitor
    def bulk_update_users(self, updates: List[Dict[str, Any]]) -> Tuple[int, str]:
        """Bulk update users for better performance."""
        if not updates:
            return 0, "No updates provided"

        try:
            updated_count = 0
            
            with transaction.atomic():
                # Group updates by fields to optimize queries
                field_updates = {}
                for update in updates:
                    user_id = update.pop('id')
                    for field, value in update.items():
                        if field not in field_updates:
                            field_updates[field] = []
                        field_updates[field].append((user_id, value))

                # Execute bulk updates for each field
                for field, values in field_updates.items():
                    user_ids = [user_id for user_id, _ in values]
                    
                    # Use bulk_update for better performance
                    users_to_update = []
                    users = User.objects.filter(id__in=user_ids)
                    
                    for user in users:
                        for user_id, value in values:
                            if str(user.id) == str(user_id):
                                setattr(user, field, value)
                                users_to_update.append(user)
                                break

                    if users_to_update:
                        User.objects.bulk_update(users_to_update, [field])
                        updated_count += len(users_to_update)

                # Clear caches for updated users
                for update in updates:
                    if 'id' in update:
                        user = User.objects.get(id=update['id'])
                        self._invalidate_user_caches(str(user.id), user.username)

            return updated_count, f"Successfully updated {updated_count} users"

        except Exception as e:
            logger.error(f"Bulk update failed: {e}")
            return 0, str(e)

    def cleanup_expired_data(self) -> Dict[str, int]:
        """Clean up expired user-related data."""
        cleanup_stats = {
            'cleared_lockouts': 0,
            'cleared_failed_attempts': 0,
            'deleted_inactive_sessions': 0
        }

        try:
            # This would be implemented based on your specific cleanup needs
            # For now, just return empty stats
            pass

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

        return cleanup_stats

    @performance_monitor
    def get_user_activity_summary(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get user activity summary with caching."""
        cache_key = f"activity:{user_id}:{days}"
        cached_result = self.get_cached(cache_key)
        if cached_result:
            return cached_result

        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return {}

            cutoff_date = timezone.now() - timedelta(days=days)
            
            activity = {
                'user_id': user_id,
                'username': user.username,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'account_age_days': (timezone.now().date() - user.date_joined.date()).days,
                'is_active': user.last_login and user.last_login >= cutoff_date,
            }

            self.set_cached(cache_key, activity, 600)  # Cache for 10 minutes
            return activity

        except Exception as e:
            logger.error(f"Failed to get activity summary for user {user_id}: {e}")
            return {}

    def _health_check(self):
        """Enhanced health check for user service."""
        try:
            # Check database connectivity
            User.objects.count()
            
            # Check cache connectivity
            self.set_cached("health_check", True, 60)
            self.get_cached("health_check")
            
            self._healthy = True
        except Exception as e:
            logger.error(f"User service health check failed: {e}")
            self._healthy = False
