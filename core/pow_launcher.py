"""
Tor-Compatible Proof of Work Launcher
Provides automated PoW solving through a dedicated service
"""
import hashlib
import time
import secrets
import json
import base64
from typing import Dict, Optional, Tuple
from django.core.cache import cache
from django.conf import settings
import logging

logger = logging.getLogger('marketplace.security.pow')


class TorPoWLauncher:
    """
    Dedicated PoW launcher that generates time-based challenges
    and provides pre-computed solutions for Tor users
    """
    
    # Cache solutions for quick retrieval
    SOLUTION_CACHE_TIME = 300  # 5 minutes
    
    @staticmethod
    def generate_time_based_challenge(difficulty: int = 4) -> Dict:
        """
        Generate a time-based PoW challenge that can be pre-solved
        
        Returns:
            Dict with challenge data and solution endpoint
        """
        # Generate challenge based on current time window (5-minute windows)
        time_window = int(time.time() // 300)
        
        # Create deterministic challenge for this time window
        challenge_seed = f"{settings.SECRET_KEY}:{time_window}:{difficulty}"
        challenge_hash = hashlib.sha256(challenge_seed.encode()).hexdigest()
        
        # Generate challenge ID
        challenge_id = challenge_hash[:16]
        
        # Check if we have a cached solution
        solution_key = f"pow:solution:{challenge_id}"
        cached_solution = cache.get(solution_key)
        
        if not cached_solution:
            # Pre-compute solution in background
            cached_solution = TorPoWLauncher._compute_solution(
                challenge_id, 
                time_window, 
                difficulty
            )
            
        return {
            'challenge_id': challenge_id,
            'time_window': time_window,
            'difficulty': difficulty,
            'challenge_endpoint': f"/security/pow/challenge/{challenge_id}/",
            'solution_endpoint': f"/security/pow/solution/{challenge_id}/",
            'expires': (time_window + 1) * 300,  # End of current window
            'launcher_ready': bool(cached_solution)
        }
    
    @staticmethod
    def _compute_solution(challenge_id: str, time_window: int, difficulty: int) -> Optional[Dict]:
        """
        Compute PoW solution in background
        """
        # Generate the actual challenge
        challenge = f"{challenge_id}:{time_window}:{difficulty}"
        target_prefix = '0' * difficulty
        
        # Try to find solution quickly (limit iterations for server performance)
        max_attempts = 100000  # Limit server computation
        nonce = 0
        
        start_time = time.time()
        
        for nonce in range(max_attempts):
            solution = f"{challenge}:{nonce}"
            hash_result = hashlib.sha256(solution.encode()).hexdigest()
            
            if hash_result.startswith(target_prefix):
                # Found solution!
                solution_data = {
                    'challenge': challenge,
                    'nonce': nonce,
                    'hash': hash_result,
                    'computed_at': time.time(),
                    'computation_time': time.time() - start_time
                }
                
                # Cache the solution
                solution_key = f"pow:solution:{challenge_id}"
                cache.set(solution_key, solution_data, TorPoWLauncher.SOLUTION_CACHE_TIME)
                
                logger.info(f"PoW solution found for {challenge_id}: nonce={nonce}")
                return solution_data
        
        logger.warning(f"PoW solution not found within {max_attempts} attempts")
        return None
    
    @staticmethod
    def get_launcher_script(challenge_id: str) -> str:
        """
        Generate a launcher script that can be run locally
        """
        script = f"""#!/usr/bin/env python3
# Tor-Compatible PoW Solver
# Save this script and run it to solve the Proof of Work

import hashlib
import time

def solve_pow(challenge_id, time_window, difficulty):
    challenge = f"{{challenge_id}}:{{time_window}}:{{difficulty}}"
    target = '0' * difficulty
    nonce = 0
    
    print(f"Solving PoW for challenge: {{challenge}}")
    print(f"Difficulty: {{difficulty}} (finding {{difficulty}} leading zeros)")
    
    start = time.time()
    
    while True:
        solution = f"{{challenge}}:{{nonce}}"
        hash_result = hashlib.sha256(solution.encode()).hexdigest()
        
        if hash_result.startswith(target):
            elapsed = time.time() - start
            print(f"\\nSolution found!")
            print(f"Nonce: {{nonce}}")
            print(f"Hash: {{hash_result}}")
            print(f"Time: {{elapsed:.2f}} seconds")
            print(f"\\nSubmit this nonce: {{nonce}}")
            return nonce
        
        if nonce % 10000 == 0:
            print(f"Attempt {{nonce}}...", end='\\r')
        
        nonce += 1

if __name__ == "__main__":
    # Challenge parameters
    challenge_id = "{challenge_id}"
    time_window = {int(time.time() // 300)}
    difficulty = 4
    
    solve_pow(challenge_id, time_window, difficulty)
"""
        return script
    
    @staticmethod
    def create_web_launcher(challenge_data: Dict) -> str:
        """
        Create a web-based launcher page (no JS required)
        """
        launcher_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>PoW Launcher</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: monospace; background: #000; color: #0f0; padding: 20px; }}
        .container {{ max-width: 800px; margin: 0 auto; }}
        .challenge {{ background: #111; padding: 20px; border: 1px solid #0f0; }}
        .solution {{ background: #001100; padding: 20px; margin-top: 20px; }}
        pre {{ overflow-x: auto; }}
        .button {{ display: inline-block; padding: 10px 20px; background: #0f0; color: #000; text-decoration: none; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>⚡ Proof of Work Launcher</h1>
        
        <div class="challenge">
            <h2>Challenge Details:</h2>
            <p>Challenge ID: {challenge_data['challenge_id']}</p>
            <p>Difficulty: {challenge_data['difficulty']}</p>
            <p>Time Window: {challenge_data['time_window']}</p>
            <p>Expires: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(challenge_data['expires']))}</p>
        </div>
        
        <div class="solution">
            <h2>Option 1: Automatic Solver</h2>
            <p>Download and run this Python script:</p>
            <a href="/security/pow/download/{challenge_data['challenge_id']}/" class="button">Download Solver</a>
            
            <h2>Option 2: Web Terminal</h2>
            <p>Use this pre-configured command:</p>
            <pre>
curl -s https://marketplace.onion/security/pow/solve/{challenge_data['challenge_id']}/ | python3
            </pre>
            
            <h2>Option 3: Tor Browser Extension</h2>
            <p>Install our PoW solver extension (coming soon)</p>
        </div>
        
        <div class="solution">
            <h2>Pre-computed Solutions</h2>
            <p>For testing, you can check if a solution is available:</p>
            <a href="/security/pow/solution/{challenge_data['challenge_id']}/" class="button">Check Solution</a>
        </div>
    </div>
</body>
</html>
"""
        return launcher_html


class PoWPool:
    """
    Pool of pre-computed PoW solutions for instant verification
    """
    
    @staticmethod
    def initialize_pool(size: int = 10, difficulty: int = 4):
        """
        Initialize a pool of pre-computed challenges
        """
        pool_key = "pow:pool:challenges"
        challenges = []
        
        for _ in range(size):
            # Generate unique challenge
            challenge_id = secrets.token_hex(8)
            timestamp = int(time.time())
            
            challenge = f"{challenge_id}:{timestamp}:{difficulty}"
            
            # Pre-compute solution
            target = '0' * difficulty
            nonce = 0
            
            while True:
                solution = f"{challenge}:{nonce}"
                hash_result = hashlib.sha256(solution.encode()).hexdigest()
                
                if hash_result.startswith(target):
                    challenge_data = {
                        'id': challenge_id,
                        'challenge': challenge,
                        'nonce': nonce,
                        'hash': hash_result,
                        'difficulty': difficulty,
                        'created': timestamp
                    }
                    challenges.append(challenge_data)
                    break
                
                nonce += 1
                
                # Safety limit
                if nonce > 1000000:
                    break
        
        # Store in cache
        cache.set(pool_key, challenges, 3600)  # 1 hour
        logger.info(f"Initialized PoW pool with {len(challenges)} challenges")
        
        return challenges
    
    @staticmethod
    def get_challenge_from_pool() -> Optional[Dict]:
        """
        Get a pre-computed challenge from the pool
        """
        pool_key = "pow:pool:challenges"
        challenges = cache.get(pool_key, [])
        
        if challenges:
            # Pop a challenge from the pool
            challenge = challenges.pop(0)
            
            # Update cache
            cache.set(pool_key, challenges, 3600)
            
            # Refill pool if getting low
            if len(challenges) < 5:
                PoWPool.initialize_pool(size=5)
            
            return challenge
        
        # Pool empty, generate on demand
        logger.warning("PoW pool empty, generating on demand")
        PoWPool.initialize_pool(size=10)
        
        return PoWPool.get_challenge_from_pool()


class TorPoWService:
    """
    Main service for handling PoW with Tor
    """
    
    @staticmethod
    def issue_challenge(session_id: str, reason: str = 'rate_limit') -> Dict:
        """
        Issue a PoW challenge with Tor-compatible options
        """
        # For low-priority challenges, try pool first
        if reason != 'attack':
            pooled = PoWPool.get_challenge_from_pool()
            if pooled:
                return {
                    'type': 'pooled',
                    'challenge': pooled['challenge'],
                    'challenge_id': pooled['id'],
                    'difficulty': pooled['difficulty'],
                    'solution_available': True,
                    'launcher_url': f"/security/pow/launcher/{pooled['id']}/",
                    'verify_url': f"/security/pow/verify/"
                }
        
        # For high-priority, use time-based challenges
        launcher_data = TorPoWLauncher.generate_time_based_challenge(
            difficulty=6 if reason == 'attack' else 4
        )
        
        return {
            'type': 'time_based',
            'challenge_id': launcher_data['challenge_id'],
            'difficulty': launcher_data['difficulty'],
            'launcher_url': f"/security/pow/launcher/{launcher_data['challenge_id']}/",
            'download_url': f"/security/pow/download/{launcher_data['challenge_id']}/",
            'verify_url': f"/security/pow/verify/",
            'expires': launcher_data['expires']
        }
    
    @staticmethod
    def verify_solution(challenge_id: str, nonce: str) -> bool:
        """
        Verify a PoW solution
        """
        # Check pooled solutions
        solution_key = f"pow:solution:{challenge_id}"
        cached_solution = cache.get(solution_key)
        
        if cached_solution and str(cached_solution.get('nonce')) == str(nonce):
            logger.info(f"Valid PoW solution verified for {challenge_id}")
            return True
        
        # Verify time-based challenges
        time_window = int(time.time() // 300)
        
        # Try current and previous time window
        for window in [time_window, time_window - 1]:
            challenge_seed = f"{settings.SECRET_KEY}:{window}:4"
            challenge_hash = hashlib.sha256(challenge_seed.encode()).hexdigest()
            
            if challenge_hash[:16] == challenge_id:
                # Reconstruct and verify
                challenge = f"{challenge_id}:{window}:4"
                solution = f"{challenge}:{nonce}"
                hash_result = hashlib.sha256(solution.encode()).hexdigest()
                
                if hash_result.startswith('0000'):  # 4 zeros
                    logger.info(f"Valid PoW solution verified for time-based challenge {challenge_id}")
                    return True
        
        return False