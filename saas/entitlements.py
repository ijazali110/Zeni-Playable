"""Server-authoritative Zeni PlayAd entitlement and export ledger.
This is a staging library, not wired to the live public converter.
"""
import sqlite3
import time
import uuid

ALLOWED_FREE_PRO = frozenset(("unity", "tiktok", "pangle", "meta"))
NETWORK_ALIASES = {
    "unity ads": "unity", "unityads": "unity",
    "facebook": "meta", "fb": "meta",
    "tiktok/pangle": "pangle",
}
LIMITS = {"free": 3, "pro": 30, "business": None}

def normalize_network(network):
    key = str(network).strip().lower()
    return NETWORK_ALIASES.get(key, key)

class EntitlementError(ValueError):
    pass

def connect(path):
    db = sqlite3.connect(path, isolation_level=None, timeout=15)
    db.execute("PRAGMA busy_timeout=15000")
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id TEXT PRIMARY KEY, plan TEXT NOT NULL DEFAULT 'free',
          period_start INTEGER, period_end INTEGER,
          created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS export_jobs(
          id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
          network TEXT NOT NULL, state TEXT NOT NULL,
          period_key TEXT NOT NULL, created_at INTEGER NOT NULL,
          updated_at INTEGER NOT NULL
        );
        CREATE INDEX IF NOT EXISTS export_user_period
          ON export_jobs(user_id,period_key,state);
    """)
    return db

def period_key(plan, start, end, now):
    if plan == "free":
        return "lifetime"
    if plan == "business":
        return "business"
    if not start or not end or not start <= now < end:
        raise EntitlementError("Pro subscription inactive or billing period missing")
    return f"{start}:{end}"

def reserve_export(db, user_id, network, job_id=None, now=None):
    """An in-flight job reserves quota. Only finalized jobs consume quota."""
    now = int(time.time()) if now is None else int(now)
    network = normalize_network(network)
    job_id = job_id or str(uuid.uuid4())
    db.execute("BEGIN IMMEDIATE")
    try:
        user = db.execute(
            "SELECT plan,period_start,period_end FROM users WHERE id=?", (user_id,)
        ).fetchone()
        if not user:
            raise EntitlementError("Unknown user")
        plan, start, end = user
        if plan not in LIMITS:
            raise EntitlementError("Invalid plan")
        if plan != "business" and network not in ALLOWED_FREE_PRO:
            raise EntitlementError("Export network not included in plan")
        key = period_key(plan, start, end, now)
        prior = db.execute(
            "SELECT user_id,network,state FROM export_jobs WHERE id=?", (job_id,)
        ).fetchone()
        if prior:
            if prior[0] != user_id or prior[1] != network:
                raise EntitlementError("Idempotency key used for a different export")
            db.execute("COMMIT")
            return job_id, prior[2]
        limit = LIMITS[plan]
        if limit is not None:
            count = db.execute(
                """SELECT COUNT(*) FROM export_jobs
                WHERE user_id=? AND period_key=? AND state IN ('reserved','completed')""",
                (user_id, key)
            ).fetchone()[0]
            if count >= limit:
                raise EntitlementError("Export quota exhausted")
        db.execute(
            """INSERT INTO export_jobs(id,user_id,network,state,period_key,created_at,updated_at)
            VALUES(?,?,?,'reserved',?,?,?)""",
            (job_id,user_id,network,key,now,now))
        db.execute("COMMIT")
        return job_id, "reserved"
    except BaseException:
        db.execute("ROLLBACK")
        raise

def finish_export(db, user_id, job_id, successful, now=None):
    """Completion is idempotent. A completed job cannot be marked failed later."""
    now = int(time.time()) if now is None else int(now)
    db.execute("BEGIN IMMEDIATE")
    try:
        row = db.execute("SELECT state FROM export_jobs WHERE id=? AND user_id=?",
                         (job_id,user_id)).fetchone()
        if not row:
            raise EntitlementError("Export reservation missing")
        old = row[0]
        if old == "reserved":
            new = "completed" if successful else "failed"
            db.execute("UPDATE export_jobs SET state=?,updated_at=? WHERE id=?",
                       (new,now,job_id))
        else:
            new = old
        db.execute("COMMIT")
        return new
    except BaseException:
        db.execute("ROLLBACK")
        raise

def can_convert(db, user_id, now=None):
    now = int(time.time()) if now is None else int(now)
    row = db.execute("SELECT plan,period_start,period_end FROM users WHERE id=?",
                     (user_id,)).fetchone()
    if not row:
        return False
    plan,start,end = row
    return plan == "business" or (plan == "pro" and bool(start and end and start <= now < end))
