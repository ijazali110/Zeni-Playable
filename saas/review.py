"""Verified artifact review API helpers for staging only.
User-submitted artifacts are never represented as server-generated conversions.
"""
import hashlib
import hmac
import os
import secrets
import time
from pathlib import Path
from entitlements import EntitlementError
from vault import retrieve_for_review

def setup(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS artifact_access(
      job_id TEXT PRIMARY KEY REFERENCES export_jobs(id),
      approved INTEGER NOT NULL DEFAULT 0,
      approved_by TEXT,
      approved_at INTEGER
    );
    """)

def approve_review(db,job_id,reviewer,validator_ok=False,now=None):
    """Developer-only approval AFTER external validator evidence.
    This marks QA readiness, not paid export completion.
    """
    if not validator_ok:
        raise ValueError("Verified QA evidence required")
    now=int(time.time()) if now is None else int(now)
    row=db.execute("SELECT id FROM stored_artifacts WHERE job_id=?",(job_id,)).fetchone()
    if not row:raise EntitlementError("Unknown stored artifact")
    db.execute("""INSERT INTO artifact_access(job_id,approved,approved_by,approved_at)
                  VALUES(?,1,?,?) ON CONFLICT(job_id) DO UPDATE SET
                  approved=1,approved_by=excluded.approved_by,approved_at=excluded.approved_at""",
               (job_id,reviewer,now))

def status(db,user_id,job_id):
    row=db.execute("""SELECT e.network,e.state,a.size,a.digest,
                      COALESCE(r.approved,0) FROM export_jobs e
                      LEFT JOIN stored_artifacts a ON a.job_id=e.id
                      LEFT JOIN artifact_access r ON r.job_id=e.id
                      WHERE e.id=? AND e.user_id=?""",(job_id,user_id)).fetchone()
    if not row:raise EntitlementError("Unknown job")
    return {"network":row[0],"state":row[1],"size":row[2],
            "sha256":row[3],"review_approved":bool(row[4]),
            "download_available":False}

def review_bytes(db,root,user_id,job_id):
    return retrieve_for_review(db,root,user_id,job_id)
