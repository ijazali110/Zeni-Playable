"""Signup anti-abuse signals. Privacy-conscious, non-permanent identity checks.
No automatic ban based on shared IP alone.
"""
import hashlib
import hmac
import ipaddress
import sqlite3
import time

class SignupThrottled(Exception):
    pass

def key_hash(value,secret):
    return hmac.new(secret.encode(),value.encode(),hashlib.sha256).hexdigest()

def prefix(ip):
    address=ipaddress.ip_address(ip)
    if isinstance(address,ipaddress.IPv4Address):
        return str(ipaddress.ip_network(f"{address}/24",strict=False))
    return str(ipaddress.ip_network(f"{address}/56",strict=False))

def setup(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS signup_attempts(
      id INTEGER PRIMARY KEY, ip_hash TEXT NOT NULL,
      device_hash TEXT, created_at INTEGER NOT NULL
    );
    CREATE INDEX IF NOT EXISTS signup_ip_time ON signup_attempts(ip_hash,created_at);
    CREATE INDEX IF NOT EXISTS signup_device_time ON signup_attempts(device_hash,created_at);
    """)

def check_signup(db, ip, device_hint, secret, now=None):
    """Record every attempted signup; return challenge advice, never IP-only rejection.
    Requires server-verified CAPTCHA / email verification before creating an account.
    """
    if len(secret)<32:
        raise ValueError("Anti-abuse secret must be at least 32 characters")
    now=int(time.time()) if now is None else int(now)
    ipkey=key_hash(prefix(ip),secret)
    devicekey=key_hash(device_hint,secret) if device_hint else None
    setup(db)
    db.execute("BEGIN IMMEDIATE")
    try:
        db.execute("DELETE FROM signup_attempts WHERE created_at<?",(now-604800,))
        recent_ip=db.execute(
            "SELECT COUNT(*) FROM signup_attempts WHERE ip_hash=? AND created_at>?",
            (ipkey,now-3600)).fetchone()[0]
        recent_device=(db.execute(
            "SELECT COUNT(*) FROM signup_attempts WHERE device_hash=? AND created_at>?",
            (devicekey,now-86400)).fetchone()[0] if devicekey else 0)
        db.execute("INSERT INTO signup_attempts(ip_hash,device_hash,created_at) VALUES(?,?,?)",
                   (ipkey,devicekey,now))
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    return {"require_challenge":recent_ip>=5 or recent_device>=2,
            "require_manual_review":recent_device>=6,
            "reason_codes":(["ip_velocity"] if recent_ip>=5 else [])+
                           (["device_velocity"] if recent_device>=2 else []),
            "review_only":True}
