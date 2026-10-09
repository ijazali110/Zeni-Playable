"""Staging security: strict upload request envelope and portable rate limiter."""
import base64
import binascii
import json
import time
from artifacts import ArtifactError

MAX_JSON=7*1024*1024
MAX_ARTIFACT=5*1024*1024

def decode_upload(body):
    if not isinstance(body,(bytes,bytearray)) or len(body)>MAX_JSON:
        raise ArtifactError("Upload envelope too large")
    try:
        data=json.loads(body)
        if not isinstance(data,dict):
            raise ArtifactError("JSON object required")
        name=data.get("filename")
        network=data.get("network")
        value=data.get("content_base64")
        if not isinstance(name,str) or not isinstance(network,str) or not isinstance(value,str):
            raise ArtifactError("Missing upload fields")
        if len(value)>((MAX_ARTIFACT+2)//3)*4+4:
            raise ArtifactError("Content exceeds upload maximum")
        raw=base64.b64decode(value,validate=True)
        if len(raw)>MAX_ARTIFACT:raise ArtifactError("Content exceeds upload maximum")
        return network,name,raw
    except (binascii.Error,UnicodeDecodeError) as exc:
        raise ArtifactError("Malformed base64 artifact") from exc
    except (TypeError,ValueError) as exc:
        if isinstance(exc,ArtifactError):raise
        raise ArtifactError("Malformed upload JSON") from exc

def limit(db,identity,action,max_attempts=20,window=60,now=None):
    now=int(time.time()) if now is None else int(now)
    if max_attempts<1 or window<1:raise ValueError("Bad rate limit")
    db.execute("""CREATE TABLE IF NOT EXISTS request_rates(
        actor TEXT NOT NULL, action TEXT NOT NULL, stamp INTEGER NOT NULL)""")
    db.execute("BEGIN IMMEDIATE")
    try:
        db.execute("DELETE FROM request_rates WHERE stamp<?",(now-window,))
        count=db.execute("SELECT COUNT(*) FROM request_rates WHERE actor=? AND action=? AND stamp>?",
                         (identity,action,now-window)).fetchone()[0]
        allowed=count<max_attempts
        db.execute("INSERT INTO request_rates(actor,action,stamp) VALUES(?,?,?)",(identity,action,now))
        db.execute("COMMIT")
        return allowed
    except BaseException:
        db.execute("ROLLBACK")
        raise
