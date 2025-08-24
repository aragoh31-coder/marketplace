#!/usr/bin/env python
"""
Fix all wallet-related database tables
This script ensures all wallet tables have the correct schema
"""

import sqlite3
import sys
from datetime import datetime

def log(message, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")

def fix_wallet_tables():
    """Fix all wallet-related tables"""
    conn = sqlite3.connect('/workspace/db.sqlite3')
    cursor = conn.cursor()
    
    try:
        log("Starting wallet tables fix...")
        
        # 1. Fix wallets_transaction table
        log("Checking wallets_transaction table...")
        cursor.execute("PRAGMA table_info(wallets_transaction)")
        columns = {col[1]: col for col in cursor.fetchall()}
        
        # Add missing columns
        missing_columns = {
            'type': 'VARCHAR(20) NOT NULL DEFAULT "deposit"',
            'transaction_hash': 'VARCHAR(64)',
            'reference': 'VARCHAR(255)',
            'related_object_type': 'VARCHAR(50)',
            'related_object_id': 'INTEGER',
            'metadata': 'TEXT DEFAULT "{}"',
            'balance_before': 'DECIMAL(16,12) DEFAULT 0',
            'balance_after': 'DECIMAL(16,12) DEFAULT 0',
            'converted_amount': 'DECIMAL(16,12)',
            'converted_currency': 'VARCHAR(3)',
            'conversion_rate': 'DECIMAL(20,12)'
        }
        
        for col_name, col_def in missing_columns.items():
            if col_name not in columns:
                try:
                    log(f"Adding column wallets_transaction.{col_name}")
                    cursor.execute(f"ALTER TABLE wallets_transaction ADD COLUMN {col_name} {col_def}")
                    conn.commit()
                except sqlite3.OperationalError as e:
                    if "duplicate column" not in str(e).lower():
                        log(f"Error adding column {col_name}: {e}", "ERROR")
        
        # 2. Ensure all wallet tables exist with correct schema
        tables_sql = {
            'wallets_wallet': '''
                CREATE TABLE IF NOT EXISTS wallets_wallet (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id CHAR(32) UNIQUE NOT NULL,
                    balance_btc DECIMAL(16,8) DEFAULT 0.00000000,
                    balance_xmr DECIMAL(16,12) DEFAULT 0.000000000000,
                    escrow_btc DECIMAL(16,8) DEFAULT 0.00000000,
                    escrow_xmr DECIMAL(16,12) DEFAULT 0.000000000000,
                    withdrawal_pin VARCHAR(128),
                    two_fa_enabled BOOLEAN DEFAULT 0,
                    two_fa_secret VARCHAR(32),
                    daily_withdrawal_limit_btc DECIMAL(16,8) DEFAULT 1.00000000,
                    daily_withdrawal_limit_xmr DECIMAL(16,12) DEFAULT 100.000000000000,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_activity DATETIME,
                    is_active BOOLEAN DEFAULT 1,
                    currency VARCHAR(3),
                    address VARCHAR(255),
                    private_key TEXT,
                    balance DECIMAL,
                    FOREIGN KEY (user_id) REFERENCES accounts_user (id)
                )
            ''',
            
            'wallets_transaction': '''
                CREATE TABLE IF NOT EXISTS wallets_transaction (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id CHAR(32) NOT NULL,
                    type VARCHAR(20) NOT NULL DEFAULT "deposit",
                    amount DECIMAL(16,12) NOT NULL,
                    currency VARCHAR(3) NOT NULL,
                    converted_amount DECIMAL(16,12),
                    converted_currency VARCHAR(3),
                    conversion_rate DECIMAL(20,12),
                    balance_before DECIMAL(16,12) DEFAULT 0,
                    balance_after DECIMAL(16,12) DEFAULT 0,
                    reference VARCHAR(255),
                    related_object_type VARCHAR(50),
                    related_object_id INTEGER,
                    transaction_hash VARCHAR(64),
                    metadata TEXT DEFAULT "{}",
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    transaction_id VARCHAR(64),
                    wallet_id INTEGER,
                    transaction_type VARCHAR(20),
                    fee DECIMAL(16,8) DEFAULT 0,
                    status VARCHAR(20),
                    blockchain_txid VARCHAR(128),
                    from_address VARCHAR(255),
                    to_address VARCHAR(255),
                    memo TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    processed_at DATETIME,
                    confirmations INTEGER DEFAULT 0,
                    error_message TEXT,
                    FOREIGN KEY (user_id) REFERENCES accounts_user (id),
                    FOREIGN KEY (wallet_id) REFERENCES wallets_wallet (id)
                )
            ''',
            
            'wallets_withdrawalrequest': '''
                CREATE TABLE IF NOT EXISTS wallets_withdrawalrequest (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    request_id VARCHAR(64) UNIQUE NOT NULL,
                    user_id CHAR(32) NOT NULL,
                    currency VARCHAR(3) NOT NULL,
                    amount DECIMAL(16,8) NOT NULL,
                    fee DECIMAL(16,8) DEFAULT 0,
                    to_address VARCHAR(255) NOT NULL,
                    memo TEXT,
                    status VARCHAR(20) DEFAULT "pending",
                    pin_verified BOOLEAN DEFAULT 0,
                    two_fa_verified BOOLEAN DEFAULT 0,
                    admin_approved BOOLEAN DEFAULT 0,
                    admin_notes TEXT,
                    blockchain_txid VARCHAR(128),
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    processed_at DATETIME,
                    cancelled_at DATETIME,
                    cancellation_reason TEXT,
                    security_checks TEXT DEFAULT "{}",
                    risk_score INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES accounts_user (id)
                )
            ''',
            
            'wallets_walletbalancecheck': '''
                CREATE TABLE IF NOT EXISTS wallets_walletbalancecheck (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    wallet_id INTEGER NOT NULL,
                    expected_btc DECIMAL(16,8) NOT NULL,
                    expected_xmr DECIMAL(16,12) NOT NULL,
                    expected_escrow_btc DECIMAL(16,8) NOT NULL,
                    expected_escrow_xmr DECIMAL(16,12) NOT NULL,
                    actual_btc DECIMAL(16,8) NOT NULL,
                    actual_xmr DECIMAL(16,12) NOT NULL,
                    actual_escrow_btc DECIMAL(16,8) NOT NULL,
                    actual_escrow_xmr DECIMAL(16,12) NOT NULL,
                    discrepancy_found BOOLEAN DEFAULT 0,
                    discrepancy_details TEXT DEFAULT "{}",
                    resolved BOOLEAN DEFAULT 0,
                    resolved_by_id CHAR(32),
                    resolution_notes TEXT,
                    checked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    resolved_at DATETIME,
                    FOREIGN KEY (wallet_id) REFERENCES wallets_wallet (id),
                    FOREIGN KEY (resolved_by_id) REFERENCES accounts_user (id)
                )
            ''',
            
            'wallets_conversionrate': '''
                CREATE TABLE IF NOT EXISTS wallets_conversionrate (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_currency VARCHAR(3) NOT NULL,
                    to_currency VARCHAR(3) NOT NULL,
                    rate DECIMAL(16,8) NOT NULL,
                    fee_percentage DECIMAL(5,2) DEFAULT 0.5,
                    min_amount DECIMAL(16,8) DEFAULT 0.0001,
                    max_amount DECIMAL(16,8) DEFAULT 10,
                    enabled BOOLEAN DEFAULT 1,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(from_currency, to_currency)
                )
            ''',
            
            'wallets_auditlog': '''
                CREATE TABLE IF NOT EXISTS wallets_auditlog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id CHAR(32) NOT NULL,
                    action VARCHAR(100) NOT NULL,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    details TEXT DEFAULT "{}",
                    suspicious BOOLEAN DEFAULT 0,
                    risk_score INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES accounts_user (id)
                )
            '''
        }
        
        # Create tables if they don't exist
        for table_name, create_sql in tables_sql.items():
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
            if not cursor.fetchone():
                log(f"Creating table {table_name}")
                cursor.execute(create_sql)
                conn.commit()
        
        # 3. Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_transaction_user_type ON wallets_transaction(user_id, type, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_transaction_reference ON wallets_transaction(reference)",
            "CREATE INDEX IF NOT EXISTS idx_transaction_hash ON wallets_transaction(transaction_hash)",
            "CREATE INDEX IF NOT EXISTS idx_withdrawal_status ON wallets_withdrawalrequest(status, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_audit_user ON wallets_auditlog(user_id, created_at)",
            "CREATE INDEX IF NOT EXISTS idx_balance_check ON wallets_walletbalancecheck(discrepancy_found, resolved, checked_at)"
        ]
        
        for index_sql in indexes:
            try:
                cursor.execute(index_sql)
                conn.commit()
            except sqlite3.OperationalError:
                pass  # Index already exists
        
        # 4. Test queries
        log("\nTesting wallet queries...")
        test_queries = [
            ("SELECT COUNT(*) FROM wallets_wallet", "Wallet count"),
            ("SELECT COUNT(*) FROM wallets_transaction", "Transaction count"),
            ("SELECT COUNT(*) FROM wallets_withdrawalrequest", "Withdrawal count"),
            ("SELECT COUNT(*) FROM wallets_walletbalancecheck", "Balance check count"),
            ("SELECT COUNT(*) FROM wallets_conversionrate", "Conversion rate count"),
            ("SELECT COUNT(*) FROM wallets_auditlog", "Audit log count")
        ]
        
        all_good = True
        for query, description in test_queries:
            try:
                cursor.execute(query)
                count = cursor.fetchone()[0]
                log(f"✓ {description}: {count}")
            except Exception as e:
                log(f"✗ {description} failed: {e}", "ERROR")
                all_good = False
        
        if all_good:
            log("\n✅ All wallet tables are fixed and working!")
        else:
            log("\n⚠️ Some issues remain, please check the errors above", "WARNING")
            
    except Exception as e:
        log(f"Critical error: {e}", "ERROR")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_wallet_tables()