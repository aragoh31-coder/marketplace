"""
User Service
Handles all user-related business logic and operations.
"""

import logging
import secrets
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import models, transaction
from django.utils import timezone

from .base_service import BaseService

logger = logging.getLogger(__name__)
User = get_user_model()


class UserService(BaseService):
    """Service for managing users and authentication."""

    service_name = "user_service"
    version = "1.0.0"
    description = "User management and authentication service"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._user_cache = {}
        self._failed_login_cache = {}

    def initialize(self) -> bool:
        """Initialize the user service."""
        try:
            # Set up any connections or validate configuration
            logger.info("User service initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize user service: {e}")
            return False

    def cleanup(self) -> bool:
        """Clean up the user service."""
        try:
            # Clear caches
            self._user_cache.clear()
            self._failed_login_cache.clear()
            logger.info("User service cleaned up successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup user service: {e}")
            return False

    def get_required_config(self) -> List[str]:
        """Get required configuration keys."""
        return ["max_login_attempts", "lockout_duration"]

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID with caching."""
        cache_key = f"user:{user_id}"

        # Try cache first
        cached_user = self.get_cached(cache_key)
        if cached_user:
            return cached_user

        try:
            user = User.objects.get(id=user_id)
            # Cache user for 5 minutes
            self.set_cached(cache_key, user, timeout=300)
            return user
        except User.DoesNotExist:
            return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username with caching."""
        cache_key = f"user:username:{username}"

        # Try cache first
        cached_user = self.get_cached(cache_key)
        if cached_user:
            return cached_user

        try:
            user = User.objects.get(username=username)
            # Cache user for 5 minutes
            self.set_cached(cache_key, user, timeout=300)
            return user
        except User.DoesNotExist:
            return None

    def get_user_by_pgp_fingerprint(self, fingerprint: str) -> Optional[User]:
        """Get user by PGP fingerprint."""
        try:
            return User.objects.get(pgp_fingerprint=fingerprint)
        except User.DoesNotExist:
            return None

    def create_user(self, username: str, email: str, password: str, **kwargs) -> Tuple[User, bool]:
        """Create a new user with validation."""
        try:
            with transaction.atomic():
                # Check if username or email already exists
                if User.objects.filter(username=username).exists():
                    return None, False, "Username already exists"

                if User.objects.filter(email=email).exists():
                    return None, False, "Email already exists"

                # Create user
                user = User.objects.create_user(username=username, email=email, password=password, **kwargs)

                # Clear related caches
                self.clear_cache(f"user:{user.id}")
                self.clear_cache(f"user:username:{username}")

                logger.info(f"User created successfully: {username}")
                return user, True, "User created successfully"

        except Exception as e:
            logger.error(f"Failed to create user {username}: {e}")
            return None, False, str(e)

    def update_user(self, user_id: str, **kwargs) -> Tuple[User, bool, str]:
        """Update user information."""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return None, False, "User not found"

            with transaction.atomic():
                # Update fields
                for field, value in kwargs.items():
                    if hasattr(user, field):
                        setattr(user, field, value)

                user.save()

                # Clear caches
                self.clear_cache(f"user:{user_id}")
                self.clear_cache(f"user:username:{user.username}")

                logger.info(f"User updated successfully: {user.username}")
                return user, True, "User updated successfully"

        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {e}")
            return None, False, str(e)

    def delete_user(self, user_id: str) -> Tuple[bool, str]:
        """Delete a user account."""
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False, "User not found"

            with transaction.atomic():
                username = user.username
                user.delete()

                # Clear caches
                self.clear_cache(f"user:{user_id}")
                self.clear_cache(f"user:username:{username}")

                logger.info(f"User deleted successfully: {username}")
                return True, "User deleted successfully"

        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            return False, str(e)

    def authenticate_user(
        self, username: str, password: str, ip_address: str = None
    ) -> Tuple[Optional[User], bool, str]:
        """Authenticate user with password."""
        try:
            user = self.get_user_by_username(username)
            if not user:
                return None, False, "Invalid credentials"

            # Check if user is locked out
            if self.is_user_locked_out(username):
                return None, False, "Account temporarily locked due to too many failed attempts"

            # Check if user is active
            if not user.is_active:
                return None, False, "Account is disabled"

            # Verify password
            if user.check_password(password):
                # Reset failed login attempts
                self.reset_failed_login_attempts(username)

                # Log successful login
                self.log_login_attempt(user, ip_address, True)

                logger.info(f"User authenticated successfully: {username}")
                return user, True, "Authentication successful"
            else:
                # Increment failed login attempts
                self.increment_failed_login_attempts(username)

                # Log failed login
                self.log_login_attempt(user, ip_address, False)

                return None, False, "Invalid credentials"

        except Exception as e:
            logger.error(f"Authentication failed for {username}: {e}")
            return None, False, "Authentication failed"

    def authenticate_with_pgp(self, fingerprint: str, challenge_response: str) -> Tuple[Optional[User], bool, str]:
        """Authenticate user with PGP challenge."""
        try:
            user = self.get_user_by_pgp_fingerprint(fingerprint)
            if not user:
                return None, False, "Invalid PGP fingerprint"

            # Check if PGP login is enabled
            if not user.pgp_login_enabled:
                return None, False, "PGP login is not enabled for this account"

            # Verify challenge response
            if user.verify_pgp_challenge(challenge_response):
                # Log successful login
                self.log_login_attempt(user, None, True, method="PGP")

                logger.info(f"User authenticated with PGP: {user.username}")
                return user, True, "PGP authentication successful"
            else:
                return None, False, "Invalid PGP challenge response"

        except Exception as e:
            logger.error(f"PGP authentication failed for fingerprint {fingerprint}: {e}")
            return None, False, "PGP authentication failed"

    def generate_pgp_challenge(self, username: str) -> Tuple[bool, str, str]:
        """Generate PGP challenge for user."""
        try:
            user = self.get_user_by_username(username)
            if not user:
                return False, "", "User not found"

            if not user.pgp_login_enabled:
                return False, "", "PGP login is not enabled for this account"

            # Generate challenge
            challenge = user.generate_pgp_challenge()

            logger.info(f"PGP challenge generated for user: {username}")
            return True, challenge, "PGP challenge generated successfully"

        except Exception as e:
            logger.error(f"Failed to generate PGP challenge for {username}: {e}")
            return False, "", str(e)

    def is_user_locked_out(self, username: str) -> bool:
        """Check if user is locked out due to failed login attempts."""
        cache_key = f"failed_login:{username}"
        failed_attempts = self._failed_login_cache.get(username, 0)

        if failed_attempts >= self.get_config("max_login_attempts", 5):
            # Check if lockout period has expired
            lockout_key = f"lockout:{username}"
            lockout_time = cache.get(lockout_key)

            if lockout_time and timezone.now() < lockout_time:
                return True
            else:
                # Reset failed attempts if lockout expired
                self.reset_failed_login_attempts(username)
                return False

        return False

    def increment_failed_login_attempts(self, username: str) -> None:
        """Increment failed login attempts for user."""
        current_attempts = self._failed_login_cache.get(username, 0) + 1
        self._failed_login_cache[username] = current_attempts

        # If max attempts reached, lock out user
        if current_attempts >= self.get_config("max_login_attempts", 5):
            lockout_duration = self.get_config("lockout_duration", 300)  # 5 minutes
            lockout_until = timezone.now() + timedelta(seconds=lockout_duration)

            cache_key = f"lockout:{username}"
            cache.set(cache_key, lockout_until, timeout=lockout_duration)

            logger.warning(f"User {username} locked out due to failed login attempts")

    def reset_failed_login_attempts(self, username: str) -> None:
        """Reset failed login attempts for user."""
        self._failed_login_cache.pop(username, None)
        cache.delete(f"lockout:{username}")

    def log_login_attempt(
        self, user: User, ip_address: str = None, success: bool = True, method: str = "password"
    ) -> None:
        """Log login attempt for audit purposes."""
        try:
            from accounts.models import LoginHistory

            LoginHistory.objects.create(
                user=user,
                ip_hash=self._hash_ip(ip_address) if ip_address else "",
                user_agent="",  # Could be extracted from request
                success=success,
            )

        except Exception as e:
            logger.error(f"Failed to log login attempt: {e}")

    def _hash_ip(self, ip_address: str) -> str:
        """Hash IP address for privacy."""
        import hashlib

        return hashlib.sha256(ip_address.encode()).hexdigest()

    def get_user_trust_level(self, user_id: str) -> str:
        """Get user trust level based on trades and feedback."""
        user = self.get_user_by_id(user_id)
        if not user:
            return "Unknown"

        return user.get_trust_level()

    def update_user_activity(self, user_id: str) -> bool:
        """Update user's last activity timestamp."""
        try:
            user = self.get_user_by_id(user_id)
            if user:
                user.last_activity = timezone.now()
                user.save(update_fields=["last_activity"])
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update user activity for {user_id}: {e}")
            return False

    def get_user_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user statistics."""
        user = self.get_user_by_id(user_id)
        if not user:
            return {}

        return {
            "username": user.username,
            "trust_level": self.get_user_trust_level(user_id),
            "feedback_score": user.feedback_score,
            "total_trades": user.total_trades,
            "positive_feedback_count": user.positive_feedback_count,
            "account_created": user.account_created,
            "last_activity": user.last_activity,
            "is_vendor": user.is_vendor,
            "default_currency": user.default_currency,
        }

    def search_users(self, query: str, limit: int = 20) -> List[User]:
        """Search users by username or email."""
        try:
            users = User.objects.filter(models.Q(username__icontains=query) | models.Q(email__icontains=query))[:limit]

            return list(users)
        except Exception as e:
            logger.error(f"User search failed: {e}")
            return []

    def get_online_users(self, minutes: int = 15) -> List[User]:
        """Get users who were active in the last N minutes."""
        try:
            cutoff_time = timezone.now() - timedelta(minutes=minutes)
            users = User.objects.filter(last_activity__gte=cutoff_time, is_active=True)

            return list(users)
        except Exception as e:
            logger.error(f"Failed to get online users: {e}")
            return []

    def get_service_health(self) -> Dict[str, Any]:
        """Get service health status."""
        try:
            total_users = User.objects.count()
            active_users = User.objects.filter(is_active=True).count()

            return {
                "total_users": total_users,
                "active_users": active_users,
                "user_cache_size": len(self._user_cache),
                "failed_login_cache_size": len(self._failed_login_cache),
            }
        except Exception as e:
            logger.error(f"Failed to get service health: {e}")
            return {"error": str(e)}
