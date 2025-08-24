"""
Input validation utilities for security
"""
import re
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from decimal import Decimal, InvalidOperation


class InputValidator:
    """Central input validation class"""
    
    # Regex patterns
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{3,30}$')
    BITCOIN_ADDRESS_PATTERN = re.compile(r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$|^bc1[a-z0-9]{39,59}$')
    MONERO_ADDRESS_PATTERN = re.compile(r'^4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}$')
    PGP_KEY_PATTERN = re.compile(r'^-----BEGIN PGP PUBLIC KEY BLOCK-----[\s\S]+-----END PGP PUBLIC KEY BLOCK-----$')
    
    @staticmethod
    def validate_username(username):
        """Validate username format"""
        if not username or not InputValidator.USERNAME_PATTERN.match(username):
            raise ValidationError(
                "Username must be 3-30 characters, containing only letters, numbers, underscore and hyphen"
            )
        return username
    
    @staticmethod
    def validate_bitcoin_address(address):
        """Validate Bitcoin address format"""
        if not address or not InputValidator.BITCOIN_ADDRESS_PATTERN.match(address):
            raise ValidationError("Invalid Bitcoin address format")
        return address
    
    @staticmethod
    def validate_monero_address(address):
        """Validate Monero address format"""
        if not address or not InputValidator.MONERO_ADDRESS_PATTERN.match(address):
            raise ValidationError("Invalid Monero address format")
        return address
    
    @staticmethod
    def validate_cryptocurrency_address(address, currency):
        """Validate cryptocurrency address based on currency"""
        if currency.upper() == 'BTC':
            return InputValidator.validate_bitcoin_address(address)
        elif currency.upper() == 'XMR':
            return InputValidator.validate_monero_address(address)
        else:
            raise ValidationError(f"Unsupported currency: {currency}")
    
    @staticmethod
    def validate_pgp_key(key):
        """Validate PGP public key format"""
        if not key:
            raise ValidationError("PGP key is required")
        
        # Remove extra whitespace
        key = key.strip()
        
        if not InputValidator.PGP_KEY_PATTERN.match(key):
            raise ValidationError("Invalid PGP public key format")
        
        # Check key block structure
        if key.count('-----BEGIN PGP PUBLIC KEY BLOCK-----') != 1:
            raise ValidationError("Multiple key blocks not allowed")
        
        return key
    
    @staticmethod
    def validate_amount(amount, min_amount=Decimal('0.00000001'), max_amount=Decimal('21000000')):
        """Validate cryptocurrency amount"""
        try:
            amount = Decimal(str(amount))
        except (InvalidOperation, ValueError):
            raise ValidationError("Invalid amount format")
        
        if amount <= 0:
            raise ValidationError("Amount must be positive")
        
        if amount < min_amount:
            raise ValidationError(f"Amount must be at least {min_amount}")
        
        if amount > max_amount:
            raise ValidationError(f"Amount cannot exceed {max_amount}")
        
        return amount
    
    @staticmethod
    def validate_product_name(name):
        """Validate product name"""
        if not name or len(name) < 3:
            raise ValidationError("Product name must be at least 3 characters")
        
        if len(name) > 200:
            raise ValidationError("Product name cannot exceed 200 characters")
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'<script',
            r'javascript:',
            r'data:text/html',
            r'vbscript:',
            r'onload=',
            r'onerror=',
            r'onclick='
        ]
        
        name_lower = name.lower()
        for pattern in suspicious_patterns:
            if re.search(pattern, name_lower):
                raise ValidationError("Product name contains invalid content")
        
        return name
    
    @staticmethod
    def validate_description(text, max_length=5000):
        """Validate description text"""
        if not text:
            return text
        
        if len(text) > max_length:
            raise ValidationError(f"Description cannot exceed {max_length} characters")
        
        # Check for malicious content
        if '<script' in text.lower() or 'javascript:' in text.lower():
            raise ValidationError("Description contains invalid content")
        
        return text
    
    @staticmethod
    def validate_quantity(quantity, max_quantity=10000):
        """Validate product quantity"""
        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            raise ValidationError("Quantity must be a whole number")
        
        if quantity <= 0:
            raise ValidationError("Quantity must be positive")
        
        if quantity > max_quantity:
            raise ValidationError(f"Quantity cannot exceed {max_quantity}")
        
        return quantity
    
    @staticmethod
    def sanitize_search_query(query):
        """Sanitize search query for safety"""
        if not query:
            return ""
        
        # Remove potentially dangerous characters
        query = re.sub(r'[<>\"\'%;()&+]', '', query)
        
        # Limit length
        query = query[:200]
        
        # Remove extra whitespace
        query = ' '.join(query.split())
        
        return query
    
    @staticmethod
    def validate_order_status(status):
        """Validate order status value"""
        valid_statuses = [
            'created', 'paid', 'shipped', 'completed', 
            'cancelled', 'refunded', 'disputed'
        ]
        
        if status not in valid_statuses:
            raise ValidationError(f"Invalid order status: {status}")
        
        return status
    
    @staticmethod
    def validate_currency_code(currency):
        """Validate currency code"""
        valid_currencies = ['BTC', 'XMR']
        
        currency = currency.upper()
        if currency not in valid_currencies:
            raise ValidationError(f"Invalid currency: {currency}")
        
        return currency
    
    @staticmethod
    def validate_pin(pin):
        """Validate withdrawal PIN"""
        if not pin or len(pin) < 4:
            raise ValidationError("PIN must be at least 4 characters")
        
        if len(pin) > 20:
            raise ValidationError("PIN cannot exceed 20 characters")
        
        if not re.match(r'^[0-9]+$', pin):
            raise ValidationError("PIN must contain only numbers")
        
        return pin