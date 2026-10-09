import json, os, tempfile, threading, unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import server
from entitlements import connect

class APITest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  f=tempfile.NamedTemporaryFile(delete=False);cls.path=f.name;f.close()
  server.DB_PATH=cls.path
  db=connect(cls.path);server.setup(db)
  db.executemany("INSERT INTO users(id,plan,period_start,period_end,created_at) VALUES(?,?,?,?,?)",
   [('u','free',None,None,0),('d','business',None,None,0)])
  cls.user=server.make_token(db,'u');cls.dev=server.make_token(db,'d','developer')
  db.close()
  cls.http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
  cls.port=cls.http.server_address[1]
  cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
 @classmethod
 def tearDownClass(cls):
  cls.http.shutdown();cls.http.server_close();os.unlink(cls.path)
 def request(self,method,path,token='',payload=None):
  c=HTTPConnection('127.0.0.1',self.port,timeout=3)
  headers={}
  if token:headers['Authorization']='Bearer '+token
  body=None
  if payload is not None:
   body=json.dumps(payload)
   headers['Content-Type']='application/json'
  c.request(method,path,body=body,headers=headers)
  r=c.getresponse();status=r.status;content=json.loads(r.read());c.close()
  return status,content
 def test_auth(self):
  self.assertEqual(self.request('GET','/api/me')[0],401)
  self.assertEqual(self.request('GET','/api/me',self.user)[1]['export_limit'],3)
 def test_developer(self):
  self.assertEqual(self.request('GET','/api/developer/ai',self.user)[0],403)
  self.assertEqual(self.request('GET','/api/developer/ai',self.dev)[0],200)
 def test_quota(self):
  for i in range(3):
   self.assertEqual(self.request('POST','/api/exports/reserve',self.user,{'network':'unity','job_id':'j'+str(i)})[0],200)
  self.assertEqual(self.request('POST','/api/exports/reserve',self.user,{'network':'unity','job_id':'j3'})[0],403)
  self.assertEqual(self.request('POST','/api/exports/reserve',self.user,{'network':'applovin'})[0],403)
 def test_unverified_completion(self):
  self.assertEqual(self.request('POST','/api/exports/complete',self.user,{'job_id':'j0'})[0],404)
if __name__=='__main__':unittest.main(verbosity=2)
