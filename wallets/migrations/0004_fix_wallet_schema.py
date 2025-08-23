# Generated manually to fix wallet table schema

from decimal import Decimal
from django.db import migrations, models
import django.core.validators


def fix_wallet_schema(apps, schema_editor):
    """Fix wallet table schema by adding missing columns"""
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Check existing columns
        cursor.execute("PRAGMA table_info(wallets_wallet)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Add missing columns if they don't exist
        if 'balance_btc' not in columns:
            cursor.execute("""
                ALTER TABLE wallets_wallet 
                ADD COLUMN balance_btc DECIMAL(16, 8) DEFAULT 0.00000000
            """)
        
        if 'balance_xmr' not in columns:
            cursor.execute("""
                ALTER TABLE wallets_wallet 
                ADD COLUMN balance_xmr DECIMAL(16, 12) DEFAULT 0.000000000000
            """)
            
        if 'escrow_btc' not in columns:
            cursor.execute("""
                ALTER TABLE wallets_wallet 
                ADD COLUMN escrow_btc DECIMAL(16, 8) DEFAULT 0.00000000
            """)
            
        if 'escrow_xmr' not in columns:
            cursor.execute("""
                ALTER TABLE wallets_wallet 
                ADD COLUMN escrow_xmr DECIMAL(16, 12) DEFAULT 0.000000000000
            """)
            
        if 'last_activity' not in columns:
            cursor.execute("""
                ALTER TABLE wallets_wallet 
                ADD COLUMN last_activity DATETIME NULL
            """)
            
        if 'is_locked' not in columns:
            cursor.execute("""
                ALTER TABLE wallets_wallet 
                ADD COLUMN is_locked BOOLEAN DEFAULT 0
            """)
            
        if 'locked_until' not in columns:
            cursor.execute("""
                ALTER TABLE wallets_wallet 
                ADD COLUMN locked_until DATETIME NULL
            """)
            
        if 'total_received_btc' not in columns:
            cursor.execute("""
                ALTER TABLE wallets_wallet 
                ADD COLUMN total_received_btc DECIMAL(16, 8) DEFAULT 0.00000000
            """)
            
        if 'total_sent_btc' not in columns:
            cursor.execute("""
                ALTER TABLE wallets_wallet 
                ADD COLUMN total_sent_btc DECIMAL(16, 8) DEFAULT 0.00000000
            """)
            
        if 'total_received_xmr' not in columns:
            cursor.execute("""
                ALTER TABLE wallets_wallet 
                ADD COLUMN total_received_xmr DECIMAL(16, 12) DEFAULT 0.000000000000
            """)
            
        if 'total_sent_xmr' not in columns:
            cursor.execute("""
                ALTER TABLE wallets_wallet 
                ADD COLUMN total_sent_xmr DECIMAL(16, 12) DEFAULT 0.000000000000
            """)
            
        # If old 'balance' column exists and new columns were added, migrate data
        if 'balance' in columns and 'balance_btc' not in columns:
            # Migrate balance to balance_btc (assuming old balance was BTC)
            cursor.execute("""
                UPDATE wallets_wallet 
                SET balance_btc = COALESCE(balance, 0.00000000)
                WHERE balance_btc = 0.00000000
            """)


def reverse_fix_wallet_schema(apps, schema_editor):
    """Reverse operation - not implemented as this is a fix"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("wallets", "0003_remove_auditlog_ip_address_and_more"),
    ]

    operations = [
        migrations.RunPython(fix_wallet_schema, reverse_fix_wallet_schema),
    ]