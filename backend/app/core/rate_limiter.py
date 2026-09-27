import base64
import ipaddress
import json
import logging
import threading
import time
from typing import Dict, List, Optional
from fastapi import HTTPException, Request
from app.config import settings
from app.auth import get_optional_user_id

logger = logging.getLogger("stokvigil.rate_limiter")

# In-Memory Sliding Window Rate Limiter (Max 120 req/min per client IP or authenticated user)
_RATE_LIMIT_BUCKETS: Dict[str, List[float]] = {}
_RATE_LIMIT_WINDOW = 60.0  # 1 minute sliding window
_RATE_LIMIT_MAX_REQ = 120  # Max requests per window
_RATE_LIMIT_MAX_BUCKETS = 10000  # Hard memory cap on tracked buckets to prevent OOM
_RATE_LIMIT_LOCK = threading.Lock()
_RATE_LIMIT_LAST_PRUNE = 0.0
_RATE_LIMIT_PRUNE_INTERVAL = 60.0  # Prune expired keys every 60 seconds

_TRUSTED_PROXY_SUBNETS = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
)


def _is_trusted_proxy(host: Optional[str]) -> bool:
    """
    Determines if the direct socket peer (request.client.host) is a trusted internal proxy
    (Cloud Run, AWS ALB, Render, Nginx, Docker gateway, Kubernetes Ingress, or localhost).
    Proxy headers are ONLY trusted when incoming requests originate from these trusted peers.
    """
    if not host:
        return False
    clean = host.strip()
    if clean in ("testclient", "localhost"):
        return True
    trusted_list = getattr(settings, "trusted_proxies_list", [])
    if clean in trusted_list:
        return True
    try:
        ip = ipaddress.ip_address(clean)
        return any(ip in net for net in _TRUSTED_PROXY_SUBNETS)
    except ValueError:
        return False


def _sanitize_ip(ip_str: Optional[str]) -> Optional[str]:
    """
    Validates and canonicalizes IPv4 and IPv6 strings using Python's ipaddress library.
    Rejects malformed strings, command injections, and prevents dictionary key inflation.
    """
    if not ip_str:
        return None
    candidate = ip_str.strip()
    if len(candidate) > 45:  # Standard max length for valid IPv6 string representations
        return None
    try:
        validated = ipaddress.ip_address(candidate)
        return str(validated)
    except ValueError:
        return None


def _extract_client_ip(request: Request) -> str:
    """
    Extracts the genuine client IP, strictly validating IP syntax and preventing header spoofing.
    Reverse-proxy headers (Cloudflare, X-Real-IP, X-Forwarded-For) are ONLY inspected if the
    immediate socket connection originates from a trusted private or loopback proxy.
    Direct public internet connections always use request.client.host.
    """
    direct_host = request.client.host if (request.client and request.client.host) else None

    # Only inspect proxy headers if the immediate peer is a verified trusted internal proxy or test client
    if _is_trusted_proxy(direct_host):
        # 1. Check Cloudflare connecting IP
        cf_ip = _sanitize_ip(request.headers.get("cf-connecting-ip"))
        if cf_ip:
            return cf_ip

        # 2. Check X-Real-IP
        x_real = _sanitize_ip(request.headers.get("x-real-ip"))
        if x_real:
            return x_real

        # 3. Check X-Forwarded-For (first valid client IP in proxy chain)
        x_forwarded = request.headers.get("x-forwarded-for")
        if x_forwarded and x_forwarded.strip():
            for part in x_forwarded.split(","):
                cand = _sanitize_ip(part)
                if cand:
                    return cand

    # Direct connection host (public connection or fallback)
    sanitized_direct = _sanitize_ip(direct_host)
    if sanitized_direct:
        return sanitized_direct

    if direct_host in ("testclient", "localhost"):
        return direct_host

    return "unverified_client"


