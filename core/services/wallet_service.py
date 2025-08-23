"""
Wallet Service
Handles all wallet-related business logic and operations.
"""

from typing import Dict, List, Any, Optional, Tuple, Decimal
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache
from .base_service import BaseService
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)
User = get_user_model()


class WalletService(BaseService):
    """Service for managing wallets and financial operations."""
    
    service_name = "wallet_service"
    version = "1.0.0"
    description = "Wallet management and financial operations service"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._wallet_cache = {}
        self._transaction_cache = {}
    
    def initialize(self) -> bool:
        """Initialize the wallet service."""
        try:
            # Set up any connections or validate configuration
            logger.info("Wallet service initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize wallet service: {e}")
            return False
    
    def cleanup(self) -> bool:
        """Clean up the wallet service."""
        try:
            # Clear caches
            self._wallet_cache.clear()
            self._transaction_cache.clear()
            logger.info("Wallet service cleaned up successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup wallet service: {e}")
            return False
    
    def get_required_config(self) -> List[str]:
        """Get required configuration keys."""
        return ['max_daily_withdrawal', 'withdrawal_cooldown']
    
    def get_wallet_by_user(self, user_id: str) -> Optional[Any]:
        """Get wallet for a specific user with caching."""
        cache_key = f"wallet:{user_id}"
        
        # Try cache first
        cached_wallet = self.get_cached(cache_key)
        if cached_wallet:
            return cached_wallet
        
        try:
            from wallets.models import Wallet
            wallet = Wallet.objects.get(user_id=user_id)
            
            # Cache wallet for 2 minutes
            self.set_cached(cache_key, wallet, timeout=120)
            return wallet
            
        except Exception as e:
            logger.error(f"Failed to get wallet for user {user_id}: {e}")
            return None
    
    def create_wallet(self, user_id: str, **kwargs) -> Tuple[Any, bool, str]:
        """Create a new wallet for a user."""
        try:
            from wallets.models import Wallet
            
            with transaction.atomic():
                # Check if wallet already exists
                if Wallet.objects.filter(user_id=user_id).exists():
                    return None, False, "Wallet already exists for this user"
                
                # Create wallet
                wallet = Wallet.objects.create(user_id=user_id, **kwargs)
                
                # Clear cache
                self.clear_cache(f"wallet:{user_id}")
                
                logger.info(f"Wallet created successfully for user {user_id}")
                return wallet, True, "Wallet created successfully"
                
        except Exception as e:
            logger.error(f"Failed to create wallet for user {user_id}: {e}")
            return None, False, str(e)
    
    def get_balance(self, user_id: str, currency: str) -> Tuple[Decimal, str]:
        """Get user's balance for a specific currency."""
        try:
            wallet = self.get_wallet_by_user(user_id)
            if not wallet:
                return Decimal('0'), "Wallet not found"
            
            currency = currency.lower()
            if currency == 'btc':
                return wallet.balance_btc, "OK"
            elif currency == 'xmr':
                return wallet.balance_xmr, "OK"
            else:
                return Decimal('0'), f"Unsupported currency: {currency}"
                
        except Exception as e:
            logger.error(f"Failed to get balance for user {user_id}, currency {currency}: {e}")
            return Decimal('0'), str(e)
    
    def get_available_balance(self, user_id: str, currency: str) -> Tuple[Decimal, str]:
        """Get user's available balance (total - escrow) for a specific currency."""
        try:
            wallet = self.get_wallet_by_user(user_id)
            if not wallet:
                return Decimal('0'), "Wallet not found"
            
            currency = currency.lower()
            if currency == 'btc':
                available = wallet.balance_btc - wallet.escrow_btc
                return max(available, Decimal('0')), "OK"
            elif currency == 'xmr':
                available = wallet.balance_xmr - wallet.escrow_xmr
                return max(available, Decimal('0')), "OK"
            else:
                return Decimal('0'), f"Unsupported currency: {currency}"
                
        except Exception as e:
            logger.error(f"Failed to get available balance for user {user_id}, currency {currency}: {e}")
            return Decimal('0'), str(e)
    
    def add_funds(self, user_id: str, currency: str, amount: Decimal, source: str = "deposit") -> Tuple[bool, str]:
        """Add funds to user's wallet."""
        try:
            if amount <= 0:
                return False, "Amount must be positive"
            
            wallet = self.get_wallet_by_user(user_id)
            if not wallet:
                return False, "Wallet not found"
            
            with transaction.atomic():
                currency = currency.lower()
                if currency == 'btc':
                    wallet.balance_btc += amount
                elif currency == 'xmr':
                    wallet.balance_xmr += amount
                else:
                    return False, f"Unsupported currency: {currency}"
                
                wallet.save()
                
                # Log transaction
                self._log_transaction(user_id, currency, amount, "credit", source)
                
                # Clear cache
                self.clear_cache(f"wallet:{user_id}")
                
                logger.info(f"Added {amount} {currency.upper()} to wallet for user {user_id}")
                return True, f"Successfully added {amount} {currency.upper()}"
                
        except Exception as e:
            logger.error(f"Failed to add funds for user {user_id}: {e}")
            return False, str(e)
    
    def deduct_funds(self, user_id: str, currency: str, amount: Decimal, reason: str = "withdrawal") -> Tuple[bool, str]:
        """Deduct funds from user's wallet."""
        try:
            if amount <= 0:
                return False, "Amount must be positive"
            
            wallet = self.get_wallet_by_user(user_id)
            if not wallet:
                return False, "Wallet not found"
            
            # Check available balance
            available, msg = self.get_available_balance(user_id, currency)
            if available < amount:
                return False, f"Insufficient available balance. Available: {available}, Required: {amount}"
            
            with transaction.atomic():
                currency = currency.lower()
                if currency == 'btc':
                    wallet.balance_btc -= amount
                elif currency == 'xmr':
                    wallet.balance_xmr -= amount
                else:
                    return False, f"Unsupported currency: {currency}"
                
                wallet.save()
                
                # Log transaction
                self._log_transaction(user_id, currency, amount, "debit", reason)
                
                # Clear cache
                self.clear_cache(f"wallet:{user_id}")
                
                logger.info(f"Deducted {amount} {currency.upper()} from wallet for user {user_id}")
                return True, f"Successfully deducted {amount} {currency.upper()}"
                
        except Exception as e:
            logger.error(f"Failed to deduct funds for user {user_id}: {e}")
            return False, str(e)
    
    def move_to_escrow(self, user_id: str, currency: str, amount: Decimal, order_id: str = None) -> Tuple[bool, str]:
        """Move funds to escrow for an order."""
        try:
            if amount <= 0:
                return False, "Amount must be positive"
            
            wallet = self.get_wallet_by_user(user_id)
            if not wallet:
                return False, "Wallet not found"
            
            # Check available balance
            available, msg = self.get_available_balance(user_id, currency)
            if available < amount:
                return False, f"Insufficient available balance. Available: {available}, Required: {amount}"
            
            with transaction.atomic():
                currency = currency.lower()
                if currency == 'btc':
                    wallet.escrow_btc += amount
                elif currency == 'xmr':
                    wallet.escrow_xmr += amount
                else:
                    return False, f"Unsupported currency: {currency}"
                
                wallet.save()
                
                # Log escrow transaction
                self._log_transaction(user_id, currency, amount, "escrow_lock", f"order_{order_id}" if order_id else "escrow")
                
                # Clear cache
                self.clear_cache(f"wallet:{user_id}")
                
                logger.info(f"Moved {amount} {currency.upper()} to escrow for user {user_id}")
                return True, f"Successfully moved {amount} {currency.upper()} to escrow"
                
        except Exception as e:
            logger.error(f"Failed to move funds to escrow for user {user_id}: {e}")
            return False, str(e)
    
    def release_from_escrow(self, user_id: str, currency: str, amount: Decimal, order_id: str = None) -> Tuple[bool, str]:
        """Release funds from escrow."""
        try:
            if amount <= 0:
                return False, "Amount must be positive"
            
            wallet = self.get_wallet_by_user(user_id)
            if not wallet:
                return False, "Wallet not found"
            
            # Check escrow balance
            currency = currency.lower()
            if currency == 'btc':
                if wallet.escrow_btc < amount:
                    return False, f"Insufficient escrow balance. Escrow: {wallet.escrow_btc}, Required: {amount}"
            elif currency == 'xmr':
                if wallet.escrow_xmr < amount:
                    return False, f"Insufficient escrow balance. Escrow: {wallet.escrow_xmr}, Required: {amount}"
            else:
                return False, f"Unsupported currency: {currency}"
            
            with transaction.atomic():
                if currency == 'btc':
                    wallet.escrow_btc -= amount
                elif currency == 'xmr':
                    wallet.escrow_xmr -= amount
                
                wallet.save()
                
                # Log escrow release
                self._log_transaction(user_id, currency, amount, "escrow_release", f"order_{order_id}" if order_id else "escrow")
                
                # Clear cache
                self.clear_cache(f"wallet:{user_id}")
                
                logger.info(f"Released {amount} {currency.upper()} from escrow for user {user_id}")
                return True, f"Successfully released {amount} {currency.upper()} from escrow"
                
        except Exception as e:
            logger.error(f"Failed to release funds from escrow for user {user_id}: {e}")
            return False, str(e)
    
    def can_withdraw(self, user_id: str, currency: str, amount: Decimal) -> Tuple[bool, str]:
        """Check if user can withdraw the specified amount."""
        try:
            wallet = self.get_wallet_by_user(user_id)
            if not wallet:
                return False, "Wallet not found"
            
            # Check available balance
            available, msg = self.get_available_balance(user_id, currency)
            if available < amount:
                return False, f"Insufficient available balance. Available: {available}, Required: {amount}"
            
            # Check daily withdrawal limit
            daily_total = self.get_daily_withdrawal_total(user_id, currency)
            currency = currency.lower()
            
            if currency == 'btc':
                limit = wallet.daily_withdrawal_limit_btc
            elif currency == 'xmr':
                limit = wallet.daily_withdrawal_limit_xmr
            else:
                return False, f"Unsupported currency: {currency}"
            
            if daily_total + amount > limit:
                return False, f"Daily withdrawal limit exceeded. Limit: {limit}, Already withdrawn: {daily_total}"
            
            # Check withdrawal velocity
            if self.check_withdrawal_velocity(user_id, currency):
                return False, "Too many withdrawal attempts. Please try again later."
            
            return True, "OK"
            
        except Exception as e:
            logger.error(f"Failed to check withdrawal for user {user_id}: {e}")
            return False, str(e)
    
    def get_daily_withdrawal_total(self, user_id: str, currency: str) -> Decimal:
        """Get total withdrawals for today for a specific currency."""
        try:
            from wallets.models import WithdrawalRequest
            
            today = timezone.now().date()
            currency = currency.lower()
            
            total = WithdrawalRequest.objects.filter(
                user_id=user_id,
                currency=currency.upper(),
                status='completed',
                processed_at__date=today
            ).aggregate(
                total=models.Sum('amount')
            )['total'] or Decimal('0')
            
            return total
            
        except Exception as e:
            logger.error(f"Failed to get daily withdrawal total for user {user_id}: {e}")
            return Decimal('0')
    
    def check_withdrawal_velocity(self, user_id: str, currency: str) -> bool:
        """Check if user has made too many withdrawal attempts recently."""
        try:
            from wallets.models import WithdrawalRequest
            
            # Check last 10 minutes
            recent_cutoff = timezone.now() - timezone.timedelta(minutes=10)
            recent_attempts = WithdrawalRequest.objects.filter(
                user_id=user_id,
                currency=currency.upper(),
                created_at__gte=recent_cutoff
            ).count()
            
            # Allow max 3 attempts per 10 minutes
            return recent_attempts >= 3
            
        except Exception as e:
            logger.error(f"Failed to check withdrawal velocity for user {user_id}: {e}")
            return True  # Fail safe - assume too many attempts
    
    def create_withdrawal_request(self, user_id: str, currency: str, amount: Decimal, 
                                address: str, withdrawal_pin: str = None) -> Tuple[Any, bool, str]:
        """Create a withdrawal request."""
        try:
            # Validate withdrawal
            can_withdraw, message = self.can_withdraw(user_id, currency, amount)
            if not can_withdraw:
                return None, False, message
            
            # Verify withdrawal PIN if required
            wallet = self.get_wallet_by_user(user_id)
            if wallet.withdrawal_pin and not self.verify_withdrawal_pin(wallet, withdrawal_pin):
                return False, "Invalid withdrawal PIN"
            
            with transaction.atomic():
                from wallets.models import WithdrawalRequest
                
                # Create withdrawal request
                withdrawal = WithdrawalRequest.objects.create(
                    user_id=user_id,
                    currency=currency.upper(),
                    amount=amount,
                    address=address,
                    status='pending'
                )
                
                # Move funds to escrow
                success, msg = self.move_to_escrow(user_id, currency, amount, str(withdrawal.id))
                if not success:
                    raise Exception(f"Failed to move funds to escrow: {msg}")
                
                logger.info(f"Withdrawal request created for user {user_id}: {amount} {currency.upper()}")
                return withdrawal, True, "Withdrawal request created successfully"
                
        except Exception as e:
            logger.error(f"Failed to create withdrawal request for user {user_id}: {e}")
            return None, False, str(e)
    
    def verify_withdrawal_pin(self, wallet: Any, pin: str) -> bool:
        """Verify withdrawal PIN."""
        try:
            if not wallet.withdrawal_pin:
                return True  # No PIN required
            
            import hashlib
            hashed_pin = hashlib.sha256(pin.encode()).hexdigest()
            return hashed_pin == wallet.withdrawal_pin
            
        except Exception as e:
            logger.error(f"Failed to verify withdrawal PIN: {e}")
            return False
    
    def _log_transaction(self, user_id: str, currency: str, amount: Decimal, 
                        transaction_type: str, description: str) -> None:
        """Log a wallet transaction."""
        try:
            from wallets.models import WalletTransaction
            
            WalletTransaction.objects.create(
                user_id=user_id,
                currency=currency.upper(),
                amount=amount,
                transaction_type=transaction_type,
                description=description,
                timestamp=timezone.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to log transaction: {e}")
    
    def get_transaction_history(self, user_id: str, currency: str = None, 
                              limit: int = 50) -> List[Dict[str, Any]]:
        """Get transaction history for a user."""
        try:
            from wallets.models import WalletTransaction
            
            query = {'user_id': user_id}
            if currency:
                query['currency'] = currency.upper()
            
            transactions = WalletTransaction.objects.filter(
                **query
            ).order_by('-timestamp')[:limit]
            
            return [
                {
                    'id': str(t.id),
                    'currency': t.currency,
                    'amount': str(t.amount),
                    'type': t.transaction_type,
                    'description': t.description,
                    'timestamp': t.timestamp.isoformat(),
                }
                for t in transactions
            ]
            
        except Exception as e:
            logger.error(f"Failed to get transaction history for user {user_id}: {e}")
            return []
    
    def get_wallet_summary(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive wallet summary for a user."""
        try:
            wallet = self.get_wallet_by_user(user_id)
            if not wallet:
                return {}
            
            return {
                'user_id': user_id,
                'balances': {
                    'BTC': {
                        'total': str(wallet.balance_btc),
                        'available': str(wallet.balance_btc - wallet.escrow_btc),
                        'escrow': str(wallet.escrow_btc),
                        'daily_limit': str(wallet.daily_withdrawal_limit_btc)
                    },
                    'XMR': {
                        'total': str(wallet.balance_xmr),
                        'available': str(wallet.balance_xmr - wallet.escrow_xmr),
                        'escrow': str(wallet.escrow_xmr),
                        'daily_limit': str(wallet.daily_withdrawal_limit_xmr)
                    }
                },
                'security': {
                    'two_fa_enabled': wallet.two_fa_enabled,
                    'withdrawal_pin_set': bool(wallet.withdrawal_pin)
                },
                'created_at': wallet.created_at.isoformat(),
                'last_activity': wallet.last_activity.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get wallet summary for user {user_id}: {e}")
            return {}
    
    def get_service_health(self) -> Dict[str, Any]:
        """Get service health status."""
        try:
            from wallets.models import Wallet, WalletTransaction
            
            total_wallets = Wallet.objects.count()
            total_transactions = WalletTransaction.objects.count()
            
            return {
                'total_wallets': total_wallets,
                'total_transactions': total_transactions,
                'wallet_cache_size': len(self._wallet_cache),
                'transaction_cache_size': len(self._transaction_cache),
            }
        except Exception as e:
            logger.error(f"Failed to get service health: {e}")
            return {'error': str(e)}