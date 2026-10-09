"""Staging artifact vault. Structural validation only; never a trusted converter."""
import hashlib
import os
import sqlite3
import tempfile
import time
from pathlib import Path
from artifacts import inspect_artifact, ArtifactError
from entitlements import EntitlementError, reserve_export, finish_export

MAX_UPLOAD=5*1024*1024

def setup(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS stored_artifacts(
      job_id TEXT PRIMARY KEY REFERENCES export_jobs(id),
      user_id TEXT NOT NULL REFERENCES users(id),
      digest TEXT NOT NULL, filename TEXT NOT NULL,
      size INTEGER NOT NULL, created_at INTEGER NOT NULL
    );
    """)

def safe_filename(value):
    name=Path(str(value).replace(chr(92),"/")).name
    if not name or len(name)>160 or name.startswith(".") or not name.lower().endswith((".html",".htm",".zip")):
        raise ArtifactError("invalid filename")
    return name

def submit(db, storage_root, user_id, network, filename, contents, job_id=None, now=None):
    """Safely store submitted bytes under an opaque job id. NOT a paid export."""
    if not isinstance(contents,bytes) or len(contents)>MAX_UPLOAD:
        raise ArtifactError("upload exceeds limit")
    name=safe_filename(filename)
    details=inspect_artifact(contents,name,network)
    now=int(time.time()) if now is None else int(now)
    job,state=reserve_export(db,user_id,network,job_id,now)
    if state!="reserved":
        raise EntitlementError("job cannot be resubmitted")
    root=Path(storage_root).resolve()
    root.mkdir(mode=0o700,parents=True,exist_ok=True)
    stored=root/(job+".bin")
    if stored.exists():
        raise EntitlementError("artifact already exists")
    fd,tmp=tempfile.mkstemp(prefix=".upload-",dir=root)
    try:
        with os.fdopen(fd,"wb") as output:
            output.write(contents)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(tmp,0o600)
        os.replace(tmp,stored)
        try:
            db.execute("INSERT INTO stored_artifacts VALUES(?,?,?,?,?,?)",
                       (job,user_id,hashlib.sha256(contents).hexdigest(),name,len(contents),now))
        except BaseException:
            stored.unlink(missing_ok=True)
            raise
        return {"job_id":job,"state":"quarantined","size":len(contents),
                "sha256":hashlib.sha256(contents).hexdigest(),
                "validation":details["validation"],"download_available":False}
    except BaseException:
        if os.path.exists(tmp):os.unlink(tmp)
        finish_export(db,user_id,job,False,now)
        raise

def retrieve_for_review(db,storage_root,user_id,job_id):
    """Internal diagnostics access, never the public paid download route."""
    row=db.execute("SELECT digest,filename FROM stored_artifacts WHERE job_id=? AND user_id=?",
                   (job_id,user_id)).fetchone()
    if not row: raise EntitlementError("artifact not found")
    path=Path(storage_root).resolve()/(job_id+".bin")
    data=path.read_bytes()
    if hashlib.sha256(data).hexdigest()!=row[0]:
        raise ArtifactError("artifact digest mismatch")
    return row[1],data
