import io,os,tempfile,unittest,zipfile
from artifacts import inspect_artifact,ArtifactError
from entitlements import connect,reserve_export
from jobs import expire_stale,job_status
HTML=b'<!doctype html><html><head></head><body><script>window.play=true</script></body></html>'
class Tests(unittest.TestCase):
 def test_html(self):
  result=inspect_artifact(HTML,"game.html","unity")
  self.assertEqual(result["validation"],"structural_only")
  self.assertFalse(result["runtime_verified"])
 def test_zip(self):
  buff=io.BytesIO()
  with zipfile.ZipFile(buff,'w') as z:z.writestr("index.html",HTML)
  self.assertEqual(inspect_artifact(buff.getvalue(),"game.zip","meta")["package"],"zip")
 def test_invalid(self):
  for payload in [b'',b'x'*70]:
   with self.assertRaises(ArtifactError):inspect_artifact(payload,"game.html","unity")
 def test_recovery(self):
  tmp=tempfile.NamedTemporaryFile(delete=False);path=tmp.name;tmp.close()
  try:
   db=connect(path)
   db.execute("INSERT INTO users VALUES('u','free',NULL,NULL,0)")
   j,_=reserve_export(db,'u','unity',now=1000)
   self.assertEqual(expire_stale(db,now=5000),1)
   self.assertEqual(job_status(db,'u',j)['state'],'failed')
   self.assertEqual(expire_stale(db,now=6000),0)
   db.close()
  finally:os.unlink(path)
if __name__=='__main__':unittest.main(verbosity=2)
