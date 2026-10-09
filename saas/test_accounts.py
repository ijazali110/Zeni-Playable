import os,tempfile,unittest
from entitlements import connect
from accounts import initialize,signup,authenticate_password,issue_verification,confirm_verification,verify_password
class AccountsTest(unittest.TestCase):
 def setUp(self):
  f=tempfile.NamedTemporaryFile(delete=False);self.path=f.name;f.close()
  self.db=connect(self.path);initialize(self.db)
 def tearDown(self):
  self.db.close();os.unlink(self.path)
 def test_verification_lifecycle(self):
  uid=signup(self.db,'Test@Example.com','my password is long enough',now=100)
  self.assertIsNone(authenticate_password(self.db,'test@example.com','my password is long enough'))
  token=issue_verification(self.db,uid,now=100)
  self.assertFalse(confirm_verification(self.db,'incorrect',now=120))
  self.assertTrue(confirm_verification(self.db,token,now=120))
  self.assertFalse(confirm_verification(self.db,token,now=121))
  self.assertEqual(authenticate_password(self.db,'test@example.com','my password is long enough'),uid)
  self.assertIsNone(authenticate_password(self.db,'test@example.com','wrong'))
 def test_expired_token(self):
  uid=signup(self.db,'expired@example.com','a sufficiently long password',now=100)
  token=issue_verification(self.db,uid,now=100)
  self.assertFalse(confirm_verification(self.db,token,now=2000))
 def test_duplicate_email_and_password(self):
  signup(self.db,'A@Example.com','password longer than twelve')
  with self.assertRaises(Exception):signup(self.db,'a@example.com','password longer than twelve')
  self.assertFalse(verify_password('x','unrecognized-hash'))
if __name__=='__main__':unittest.main()
