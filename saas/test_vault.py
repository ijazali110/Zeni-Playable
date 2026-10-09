import tempfile,unittest
from pathlib import Path
from entitlements import connect,EntitlementError
from vault import setup,submit,retrieve_for_review
from artifacts import ArtifactError

HTML=b'<!doctype html><html><head></head><body><script>window.play=true</script></body></html>'
class VaultTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.db=connect(str(Path(self.tmp.name)/"db.sqlite"))
  setup(self.db)
  self.db.execute("INSERT INTO users VALUES('free','free',NULL,NULL,0)")
 def tearDown(self):
  self.db.close()
  self.tmp.cleanup()
 def test_quarantine_and_ownership(self):
  result=submit(self.db,Path(self.tmp.name)/"storage","free","unity","game.html",HTML,now=1000)
  self.assertFalse(result["download_available"])
  self.assertEqual(result["state"],"quarantined")
  self.assertEqual(retrieve_for_review(self.db,Path(self.tmp.name)/"storage","free",result["job_id"])[1],HTML)
  with self.assertRaises(EntitlementError):
   retrieve_for_review(self.db,Path(self.tmp.name)/"storage","other",result["job_id"])
 def test_invalid_does_not_use_credit(self):
  with self.assertRaises(ArtifactError):
   submit(self.db,Path(self.tmp.name)/"storage","free","unity","game.html",b"bad")
  count=self.db.execute("SELECT COUNT(*) FROM export_jobs").fetchone()[0]
  self.assertEqual(count,0)
 def test_limits(self):
  for i in range(3):
   submit(self.db,Path(self.tmp.name)/"storage","free","unity","game.html",HTML,now=1000+i)
  with self.assertRaises(EntitlementError):
   submit(self.db,Path(self.tmp.name)/"storage","free","unity","game.html",HTML,now=1005)
  with self.assertRaises(EntitlementError):
   submit(self.db,Path(self.tmp.name)/"storage","free","applovin","game.html",HTML,now=1005)
if __name__=="__main__": unittest.main(verbosity=2)
