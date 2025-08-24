#!/usr/bin/env python
import os
import sys
import sqlite3
import django

# Setup Django
sys.path.insert(0, '/workspace')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marketplace.settings')
django.setup()

# Connect to the database
db_path = '/workspace/db.sqlite3'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check if wallets_wallet table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='wallets_wallet';")
table_exists = cursor.fetchone()

if table_exists:
    # Check existing columns
    cursor.execute("PRAGMA table_info(wallets_wallet);")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    print(f"Existing columns: {column_names}")
    
    # Add missing columns if they don't exist
    columns_to_add = [
        ('balance_btc', 'DECIMAL(16, 8)', '0.00000000'),
        ('balance_xmr', 'DECIMAL(16, 12)', '0.000000000000'),
        ('escrow_btc', 'DECIMAL(16, 8)', '0.00000000'),
        ('escrow_xmr', 'DECIMAL(16, 12)', '0.000000000000'),
        ('withdrawal_pin', 'VARCHAR(128)', 'NULL'),
        ('two_fa_enabled', 'BOOLEAN', '0'),
        ('two_fa_secret', 'VARCHAR(32)', 'NULL'),
        ('daily_withdrawal_limit_btc', 'DECIMAL(16, 8)', '1.00000000'),
        ('daily_withdrawal_limit_xmr', 'DECIMAL(16, 12)', '100.000000000000'),
        ('created_at', 'DATETIME', "datetime('now')"),
        ('updated_at', 'DATETIME', "datetime('now')"),
        ('last_activity', 'DATETIME', "datetime('now')")
    ]
    
    for col_name, col_type, default_value in columns_to_add:
        if col_name not in column_names:
            try:
                if default_value == 'NULL':
                    cursor.execute(f"ALTER TABLE wallets_wallet ADD COLUMN {col_name} {col_type} DEFAULT NULL;")
                else:
                    cursor.execute(f"ALTER TABLE wallets_wallet ADD COLUMN {col_name} {col_type} DEFAULT {default_value};")
                print(f"Added column: {col_name}")
            except sqlite3.OperationalError as e:
                print(f"Error adding column {col_name}: {e}")
    
    conn.commit()
    print("Wallet table schema fixed!")
else:
    print("wallets_wallet table doesn't exist!")

# Close connection
conn.close()