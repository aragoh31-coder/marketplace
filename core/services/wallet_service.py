"""
Wallet Service
Handles all wallet-related business logic and operations.
"""

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from datetime import timedelta, datetime

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q, F, Sum, Count, Max, Min, Avg
from django.utils import timezone

from .base_service import BaseService, performance_monitor, cache_result

logger = logging.getLogger(__name__)
User = get_user_model()


class WalletService(BaseService):
    """
    Optimized service for managing wallet operations with advanced caching and bulk operations.
    """

    service_name = "wallet_service"
    version = "2.0.0"
    description = "Optimized wallet management service"

    # Cache timeouts
    WALLET_CACHE_TIMEOUT = 300  # 5 minutes
    BALANCE_CACHE_TIMEOUT = 120  # 2 minutes
    TRANSACTION_CACHE_TIMEOUT = 600  # 10 minutes
    STATS_CACHE_TIMEOUT = 1800  # 30 minutes

    # Supported currencies with their decimal places
    SUPPORTED_CURRENCIES = {
        'btc': 8,
        'xmr': 12,
        'usd': 2
    }

    def initialize(self) -> bool:
        """Initialize the wallet service."""
        try:
            # Warm up cache with frequently accessed data
            self._warm_cache()
            return True
        except Exception as e:
            logger.error(f"Failed to initialize wallet service: {e}")
            return False

    def cleanup(self) -> bool:
        """Clean up the wallet service."""
        try:
            # Clear service-specific caches
            self.clear_cache()
            return True
        except Exception as e:
            logger.error(f"Failed to cleanup wallet service: {e}")
            return False

    def get_required_config(self) -> List[str]:
        """Get required configuration keys."""
        return ["max_daily_withdrawal", "withdrawal_cooldown"]

    def _warm_cache(self):
        """Warm up frequently accessed cache data."""
        try:
            # Cache total wallet count
            self.get_total_wallet_count()
            # Cache currency exchange rates
            self._cache_exchange_rates()
        except Exception as e:
            logger.warning(f"Cache warming failed: {e}")

    def _cache_exchange_rates(self):
        """Cache exchange rates for supported currencies."""
        try:
            from wallets.models import ConversionRate
            
            # Get all active conversion rates
            rates = ConversionRate.objects.filter(is_active=True).values(
                'from_currency', 'to_currency', 'rate'
            )
            
            rate_dict = {}
            for rate in rates:
                key = f"{rate['from_currency']}_{rate['to_currency']}"
                rate_dict[key] = float(rate['rate'])
            
            self.set_cached("exchange_rates", rate_dict, 1800)  # Cache for 30 minutes
            
        except Exception as e:
            logger.warning(f"Failed to cache exchange rates: {e}")

    @performance_monitor
    @cache_result(timeout=WALLET_CACHE_TIMEOUT, key_func=lambda user_id: f"wallet:{user_id}")
    def get_wallet_by_user(self, user_id: str) -> Optional[Any]:
        """Get wallet for a specific user with optimized caching."""
        try:
            from wallets.models import Wallet
            return Wallet.objects.select_related('user').get(user_id=user_id)
        except Exception as e:
            logger.error(f"Failed to get wallet for user {user_id}: {e}")
            return None

    @performance_monitor
    def get_wallets_by_users(self, user_ids: List[str]) -> Dict[str, Any]:
        """Bulk fetch wallets for multiple users with optimized queries."""
        if not user_ids:
            return {}

        # Check cache first
        cached_wallets = {}
        uncached_ids = []
        
        for user_id in user_ids:
            cached_wallet = self.get_cached(f"wallet:{user_id}")
            if cached_wallet:
                cached_wallets[user_id] = cached_wallet
            else:
                uncached_ids.append(user_id)

        # Fetch uncached wallets in bulk
        if uncached_ids:
            try:
                from wallets.models import Wallet
                
                db_wallets = Wallet.objects.filter(
                    user_id__in=uncached_ids
                ).select_related('user')
                
                for wallet in db_wallets:
                    cached_wallets[str(wallet.user_id)] = wallet
                    # Cache the fetched wallet
                    self.set_cached(f"wallet:{wallet.user_id}", wallet, self.WALLET_CACHE_TIMEOUT)

            except Exception as e:
                logger.error(f"Failed to bulk fetch wallets: {e}")

        return cached_wallets

    @performance_monitor
    def create_wallet(self, user_id: str, **kwargs) -> Tuple[Any, bool, str]:
        """Create a new wallet for a user with optimized creation."""
        try:
            from wallets.models import Wallet

            with transaction.atomic():
                # Check if wallet already exists
                if Wallet.objects.filter(user_id=user_id).exists():
                    return None, False, "Wallet already exists for this user"

                # Set default values for all supported currencies
                default_values = {
                    'user_id': user_id,
                    'balance_btc': Decimal('0'),
                    'balance_xmr': Decimal('0'),
                    'escrow_btc': Decimal('0'),
                    'escrow_xmr': Decimal('0'),
                    **kwargs
                }

                # Create wallet
                wallet = Wallet.objects.create(**default_values)

                # Clear cache
                self.clear_cache(f"wallet:{user_id}")
                self.clear_cache("total_wallet_count")

                logger.info(f"Wallet created successfully for user {user_id}")
                return wallet, True, "Wallet created successfully"

        except Exception as e:
            logger.error(f"Failed to create wallet for user {user_id}: {e}")
            return None, False, str(e)

    @performance_monitor
    @cache_result(timeout=BALANCE_CACHE_TIMEOUT, key_func=lambda user_id, currency: f"balance:{user_id}:{currency}")
    def get_balance(self, user_id: str, currency: str) -> Tuple[Decimal, str]:
        """Get user's balance for a specific currency with caching."""
        try:
            wallet = self.get_wallet_by_user(user_id)
            if not wallet:
                return Decimal('0'), "Wallet not found"

            currency = currency.lower()
            if currency not in self.SUPPORTED_CURRENCIES:
                return Decimal('0'), f"Unsupported currency: {currency}"

            balance_field = f'balance_{currency}'
            if hasattr(wallet, balance_field):
                return getattr(wallet, balance_field), "OK"
            else:
                return Decimal('0'), f"Currency {currency} not found in wallet"

        except Exception as e:
            logger.error(f"Failed to get balance for user {user_id}, currency {currency}: {e}")
            return Decimal('0'), str(e)

    @performance_monitor
    def get_balances_bulk(self, user_ids: List[str], currencies: List[str]) -> Dict[str, Dict[str, Decimal]]:
        """Bulk fetch balances for multiple users and currencies."""
        result = {}
        
        # Validate currencies
        valid_currencies = [c for c in currencies if c.lower() in self.SUPPORTED_CURRENCIES]
        
        if not valid_currencies or not user_ids:
            return result

        try:
            # Get wallets in bulk
            wallets = self.get_wallets_by_users(user_ids)
            
            for user_id, wallet in wallets.items():
                user_balances = {}
                for currency in valid_currencies:
                    currency = currency.lower()
                    balance_field = f'balance_{currency}'
                    if hasattr(wallet, balance_field):
                        user_balances[currency] = getattr(wallet, balance_field)
                    else:
                        user_balances[currency] = Decimal('0')
                
                result[user_id] = user_balances

        except Exception as e:
            logger.error(f"Failed to get bulk balances: {e}")

        return result

    @performance_monitor
    def get_available_balance(self, user_id: str, currency: str) -> Tuple[Decimal, str]:
        """Get user's available balance (total - escrow) with caching."""
        try:
            wallet = self.get_wallet_by_user(user_id)
            if not wallet:
                return Decimal('0'), "Wallet not found"

            currency = currency.lower()
            if currency not in self.SUPPORTED_CURRENCIES:
                return Decimal('0'), f"Unsupported currency: {currency}"

            balance_field = f'balance_{currency}'
            escrow_field = f'escrow_{currency}'
            
            total_balance = getattr(wallet, balance_field, Decimal('0'))
            escrow_balance = getattr(wallet, escrow_field, Decimal('0'))
            
            available = max(total_balance - escrow_balance, Decimal('0'))
            return available, "OK"

        except Exception as e:
            logger.error(f"Failed to get available balance for user {user_id}, currency {currency}: {e}")
            return Decimal('0'), str(e)

    @performance_monitor
    def add_funds(self, user_id: str, currency: str, amount: Decimal, source: str = "deposit") -> Tuple[bool, str]:
        """Add funds to user's wallet with optimized transaction handling."""
        try:
            if amount <= 0:
                return False, "Amount must be positive"

            currency = currency.lower()
            if currency not in self.SUPPORTED_CURRENCIES:
                return False, f"Unsupported currency: {currency}"

            with transaction.atomic():
                from wallets.models import Wallet, WalletTransaction
                
                # Use select_for_update to prevent race conditions
                wallet = Wallet.objects.select_for_update().get(user_id=user_id)
                
                balance_field = f'balance_{currency}'
                old_balance = getattr(wallet, balance_field)
                new_balance = old_balance + amount
                
                # Update balance
                setattr(wallet, balance_field, new_balance)
                wallet.save(update_fields=[balance_field, 'updated_at'])

                # Log transaction
                self._log_transaction(
                    user_id, currency, amount, "credit", 
                    f"Funds added from {source}",
                    old_balance, new_balance
                )

                # Clear caches
                self._invalidate_wallet_caches(user_id, currency)

                logger.info(f"Added {amount} {currency.upper()} to user {user_id} wallet")
                return True, "Funds added successfully"

        except Exception as e:
            logger.error(f"Failed to add funds for user {user_id}: {e}")
            return False, str(e)

    @performance_monitor
    def deduct_funds(self, user_id: str, currency: str, amount: Decimal, reason: str = "withdrawal") -> Tuple[bool, str]:
        """Deduct funds from user's wallet with balance validation."""
        try:
            if amount <= 0:
                return False, "Amount must be positive"

            currency = currency.lower()
            if currency not in self.SUPPORTED_CURRENCIES:
                return False, f"Unsupported currency: {currency}"

            with transaction.atomic():
                from wallets.models import Wallet
                
                # Use select_for_update to prevent race conditions
                wallet = Wallet.objects.select_for_update().get(user_id=user_id)
                
                balance_field = f'balance_{currency}'
                old_balance = getattr(wallet, balance_field)
                
                if old_balance < amount:
                    return False, "Insufficient balance"

                new_balance = old_balance - amount
                
                # Update balance
                setattr(wallet, balance_field, new_balance)
                wallet.save(update_fields=[balance_field, 'updated_at'])

                # Log transaction
                self._log_transaction(
                    user_id, currency, amount, "debit", 
                    f"Funds deducted for {reason}",
                    old_balance, new_balance
                )

                # Clear caches
                self._invalidate_wallet_caches(user_id, currency)

                logger.info(f"Deducted {amount} {currency.upper()} from user {user_id} wallet")
                return True, "Funds deducted successfully"

        except Exception as e:
            logger.error(f"Failed to deduct funds for user {user_id}: {e}")
            return False, str(e)

    @performance_monitor
    def bulk_transfer(self, transfers: List[Dict[str, Any]]) -> Tuple[int, int, str]:
        """Perform bulk transfers for better performance."""
        if not transfers:
            return 0, 0, "No transfers provided"

        successful_transfers = 0
        failed_transfers = 0
        
        try:
            with transaction.atomic():
                from wallets.models import Wallet
                
                # Group transfers by currency for optimization
                currency_groups = {}
                for transfer in transfers:
                    currency = transfer['currency'].lower()
                    if currency not in currency_groups:
                        currency_groups[currency] = []
                    currency_groups[currency].append(transfer)

                # Process each currency group
                for currency, currency_transfers in currency_groups.items():
                    if currency not in self.SUPPORTED_CURRENCIES:
                        failed_transfers += len(currency_transfers)
                        continue

                    # Get all involved wallets in bulk
                    user_ids = set()
                    for transfer in currency_transfers:
                        user_ids.add(transfer['from_user_id'])
                        user_ids.add(transfer['to_user_id'])

                    wallets = {
                        str(w.user_id): w for w in 
                        Wallet.objects.filter(user_id__in=user_ids).select_for_update()
                    }

                    # Process transfers for this currency
                    for transfer in currency_transfers:
                        try:
                            from_user_id = transfer['from_user_id']
                            to_user_id = transfer['to_user_id']
                            amount = Decimal(str(transfer['amount']))

                            from_wallet = wallets.get(from_user_id)
                            to_wallet = wallets.get(to_user_id)

                            if not from_wallet or not to_wallet:
                                failed_transfers += 1
                                continue

                            balance_field = f'balance_{currency}'
                            from_balance = getattr(from_wallet, balance_field)
                            
                            if from_balance < amount:
                                failed_transfers += 1
                                continue

                            # Update balances
                            setattr(from_wallet, balance_field, from_balance - amount)
                            to_balance = getattr(to_wallet, balance_field)
                            setattr(to_wallet, balance_field, to_balance + amount)

                            successful_transfers += 1

                        except Exception as e:
                            logger.error(f"Transfer failed: {e}")
                            failed_transfers += 1

                    # Save all wallet changes for this currency
                    if currency_transfers:
                        updated_wallets = [wallets[uid] for uid in user_ids if uid in wallets]
                        Wallet.objects.bulk_update(
                            updated_wallets, 
                            [f'balance_{currency}', 'updated_at']
                        )

                # Clear caches for all affected users
                for transfer in transfers:
                    self._invalidate_wallet_caches(transfer['from_user_id'], transfer['currency'])
                    self._invalidate_wallet_caches(transfer['to_user_id'], transfer['currency'])

            return successful_transfers, failed_transfers, f"Processed {successful_transfers} successful, {failed_transfers} failed transfers"

        except Exception as e:
            logger.error(f"Bulk transfer failed: {e}")
            return 0, len(transfers), str(e)

    @performance_monitor
    def move_to_escrow(self, user_id: str, currency: str, amount: Decimal, order_id: str = None) -> Tuple[bool, str]:
        """Move funds to escrow with atomic transaction."""
        try:
            if amount <= 0:
                return False, "Amount must be positive"

            currency = currency.lower()
            if currency not in self.SUPPORTED_CURRENCIES:
                return False, f"Unsupported currency: {currency}"

            with transaction.atomic():
                from wallets.models import Wallet
                
                wallet = Wallet.objects.select_for_update().get(user_id=user_id)
                
                balance_field = f'balance_{currency}'
                escrow_field = f'escrow_{currency}'
                
                current_balance = getattr(wallet, balance_field)
                current_escrow = getattr(wallet, escrow_field)
                
                if current_balance < amount:
                    return False, "Insufficient balance"

                # Move funds from balance to escrow
                setattr(wallet, balance_field, current_balance - amount)
                setattr(wallet, escrow_field, current_escrow + amount)
                
                wallet.save(update_fields=[balance_field, escrow_field, 'updated_at'])

                # Log escrow transaction
                self._log_transaction(
                    user_id, currency, amount, "escrow", 
                    f"Funds moved to escrow for order {order_id}",
                    current_balance, current_balance - amount
                )

                # Clear caches
                self._invalidate_wallet_caches(user_id, currency)

                logger.info(f"Moved {amount} {currency.upper()} to escrow for user {user_id}")
                return True, "Funds moved to escrow successfully"

        except Exception as e:
            logger.error(f"Failed to move funds to escrow for user {user_id}: {e}")
            return False, str(e)

    @performance_monitor
    def release_from_escrow(self, user_id: str, currency: str, amount: Decimal, order_id: str = None) -> Tuple[bool, str]:
        """Release funds from escrow back to available balance."""
        try:
            if amount <= 0:
                return False, "Amount must be positive"

            currency = currency.lower()
            if currency not in self.SUPPORTED_CURRENCIES:
                return False, f"Unsupported currency: {currency}"

            with transaction.atomic():
                from wallets.models import Wallet
                
                wallet = Wallet.objects.select_for_update().get(user_id=user_id)
                
                balance_field = f'balance_{currency}'
                escrow_field = f'escrow_{currency}'
                
                current_balance = getattr(wallet, balance_field)
                current_escrow = getattr(wallet, escrow_field)
                
                if current_escrow < amount:
                    return False, "Insufficient escrow balance"

                # Move funds from escrow back to balance
                setattr(wallet, balance_field, current_balance + amount)
                setattr(wallet, escrow_field, current_escrow - amount)
                
                wallet.save(update_fields=[balance_field, escrow_field, 'updated_at'])

                # Log release transaction
                self._log_transaction(
                    user_id, currency, amount, "escrow_release", 
                    f"Funds released from escrow for order {order_id}",
                    current_balance, current_balance + amount
                )

                # Clear caches
                self._invalidate_wallet_caches(user_id, currency)

                logger.info(f"Released {amount} {currency.upper()} from escrow for user {user_id}")
                return True, "Funds released from escrow successfully"

        except Exception as e:
            logger.error(f"Failed to release funds from escrow for user {user_id}: {e}")
            return False, str(e)

    def _invalidate_wallet_caches(self, user_id: str, currency: str):
        """Invalidate all caches related to a wallet and currency."""
        cache_keys = [
            f"wallet:{user_id}",
            f"balance:{user_id}:{currency}",
            f"available_balance:{user_id}:{currency}",
            f"wallet_stats:{user_id}"
        ]
        for key in cache_keys:
            self.clear_cache(key)

    @performance_monitor
    @cache_result(timeout=STATS_CACHE_TIMEOUT)
    def get_total_wallet_count(self) -> int:
        """Get total wallet count with caching."""
        try:
            from wallets.models import Wallet
            return Wallet.objects.count()
        except Exception as e:
            logger.error(f"Failed to get wallet count: {e}")
            return 0

    @performance_monitor
    @cache_result(timeout=STATS_CACHE_TIMEOUT, key_func=lambda currency: f"total_balance:{currency}")
    def get_total_balance_by_currency(self, currency: str) -> Decimal:
        """Get total balance across all wallets for a currency."""
        try:
            from wallets.models import Wallet
            
            currency = currency.lower()
            if currency not in self.SUPPORTED_CURRENCIES:
                return Decimal('0')

            balance_field = f'balance_{currency}'
            result = Wallet.objects.aggregate(
                total=Sum(balance_field)
            )
            
            return result['total'] or Decimal('0')

        except Exception as e:
            logger.error(f"Failed to get total balance for {currency}: {e}")
            return Decimal('0')

    @performance_monitor
    def get_wallet_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive wallet statistics."""
        cache_key = f"wallet_stats:{days}"
        cached_result = self.get_cached(cache_key)
        if cached_result:
            return cached_result

        try:
            from wallets.models import Wallet, WalletTransaction
            
            cutoff_date = timezone.now() - timedelta(days=days)
            
            # Get wallet statistics
            wallet_stats = Wallet.objects.aggregate(
                total_wallets=Count('id'),
                total_btc=Sum('balance_btc'),
                total_xmr=Sum('balance_xmr'),
                total_escrow_btc=Sum('escrow_btc'),
                total_escrow_xmr=Sum('escrow_xmr'),
                avg_btc_balance=Avg('balance_btc'),
                avg_xmr_balance=Avg('balance_xmr')
            )

            # Get transaction statistics
            transaction_stats = WalletTransaction.objects.filter(
                timestamp__gte=cutoff_date
            ).aggregate(
                total_transactions=Count('id'),
                total_volume_btc=Sum('amount', filter=Q(currency='BTC')),
                total_volume_xmr=Sum('amount', filter=Q(currency='XMR'))
            )

            stats = {
                **wallet_stats,
                **transaction_stats,
                'period_days': days,
                'timestamp': timezone.now().isoformat()
            }

            # Convert Decimal values to float for JSON serialization
            for key, value in stats.items():
                if isinstance(value, Decimal):
                    stats[key] = float(value) if value else 0.0

            self.set_cached(cache_key, stats, self.STATS_CACHE_TIMEOUT)
            return stats

        except Exception as e:
            logger.error(f"Failed to get wallet statistics: {e}")
            return {}

    def _log_transaction(self, user_id: str, currency: str, amount: Decimal,
                        transaction_type: str, description: str, 
                        balance_before: Decimal = None, balance_after: Decimal = None) -> None:
        """Log a wallet transaction with optimized creation."""
        try:
            from wallets.models import WalletTransaction

            WalletTransaction.objects.create(
                user_id=user_id,
                currency=currency.upper(),
                amount=amount,
                transaction_type=transaction_type,
                description=description,
                balance_before=balance_before,
                balance_after=balance_after,
                timestamp=timezone.now()
            )

        except Exception as e:
            logger.error(f"Failed to log transaction: {e}")

    @performance_monitor
    def get_transaction_history(self, user_id: str, currency: str = None, 
                              limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get user's transaction history with pagination and caching."""
        cache_key = f"transactions:{user_id}:{currency}:{limit}:{offset}"
        cached_result = self.get_cached(cache_key)
        if cached_result:
            return cached_result

        try:
            from wallets.models import WalletTransaction

            queryset = WalletTransaction.objects.filter(user_id=user_id)
            
            if currency:
                currency = currency.upper()
                queryset = queryset.filter(currency=currency)

            transactions = queryset.order_by('-timestamp').values(
                'id', 'currency', 'amount', 'transaction_type', 
                'description', 'timestamp', 'balance_before', 'balance_after'
            )[offset:offset + limit]

            result = list(transactions)
            
            # Convert Decimal values for JSON serialization
            for tx in result:
                for field in ['amount', 'balance_before', 'balance_after']:
                    if tx[field] and isinstance(tx[field], Decimal):
                        tx[field] = float(tx[field])

            self.set_cached(cache_key, result, self.TRANSACTION_CACHE_TIMEOUT)
            return result

        except Exception as e:
            logger.error(f"Failed to get transaction history for user {user_id}: {e}")
            return []

    def cleanup_old_data(self) -> Dict[str, int]:
        """Clean up old wallet data and optimize performance."""
        cleanup_stats = {
            'deleted_old_transactions': 0,
            'optimized_balances': 0,
            'cleared_cache_entries': 0
        }

        try:
            # Clean up old transaction logs (keep last 90 days)
            from wallets.models import WalletTransaction
            
            cutoff_date = timezone.now() - timedelta(days=90)
            deleted_count, _ = WalletTransaction.objects.filter(
                timestamp__lt=cutoff_date
            ).delete()
            
            cleanup_stats['deleted_old_transactions'] = deleted_count

            # Clear expired caches
            # This would require a more sophisticated cache implementation
            # For now, we'll just clear all wallet-related caches
            cleanup_stats['cleared_cache_entries'] = self._clear_expired_caches()

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

        return cleanup_stats

    def _clear_expired_caches(self) -> int:
        """Clear expired wallet caches."""
        # This is a simplified implementation
        # In production, you'd want more sophisticated cache management
        try:
            # Clear pattern-based caches if supported
            cleared_count = 0
            # Implementation would depend on cache backend
            return cleared_count
        except Exception as e:
            logger.error(f"Failed to clear expired caches: {e}")
            return 0

    def _health_check(self):
        """Enhanced health check for wallet service."""
        try:
            # Check database connectivity
            from wallets.models import Wallet
            Wallet.objects.count()
            
            # Check cache connectivity
            self.set_cached("health_check", True, 60)
            self.get_cached("health_check")
            
            # Check exchange rates cache
            self._cache_exchange_rates()
            
            self._healthy = True
        except Exception as e:
            logger.error(f"Wallet service health check failed: {e}")
            self._healthy = False
