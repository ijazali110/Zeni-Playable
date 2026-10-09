from pathlib import Path
p=Path("/root/github-export/Zeni-Playable/saas/server.py")
s=p.read_text()
s=s.replace("from entitlements import connect, reserve_export, can_convert, EntitlementError, LIMITS",
"""from entitlements import connect, reserve_export, can_convert, EntitlementError, LIMITS
from request_security import decode_upload, limit, MAX_JSON
from artifacts import ArtifactError
from vault import setup as vault_setup, submit
from review import setup as review_setup, status as review_status
from jobs import job_status""")
s=s.replace("MAX_BODY = 8192","MAX_BODY = 8192\nVAULT_PATH=os.environ.get('ZENI_VAULT','/tmp/zeni-playad-vault')")
needle="""            if self.command=="POST" and p=="/api/exports/reserve":"""
addition="""            if self.command=="GET" and p.startswith("/api/jobs/"):
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
"""
assert needle in s
s=s.replace(needle,addition+needle)
p.write_text(s)
print("Updated staging API endpoints")
