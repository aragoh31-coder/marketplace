# Generated manually to add remaining missing fields

from django.db import migrations


def add_remaining_fields(apps, schema_editor):
    """Add remaining missing fields to wallet table"""
    from django.db import connection
    
    with connection.cursor() as cursor:
        # Check existing columns
        cursor.execute("PRAGMA table_info(wallets_wallet)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Add withdrawal_pin if missing
        if 'withdrawal_pin' not in columns:
            cursor.execute("""
                ALTER TABLE wallets_wallet 
                ADD COLUMN withdrawal_pin VARCHAR(128) NULL
            """)
            
        # Add any other potentially missing fields from the model
        if 'last_sync' not in columns:
            cursor.execute("""
                ALTER TABLE wallets_wallet 
                ADD COLUMN last_sync DATETIME NULL
            """)
            
        if 'sync_in_progress' not in columns:
            cursor.execute("""
                ALTER TABLE wallets_wallet 
                ADD COLUMN sync_in_progress BOOLEAN DEFAULT 0
            """)


def reverse_add_remaining_fields(apps, schema_editor):
    """Reverse operation - not implemented"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("wallets", "0004_fix_wallet_schema"),
    ]

    operations = [
        migrations.RunPython(add_remaining_fields, reverse_add_remaining_fields),
    ]