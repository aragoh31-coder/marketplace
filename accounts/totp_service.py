import pyotp
import qrcode
import io
import base64
import secrets
from typing import List, Optional


class TOTPService:
    """Service for managing TOTP (Time-based One-Time Password) authentication"""
    
    @staticmethod
    def generate_secret() -> str:
        """Generate a new TOTP secret"""
        return pyotp.random_base32()
    
    @staticmethod
    def generate_backup_codes(count: int = 10) -> List[str]:
        """Generate backup codes for account recovery"""
        codes = []
        for _ in range(count):
            # Generate 8-character alphanumeric codes
            code = ''.join(secrets.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(8))
            # Format as XXXX-XXXX for readability
            formatted_code = f"{code[:4]}-{code[4:]}"
            codes.append(formatted_code)
        return codes
    
    @staticmethod
    def get_totp_uri(user, secret: str, issuer: str = "SecureMarket") -> str:
        """Get the TOTP URI for QR code generation"""
        return pyotp.totp.TOTP(secret).provisioning_uri(
            name=user.username,
            issuer_name=issuer
        )
    
    @staticmethod
    def generate_qr_code(uri: str) -> str:
        """Generate QR code as base64 string"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return base64.b64encode(buffer.getvalue()).decode()
    
    @staticmethod
    def verify_token(secret: str, token: str, window: int = 1) -> bool:
        """Verify a TOTP token"""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=window)
    
    @staticmethod
    def verify_backup_code(user, code: str) -> bool:
        """Verify and consume a backup code"""
        # Remove formatting from input code
        clean_code = code.replace('-', '').upper()
        
        # Check if code exists in user's backup codes
        for stored_code in user.totp_backup_codes:
            if stored_code.replace('-', '') == clean_code:
                # Remove used code
                user.totp_backup_codes.remove(stored_code)
                user.save()
                return True
        
        return False
    
    @staticmethod
    def setup_totp(user) -> dict:
        """Setup TOTP for a user and return setup data"""
        secret = TOTPService.generate_secret()
        backup_codes = TOTPService.generate_backup_codes()
        uri = TOTPService.get_totp_uri(user, secret)
        qr_code = TOTPService.generate_qr_code(uri)
        
        return {
            'secret': secret,
            'backup_codes': backup_codes,
            'uri': uri,
            'qr_code': qr_code
        }