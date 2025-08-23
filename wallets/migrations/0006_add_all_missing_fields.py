# Generated manually to add all missing fields

from django.db import migrations
from decimal import Decimal


def add_all_missing_fields(apps, schema_editor):
    """Add all missing fields to wallet table"""
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Check existing columns
        cursor.execute("PRAGMA table_info(wallets_wallet)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Add all missing fields
        missing_fields = [
            ('two_fa_enabled', 'BOOLEAN DEFAULT 0'),
            ('two_fa_secret', 'VARCHAR(32) NULL'),
            ('daily_withdrawal_limit_btc', 'DECIMAL(16, 8) DEFAULT 1.00000000'),
            ('daily_withdrawal_limit_xmr', 'DECIMAL(16, 12) DEFAULT 100.000000000000'),
        ]
        
        for field_name, field_def in missing_fields:
            if field_name not in columns:
                cursor.execute(f"""
                    ALTER TABLE wallets_wallet 
                    ADD COLUMN {field_name} {field_def}
                """)
                print(f"Added column: {field_name}")
        
        # Also check for any fields that might be in the model but not in our list
        # Let's check all the fields from the Wallet model
        model_fields = [
            ('balance_btc', 'DECIMAL(16, 8) DEFAULT 0.00000000'),
            ('balance_xmr', 'DECIMAL(16, 12) DEFAULT 0.000000000000'),
            ('escrow_btc', 'DECIMAL(16, 8) DEFAULT 0.00000000'),
            ('escrow_xmr', 'DECIMAL(16, 12) DEFAULT 0.000000000000'),
            ('withdrawal_pin', 'VARCHAR(128) NULL'),
            ('two_fa_enabled', 'BOOLEAN DEFAULT 0'),
            ('two_fa_secret', 'VARCHAR(32) NULL'),
            ('daily_withdrawal_limit_btc', 'DECIMAL(16, 8) DEFAULT 1.00000000'),
            ('daily_withdrawal_limit_xmr', 'DECIMAL(16, 12) DEFAULT 100.000000000000'),
            ('last_activity', 'DATETIME NULL'),
            ('is_locked', 'BOOLEAN DEFAULT 0'),
            ('locked_until', 'DATETIME NULL'),
            ('total_received_btc', 'DECIMAL(16, 8) DEFAULT 0.00000000'),
            ('total_sent_btc', 'DECIMAL(16, 8) DEFAULT 0.00000000'),
            ('total_received_xmr', 'DECIMAL(16, 12) DEFAULT 0.000000000000'),
            ('total_sent_xmr', 'DECIMAL(16, 12) DEFAULT 0.000000000000'),
            ('last_sync', 'DATETIME NULL'),
            ('sync_in_progress', 'BOOLEAN DEFAULT 0'),
        ]
        
        for field_name, field_def in model_fields:
            if field_name not in columns:
                try:
                    cursor.execute(f"""
                        ALTER TABLE wallets_wallet 
                        ADD COLUMN {field_name} {field_def}
                    """)
                    print(f"Added column: {field_name}")
                except Exception as e:
                    print(f"Column {field_name} might already exist or error: {e}")


def reverse_add_all_missing_fields(apps, schema_editor):
    """Reverse operation - not implemented"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("wallets", "0005_add_remaining_fields"),
    ]

    operations = [
        migrations.RunPython(add_all_missing_fields, reverse_add_all_missing_fields),
    ]