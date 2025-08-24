from django.core.management.base import BaseCommand
from django.utils import timezone
from orders.models import Order
from orders.escrow import EscrowService
import logging

logger = logging.getLogger('orders.auto_finalize')


class Command(BaseCommand):
    help = 'Auto-finalize shipped orders after 14 days'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes',
        )
    
    def handle(self, *args, **kwargs):
        dry_run = kwargs.get('dry_run', False)
        now = timezone.now()
        
        # Find orders eligible for auto-finalization
        orders = Order.objects.filter(
            status='SHIPPED',
            auto_finalize_at__lte=now,
            escrow_released=False
        )
        
        count = orders.count()
        
        if count == 0:
            self.stdout.write("No orders to auto-finalize")
            return
        
        self.stdout.write(f"Found {count} orders to auto-finalize")
        
        success_count = 0
        error_count = 0
        
        for order in orders:
            try:
                if dry_run:
                    self.stdout.write(
                        self.style.SUCCESS(f"[DRY RUN] Would auto-finalize order {order.id}")
                    )
                else:
                    EscrowService.release_funds(order)
                    self.stdout.write(
                        self.style.SUCCESS(f"Auto-finalized order {order.id}")
                    )
                    
                    # Log the auto-finalization
                    from wallets.models import AuditLog
                    AuditLog.objects.create(
                        user=order.user,
                        action='withdrawal_approved',
                        details={
                            'order_id': str(order.id),
                            'type': 'auto_finalization',
                            'amount': str(order.total_btc if order.currency_used == 'BTC' else order.total_xmr),
                            'currency': order.currency_used,
                            'vendor': order.vendor.user.username
                        }
                    )
                    
                success_count += 1
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"Failed to auto-finalize order {order.id}: {str(e)}")
                )
                logger.error(f"Auto-finalization failed for order {order.id}: {str(e)}")
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\nAuto-finalization complete: {success_count} successful, {error_count} failed"
            )
        )