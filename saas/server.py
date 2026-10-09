"""Zeni PlayAd staging API. No public deployment.
Usage: ZENI_DB=/safe/path/db.sqlite python3 saas/server.py
"""
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from entitlements import connect, reserve_export, can_convert, EntitlementError, LIMITS
from request_security import decode_upload, limit, MAX_JSON
from artifacts import ArtifactError
from vault import setup as vault_setup, submit
from review import setup as review_setup, status as review_status
from jobs import job_status

HOST = os.environ.get("ZENI_HOST", "127.0.0.1")
PORT = int(os.environ.get("ZENI_PORT", "8844"))
DB_PATH = os.environ.get("ZENI_DB", "/tmp/zeni-playad-staging.sqlite3")
MAX_BODY = 8192
VAULT_PATH=os.environ.get('ZENI_VAULT','/tmp/zeni-playad-vault')
ALLOWED_ORIGINS = set(filter(None, os.environ.get("ZENI_ALLOWED_ORIGINS", "").split(",")))

def setup(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS api_tokens(
      token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id),
      role TEXT NOT NULL CHECK(role IN ('user','developer')),
      expires_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS audit_events(
      id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT,
      event TEXT NOT NULL, created_at INTEGER NOT NULL
    );
    """)
def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()
def authenticate(db, authorization):
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or len(token) < 32:
        return None
    row = db.execute("SELECT user_id,role,expires_at FROM api_tokens WHERE token_hash=?",
                     (digest(token),)).fetchone()
    if not row or row[2] <= int(time.time()):
        return None
    return row[:2]
def make_token(db, user_id, role="user", lifetime=3600):
    if role not in ("developer","user"):
        raise ValueError("invalid role")
    token=secrets.token_urlsafe(40)
    db.execute("INSERT INTO api_tokens VALUES(?,?,?,?)",
               (digest(token),user_id,role,int(time.time())+lifetime))
    return token

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass
    def send_json(self, status, value):
        data=json.dumps(value).encode()
        self.send_response(status)
        self.send_header("Content-Type","application/json")
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Content-Length",str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def handle_api(self):
        origin=self.headers.get("Origin")
        if origin and origin not in ALLOWED_ORIGINS:
            return self.send_json(403,{"error":"origin_not_allowed"})
        p=urlsplit(self.path).path
        if p=="/health" and self.command=="GET":
            return self.send_json(200,{"ok":True,"staging":True})
        with connect(DB_PATH) as db:
            setup(db)
            identity=authenticate(db,self.headers.get("Authorization",""))
            if not identity:
                return self.send_json(401,{"error":"unauthorized"})
            uid,role=identity
            if self.command=="GET" and p=="/api/me":
                row=db.execute("SELECT plan,period_start,period_end FROM users WHERE id=?",(uid,)).fetchone()
                if not row:
                    return self.send_json(403,{"error":"no_account"})
                return self.send_json(200,{"plan":row[0],"can_convert":can_convert(db,uid),
                  "export_limit":LIMITS.get(row[0]),"developer":role=="developer"})
            if self.command=="GET" and p=="/api/developer/ai":
                if role!="developer":
                    return self.send_json(403,{"error":"developer_only"})
                return self.send_json(200,{"configured":bool(os.environ.get("OPENAI_API_KEY")),
                    "mode":"disabled","note":"AI repair is not enabled in staging"})
            if self.command=="GET" and p.startswith("/api/jobs/"):
                job_id=p.rsplit("/",1)[-1]
                if not job_id or len(job_id)>100:
                    return self.send_json(400,{"error":"invalid_job"})
                try:
                    review_setup(db)
                    return self.send_json(200,review_status(db,uid,job_id))
                except EntitlementError:
                    return self.send_json(404,{"error":"not_found"})
            if self.command=="POST" and p=="/api/artifacts/quarantine":
                if not limit(db,uid,"upload",max_attempts=12,window=3600):
                    return self.send_json(429,{"error":"rate_limited"})
                try:
                    size=int(self.headers.get("Content-Length","0"))
                    if size<2 or size>MAX_JSON:
                        return self.send_json(413,{"error":"upload_too_large"})
                    network,filename,raw=decode_upload(self.rfile.read(size))
                    vault_setup(db)
                    result=submit(db,VAULT_PATH,uid,network,filename,raw)
                    return self.send_json(201,result)
                except (ArtifactError,EntitlementError,ValueError) as exc:
                    return self.send_json(400,{"error":str(exc)})
            if self.command=="POST" and p=="/api/exports/reserve":
                size=int(self.headers.get("Content-Length","0"))
                if size<2 or size>MAX_BODY:
                    return self.send_json(413,{"error":"invalid_body_size"})
                try:
                    obj=json.loads(self.rfile.read(size))
                    if not isinstance(obj,dict):
                        raise ValueError("object required")
                    job_id=obj.get("job_id")
                    if job_id is not None and (not isinstance(job_id,str) or len(job_id)>100):
                        raise ValueError("invalid job id")
                    job,state=reserve_export(db,uid,obj.get("network",""),job_id)
                    db.execute("INSERT INTO audit_events(user_id,event,created_at) VALUES(?,?,?)",
                               (uid,"export_reserved",int(time.time())))
                    return self.send_json(200,{"job_id":job,"state":state})
                except (EntitlementError,ValueError,sqlite3.Error) as exc:
                    return self.send_json(403,{"error":str(exc)})
            return self.send_json(404,{"error":"not_found"})
    do_GET=handle_api
    do_POST=handle_api

if __name__=="__main__":
    db=connect(DB_PATH)
    setup(db)
    db.close()
    print(f"Zeni staging listening on {HOST}:{PORT}",flush=True)
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
