"""
Enhanced security utilities for the marketplace
"""
import hashlib
import hmac
import secrets
import string
from typing import Optional, Tuple
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
import re


class SecurityValidator:
    """Validation utilities for security-critical operations"""
    
    # Regex patterns for validation
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]{3,30}$')
    BITCOIN_ADDRESS_PATTERN = re.compile(r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$|^bc1[a-z0-9]{39,59}$')
    MONERO_ADDRESS_PATTERN = re.compile(r'^4[0-9AB][0-9a-zA-Z]{93}$')
    
    @staticmethod
    def validate_username(username: str) -> bool:
        """Validate username format"""
        return bool(SecurityValidator.USERNAME_PATTERN.match(username))
    
    @staticmethod
    def validate_bitcoin_address(address: str) -> bool:
        """Validate Bitcoin address format"""
        return bool(SecurityValidator.BITCOIN_ADDRESS_PATTERN.match(address))
    
    @staticmethod
    def validate_monero_address(address: str) -> bool:
        """Validate Monero address format"""
        return bool(SecurityValidator.MONERO_ADDRESS_PATTERN.match(address))
    
    @staticmethod
    def validate_pgp_fingerprint(fingerprint: str) -> bool:
        """Validate PGP fingerprint format"""
        # Remove spaces and convert to uppercase
        fingerprint = fingerprint.replace(' ', '').upper()
        # Check if it's a valid 40-character hex string
        return len(fingerprint) == 40 and all(c in '0123456789ABCDEF' for c in fingerprint)
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 1000) -> str:
        """Sanitize user input for storage"""
        if not text:
            return ""
        
        # Strip whitespace
        text = text.strip()
        
        # Limit length
        text = text[:max_length]
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Remove control characters except newlines and tabs
        text = ''.join(char for char in text if char in ['\n', '\t'] or not char.isspace() or char.isprintable())
        
        return text


class TokenGenerator:
    """Generate secure tokens for various purposes"""
    
    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """Generate a cryptographically secure random token"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_numeric_code(length: int = 6) -> str:
        """Generate a numeric code (e.g., for 2FA)"""
        return ''.join(secrets.choice(string.digits) for _ in range(length))
    
    @staticmethod
    def generate_challenge_code(prefix: str = "CHALLENGE") -> str:
        """Generate a challenge code with prefix"""
        random_part = secrets.token_hex(8).upper()
        return f"{prefix}-{random_part[:4]}-{random_part[4:8]}-{random_part[8:12]}-{random_part[12:16]}"
    
    @staticmethod
    def generate_session_id() -> str:
        """Generate a secure session ID"""
        timestamp = str(int(timezone.now().timestamp()))
        random_part = secrets.token_hex(16)
        return hashlib.sha256(f"{timestamp}{random_part}".encode()).hexdigest()


class RateLimiter:
    """Advanced rate limiting utilities"""
    
    @staticmethod
    def get_rate_limit_key(identifier: str, action: str) -> str:
        """Generate rate limit cache key"""
        return f"rate_limit:{action}:{identifier}"
    
    @staticmethod
    def check_rate_limit(identifier: str, action: str, max_attempts: int, window_seconds: int) -> Tuple[bool, int]:
        """
        Check if rate limit is exceeded
        Returns: (is_allowed, remaining_attempts)
        """
        from django.core.cache import cache
        
        key = RateLimiter.get_rate_limit_key(identifier, action)
        current_attempts = cache.get(key, 0)
        
        if current_attempts >= max_attempts:
            return False, 0
        
        # Increment counter
        cache.set(key, current_attempts + 1, window_seconds)
        
        return True, max_attempts - current_attempts - 1
    
    @staticmethod
    def reset_rate_limit(identifier: str, action: str):
        """Reset rate limit for an identifier"""
        from django.core.cache import cache
        key = RateLimiter.get_rate_limit_key(identifier, action)
        cache.delete(key)


class PasswordStrengthChecker:
    """Check password strength and complexity"""
    
    MIN_LENGTH = 12
    
    @staticmethod
    def check_password_strength(password: str) -> Tuple[bool, list]:
        """
        Check password strength
        Returns: (is_strong, list_of_issues)
        """
        issues = []
        
        if len(password) < PasswordStrengthChecker.MIN_LENGTH:
            issues.append(f"Password must be at least {PasswordStrengthChecker.MIN_LENGTH} characters long")
        
        if not re.search(r'[A-Z]', password):
            issues.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            issues.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', password):
            issues.append("Password must contain at least one number")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            issues.append("Password must contain at least one special character")
        
        # Check for common patterns
        common_patterns = ['123', 'abc', 'password', 'qwerty', 'admin']
        for pattern in common_patterns:
            if pattern in password.lower():
                issues.append(f"Password contains common pattern: {pattern}")
                break
        
        return len(issues) == 0, issues


class HMACValidator:
    """HMAC validation for secure communication"""
    
    @staticmethod
    def generate_hmac(data: str, secret: str = None) -> str:
        """Generate HMAC for data"""
        if secret is None:
            secret = settings.SECRET_KEY
        
        return hmac.new(
            secret.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def verify_hmac(data: str, provided_hmac: str, secret: str = None) -> bool:
        """Verify HMAC for data"""
        expected_hmac = HMACValidator.generate_hmac(data, secret)
        return hmac.compare_digest(expected_hmac, provided_hmac)


class SessionSecurity:
    """Session security utilities"""
    
    @staticmethod
    def generate_session_fingerprint(request) -> str:
        """Generate browser fingerprint for session validation"""
        components = [
            request.META.get('HTTP_USER_AGENT', ''),
            request.META.get('HTTP_ACCEPT_LANGUAGE', ''),
            request.META.get('HTTP_ACCEPT_ENCODING', ''),
            # Don't use IP for Tor compatibility
        ]
        
        fingerprint_data = '|'.join(components)
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()
    
    @staticmethod
    def validate_session_fingerprint(request, stored_fingerprint: str) -> bool:
        """Validate session fingerprint matches"""
        current_fingerprint = SessionSecurity.generate_session_fingerprint(request)
        return hmac.compare_digest(current_fingerprint, stored_fingerprint)


class AntiPhishingCode:
    """Anti-phishing code generation and validation"""
    
    @staticmethod
    def generate_code(user_id: str) -> str:
        """Generate unique anti-phishing code for user"""
        # Use user ID and secret to generate consistent code
        data = f"{user_id}:{settings.SECRET_KEY}"
        hash_value = hashlib.sha256(data.encode()).hexdigest()
        
        # Take first 6 characters and format nicely
        return f"{hash_value[:3].upper()}-{hash_value[3:6].upper()}"
    
    @staticmethod
    def verify_code(user_id: str, provided_code: str) -> bool:
        """Verify anti-phishing code"""
        expected_code = AntiPhishingCode.generate_code(user_id)
        return hmac.compare_digest(expected_code, provided_code)