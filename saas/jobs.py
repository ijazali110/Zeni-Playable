"""Recovery for abandoned export reservations.
No completed exports are ever refunded.
"""
import time
from entitlements import EntitlementError

def expire_stale(db, older_than=3600, now=None):
    now=int(time.time()) if now is None else int(now)
    if older_than<300:
        raise ValueError("minimum stale period is 300 seconds")
    db.execute("BEGIN IMMEDIATE")
    try:
        result=db.execute(
          """UPDATE export_jobs SET state='failed',updated_at=?
             WHERE state='reserved' AND created_at<?""",
          (now,now-older_than))
        count=result.rowcount
        db.execute("COMMIT")
        return count
    except BaseException:
        db.execute("ROLLBACK")
        raise

def job_status(db, uid, job_id):
    row=db.execute(
      "SELECT network,state,created_at,updated_at FROM export_jobs WHERE id=? AND user_id=?",
      (job_id,uid)).fetchone()
    if not row: raise EntitlementError("Job not found")
    return dict(zip(("network","state","created_at","updated_at"),row))