def _prune_rate_limit_buckets(now: float) -> None:
    """Evicts expired IP buckets to prevent memory accumulation and memory exhaustion attacks."""
    global _RATE_LIMIT_LAST_PRUNE
    _RATE_LIMIT_LAST_PRUNE = now

    # Remove buckets where all timestamps are older than the sliding window
    expired_ips = [
        ip for ip, timestamps in _RATE_LIMIT_BUCKETS.items()
        if not timestamps or (now - timestamps[-1] >= _RATE_LIMIT_WINDOW)
    ]
    for ip in expired_ips:
        _RATE_LIMIT_BUCKETS.pop(ip, None)

    # Hard cap emergency eviction if adversary floods millions of random spoofed IPs
    if len(_RATE_LIMIT_BUCKETS) > _RATE_LIMIT_MAX_BUCKETS:
        keys_to_evict = list(_RATE_LIMIT_BUCKETS.keys())[:len(_RATE_LIMIT_BUCKETS) // 4]
        for ip in keys_to_evict:
            _RATE_LIMIT_BUCKETS.pop(ip, None)


# In-memory verified JWT cache: token -> (expiry_ts, user_id)
_VERIFIED_JWT_CACHE: Dict[str, tuple] = {}
_VERIFIED_JWT_TTL = 60.0  # Cache verified tokens for 60 seconds to avoid Supabase network latency on repeat requests


def check_rate_limit(request: Request):
    """
    Protects public search, quote, and market intelligence APIs from abuse, scraping, and DoS attacks.
    Features Hybrid (Verified User-ID + IP) sliding-window rate limiting for 10K+ user scalability.
    Strictly verifies JWT claims to prevent attacker-spoofed rate-limit exhaustion attacks.
    """
    # Automated unit tests and development testclient socket exemption:
    direct_host = request.client.host if (request.client and request.client.host) else None
    if settings.ENVIRONMENT in ["test", "development"] and direct_host in ["testclient", "127.0.0.1", "localhost", "::1"]:
        return

    # Hybrid identifier for 10K+ scale:
    # Cryptographically verified authenticated users get their own user-scoped bucket.
    # Unauthenticated visitors and unverified/forged tokens are throttled by verified client IP.
    user_id = None
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split("Bearer ")[1].strip()
        now_ts = time.time()
        cached_auth = _VERIFIED_JWT_CACHE.get(token)
        if cached_auth and now_ts < cached_auth[0]:
            user_id = cached_auth[1]
        else:
            try:
                verified_uid = get_optional_user_id(auth_header)
                if verified_uid:
                    user_id = verified_uid
                    if len(_VERIFIED_JWT_CACHE) > 5000:
                        oldest = sorted(_VERIFIED_JWT_CACHE.keys(), key=lambda k: _VERIFIED_JWT_CACHE[k][0])[:1000]
                        for ok in oldest:
                            _VERIFIED_JWT_CACHE.pop(ok, None)
                    _VERIFIED_JWT_CACHE[token] = (now_ts + _VERIFIED_JWT_TTL, verified_uid)
            except Exception:
                user_id = None

    if user_id:
        bucket_key = f"usr:{user_id}"
    else:
        bucket_key = _extract_client_ip(request)

    now = time.time()
    with _RATE_LIMIT_LOCK:
        # Periodic or capacity-triggered cleanup
        if (now - _RATE_LIMIT_LAST_PRUNE > _RATE_LIMIT_PRUNE_INTERVAL) or (len(_RATE_LIMIT_BUCKETS) > _RATE_LIMIT_MAX_BUCKETS):
            _prune_rate_limit_buckets(now)

        timestamps = _RATE_LIMIT_BUCKETS.get(bucket_key, [])
        valid_ts = [ts for ts in timestamps if now - ts < _RATE_LIMIT_WINDOW]
        if len(valid_ts) >= _RATE_LIMIT_MAX_REQ:
            logger.warning(f"Rate limit exceeded for client/user: {bucket_key}")
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please slow down and try again in a minute."
            )
        valid_ts.append(now)
        _RATE_LIMIT_BUCKETS[bucket_key] = valid_ts
