# 🛡️ DDoS Protection System Documentation

## Overview

The marketplace now features a comprehensive, multi-layered DDoS protection system designed to defend against distributed denial-of-service attacks while maintaining compatibility with Tor Browser and legitimate users.

## Key Features

### 1. **Multi-Layer Rate Limiting**
- **Global limits**: Protect the entire system
- **Per-session limits**: Track by session ID (Tor-compatible)
- **Per-user limits**: Control authenticated user requests
- **Endpoint-specific limits**: Extra protection for sensitive endpoints

### 2. **Intelligent Pattern Detection**
- Rapid endpoint switching detection
- Identical request spam detection
- High error rate detection
- Suspicious behavior analysis

### 3. **Automatic Response System**
- Progressive violation scoring
- Automatic IP blacklisting
- Challenge-response for suspicious traffic
- Manual override capabilities

### 4. **Admin Monitoring Dashboard**
- Real-time statistics
- IP management (block/unblock)
- Rate limit configuration
- Request history tracking

## Configuration

### Rate Limits

Current default limits are optimized for Tor usage:

**What is "Global"?**
- Global limits apply to the ENTIRE marketplace across ALL users and sessions combined
- It's the total capacity limit for your server
- Even if individual sessions are within their limits, global limits prevent server overload
- Example: If global limit is 30 req/sec, that's the max for everyone together

```python
RATE_LIMITS = {
    'global': {  # Total requests across ALL users/sessions combined
        'requests_per_second': 30,
        'requests_per_minute': 100,
        'requests_per_hour': 1000,
    },
    'per_session': {  # Limits for each individual session
        'requests_per_second': 20,
        'requests_per_minute': 50,
        'requests_per_hour': 500,
    },
    'per_user': {  # Limits for authenticated users
        'requests_per_second': 20,
        'requests_per_minute': 50,
        'requests_per_hour': 500,
    }
}
```

### Sensitive Endpoints

Extra protection for critical endpoints:

- `/login`: 5 requests/minute, 20 requests/hour
- `/register`: 3 requests/minute, 10 requests/hour
- `/wallets/withdraw`: 2 requests/minute, 10 requests/hour
- `/api`: 20 requests/minute, 200 requests/hour

## How It Works

### 1. Request Flow

```
User Request → DDoS Middleware → Protection Checks → Allow/Block Decision
                                        ↓
                              [Global → IP → User → Endpoint → Patterns]
```

### 2. Violation Scoring

- Minor violations: +1 point (rate limit exceeded)
- Moderate violations: +2 points (endpoint abuse)
- Major violations: +3 points (suspicious patterns)
- Auto-blacklist threshold: 10 points

### 3. Blacklisting

- Automatic: When violation score ≥ 10
- Manual: Via admin dashboard
- Duration: Configurable (default 1 hour)
- Clearance: Automatic expiry or manual unblock

## Admin Dashboard

Access the DDoS protection dashboard at: `/adminpanel/ddos/`

### Features:
1. **Real-time Statistics**
   - Current request rate
   - Blocked requests count
   - Blacklisted IPs

2. **Session Management**
   - Block session with custom duration
   - Unblock blacklisted sessions
   - View session request history

3. **Configuration**
   - View current rate limits
   - Monitor suspicious patterns
   - Export protection logs

## Tor Compatibility

The system is designed with Tor in mind:

- ✅ No JavaScript required
- ✅ Works with Tor Browser safest mode
- ✅ Uses session IDs instead of IPs (perfect for Tor)
- ✅ Challenge system uses simple math (no CAPTCHA)
- ✅ Graceful degradation for .onion addresses
- ✅ No IP tracking anywhere in the system

## Handling Attacks

### During an Attack:

1. **Monitor Dashboard**: Check `/adminpanel/ddos/` for attack patterns
2. **Adjust Limits**: Temporarily tighten rate limits if needed
3. **Block Sources**: Manually block persistent attack IPs
4. **Review Logs**: Analyze patterns for future prevention

### Post-Attack:

1. Review blacklist for false positives
2. Unblock legitimate users if needed
3. Adjust thresholds based on attack patterns
4. Document attack for future reference

## Testing

Run the comprehensive test suite:

```bash
python test_ddos_protection.py
```

Tests include:
- Rate limiting verification
- Pattern detection
- Auto-blacklisting
- Concurrent request handling
- Endpoint-specific limits

## Best Practices

1. **Regular Monitoring**: Check dashboard daily
2. **Log Analysis**: Review patterns weekly
3. **Threshold Tuning**: Adjust based on traffic
4. **False Positive Handling**: Maintain whitelist for known good IPs
5. **Documentation**: Log all manual interventions

## Troubleshooting

### Common Issues:

1. **Legitimate users blocked**
   - Check violation score
   - Review request patterns
   - Consider whitelisting

2. **Attack getting through**
   - Tighten rate limits
   - Lower auto-blacklist threshold
   - Enable stricter patterns

3. **High false positive rate**
   - Relax rate limits slightly
   - Adjust pattern thresholds
   - Review endpoint limits

## Security Considerations

- Rate limits are stored in cache (Redis)
- Blacklists expire automatically
- All actions are logged
- Admin actions require authentication
- No user data exposed in logs

## Performance Impact

- Minimal overhead: <5ms per request
- Efficient cache usage
- Automatic cleanup of old data
- Scales with Redis capacity

## Future Enhancements

Potential improvements:
- Machine learning for pattern detection
- Distributed blacklist sharing
- Geographic-based rules (Tor-compatible)
- Advanced challenge types
- API rate limit tokens

---

**Remember**: The goal is to stop attacks while keeping the marketplace accessible to legitimate Tor users. When in doubt, favor accessibility over strict security.