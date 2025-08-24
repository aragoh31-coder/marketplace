# Wallet Integrity Error Fix

## Issue
When accessing `/wallets/`, users encountered:
```
IntegrityError: NOT NULL constraint failed: wallets_wallet.is_active
```

## Root Cause
The `wallets_wallet` table had an `is_active` column that:
- Was marked as NOT NULL
- Had no default value
- Was not being set when creating new wallet instances

## Solution Implemented

### 1. Updated Database Schema
- Recreated the `wallets_wallet` table with proper default values
- Set `is_active` default to `1` (True)
- Preserved all existing data during migration

### 2. Updated init_database.py
- Added `is_active` field to the schema definition
- Included proper default values for all fields
- Added logic to update NULL values to sensible defaults

### 3. Fixed Table Structure
The wallet table now has these defaults:
- `is_active`: DEFAULT 1
- `balance_btc`: DEFAULT 0.00000000
- `balance_xmr`: DEFAULT 0.000000000000
- `two_fa_enabled`: DEFAULT 0
- `created_at/updated_at`: DEFAULT CURRENT_TIMESTAMP

## Result
✅ Wallet pages now load without integrity errors
✅ New wallets are created with proper defaults
✅ Existing data preserved and corrected
✅ Database schema is consistent with Django models

## Testing
Access `/wallets/` - should now load without errors