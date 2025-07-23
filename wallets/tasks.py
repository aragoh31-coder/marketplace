from celery import shared_task
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from datetime import timedelta
from decimal import Decimal
import logging

logger = logging.getLogger('wallet.tasks')


@shared_task
def reconcile_wallet_balances():
    """Periodic task to reconcile wallet balances"""
    from .models import Wallet, Transaction, WalletBalanceCheck
    from django.db.models import Sum, Q
    
    logger.info("Starting wallet balance reconciliation")
    
    wallets = Wallet.objects.all()
    discrepancies_found = 0
    
    for wallet in wallets:
        try:
            btc_transactions = Transaction.objects.filter(
                user=wallet.user,
                currency='btc'
            ).aggregate(
                deposits=Sum('amount', filter=Q(type='deposit')),
                withdrawals=Sum('amount', filter=Q(type='withdrawal')),
                conversions_in=Sum('converted_amount', filter=Q(converted_currency='btc')),
                conversions_out=Sum('amount', filter=Q(type='conversion', currency='btc'))
            )
            
            xmr_transactions = Transaction.objects.filter(
                user=wallet.user,
                currency='xmr'
            ).aggregate(
                deposits=Sum('amount', filter=Q(type='deposit')),
                withdrawals=Sum('amount', filter=Q(type='withdrawal')),
                conversions_in=Sum('converted_amount', filter=Q(converted_currency='xmr')),
                conversions_out=Sum('amount', filter=Q(type='conversion', currency='xmr'))
            )
            
            expected_btc = (
                (btc_transactions['deposits'] or Decimal('0')) +
                (btc_transactions['conversions_in'] or Decimal('0')) -
                (btc_transactions['withdrawals'] or Decimal('0')) -
                (btc_transactions['conversions_out'] or Decimal('0'))
            )
            
            expected_xmr = (
                (xmr_transactions['deposits'] or Decimal('0')) +
                (xmr_transactions['conversions_in'] or Decimal('0')) -
                (xmr_transactions['withdrawals'] or Decimal('0')) -
                (xmr_transactions['conversions_out'] or Decimal('0'))
            )
            
            btc_diff = abs(wallet.balance_btc - expected_btc)
            xmr_diff = abs(wallet.balance_xmr - expected_xmr)
            
            discrepancy_found = (
                btc_diff > Decimal('0.00000001') or 
                xmr_diff > Decimal('0.000000000001')
            )
            
            check = WalletBalanceCheck.objects.create(
                wallet=wallet,
                expected_btc=expected_btc,
                expected_xmr=expected_xmr,
                expected_escrow_btc=wallet.escrow_btc,
                expected_escrow_xmr=wallet.escrow_xmr,
                actual_btc=wallet.balance_btc,
                actual_xmr=wallet.balance_xmr,
                actual_escrow_btc=wallet.escrow_btc,
                actual_escrow_xmr=wallet.escrow_xmr,
                discrepancy_found=discrepancy_found,
                discrepancy_details={
                    'btc_diff': str(btc_diff),
                    'xmr_diff': str(xmr_diff)
                }
            )
            
            if discrepancy_found:
                discrepancies_found += 1
                
                if btc_diff > Decimal('0.001') or xmr_diff > Decimal('0.1'):
                    send_discrepancy_alert(wallet, check)
        
        except Exception as e:
            logger.error(f"Error reconciling wallet {wallet.id}: {str(e)}")
    
    logger.info(f"Reconciliation complete. Found {discrepancies_found} discrepancies")
    return discrepancies_found


@shared_task
def cleanup_old_audit_logs():
    """Clean up old audit logs"""
    from .models import AuditLog
    
    retention_days = getattr(settings, 'WALLET_AUDIT_LOG_RETENTION_DAYS', 365)
    cutoff_date = timezone.now() - timedelta(days=retention_days)
    
    important_logs = AuditLog.objects.filter(
        created_at__lt=cutoff_date,
        flagged=True
    )
    
    deleted_count = AuditLog.objects.filter(
        created_at__lt=cutoff_date
    ).delete()[0]
    
    logger.info(f"Deleted {deleted_count} old audit logs")
    return deleted_count


@shared_task
def check_suspicious_activity():
    """Check for suspicious wallet activity patterns"""
    from .models import WithdrawalRequest, AuditLog
    from django.contrib.auth import get_user_model
    from django.db import models
    
    User = get_user_model()
    
    recent_failed = WithdrawalRequest.objects.filter(
        status='rejected',
        created_at__gte=timezone.now() - timedelta(hours=1)
    ).values('user').annotate(
        count=models.Count('id')
    ).filter(count__gte=3)
    
    for item in recent_failed:
        user = User.objects.get(id=item['user'])
        AuditLog.objects.create(
            user=user,
            action='security_alert',
            user_agent='system',
            details={
                'alert_type': 'multiple_failed_withdrawals',
                'count': item['count']
            },
            flagged=True,
            risk_score=60
        )
    
    return True


def send_discrepancy_alert(wallet, check):
    """Send alert about wallet balance discrepancy"""
    try:
        subject = f"Wallet Balance Discrepancy - User {wallet.user.username}"
        message = render_to_string('wallets/emails/discrepancy_alert.txt', {
            'wallet': wallet,
            'check': check
        })
        
        admin_emails = [email for name, email in settings.ADMINS]
        if admin_emails:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                admin_emails,
                fail_silently=False
            )
            
    except Exception as e:
        logger.error(f"Failed to send discrepancy alert: {str(e)}")
