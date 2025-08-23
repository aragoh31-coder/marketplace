"""
Wallets Module
Modular implementation of wallet management functionality.
"""

from typing import Dict, List, Any, Optional, Type
from ..architecture.base import BaseModule
from ..architecture.decorators import module, provides_models, provides_views, provides_templates
from ..architecture.interfaces import ModelInterface, ViewInterface, TemplateInterface
from ..services.wallet_service import WalletService
import logging

logger = logging.getLogger(__name__)


@module(
    name="wallets",
    version="2.0.0",
    description="Wallet management and financial operations module",
    author="Marketplace Team",
    dependencies=["accounts"],
    required_settings=["CACHES"]
)
@provides_templates("templates/wallets")
@provides_views(
    wallet_dashboard="wallets.views.WalletDashboardView",
    wallet_transactions="wallets.views.TransactionHistoryView",
    withdrawal_request="wallets.views.WithdrawalRequestView"
)
class WalletsModule(BaseModule, ModelInterface, ViewInterface, TemplateInterface):
    """
    Modular wallets system that provides financial management capabilities.
    """
    
    def __init__(self, **kwargs):
        """Initialize the wallets module."""
        super().__init__(**kwargs)
        self.wallet_service = WalletService(**kwargs)
        self._wallet_cache = {}
    
    def initialize(self) -> bool:
        """Initialize the wallets module."""
        try:
            # Initialize the wallet service
            if not self.wallet_service.initialize():
                logger.error("Failed to initialize wallet service")
                return False
            
            # Register template tags
            self._register_template_tags()
            
            # Set up signal handlers
            self._setup_signals()
            
            logger.info(f"Wallets module {self.name} initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize wallets module: {e}")
            return False
    
    def cleanup(self) -> bool:
        """Clean up the wallets module."""
        try:
            # Clean up wallet service
            self.wallet_service.cleanup()
            
            # Clear wallet cache
            self._wallet_cache.clear()
            
            # Clean up signal handlers
            self._cleanup_signals()
            
            logger.info(f"Wallets module {self.name} cleaned up successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup wallets module: {e}")
            return False
    
    def _register_template_tags(self):
        """Register template tags for the wallets module."""
        # Template tags are automatically loaded by Django
        pass
    
    def _setup_signals(self):
        """Set up signal handlers for the wallets module."""
        # Set up signals for wallet events
        pass
    
    def _cleanup_signals(self):
        """Clean up signal handlers."""
        # Disconnect signals
        pass
    
    def get_models(self) -> List[Type]:
        """Get models provided by this module."""
        try:
            from wallets.models import Wallet, WalletTransaction, WithdrawalRequest
            return [Wallet, WalletTransaction, WithdrawalRequest]
        except ImportError:
            return []
    
    def get_admin_models(self) -> Dict[str, Type]:
        """Get admin models for this module."""
        try:
            from wallets.admin import WalletAdmin, WalletTransactionAdmin, WithdrawalRequestAdmin
            return {
                'wallet': WalletAdmin,
                'wallet_transaction': WalletTransactionAdmin,
                'withdrawal_request': WithdrawalRequestAdmin
            }
        except ImportError:
            return {}
    
    def get_signals(self) -> List:
        """Get signals provided by this module."""
        return []
    
    def get_urls(self) -> List:
        """Get URL patterns for this module."""
        from django.urls import path
        from wallets.views import (
            WalletDashboardView, TransactionHistoryView, WithdrawalRequestView,
            deposit_view, transfer_view
        )
        
        return [
            path('wallets/dashboard/', WalletDashboardView.as_view(), name='wallet_dashboard'),
            path('wallets/transactions/', TransactionHistoryView.as_view(), name='wallet_transactions'),
            path('wallets/withdraw/', WithdrawalRequestView.as_view(), name='withdrawal_request'),
            path('wallets/deposit/', deposit_view, name='deposit'),
            path('wallets/transfer/', transfer_view, name='transfer'),
        ]
    
    def get_views(self) -> Dict[str, Type]:
        """Get views provided by this module."""
        try:
            from wallets.views import (
                WalletDashboardView, TransactionHistoryView, WithdrawalRequestView,
                deposit_view, transfer_view
            )
            
            return {
                'wallet_dashboard': WalletDashboardView,
                'wallet_transactions': TransactionHistoryView,
                'withdrawal_request': WithdrawalRequestView,
                'deposit': deposit_view,
                'transfer': transfer_view,
            }
        except ImportError:
            return {}
    
    def get_permissions(self) -> Dict[str, List[str]]:
        """Get permissions required by this module."""
        return {
            'wallet_dashboard': ['wallets.view_wallet'],
            'wallet_transactions': ['wallets.view_wallettransaction'],
            'withdrawal_request': ['wallets.add_withdrawalrequest'],
            'deposit': ['wallets.change_wallet'],
            'transfer': ['wallets.change_wallet'],
        }
    
    def get_template_dirs(self) -> List[str]:
        """Get template directories for this module."""
        return ["templates/wallets"]
    
    def get_context_processors(self) -> List[str]:
        """Get context processors for this module."""
        return []
    
    def get_template_tags(self) -> List[str]:
        """Get template tags for this module."""
        return []
    
    # Module-specific functionality using the wallet service
    def get_wallet_balance(self, user_id: str, currency: str) -> tuple:
        """Get user's wallet balance."""
        return self.wallet_service.get_balance(user_id, currency)
    
    def get_available_balance(self, user_id: str, currency: str) -> tuple:
        """Get user's available balance."""
        return self.wallet_service.get_available_balance(user_id, currency)
    
    def add_funds_to_wallet(self, user_id: str, currency: str, amount: float, source: str = "deposit") -> tuple:
        """Add funds to user's wallet."""
        from decimal import Decimal
        return self.wallet_service.add_funds(user_id, currency, Decimal(str(amount)), source)
    
    def deduct_funds_from_wallet(self, user_id: str, currency: str, amount: float, reason: str = "withdrawal") -> tuple:
        """Deduct funds from user's wallet."""
        from decimal import Decimal
        return self.wallet_service.deduct_funds(user_id, currency, Decimal(str(amount)), reason)
    
    def move_funds_to_escrow(self, user_id: str, currency: str, amount: float, order_id: str = None) -> tuple:
        """Move funds to escrow."""
        from decimal import Decimal
        return self.wallet_service.move_to_escrow(user_id, currency, Decimal(str(amount)), order_id)
    
    def release_funds_from_escrow(self, user_id: str, currency: str, amount: float, order_id: str = None) -> tuple:
        """Release funds from escrow."""
        from decimal import Decimal
        return self.wallet_service.release_from_escrow(user_id, currency, Decimal(str(amount)), order_id)
    
    def check_withdrawal_eligibility(self, user_id: str, currency: str, amount: float) -> tuple:
        """Check if user can withdraw the specified amount."""
        from decimal import Decimal
        return self.wallet_service.can_withdraw(user_id, currency, Decimal(str(amount)))
    
    def create_withdrawal_request(self, user_id: str, currency: str, amount: float, 
                                address: str, withdrawal_pin: str = None) -> tuple:
        """Create a withdrawal request."""
        from decimal import Decimal
        return self.wallet_service.create_withdrawal_request(user_id, currency, Decimal(str(amount)), address, withdrawal_pin)
    
    def get_transaction_history(self, user_id: str, currency: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get transaction history for a user."""
        return self.wallet_service.get_transaction_history(user_id, currency, limit)
    
    def get_wallet_summary(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive wallet summary for a user."""
        return self.wallet_service.get_wallet_summary(user_id)
    
    def get_module_health(self) -> Dict[str, Any]:
        """Get health status of this module."""
        return {
            'module_name': self.name,
            'version': self.version,
            'enabled': self.is_enabled(),
            'wallet_service_healthy': self.wallet_service.is_available(),
            'wallet_cache_size': len(self._wallet_cache),
            'last_activity': getattr(self, '_last_activity', None),
        }
    
    def get_module_metrics(self) -> Dict[str, Any]:
        """Get metrics for this module."""
        return {
            'fund_additions': getattr(self, '_fund_additions', 0),
            'fund_deductions': getattr(self, '_fund_deductions', 0),
            'escrow_operations': getattr(self, '_escrow_operations', 0),
            'withdrawal_requests': getattr(self, '_withdrawal_requests', 0),
            'failed_transactions': getattr(self, '_failed_transactions', 0),
        }
    
    def validate_configuration(self) -> bool:
        """Validate module configuration."""
        try:
            # Check if wallet service is available
            if not self.wallet_service.is_available():
                logger.error("Wallet service is not available")
                return False
            
            # Check if required models exist
            from django.apps import apps
            if not apps.is_installed('wallets'):
                logger.error("Wallets app is not installed")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    def get_configuration_schema(self) -> Dict[str, Any]:
        """Get configuration schema for this module."""
        return {
            'max_daily_withdrawal': {
                'type': 'decimal',
                'description': 'Maximum daily withdrawal amount',
                'default': '1000.00',
                'required': False
            },
            'withdrawal_cooldown': {
                'type': 'integer',
                'description': 'Withdrawal cooldown period in seconds',
                'default': 600,
                'required': False
            },
            'transaction_cache_timeout': {
                'type': 'integer',
                'description': 'Transaction cache timeout in seconds',
                'default': 300,
                'required': False
            }
        }
    
    def set_configuration(self, config: Dict[str, Any]) -> bool:
        """Set module configuration."""
        try:
            # Update wallet service configuration
            for key, value in config.items():
                if hasattr(self.wallet_service, key):
                    setattr(self.wallet_service, key, value)
                else:
                    logger.warning(f"Unknown configuration key: {key}")
            
            logger.info(f"Configuration updated for module {self.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update configuration for module {self.name}: {e}")
            return False
    
    def get_financial_summary(self) -> Dict[str, Any]:
        """Get summary of financial operations."""
        try:
            from wallets.models import Wallet, WalletTransaction
            
            total_wallets = Wallet.objects.count()
            total_transactions = WalletTransaction.objects.count()
            
            # Calculate total balances across all wallets
            total_btc = sum(w.balance_btc for w in Wallet.objects.all())
            total_xmr = sum(w.balance_xmr for w in Wallet.objects.all())
            total_escrow_btc = sum(w.escrow_btc for w in Wallet.objects.all())
            total_escrow_xmr = sum(w.escrow_xmr for w in Wallet.objects.all())
            
            return {
                'total_wallets': total_wallets,
                'total_transactions': total_transactions,
                'total_balances': {
                    'BTC': {
                        'total': float(total_btc),
                        'available': float(total_btc - total_escrow_btc),
                        'escrow': float(total_escrow_btc)
                    },
                    'XMR': {
                        'total': float(total_xmr),
                        'available': float(total_xmr - total_escrow_xmr),
                        'escrow': float(total_escrow_xmr)
                    }
                },
                'wallet_service_health': self.wallet_service.get_health_status(),
                'recent_transactions': self._get_recent_transactions()
            }
            
        except Exception as e:
            logger.error(f"Failed to get financial summary: {e}")
            return {}
    
    def _get_recent_transactions(self) -> List[Dict[str, Any]]:
        """Get recent transactions."""
        try:
            from wallets.models import WalletTransaction
            from django.utils import timezone
            from datetime import timedelta
            
            cutoff_time = timezone.now() - timedelta(hours=24)
            
            recent_transactions = WalletTransaction.objects.filter(
                timestamp__gte=cutoff_time
            ).order_by('-timestamp')[:20]
            
            return [
                {
                    'id': str(t.id),
                    'user_id': str(t.user_id),
                    'currency': t.currency,
                    'amount': float(t.amount),
                    'type': t.transaction_type,
                    'description': t.description,
                    'timestamp': t.timestamp.isoformat(),
                }
                for t in recent_transactions
            ]
            
        except Exception as e:
            logger.error(f"Failed to get recent transactions: {e}")
            return []
    
    def perform_financial_maintenance(self) -> Dict[str, Any]:
        """Perform financial maintenance tasks."""
        try:
            results = {
                'cleaned_transactions': 0,
                'recalculated_balances': 0,
                'processed_withdrawals': 0,
                'errors': []
            }
            
            # Clean up old transaction logs (keep last 90 days)
            try:
                from wallets.models import WalletTransaction
                from django.utils import timezone
                from datetime import timedelta
                
                cutoff_date = timezone.now() - timedelta(days=90)
                old_transactions = WalletTransaction.objects.filter(
                    timestamp__lt=cutoff_date
                ).delete()
                results['cleaned_transactions'] = old_transactions[0]
                
            except Exception as e:
                results['errors'].append(f"Transaction cleanup failed: {e}")
            
            # Process pending withdrawal requests
            try:
                from wallets.models import WithdrawalRequest
                
                pending_withdrawals = WithdrawalRequest.objects.filter(status='pending')
                for withdrawal in pending_withdrawals:
                    try:
                        # Process withdrawal logic here
                        # This would typically involve blockchain operations
                        results['processed_withdrawals'] += 1
                    except Exception as e:
                        results['errors'].append(f"Failed to process withdrawal {withdrawal.id}: {e}")
                
            except Exception as e:
                results['errors'].append(f"Withdrawal processing failed: {e}")
            
            logger.info(f"Financial maintenance completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Financial maintenance failed: {e}")
            return {'error': str(e)}
    
    def generate_financial_report(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Generate financial report for a date range."""
        try:
            from wallets.models import WalletTransaction
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
            
            # Get transactions in date range
            transactions = WalletTransaction.objects.filter(
                timestamp__date__range=[start_date, end_date]
            )
            
            # Calculate totals by currency and type
            report_data = {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'total_transactions': transactions.count(),
                'by_currency': {},
                'by_type': {},
                'daily_totals': {}
            }
            
            # Group by currency
            for currency in ['BTC', 'XMR']:
                currency_transactions = transactions.filter(currency=currency)
                report_data['by_currency'][currency] = {
                    'total_volume': float(sum(t.amount for t in currency_transactions)),
                    'transaction_count': currency_transactions.count(),
                    'credits': float(sum(t.amount for t in currency_transactions if t.transaction_type == 'credit')),
                    'debits': float(sum(t.amount for t in currency_transactions if t.transaction_type == 'debit')),
                    'escrow_operations': currency_transactions.filter(transaction_type__startswith='escrow').count()
                }
            
            # Group by transaction type
            for t_type in transactions.values_list('transaction_type', flat=True).distinct():
                type_transactions = transactions.filter(transaction_type=t_type)
                report_data['by_type'][t_type] = {
                    'count': type_transactions.count(),
                    'total_volume': float(sum(t.amount for t in type_transactions))
                }
            
            # Daily totals
            current_date = start_date
            while current_date <= end_date:
                daily_transactions = transactions.filter(timestamp__date=current_date)
                daily_volume = {
                    'BTC': float(sum(t.amount for t in daily_transactions if t.currency == 'BTC')),
                    'XMR': float(sum(t.amount for t in daily_transactions if t.currency == 'XMR')),
                    'count': daily_transactions.count()
                }
                report_data['daily_totals'][current_date.isoformat()] = daily_volume
                current_date += timedelta(days=1)
            
            return report_data
            
        except Exception as e:
            logger.error(f"Failed to generate financial report: {e}")
            return {'error': str(e)}
    
    def get_user_wallet_analytics(self, user_id: str) -> Dict[str, Any]:
        """Get analytics for a specific user's wallet."""
        try:
            # Get wallet summary
            wallet_summary = self.get_wallet_summary(user_id)
            if not wallet_summary:
                return {'error': 'Wallet not found'}
            
            # Get transaction history
            transactions = self.get_transaction_history(user_id, limit=1000)
            
            # Calculate analytics
            analytics = {
                'wallet_summary': wallet_summary,
                'transaction_analytics': {
                    'total_transactions': len(transactions),
                    'by_currency': {},
                    'by_type': {},
                    'monthly_activity': {},
                    'largest_transactions': []
                }
            }
            
            # Group by currency
            for currency in ['BTC', 'XMR']:
                currency_transactions = [t for t in transactions if t['currency'] == currency]
                analytics['transaction_analytics']['by_currency'][currency] = {
                    'count': len(currency_transactions),
                    'total_volume': sum(float(t['amount']) for t in currency_transactions),
                    'average_amount': sum(float(t['amount']) for t in currency_transactions) / len(currency_transactions) if currency_transactions else 0
                }
            
            # Group by transaction type
            for transaction in transactions:
                t_type = transaction['type']
                if t_type not in analytics['transaction_analytics']['by_type']:
                    analytics['transaction_analytics']['by_type'][t_type] = {
                        'count': 0,
                        'total_volume': 0
                    }
                
                analytics['transaction_analytics']['by_type'][t_type]['count'] += 1
                analytics['transaction_analytics']['by_type'][t_type]['total_volume'] += float(transaction['amount'])
            
            # Monthly activity
            for transaction in transactions:
                month = transaction['timestamp'][:7]  # YYYY-MM
                if month not in analytics['transaction_analytics']['monthly_activity']:
                    analytics['transaction_analytics']['monthly_activity'][month] = {
                        'count': 0,
                        'volume': {'BTC': 0, 'XMR': 0}
                    }
                
                analytics['transaction_analytics']['monthly_activity'][month]['count'] += 1
                analytics['transaction_analytics']['monthly_activity'][month]['volume'][transaction['currency']] += float(transaction['amount'])
            
            # Largest transactions
            sorted_transactions = sorted(transactions, key=lambda x: float(x['amount']), reverse=True)
            analytics['transaction_analytics']['largest_transactions'] = sorted_transactions[:10]
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get user wallet analytics for {user_id}: {e}")
            return {'error': str(e)}