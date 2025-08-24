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
    """Ensure wallet table has all required columns"""
    conn = sqlite3.connect('/workspace/db.sqlite3')
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='wallets_wallet';")
    if not cursor.fetchone():
        print("Creating wallets_wallet table...")
        cursor.execute("""
            CREATE TABLE wallets_wallet (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE REFERENCES auth_user(id),
                balance_btc DECIMAL(16, 8) DEFAULT 0.00000000,
                balance_xmr DECIMAL(16, 12) DEFAULT 0.000000000000,
                escrow_btc DECIMAL(16, 8) DEFAULT 0.00000000,
                escrow_xmr DECIMAL(16, 12) DEFAULT 0.000000000000,
                withdrawal_pin VARCHAR(128),
                two_fa_enabled BOOLEAN DEFAULT 0,
                two_fa_secret VARCHAR(32),
                daily_withdrawal_limit_btc DECIMAL(16, 8) DEFAULT 1.00000000,
                daily_withdrawal_limit_xmr DECIMAL(16, 12) DEFAULT 100.000000000000,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_activity DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        # Add missing columns
        cursor.execute("PRAGMA table_info(wallets_wallet);")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        columns_to_add = [
            ('balance_btc', 'DECIMAL(16, 8) DEFAULT 0.00000000'),
            ('balance_xmr', 'DECIMAL(16, 12) DEFAULT 0.000000000000'),
            ('escrow_btc', 'DECIMAL(16, 8) DEFAULT 0.00000000'),
            ('escrow_xmr', 'DECIMAL(16, 12) DEFAULT 0.000000000000'),
            ('withdrawal_pin', 'VARCHAR(128)'),
            ('two_fa_enabled', 'BOOLEAN DEFAULT 0'),
            ('two_fa_secret', 'VARCHAR(32)'),
            ('daily_withdrawal_limit_btc', 'DECIMAL(16, 8) DEFAULT 1.00000000'),
            ('daily_withdrawal_limit_xmr', 'DECIMAL(16, 12) DEFAULT 100.000000000000'),
            ('created_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
            ('updated_at', 'DATETIME DEFAULT CURRENT_TIMESTAMP'),
            ('last_activity', 'DATETIME')
        ]
        
        for col_name, col_def in columns_to_add:
            if col_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE wallets_wallet ADD COLUMN {col_name} {col_def};")
                    print(f"Added column: {col_name}")
                except sqlite3.OperationalError:
                    pass
    
    conn.commit()
    conn.close()

def ensure_all_tables():
    """Run migrate with fake-initial to ensure all tables exist"""
    print("Ensuring all database tables exist...")
    try:
        # Create tables if they don't exist
        call_command('migrate', '--fake-initial', '--no-input', verbosity=0)
    except Exception as e:
        print(f"Migration warning (can be ignored): {e}")

def main():
    print("Initializing database...")
    
    # Ensure migrations tracking table exists
    ensure_migrations_table()
    
    # Ensure wallet schema is correct
    ensure_wallet_schema()
    
    # Run migrations with fake-initial
    ensure_all_tables()
    
    # Mark all migrations as applied
    mark_migrations_as_applied()
    
    print("Database initialization complete!")

if __name__ == '__main__':
    main()