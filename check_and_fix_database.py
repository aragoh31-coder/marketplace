#!/usr/bin/env python
"""
Database Health Check and Auto-Fix Script
Checks for missing tables, columns, and integrity issues
"""

import os
import sys
import sqlite3
from datetime import datetime

# Add the project to the Python path
sys.path.insert(0, '/workspace')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'marketplace.settings')

import django
django.setup()

from django.apps import apps
from django.db import connection

class DatabaseChecker:
    def __init__(self):
        self.conn = sqlite3.connect('/workspace/db.sqlite3')
        self.cursor = self.conn.cursor()
        self.errors = []
        self.fixes_applied = []
        
    def log(self, message, level="INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def check_table_exists(self, table_name):
        """Check if a table exists in the database"""
        self.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        return self.cursor.fetchone() is not None
    
    def get_table_columns(self, table_name):
        """Get all columns for a table"""
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        return {row[1]: {
            'type': row[2],
            'notnull': row[3],
            'default': row[4],
            'pk': row[5]
        } for row in self.cursor.fetchall()}
    
    def check_all_models(self):
        """Check all Django models against database schema"""
        self.log("Starting comprehensive database check...")
        
        for app_config in apps.get_app_configs():
            for model in app_config.get_models():
                table_name = model._meta.db_table
                
                # Check if table exists
                if not self.check_table_exists(table_name):
                    self.errors.append(f"Missing table: {table_name}")
                    self.create_table_for_model(model)
                else:
                    # Check columns
                    self.check_model_columns(model)
        
    def check_model_columns(self, model):
        """Check if all model fields exist in database"""
        table_name = model._meta.db_table
        db_columns = self.get_table_columns(table_name)
        
        for field in model._meta.fields:
            column_name = field.column
            
            if column_name not in db_columns:
                self.errors.append(f"Missing column: {table_name}.{column_name}")
                self.add_missing_column(table_name, field)
                
    def create_table_for_model(self, model):
        """Create missing table based on Django model"""
        table_name = model._meta.db_table
        self.log(f"Creating missing table: {table_name}", "WARNING")
        
        # Generate CREATE TABLE statement
        columns = []
        foreign_keys = []
        
        for field in model._meta.fields:
            col_def = self.get_column_definition(field)
            columns.append(col_def)
            
            if field.remote_field:
                fk_table = field.remote_field.model._meta.db_table
                fk_column = field.remote_field.model._meta.pk.column
                foreign_keys.append(
                    f"FOREIGN KEY ({field.column}) REFERENCES {fk_table} ({fk_column})"
                )
        
        sql = f"CREATE TABLE {table_name} (\n"
        sql += ",\n".join(columns)
        if foreign_keys:
            sql += ",\n" + ",\n".join(foreign_keys)
        sql += "\n)"
        
        try:
            self.cursor.execute(sql)
            self.conn.commit()
            self.fixes_applied.append(f"Created table: {table_name}")
        except Exception as e:
            self.log(f"Failed to create table {table_name}: {e}", "ERROR")
            
    def add_missing_column(self, table_name, field):
        """Add missing column to existing table"""
        column_name = field.column
        col_def = self.get_column_definition(field, for_alter=True)
        
        sql = f"ALTER TABLE {table_name} ADD COLUMN {col_def}"
        
        try:
            self.cursor.execute(sql)
            self.conn.commit()
            self.fixes_applied.append(f"Added column: {table_name}.{column_name}")
        except Exception as e:
            self.log(f"Failed to add column {table_name}.{column_name}: {e}", "ERROR")
            
    def get_column_definition(self, field, for_alter=False):
        """Generate SQL column definition for a Django field"""
        column_name = field.column
        field_type = field.__class__.__name__
        
        # Map Django field types to SQLite types
        if field_type in ['AutoField', 'BigAutoField']:
            sql_type = 'INTEGER PRIMARY KEY AUTOINCREMENT' if not for_alter else 'INTEGER'
        elif field_type in ['CharField', 'EmailField', 'URLField']:
            max_length = getattr(field, 'max_length', 255)
            sql_type = f'VARCHAR({max_length})'
        elif field_type == 'TextField':
            sql_type = 'TEXT'
        elif field_type in ['IntegerField', 'BigIntegerField', 'SmallIntegerField']:
            sql_type = 'INTEGER'
        elif field_type == 'DecimalField':
            sql_type = f'DECIMAL({field.max_digits}, {field.decimal_places})'
        elif field_type == 'FloatField':
            sql_type = 'REAL'
        elif field_type == 'BooleanField':
            sql_type = 'BOOLEAN'
        elif field_type == 'DateField':
            sql_type = 'DATE'
        elif field_type == 'DateTimeField':
            sql_type = 'DATETIME'
        elif field_type == 'TimeField':
            sql_type = 'TIME'
        elif field_type in ['ForeignKey', 'OneToOneField']:
            sql_type = 'CHAR(32)' if hasattr(field.remote_field.model._meta.pk, 'max_length') else 'INTEGER'
        elif field_type == 'JSONField':
            sql_type = 'TEXT'
        elif field_type == 'UUIDField':
            sql_type = 'CHAR(32)'
        else:
            sql_type = 'TEXT'
        
        col_def = f"{column_name} {sql_type}"
        
        # Handle NULL/NOT NULL
        if not field.null and not field.primary_key:
            col_def += " NOT NULL"
            
        # Handle defaults
        if field.has_default():
            default = field.get_default()
            if default is not None:
                if isinstance(default, bool):
                    default = 1 if default else 0
                elif isinstance(default, str):
                    default = f"'{default}'"
                elif hasattr(default, '__call__'):
                    # Skip callable defaults
                    pass
                else:
                    col_def += f" DEFAULT {default}"
                    
        return col_def
    
    def check_critical_tables(self):
        """Check specific critical tables that often cause issues"""
        critical_tables = {
            'wallets_wallet': {
                'columns': {
                    'id': 'INTEGER PRIMARY KEY',
                    'user_id': 'CHAR(32) UNIQUE NOT NULL',
                    'balance_btc': 'DECIMAL(16,8) DEFAULT 0.00000000',
                    'balance_xmr': 'DECIMAL(16,12) DEFAULT 0.000000000000',
                    'escrow_btc': 'DECIMAL(16,8) DEFAULT 0.00000000',
                    'escrow_xmr': 'DECIMAL(16,12) DEFAULT 0.000000000000',
                    'withdrawal_pin': 'VARCHAR(128)',
                    'two_fa_enabled': 'BOOLEAN DEFAULT 0',
                    'two_fa_secret': 'VARCHAR(32)',
                    'daily_withdrawal_limit_btc': 'DECIMAL(16,8) DEFAULT 1.00000000',
                    'daily_withdrawal_limit_xmr': 'DECIMAL(16,12) DEFAULT 100.000000000000',
                    'created_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP',
                    'updated_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP',
                    'last_activity': 'DATETIME',
                    'is_active': 'BOOLEAN DEFAULT 1',
                    'currency': 'VARCHAR(3)',
                    'address': 'VARCHAR(255)',
                    'private_key': 'TEXT',
                    'balance': 'DECIMAL'
                }
            },
            'wallets_walletbalancecheck': {
                'columns': {
                    'id': 'INTEGER PRIMARY KEY',
                    'wallet_id': 'INTEGER NOT NULL',
                    'expected_btc': 'DECIMAL(16,8) NOT NULL',
                    'expected_xmr': 'DECIMAL(16,12) NOT NULL',
                    'expected_escrow_btc': 'DECIMAL(16,8) NOT NULL',
                    'expected_escrow_xmr': 'DECIMAL(16,12) NOT NULL',
                    'actual_btc': 'DECIMAL(16,8) NOT NULL',
                    'actual_xmr': 'DECIMAL(16,12) NOT NULL',
                    'actual_escrow_btc': 'DECIMAL(16,8) NOT NULL',
                    'actual_escrow_xmr': 'DECIMAL(16,12) NOT NULL',
                    'discrepancy_found': 'BOOLEAN DEFAULT 0',
                    'discrepancy_details': 'TEXT DEFAULT \'{}\'',
                    'resolved': 'BOOLEAN DEFAULT 0',
                    'resolved_by_id': 'CHAR(32)',
                    'resolution_notes': 'TEXT',
                    'checked_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP',
                    'resolved_at': 'DATETIME'
                }
            },
            'wallets_withdrawalrequest': {
                'columns': {
                    'id': 'INTEGER PRIMARY KEY',
                    'request_id': 'VARCHAR(64) UNIQUE NOT NULL',
                    'user_id': 'CHAR(32) NOT NULL',
                    'currency': 'VARCHAR(3) NOT NULL',
                    'amount': 'DECIMAL(16,8) NOT NULL',
                    'fee': 'DECIMAL(16,8) DEFAULT 0',
                    'to_address': 'VARCHAR(255) NOT NULL',
                    'memo': 'TEXT',
                    'status': 'VARCHAR(20) DEFAULT \'pending\'',
                    'pin_verified': 'BOOLEAN DEFAULT 0',
                    'two_fa_verified': 'BOOLEAN DEFAULT 0',
                    'admin_approved': 'BOOLEAN DEFAULT 0',
                    'admin_notes': 'TEXT',
                    'blockchain_txid': 'VARCHAR(128)',
                    'created_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP',
                    'updated_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP',
                    'processed_at': 'DATETIME',
                    'cancelled_at': 'DATETIME',
                    'cancellation_reason': 'TEXT',
                    'security_checks': 'TEXT DEFAULT \'{}\'',
                    'risk_score': 'INTEGER DEFAULT 0'
                }
            },
            'wallets_transaction': {
                'columns': {
                    'id': 'INTEGER PRIMARY KEY',
                    'transaction_id': 'VARCHAR(64) UNIQUE NOT NULL',
                    'user_id': 'CHAR(32) NOT NULL',
                    'wallet_id': 'INTEGER',
                    'transaction_type': 'VARCHAR(20) NOT NULL',
                    'currency': 'VARCHAR(3) NOT NULL',
                    'amount': 'DECIMAL(16,8) NOT NULL',
                    'fee': 'DECIMAL(16,8) DEFAULT 0',
                    'status': 'VARCHAR(20) NOT NULL',
                    'blockchain_txid': 'VARCHAR(128)',
                    'from_address': 'VARCHAR(255)',
                    'to_address': 'VARCHAR(255)',
                    'memo': 'TEXT',
                    'created_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP',
                    'updated_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP',
                    'processed_at': 'DATETIME',
                    'confirmations': 'INTEGER DEFAULT 0',
                    'error_message': 'TEXT'
                }
            },
            'wallets_conversionrate': {
                'columns': {
                    'id': 'INTEGER PRIMARY KEY',
                    'from_currency': 'VARCHAR(3) NOT NULL',
                    'to_currency': 'VARCHAR(3) NOT NULL',
                    'rate': 'DECIMAL(16,8) NOT NULL',
                    'fee_percentage': 'DECIMAL(5,2) DEFAULT 0.5',
                    'min_amount': 'DECIMAL(16,8) DEFAULT 0.0001',
                    'max_amount': 'DECIMAL(16,8) DEFAULT 10',
                    'enabled': 'BOOLEAN DEFAULT 1',
                    'updated_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP'
                }
            },
            'wallets_auditlog': {
                'columns': {
                    'id': 'INTEGER PRIMARY KEY',
                    'user_id': 'CHAR(32) NOT NULL',
                    'action': 'VARCHAR(100) NOT NULL',
                    'ip_address': 'VARCHAR(45)',
                    'user_agent': 'TEXT',
                    'details': 'TEXT DEFAULT \'{}\'',
                    'suspicious': 'BOOLEAN DEFAULT 0',
                    'risk_score': 'INTEGER DEFAULT 0',
                    'created_at': 'DATETIME DEFAULT CURRENT_TIMESTAMP'
                }
            }
        }
        
        for table_name, table_spec in critical_tables.items():
            if not self.check_table_exists(table_name):
                self.log(f"Creating critical table: {table_name}", "WARNING")
                self.create_critical_table(table_name, table_spec['columns'])
            else:
                # Check columns
                db_columns = self.get_table_columns(table_name)
                for col_name, col_type in table_spec['columns'].items():
                    if col_name not in db_columns:
                        self.log(f"Adding missing column: {table_name}.{col_name}", "WARNING")
                        try:
                            self.cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
                            self.conn.commit()
                            self.fixes_applied.append(f"Added column: {table_name}.{col_name}")
                        except Exception as e:
                            self.log(f"Failed to add column: {e}", "ERROR")
    
    def create_critical_table(self, table_name, columns):
        """Create a critical table with specified columns"""
        col_defs = [f"{name} {type}" for name, type in columns.items()]
        sql = f"CREATE TABLE {table_name} (\n  " + ",\n  ".join(col_defs) + "\n)"
        
        try:
            self.cursor.execute(sql)
            self.conn.commit()
            self.fixes_applied.append(f"Created table: {table_name}")
        except Exception as e:
            self.log(f"Failed to create table {table_name}: {e}", "ERROR")
    
    def run_full_check(self):
        """Run complete database health check and fixes"""
        self.log("=" * 60)
        self.log("DATABASE HEALTH CHECK AND AUTO-FIX")
        self.log("=" * 60)
        
        # Check critical tables first
        self.log("\n1. Checking critical tables...")
        self.check_critical_tables()
        
        # Check all Django models
        self.log("\n2. Checking all Django models...")
        self.check_all_models()
        
        # Test queries
        self.log("\n3. Testing critical queries...")
        self.test_critical_queries()
        
        # Summary
        self.log("\n" + "=" * 60)
        self.log("SUMMARY")
        self.log("=" * 60)
        
        if self.errors:
            self.log(f"Errors found: {len(self.errors)}", "WARNING")
            for error in self.errors:
                self.log(f"  - {error}", "WARNING")
        else:
            self.log("No errors found!", "SUCCESS")
            
        if self.fixes_applied:
            self.log(f"\nFixes applied: {len(self.fixes_applied)}", "SUCCESS")
            for fix in self.fixes_applied:
                self.log(f"  - {fix}", "SUCCESS")
        else:
            self.log("\nNo fixes needed.", "SUCCESS")
            
    def test_critical_queries(self):
        """Test critical queries that often fail"""
        test_queries = [
            ("SELECT COUNT(*) FROM wallets_wallet", "Wallet count"),
            ("SELECT COUNT(*) FROM wallets_transaction", "Transaction count"),
            ("SELECT COUNT(*) FROM wallets_withdrawalrequest", "Withdrawal request count"),
            ("SELECT COUNT(*) FROM wallets_walletbalancecheck", "Balance check count"),
            ("SELECT COUNT(*) FROM accounts_user", "User count"),
        ]
        
        for query, description in test_queries:
            try:
                self.cursor.execute(query)
                count = self.cursor.fetchone()[0]
                self.log(f"✓ {description}: {count}")
            except Exception as e:
                self.log(f"✗ {description} failed: {e}", "ERROR")
                self.errors.append(f"Query failed: {description}")
    
    def close(self):
        """Close database connection"""
        self.conn.close()

if __name__ == "__main__":
    checker = DatabaseChecker()
    try:
        checker.run_full_check()
    finally:
        checker.close()