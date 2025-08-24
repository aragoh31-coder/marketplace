#!/usr/bin/env python
"""
Database initialization script to ensure all tables and columns exist
This prevents migration issues on startup
"""
import os
import sys
import sqlite3
import django

# Setup Django
sys.path.insert(0, '/workspace')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marketplace.settings')
django.setup()

from django.core.management import call_command
from django.db import connection

def ensure_migrations_table():
    """Ensure django_migrations table exists"""
    with connection.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS django_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL,
                applied DATETIME NOT NULL
            )
        """)

def mark_migrations_as_applied():
    """Mark all migrations as applied to prevent re-running"""
    apps_to_fake = [
        'contenttypes', 'auth', 'admin', 'sessions', 'sites',
        'accounts', 'wallets', 'products', 'orders', 'vendors',
        'messaging', 'support', 'adminpanel', 'disputes', 'core',
        'security'
    ]
    
    with connection.cursor() as cursor:
        for app in apps_to_fake:
            # Get all migration files for this app
            try:
                from django.db.migrations.loader import MigrationLoader
                loader = MigrationLoader(connection)
                app_migrations = [
                    (app, migration_name) 
                    for (app_name, migration_name) in loader.disk_migrations 
                    if app_name == app
                ]
                
                # Mark each migration as applied
                for app_name, migration_name in app_migrations:
                    cursor.execute(
                        "INSERT OR IGNORE INTO django_migrations (app, name, applied) VALUES (?, ?, datetime('now'))",
                        [app_name, migration_name]
                    )
            except Exception as e:
                print(f"Warning: Could not process migrations for {app}: {e}")

def ensure_wallet_schema():
    """Ensure wallets_wallet table has all required columns"""
    import sqlite3
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    
    try:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='wallets_wallet'")
        if not cursor.fetchone():
            print("Creating wallets_wallet table...")
            cursor.execute("""
                CREATE TABLE wallets_wallet (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    balance_btc DECIMAL(16, 8) DEFAULT 0.00000000,
                    balance_xmr DECIMAL(16, 12) DEFAULT 0.000000000000,
                    escrow_btc DECIMAL(16, 8) DEFAULT 0.00000000,
                    escrow_xmr DECIMAL(16, 12) DEFAULT 0.000000000000,
                    withdrawal_pin VARCHAR(128),
                    two_fa_enabled BOOLEAN DEFAULT 0,
                    two_fa_secret VARCHAR(32),
                    daily_withdrawal_limit_btc DECIMAL(16, 8) DEFAULT 1.00000000,
                    daily_withdrawal_limit_xmr DECIMAL(16, 12) DEFAULT 100.000000000000,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    last_activity DATETIME,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    currency VARCHAR(3),
                    address VARCHAR(255),
                    private_key TEXT,
                    balance DECIMAL,
                    FOREIGN KEY (user_id) REFERENCES auth_user (id)
                )
            """)
        
        # Ensure all columns exist with proper defaults
        columns_to_check = [
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
            ('last_activity', 'DATETIME', 'NULL'),
            ('is_active', 'BOOLEAN', '1'),
            ('currency', 'VARCHAR(3)', 'NULL'),
            ('address', 'VARCHAR(255)', 'NULL'),
            ('private_key', 'TEXT', 'NULL'),
            ('balance', 'DECIMAL', 'NULL')
        ]
        
        for col_name, col_type, default_val in columns_to_check:
            cursor.execute(f"PRAGMA table_info(wallets_wallet)")
            columns = {row[1]: row for row in cursor.fetchall()}
            
            if col_name not in columns:
                print(f"Adding column {col_name} to wallets_wallet...")
                if default_val == 'NULL':
                    cursor.execute(f"ALTER TABLE wallets_wallet ADD COLUMN {col_name} {col_type}")
                else:
                    cursor.execute(f"ALTER TABLE wallets_wallet ADD COLUMN {col_name} {col_type} DEFAULT {default_val}")
        
        # Update existing rows to have is_active = 1 if NULL
        cursor.execute("UPDATE wallets_wallet SET is_active = 1 WHERE is_active IS NULL")
        
        conn.commit()
        print("✓ Wallet schema updated successfully")
        
    except Exception as e:
        print(f"Error updating wallet schema: {e}")
        conn.rollback()
    finally:
        conn.close()

def ensure_all_tables():
    """Run migrate with fake-initial to ensure all tables exist"""
    print("Ensuring all database tables exist...")
    try:
        # Create tables if they don't exist
        call_command('migrate', '--fake-initial', '--no-input', verbosity=0)
    except Exception as e:
        print(f"Migration warning (can be ignored): {e}")

def ensure_orders_schema():
    """Ensure orders_order table has all required columns"""
    import sqlite3
    conn = sqlite3.connect('db.sqlite3')
    cursor = conn.cursor()
    
    try:
        # Check if table exists first
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders_order'")
        if cursor.fetchone():
            # Check existing columns
            cursor.execute("PRAGMA table_info(orders_order)")
            existing_columns = {col[1]: col for col in cursor.fetchall()}
            
            # Define all required columns
            required_columns = {
                'vendor_id': 'CHAR(32) REFERENCES vendors_vendor(id)',
                'buyer_wallet_id': 'INTEGER REFERENCES wallets_wallet(id)',
                'currency_used': 'VARCHAR(3)',
                'quantity': 'INTEGER DEFAULT 1',
                'locked_at': 'DATETIME',
                'shipped_at': 'DATETIME',
                'completed_at': 'DATETIME',
                'refunded_at': 'DATETIME',
                'escrow_released': 'BOOLEAN DEFAULT 0',
                'auto_finalize_at': 'DATETIME'
            }
            
            # Add missing columns
            for col_name, col_def in required_columns.items():
                if col_name not in existing_columns:
                    print(f"Adding {col_name} column to orders_order...")
                    try:
                        cursor.execute(f"ALTER TABLE orders_order ADD COLUMN {col_name} {col_def}")
                        conn.commit()
                        print(f"✓ Added {col_name}")
                    except sqlite3.OperationalError as e:
                        if "duplicate column" not in str(e).lower():
                            print(f"Note: Could not add {col_name}: {e}")
            
    except Exception as e:
        print(f"Note: Could not update orders table: {e}")
    finally:
        conn.close()

def main():
    print("Initializing database...")
    
    # Ensure migrations tracking table exists
    ensure_migrations_table()
    
    # Ensure wallet schema is correct
    ensure_wallet_schema()
    
    # Run migrations with fake-initial
    ensure_all_tables()
    
    # Ensure orders schema is correct
    ensure_orders_schema()
    
    # Mark all migrations as applied
    mark_migrations_as_applied()
    
    print("Database initialization complete!")

if __name__ == '__main__':
    main()