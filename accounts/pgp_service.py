import gnupg
import tempfile
import os
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class PGPService:
    def __init__(self):
        """Initialize PGP service with temporary GPG directory"""
        self.temp_dir = tempfile.mkdtemp(prefix='marketplace_gpg_')
        self.gpg = gnupg.GPG(gnupghome=self.temp_dir)
        
        if hasattr(settings, 'GPG_BINARY'):
            self.gpg.gpgbinary = settings.GPG_BINARY
        
        logger.debug(f"PGP Service initialized with temp dir: {self.temp_dir}")
        logger.debug(f"GPG Version: {self.gpg.version}")
    
    def __del__(self):
        """Clean up temporary directory"""
        try:
            import shutil
            if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.debug(f"Cleaned up temp dir: {self.temp_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up temp dir: {e}")
    
    def import_public_key(self, public_key_data):
        """
        Import a public key and return import result
        
        Args:
            public_key_data (str): PGP public key block
            
        Returns:
            dict: Import result with success status and details
        """
        try:
            logger.debug("Importing public key...")
            import_result = self.gpg.import_keys(public_key_data)
            
            if import_result.count > 0:
                fingerprint = import_result.fingerprints[0] if import_result.fingerprints else None
                logger.info(f"Successfully imported key with fingerprint: {fingerprint}")
                
                return {
                    'success': True,
                    'fingerprint': fingerprint,
                    'count': import_result.count,
                    'message': f'Successfully imported {import_result.count} key(s)'
                }
            else:
                logger.warning("No keys were imported")
                return {
                    'success': False,
                    'error': 'No keys were imported',
                    'details': str(import_result.stderr) if hasattr(import_result, 'stderr') else 'Unknown error'
                }
                
        except Exception as e:
            logger.error(f"Error importing public key: {e}")
            return {
                'success': False,
                'error': f'Import failed: {str(e)}'
            }
    
    def encrypt_message(self, message, recipient_fingerprint):
        """
        Encrypt a message for a specific recipient
        
        Args:
            message (str): Plain text message to encrypt
            recipient_fingerprint (str): Recipient's key fingerprint
            
        Returns:
            dict: Encryption result with success status and encrypted message
        """
        try:
            logger.debug(f"Encrypting message for fingerprint: {recipient_fingerprint}")
            
            encrypted_data = self.gpg.encrypt(
                message, 
                recipients=[recipient_fingerprint],
                always_trust=True  # Trust imported keys
            )
            
            if encrypted_data.ok:
                encrypted_message = str(encrypted_data)
                logger.info("Message encrypted successfully")
                logger.debug(f"Encrypted message length: {len(encrypted_message)} bytes")
                
                if encrypted_message.startswith('-----BEGIN PGP MESSAGE-----'):
                    return {
                        'success': True,
                        'encrypted_message': encrypted_message,
                        'fingerprint': recipient_fingerprint
                    }
                else:
                    logger.error("Encrypted data is not in proper PGP format")
                    return {
                        'success': False,
                        'error': 'Encrypted data is not in proper PGP format'
                    }
            else:
                logger.error(f"Encryption failed: {encrypted_data.stderr}")
                return {
                    'success': False,
                    'error': f'Encryption failed: {encrypted_data.stderr}'
                }
                
        except Exception as e:
            logger.error(f"Error encrypting message: {e}")
            return {
                'success': False,
                'error': f'Encryption error: {str(e)}'
            }
    
    def verify_signature(self, signed_message):
        """
        Verify a PGP signed message
        
        Args:
            signed_message (str): PGP signed message
            
        Returns:
            dict: Verification result with success status and details
        """
        try:
            logger.debug("Verifying PGP signature...")
            
            verified = self.gpg.verify(signed_message)
            
            if verified.valid:
                logger.info(f"Signature verified successfully for key: {verified.key_id}")
                return {
                    'success': True,
                    'valid': True,
                    'key_id': verified.key_id,
                    'fingerprint': verified.fingerprint,
                    'username': verified.username,
                    'message': 'Signature is valid'
                }
            else:
                logger.warning(f"Signature verification failed: {verified.stderr}")
                return {
                    'success': True,
                    'valid': False,
                    'error': verified.stderr or 'Invalid signature',
                    'message': 'Signature is invalid'
                }
                
        except Exception as e:
            logger.error(f"Error verifying signature: {e}")
            return {
                'success': False,
                'error': f'Verification error: {str(e)}'
            }
    
    def extract_message_from_signature(self, signed_message):
        """
        Extract the original message from a clearsigned PGP message
        
        Args:
            signed_message (str): PGP clearsigned message
            
        Returns:
            dict: Extraction result with success status and message
        """
        try:
            logger.debug("Extracting message from PGP signature...")
            
            verification_result = self.verify_signature(signed_message)
            
            if not verification_result['success'] or not verification_result.get('valid'):
                return {
                    'success': False,
                    'error': 'Invalid signature - cannot extract message'
                }
            
            lines = signed_message.split('\n')
            message_lines = []
            in_message = False
            
            for line in lines:
                if line.startswith('-----BEGIN PGP SIGNED MESSAGE-----'):
                    in_message = True
                    continue
                elif line.startswith('-----BEGIN PGP SIGNATURE-----'):
                    break
                elif in_message and line.startswith('Hash: '):
                    continue
                elif in_message and line.strip() == '':
                    if message_lines:  # Skip empty line after headers
                        message_lines.append(line)
                elif in_message:
                    message_lines.append(line)
            
            extracted_message = '\n'.join(message_lines).strip()
            
            logger.info("Message extracted successfully from signature")
            logger.debug(f"Extracted message: {extracted_message[:100]}...")
            
            return {
                'success': True,
                'message': extracted_message,
                'verification': verification_result
            }
            
        except Exception as e:
            logger.error(f"Error extracting message from signature: {e}")
            return {
                'success': False,
                'error': f'Extraction error: {str(e)}'
            }
    
    def get_key_info(self, fingerprint):
        """
        Get information about a key by fingerprint
        
        Args:
            fingerprint (str): Key fingerprint
            
        Returns:
            dict: Key information
        """
        try:
            keys = self.gpg.list_keys()
            for key in keys:
                if key['fingerprint'] == fingerprint:
                    return {
                        'success': True,
                        'fingerprint': key['fingerprint'],
                        'keyid': key['keyid'],
                        'uids': key['uids'],
                        'length': key['length'],
                        'algo': key['algo'],
                        'expires': key['expires'],
                        'trust': key['trust']
                    }
            
            return {
                'success': False,
                'error': 'Key not found'
            }
            
        except Exception as e:
            logger.error(f"Error getting key info: {e}")
            return {
                'success': False,
                'error': f'Key info error: {str(e)}'
            }
