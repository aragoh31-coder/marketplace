"""
Advanced Anti-DDoS Protection System with Stateless Verification
Implements:
- HMAC-chained challenges (no session storage)
- Blind Token Bucket with cryptographic tickets
- Proof of Work (PoW) challenges
- Tor circuit awareness
"""
import hashlib
import hmac
import time
import json
import secrets
import struct
from typing import Dict, Tuple, Optional, List
from datetime import datetime, timedelta
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger('marketplace.security.ddos.advanced')


class ProofOfWork:
    """Proof of Work implementation for DDoS protection"""
    
    @staticmethod
    def generate_challenge(difficulty: int = 4) -> Dict[str, str]:
        """Generate a PoW challenge
        
        Args:
            difficulty: Number of leading zeros required in hash
            
        Returns:
            Dict with challenge data
        """
        challenge_id = secrets.token_hex(16)
        timestamp = int(time.time())
        
        # Create challenge string
        challenge = f"{challenge_id}:{timestamp}:{difficulty}"
        
        # Sign challenge with HMAC
        signature = hmac.new(
            settings.SECRET_KEY.encode(),
            challenge.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return {
            'challenge': challenge,
            'signature': signature,
            'difficulty': difficulty,
            'timestamp': timestamp,
            'expires': timestamp + 300  # 5 minute expiry
        }
    
    @staticmethod
    def verify_solution(challenge: str, signature: str, nonce: str) -> bool:
        """Verify a PoW solution
        
        Args:
            challenge: The original challenge string
            signature: HMAC signature of challenge
            nonce: The solution nonce
            
        Returns:
            True if valid solution
        """
        # Verify challenge signature
        expected_sig = hmac.new(
            settings.SECRET_KEY.encode(),
            challenge.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(expected_sig, signature):
            logger.warning("Invalid PoW challenge signature")
            return False
        
        # Parse challenge
        try:
            challenge_id, timestamp, difficulty = challenge.split(':')
            timestamp = int(timestamp)
            difficulty = int(difficulty)
        except ValueError:
            logger.warning("Malformed PoW challenge")
            return False
        
        # Check expiry
        if time.time() > timestamp + 300:  # 5 minute expiry
            logger.warning("Expired PoW challenge")
            return False
        
        # Verify solution
        solution = f"{challenge}:{nonce}"
        hash_result = hashlib.sha256(solution.encode()).hexdigest()
        
        # Check if hash has required number of leading zeros
        required_prefix = '0' * difficulty
        if hash_result.startswith(required_prefix):
            logger.info(f"Valid PoW solution found: {hash_result[:8]}...")
            return True
        
        return False


class BlindTokenBucket:
    """Blind Token Bucket implementation with HMAC-signed tickets"""
    
    TOKEN_VALIDITY = 3600  # 1 hour
    
    @staticmethod
    def generate_token(session_id: str, metadata: Dict = None) -> str:
        """Generate a blind token for rate limiting
        
        Args:
            session_id: Session identifier
            metadata: Optional metadata to include in token
            
        Returns:
            Signed token string
        """
        timestamp = int(time.time())
        expires = timestamp + BlindTokenBucket.TOKEN_VALIDITY
        
        # Create token payload
        payload = {
            'session_id': session_id,
            'issued_at': timestamp,
            'expires_at': expires,
            'metadata': metadata or {}
        }
        
        # Serialize payload
        payload_json = json.dumps(payload, sort_keys=True)
        
        # Create HMAC signature
        signature = hmac.new(
            settings.SECRET_KEY.encode(),
            payload_json.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Combine payload and signature
        token = f"{payload_json}:{signature}"
        
        # Base64 encode for URL safety
        import base64
        return base64.urlsafe_b64encode(token.encode()).decode()
    
    @staticmethod
    def verify_token(token: str) -> Tuple[bool, Optional[Dict]]:
        """Verify and decode a blind token
        
        Args:
            token: The token to verify
            
        Returns:
            Tuple of (is_valid, payload_dict)
        """
        try:
            # Base64 decode
            import base64
            decoded = base64.urlsafe_b64decode(token.encode()).decode()
            
            # Split payload and signature
            payload_json, signature = decoded.rsplit(':', 1)
            
            # Verify signature
            expected_sig = hmac.new(
                settings.SECRET_KEY.encode(),
                payload_json.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(expected_sig, signature):
                logger.warning("Invalid token signature")
                return False, None
            
            # Parse payload
            payload = json.loads(payload_json)
            
            # Check expiry
            if time.time() > payload.get('expires_at', 0):
                logger.warning("Expired token")
                return False, None
            
            return True, payload
            
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return False, None
    
    @staticmethod
    def consume_token(token: str, action: str) -> bool:
        """Consume a token for a specific action
        
        Args:
            token: The token to consume
            action: The action being performed
            
        Returns:
            True if token was valid and consumed
        """
        is_valid, payload = BlindTokenBucket.verify_token(token)
        if not is_valid:
            return False
        
        # Check if token has already been used for this action
        token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
        used_key = f"token:used:{token_hash}:{action}"
        
        if cache.get(used_key):
            logger.warning(f"Token already used for action: {action}")
            return False
        
        # Mark token as used for this action
        ttl = payload['expires_at'] - int(time.time())
        cache.set(used_key, True, ttl)
        
        return True


class HMACChallengeChain:
    """Stateless HMAC-chained challenge system"""
    
    @staticmethod
    def generate_challenge(session_id: str, challenge_type: str = 'math') -> Dict:
        """Generate a stateless challenge with HMAC verification
        
        Args:
            session_id: Session identifier
            challenge_type: Type of challenge (math, visual, pow)
            
        Returns:
            Challenge dictionary with HMAC signature
        """
        timestamp = int(time.time())
        nonce = secrets.token_hex(8)
        
        if challenge_type == 'math':
            # Generate math challenge
            import random
            num1 = random.randint(10, 99)
            num2 = random.randint(10, 99)
            operation = random.choice(['+', '-', '*'])
            
            if operation == '+':
                answer = num1 + num2
                question = f"{num1} + {num2}"
            elif operation == '-':
                answer = num1 - num2
                question = f"{num1} - {num2}"
            else:  # multiplication
                answer = num1 * num2
                question = f"{num1} × {num2}"
            
            # Create challenge data
            challenge_data = {
                'type': 'math',
                'session_id': session_id,
                'timestamp': timestamp,
                'nonce': nonce,
                'question': question,
                'answer': answer
            }
        
        elif challenge_type == 'pow':
            # Generate PoW challenge
            pow_challenge = ProofOfWork.generate_challenge()
            challenge_data = {
                'type': 'pow',
                'session_id': session_id,
                'timestamp': timestamp,
                'nonce': nonce,
                'pow_data': pow_challenge
            }
        
        else:
            raise ValueError(f"Unknown challenge type: {challenge_type}")
        
        # Create HMAC of challenge data
        challenge_json = json.dumps(challenge_data, sort_keys=True)
        challenge_hmac = hmac.new(
            settings.SECRET_KEY.encode(),
            challenge_json.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Return public challenge info (without answer)
        public_data = challenge_data.copy()
        if 'answer' in public_data:
            del public_data['answer']
        
        return {
            'challenge': public_data,
            'hmac': challenge_hmac,
            'expires': timestamp + 300  # 5 minute expiry
        }
    
    @staticmethod
    def verify_challenge(session_id: str, challenge_data: Dict, 
                        challenge_hmac: str, user_answer: str) -> Tuple[bool, Optional[str]]:
        """Verify a challenge response without session storage
        
        Args:
            session_id: Session identifier
            challenge_data: The challenge data
            challenge_hmac: HMAC signature of challenge
            user_answer: User's answer to challenge
            
        Returns:
            Tuple of (is_valid, next_token)
        """
        # Verify timestamp
        timestamp = challenge_data.get('timestamp', 0)
        if time.time() > timestamp + 300:  # 5 minute expiry
            logger.warning("Expired challenge")
            return False, None
        
        # Verify session matches
        if challenge_data.get('session_id') != session_id:
            logger.warning("Session mismatch in challenge")
            return False, None
        
        # Reconstruct and verify challenge based on type
        if challenge_data.get('type') == 'math':
            # For math challenges, we need to reconstruct with answer
            try:
                # Parse the question to get the answer
                question = challenge_data.get('question', '')
                if ' + ' in question:
                    parts = question.split(' + ')
                    answer = int(parts[0]) + int(parts[1])
                elif ' - ' in question:
                    parts = question.split(' - ')
                    answer = int(parts[0]) - int(parts[1])
                elif ' × ' in question:
                    parts = question.split(' × ')
                    answer = int(parts[0]) * int(parts[1])
                else:
                    return False, None
                
                # Verify user answer
                if str(answer) != str(user_answer):
                    logger.warning("Incorrect challenge answer")
                    return False, None
                
                # Reconstruct full challenge data
                full_data = challenge_data.copy()
                full_data['answer'] = answer
                
                # Verify HMAC
                challenge_json = json.dumps(full_data, sort_keys=True)
                expected_hmac = hmac.new(
                    settings.SECRET_KEY.encode(),
                    challenge_json.encode(),
                    hashlib.sha256
                ).hexdigest()
                
                if not hmac.compare_digest(expected_hmac, challenge_hmac):
                    logger.warning("Invalid challenge HMAC")
                    return False, None
                
            except Exception as e:
                logger.error(f"Challenge verification error: {e}")
                return False, None
        
        elif challenge_data.get('type') == 'pow':
            # Verify PoW solution
            pow_data = challenge_data.get('pow_data', {})
            if not ProofOfWork.verify_solution(
                pow_data.get('challenge', ''),
                pow_data.get('signature', ''),
                user_answer
            ):
                return False, None
        
        else:
            return False, None
        
        # Generate next token in chain
        next_token = BlindTokenBucket.generate_token(
            session_id,
            metadata={
                'challenge_completed': challenge_data.get('type'),
                'timestamp': int(time.time())
            }
        )
        
        return True, next_token


class TorCircuitAwareness:
    """Tor circuit-aware rate limiting"""
    
    @staticmethod
    def get_circuit_id(request) -> str:
        """Extract Tor circuit identifier from request
        
        Uses a combination of headers that may indicate circuit changes
        """
        # In Tor, we can't directly get circuit ID, but we can use
        # a combination of factors that change with circuits
        factors = [
            request.META.get('HTTP_USER_AGENT', ''),
            request.META.get('HTTP_ACCEPT_LANGUAGE', ''),
            request.META.get('HTTP_ACCEPT_ENCODING', ''),
            # Session ID is our primary identifier
            request.session.session_key if hasattr(request, 'session') else '',
        ]
        
        # Create a fingerprint
        fingerprint = ':'.join(factors)
        circuit_id = hashlib.sha256(fingerprint.encode()).hexdigest()[:16]
        
        return circuit_id
    
    @staticmethod
    def track_circuit_behavior(circuit_id: str, action: str) -> Dict:
        """Track behavior patterns for a circuit
        
        Returns:
            Dict with circuit statistics
        """
        current_time = int(time.time())
        minute_window = current_time // 60
        
        # Track actions per minute
        action_key = f"circuit:{circuit_id}:actions:{minute_window}"
        action_count = cache.get(action_key, 0) + 1
        cache.set(action_key, action_count, 120)  # 2 minute TTL
        
        # Track unique endpoints accessed
        endpoint_key = f"circuit:{circuit_id}:endpoints:{minute_window}"
        endpoints = cache.get(endpoint_key, set())
        endpoints.add(action)
        cache.set(endpoint_key, endpoints, 120)
        
        # Calculate circuit reputation
        reputation_key = f"circuit:{circuit_id}:reputation"
        reputation = cache.get(reputation_key, 100)  # Start at 100
        
        # Adjust reputation based on behavior
        if action_count > 50:  # Too many requests
            reputation -= 10
        elif len(endpoints) > 15:  # Too many different endpoints
            reputation -= 5
        else:
            reputation = min(100, reputation + 1)  # Slowly recover
        
        cache.set(reputation_key, reputation, 3600)  # 1 hour TTL
        
        return {
            'circuit_id': circuit_id,
            'action_count': action_count,
            'unique_endpoints': len(endpoints),
            'reputation': reputation
        }


class AdvancedDDoSProtection:
    """Main class integrating all advanced DDoS protection features"""
    
    @staticmethod
    def check_request(request) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """Check if request should be allowed with advanced protection
        
        Returns:
            Tuple of (is_allowed, block_reason, metadata)
        """
        # Get circuit ID
        circuit_id = TorCircuitAwareness.get_circuit_id(request)
        session_id = request.session.session_key if hasattr(request, 'session') else circuit_id
        
        # Check for valid admission token
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            is_valid, payload = BlindTokenBucket.verify_token(token)
            if is_valid:
                # Token is valid, check if it can be used for this action
                if BlindTokenBucket.consume_token(token, request.path):
                    logger.info(f"Valid token consumed for {request.path}")
                    return True, None, {'method': 'token', 'circuit_id': circuit_id}
        
        # Track circuit behavior
        circuit_stats = TorCircuitAwareness.track_circuit_behavior(
            circuit_id, 
            request.path
        )
        
        # Check circuit reputation
        if circuit_stats['reputation'] < 50:
            logger.warning(f"Low reputation circuit: {circuit_id}")
            return False, 'low_reputation', {
                'circuit_id': circuit_id,
                'reputation': circuit_stats['reputation'],
                'requires': 'pow'  # Require PoW for low reputation
            }
        
        # Check rate limits based on circuit stats
        if circuit_stats['action_count'] > 30:
            return False, 'rate_limit_circuit', {
                'circuit_id': circuit_id,
                'requires': 'challenge'
            }
        
        # Check for suspicious patterns
        if circuit_stats['unique_endpoints'] > 10:
            return False, 'suspicious_pattern', {
                'circuit_id': circuit_id,
                'requires': 'dual_challenge'
            }
        
        # All checks passed
        return True, None, {'circuit_id': circuit_id}
    
    @staticmethod
    def issue_challenge(request, challenge_type: str = 'math') -> Dict:
        """Issue a stateless challenge
        
        Args:
            request: HTTP request
            challenge_type: Type of challenge to issue
            
        Returns:
            Challenge data for template
        """
        circuit_id = TorCircuitAwareness.get_circuit_id(request)
        session_id = request.session.session_key if hasattr(request, 'session') else circuit_id
        
        # For PoW challenges, use the dedicated launcher
        if challenge_type == 'pow':
            from core.pow_launcher import TorPoWService
            
            # Determine reason based on circuit reputation
            reputation_key = f"circuit:{circuit_id}:reputation"
            reputation = cache.get(reputation_key, 100)
            reason = 'attack' if reputation < 30 else 'rate_limit'
            
            # Issue PoW challenge with launcher
            challenge_data = TorPoWService.issue_challenge(session_id, reason)
            logger.info(f"Issued PoW challenge with launcher for session {session_id[:8]}")
            
            return challenge_data
        
        # For other challenges, use HMAC chain
        challenge_data = HMACChallengeChain.generate_challenge(
            session_id,
            challenge_type
        )
        
        # Log challenge issuance
        logger.info(f"Issued {challenge_type} challenge for session {session_id[:8]}")
        
        return challenge_data
    
    @staticmethod
    def verify_challenge_response(request, challenge_data: Dict, 
                                 challenge_hmac: str, user_answer: str) -> Tuple[bool, Optional[str]]:
        """Verify a challenge response and issue token if valid
        
        Returns:
            Tuple of (success, token)
        """
        circuit_id = TorCircuitAwareness.get_circuit_id(request)
        session_id = request.session.session_key if hasattr(request, 'session') else circuit_id
        
        # Verify challenge
        is_valid, token = HMACChallengeChain.verify_challenge(
            session_id,
            challenge_data,
            challenge_hmac,
            user_answer
        )
        
        if is_valid:
            # Improve circuit reputation
            reputation_key = f"circuit:{circuit_id}:reputation"
            reputation = cache.get(reputation_key, 100)
            cache.set(reputation_key, min(100, reputation + 10), 3600)
            
            logger.info(f"Challenge completed successfully for session {session_id[:8]}")
        
        return is_valid, token