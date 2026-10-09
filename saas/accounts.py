"""Zeni PlayAd: staging account identities and email-verification state.
Never expose this module without TLS, rate limits and verified mail delivery.
"""
import hashlib
import hmac
import secrets
import sqlite3
import time
import uuid

def initialize(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS identities(
      user_id TEXT PRIMARY KEY REFERENCES users(id),
      email TEXT NOT NULL UNIQUE COLLATE NOCASE,
      password_hash TEXT NOT NULL,
      email_verified INTEGER NOT NULL DEFAULT 0,
      disabled INTEGER NOT NULL DEFAULT 0,
      created_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS verification_codes(
      code_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
      purpose TEXT NOT NULL, expires_at INTEGER NOT NULL,
      used_at INTEGER
    );
    """)

def hash_password(password):
    if not isinstance(password,str) or len(password)<12 or len(password)>1024:
        raise ValueError("Password must have 12-1024 characters")
    salt=secrets.token_bytes(16)
    digest=hashlib.scrypt(password.encode(),salt=salt,n=2**14,r=8,p=1,dklen=32)
    return "scrypt$16384$"+salt.hex()+"$"+digest.hex()

def verify_password(password,stored):
    try:
        name,n,salt,expected=stored.split("$")
        if name!="scrypt" or int(n)!=16384: return False
        result=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),
                              n=16384,r=8,p=1,dklen=32)
        return hmac.compare_digest(result,bytes.fromhex(expected))
    except (TypeError,ValueError,MemoryError):
        return False

def signup(db,email,password,now=None):
    now=int(time.time()) if now is None else int(now)
    email=str(email).strip().lower()
    if len(email)>254 or len(email)<5 or email.count("@")!=1 or "." not in email.split("@",1)[1]:
        raise ValueError("Invalid email address")
    passhash=hash_password(password)
    uid=str(uuid.uuid4())
    db.execute("BEGIN IMMEDIATE")
    try:
        db.execute("INSERT INTO users(id,plan,created_at) VALUES(?,'free',?)",(uid,now))
        db.execute("INSERT INTO identities(user_id,email,password_hash,created_at) VALUES(?,?,?,?)",
                   (uid,email,passhash,now))
        db.execute("COMMIT")
    except BaseException:
        db.execute("ROLLBACK")
        raise
    return uid

def authenticate_password(db,email,password):
    row=db.execute("SELECT user_id,password_hash,email_verified,disabled FROM identities WHERE email=?",
                   (str(email).strip().lower(),)).fetchone()
    if not row or not verify_password(password,row[1]) or not row[2] or row[3]:
        return None
    return row[0]

def issue_verification(db,user_id,purpose="email",now=None):
    now=int(time.time()) if now is None else int(now)
    if purpose not in ("email","reset"): raise ValueError("Invalid purpose")
    token=secrets.token_urlsafe(32)
    token_hash=hashlib.sha256(token.encode()).hexdigest()
    db.execute("INSERT INTO verification_codes(code_hash,user_id,purpose,expires_at) VALUES(?,?,?,?)",
               (token_hash,user_id,purpose,now+1800))
    return token

def confirm_verification(db,token,purpose="email",now=None):
    now=int(time.time()) if now is None else int(now)
    key=hashlib.sha256(token.encode()).hexdigest()
    db.execute("BEGIN IMMEDIATE")
    try:
        row=db.execute("SELECT user_id FROM verification_codes WHERE code_hash=? AND purpose=? AND used_at IS NULL AND expires_at>?",
                       (key,purpose,now)).fetchone()
        if not row:
            db.execute("ROLLBACK")
            return False
        db.execute("UPDATE verification_codes SET used_at=? WHERE code_hash=?",(now,key))
        if purpose=="email":
            db.execute("UPDATE identities SET email_verified=1 WHERE user_id=?",(row[0],))
        db.execute("COMMIT")
        return True
    except BaseException:
        db.execute("ROLLBACK")
        raise
