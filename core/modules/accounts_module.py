"""
Accounts Module
Modular implementation of account management functionality.
"""

from typing import Dict, List, Any, Optional, Type
from ..architecture.base import BaseModule
from ..architecture.decorators import module, provides_models, provides_views, provides_templates
from ..architecture.interfaces import ModelInterface, ViewInterface, TemplateInterface
from ..services.user_service import UserService
import logging
from django.db import transaction
import django.utils.timezone as timezone

logger = logging.getLogger(__name__)


@module(
    name="accounts",
    version="2.0.0",
    description="User account management and authentication module",
    author="Marketplace Team",
    dependencies=[],
    required_settings=["AUTH_USER_MODEL"]
)
@provides_templates("templates/accounts")
@provides_views(
    user_profile="accounts.views.UserProfileView",
    user_settings="accounts.views.UserSettingsView",
    pgp_management="accounts.views.PGPManagementView"
)
class AccountsModule(BaseModule, ModelInterface, ViewInterface, TemplateInterface):
    """
    Modular accounts system that provides user management capabilities.
    """
    
    def __init__(self, **kwargs):
        """Initialize the accounts module."""
        super().__init__(**kwargs)
        self.user_service = UserService(**kwargs)
        self._user_cache = {}
    
    def initialize(self) -> bool:
        """Initialize the accounts module."""
        try:
            # Initialize the user service
            if not self.user_service.initialize():
                logger.error("Failed to initialize user service")
                return False
            
            # Register template tags
            self._register_template_tags()
            
            # Set up signal handlers
            self._setup_signals()
            
            logger.info(f"Accounts module {self.name} initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize accounts module: {e}")
            return False
    
    def cleanup(self) -> bool:
        """Clean up the accounts module."""
        try:
            # Clean up user service
            self.user_service.cleanup()
            
            # Clear user cache
            self._user_cache.clear()
            
            # Clean up signal handlers
            self._cleanup_signals()
            
            logger.info(f"Accounts module {self.name} cleaned up successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup accounts module: {e}")
            return False
    
    def _register_template_tags(self):
        """Register template tags for the accounts module."""
        # Template tags are automatically loaded by Django
        pass
    
    def _setup_signals(self):
        """Set up signal handlers for the accounts module."""
        # Set up signals for user events
        pass
    
    def _cleanup_signals(self):
        """Clean up signal handlers."""
        # Disconnect signals
        pass
    
    def get_models(self) -> List[Type]:
        """Get models provided by this module."""
        try:
            from accounts.models import User, LoginHistory
            return [User, LoginHistory]
        except ImportError:
            return []
    
    def get_admin_models(self) -> Dict[str, Type]:
        """Get admin models for this module."""
        try:
            from accounts.admin import UserAdmin
            return {
                'user': UserAdmin
            }
        except ImportError:
            return {}
    
    def get_signals(self) -> List:
        """Get signals provided by this module."""
        return []
    
    def get_urls(self) -> List:
        """Get URL patterns for this module."""
        from django.urls import path
        from accounts.views import (
            UserProfileView, UserSettingsView, PGPManagementView,
            login_view, logout_view, register_view
        )
        
        return [
            path('accounts/login/', login_view, name='login'),
            path('accounts/logout/', logout_view, name='logout'),
            path('accounts/register/', register_view, name='register'),
            path('accounts/profile/', UserProfileView.as_view(), name='user_profile'),
            path('accounts/settings/', UserSettingsView.as_view(), name='user_settings'),
            path('accounts/pgp/', PGPManagementView.as_view(), name='pgp_management'),
        ]
    
    def get_views(self) -> Dict[str, Type]:
        """Get views provided by this module."""
        try:
            from accounts.views import (
                UserProfileView, UserSettingsView, PGPManagementView,
                login_view, logout_view, register_view
            )
            
            return {
                'user_profile': UserProfileView,
                'user_settings': UserSettingsView,
                'pgp_management': PGPManagementView,
                'login': login_view,
                'logout': logout_view,
                'register': register_view,
            }
        except ImportError:
            return {}
    
    def get_permissions(self) -> Dict[str, List[str]]:
        """Get permissions required by this module."""
        return {
            'user_profile': ['accounts.view_user'],
            'user_settings': ['accounts.change_user'],
            'pgp_management': ['accounts.change_user'],
        }
    
    def get_template_dirs(self) -> List[str]:
        """Get template directories for this module."""
        return ["templates/accounts"]
    
    def get_context_processors(self) -> List[str]:
        """Get context processors for this module."""
        return []
    
    def get_template_tags(self) -> List[str]:
        """Get template tags for this module."""
        return []
    
    # Module-specific functionality using the user service
    def authenticate_user(self, username: str, password: str, ip_address: str = None) -> tuple:
        """Authenticate a user using the user service."""
        return self.user_service.authenticate_user(username, password, ip_address)
    
    def create_user_account(self, username: str, email: str, password: str, **kwargs) -> tuple:
        """Create a new user account using the user service."""
        return self.user_service.create_user(username, email, password, **kwargs)
    
    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile information."""
        return self.user_service.get_user_statistics(user_id)
    
    def update_user_profile(self, user_id: str, **kwargs) -> tuple:
        """Update user profile information."""
        return self.user_service.update_user(user_id, **kwargs)
    
    def get_user_trust_level(self, user_id: str) -> str:
        """Get user trust level."""
        return self.user_service.get_user_trust_level(user_id)
    
    def search_users(self, query: str, limit: int = 20) -> List[Any]:
        """Search users."""
        return self.user_service.search_users(query, limit)
    
    def get_online_users(self, minutes: int = 15) -> List[Any]:
        """Get online users."""
        return self.user_service.get_online_users(minutes)
    
    def get_module_health(self) -> Dict[str, Any]:
        """Get health status of this module."""
        return {
            'module_name': self.name,
            'version': self.version,
            'enabled': self.is_enabled(),
            'user_service_healthy': self.user_service.is_available(),
            'user_cache_size': len(self._user_cache),
            'last_activity': getattr(self, '_last_activity', None),
        }
    
    def get_module_metrics(self) -> Dict[str, Any]:
        """Get metrics for this module."""
        return {
            'user_authentications': getattr(self, '_auth_count', 0),
            'user_creations': getattr(self, '_creation_count', 0),
            'user_updates': getattr(self, '_update_count', 0),
            'failed_logins': getattr(self, '_failed_login_count', 0),
        }
    
    def validate_configuration(self) -> bool:
        """Validate module configuration."""
        try:
            # Check if user service is available
            if not self.user_service.is_available():
                logger.error("User service is not available")
                return False
            
            # Check if required models exist
            from django.apps import apps
            if not apps.is_installed('accounts'):
                logger.error("Accounts app is not installed")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    def get_configuration_schema(self) -> Dict[str, Any]:
        """Get configuration schema for this module."""
        return {
            'max_login_attempts': {
                'type': 'integer',
                'description': 'Maximum failed login attempts before lockout',
                'default': 5,
                'required': False
            },
            'lockout_duration': {
                'type': 'integer',
                'description': 'Account lockout duration in seconds',
                'default': 300,
                'required': False
            },
            'session_timeout': {
                'type': 'integer',
                'description': 'Session timeout in seconds',
                'default': 3600,
                'required': False
            }
        }
    
    def set_configuration(self, config: Dict[str, Any]) -> bool:
        """Set module configuration."""
        try:
            # Update user service configuration
            for key, value in config.items():
                if hasattr(self.user_service, key):
                    setattr(self.user_service, key, value)
                else:
                    logger.warning(f"Unknown configuration key: {key}")
            
            logger.info(f"Configuration updated for module {self.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update configuration for module {self.name}: {e}")
            return False
    
    def get_user_management_summary(self) -> Dict[str, Any]:
        """Get summary of user management operations."""
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            total_users = User.objects.count()
            active_users = User.objects.filter(is_active=True).count()
            vendor_users = User.objects.filter(is_vendor=True).count()
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'vendor_users': vendor_users,
                'user_service_health': self.user_service.get_health_status(),
                'recent_activity': self._get_recent_user_activity()
            }
            
        except Exception as e:
            logger.error(f"Failed to get user management summary: {e}")
            return {}
    
    def _get_recent_user_activity(self) -> List[Dict[str, Any]]:
        """Get recent user activity."""
        try:
            from django.contrib.auth import get_user_model
            from django.utils import timezone
            from datetime import timedelta
            
            User = get_user_model()
            cutoff_time = timezone.now() - timedelta(hours=24)
            
            recent_users = User.objects.filter(
                last_activity__gte=cutoff_time
            ).order_by('-last_activity')[:10]
            
            return [
                {
                    'username': user.username,
                    'last_activity': user.last_activity.isoformat(),
                    'is_vendor': user.is_vendor,
                    'trust_level': self.get_user_trust_level(str(user.id))
                }
                for user in recent_users
            ]
            
        except Exception as e:
            logger.error(f"Failed to get recent user activity: {e}")
            return []
    
    def perform_user_maintenance(self) -> Dict[str, Any]:
        """Perform user maintenance tasks."""
        try:
            results = {
                'cleaned_sessions': 0,
                'deactivated_inactive': 0,
                'updated_trust_levels': 0,
                'errors': []
            }
            
            # Clean up expired sessions
            try:
                from django.contrib.sessions.models import Session
                from django.utils import timezone
                
                expired_sessions = Session.objects.filter(
                    expire_date__lt=timezone.now()
                ).delete()
                results['cleaned_sessions'] = expired_sessions[0]
                
            except Exception as e:
                results['errors'].append(f"Session cleanup failed: {e}")
            
            # Update user trust levels
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                
                users = User.objects.all()
                for user in users:
                    try:
                        old_trust = getattr(user, '_cached_trust_level', None)
                        new_trust = self.get_user_trust_level(str(user.id))
                        
                        if old_trust != new_trust:
                            user._cached_trust_level = new_trust
                            results['updated_trust_levels'] += 1
                    except Exception as e:
                        results['errors'].append(f"Failed to update trust level for {user.username}: {e}")
                
            except Exception as e:
                results['errors'].append(f"Trust level update failed: {e}")
            
            logger.info(f"User maintenance completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"User maintenance failed: {e}")
            return {'error': str(e)}
    
    def export_user_data(self, user_id: str) -> Dict[str, Any]:
        """Export user data for GDPR compliance."""
        try:
            user = self.user_service.get_user_by_id(user_id)
            if not user:
                return {'error': 'User not found'}
            
            # Get user profile data
            profile_data = self.get_user_profile(user_id)
            
            # Get login history
            try:
                from accounts.models import LoginHistory
                login_history = LoginHistory.objects.filter(user=user).values(
                    'login_time', 'ip_hash', 'user_agent', 'success'
                )
            except Exception:
                login_history = []
            
            # Get wallet data if available
            wallet_data = {}
            try:
                from core.services.wallet_service import WalletService
                wallet_service = WalletService()
                wallet_data = wallet_service.get_wallet_summary(user_id)
            except Exception:
                pass
            
            return {
                'user_id': str(user.id),
                'username': user.username,
                'email': user.email,
                'profile': profile_data,
                'login_history': list(login_history),
                'wallet_data': wallet_data,
                'exported_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to export user data for {user_id}: {e}")
            return {'error': str(e)}
    
    def delete_user_data(self, user_id: str) -> Dict[str, Any]:
        """Delete user data for GDPR compliance."""
        try:
            user = self.user_service.get_user_by_id(user_id)
            if not user:
                return {'error': 'User not found'}
            
            with transaction.atomic():
                # Anonymize user data instead of complete deletion
                user.username = f"deleted_{user.id}"
                user.email = f"deleted_{user.id}@deleted.com"
                user.first_name = ""
                user.last_name = ""
                user.is_active = False
                user.save()
                
                # Clear sensitive fields
                user.pgp_public_key = ""
                user.pgp_fingerprint = ""
                user.pgp_login_enabled = False
                user.pgp_challenge = ""
                user.pgp_challenge_expires = None
                user.panic_password = ""
                user.session_fingerprints = {}
                user.save()
                
                logger.info(f"User data anonymized for GDPR compliance: {user_id}")
                return {'success': True, 'message': 'User data anonymized successfully'}
                
        except Exception as e:
            logger.error(f"Failed to delete user data for {user_id}: {e}")
            return {'error': str(e)}