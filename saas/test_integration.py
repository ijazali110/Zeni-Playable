import base64,json,os,tempfile,unittest
from pathlib import Path
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread
import server
from entitlements import connect
HTML=b'<!doctype html><html><head></head><body><script>window.play=true</script></body></html>'
class IntegrationTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory()
  server.DB_PATH=str(Path(cls.tmp.name)/"data.db")
  server.VAULT_PATH=str(Path(cls.tmp.name)/"vault")
  db=connect(server.DB_PATH);server.setup(db)
  db.execute("INSERT INTO users VALUES('u','free',NULL,NULL,0)")
  cls.token=server.make_token(db,'u');db.close()
  cls.http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
  cls.thread=Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
 @classmethod
 def tearDownClass(cls):
  cls.http.shutdown();cls.http.server_close();cls.tmp.cleanup()
 def request(self,method,path,body=None,token=None):
  conn=HTTPConnection('127.0.0.1',self.http.server_address[1],timeout=3)
  headers={}
  if token:headers['Authorization']='Bearer '+token
  if body is not None:headers['Content-Type']='application/json'
  conn.request(method,path,json.dumps(body) if body is not None else None,headers)
  r=conn.getresponse();status=r.status;data=json.loads(r.read());conn.close()
  return status,data
 def test_upload_flow(self):
  body={'network':'unity','filename':'game.html','content_base64':base64.b64encode(HTML).decode()}
  self.assertEqual(self.request('POST','/api/artifacts/quarantine',body)[0],401)
  status,out=self.request('POST','/api/artifacts/quarantine',body,self.token)
  self.assertEqual(status,201)
  self.assertEqual(out['state'],'quarantined')
  self.assertFalse(out['download_available'])
  self.assertEqual(self.request('GET','/api/jobs/'+out['job_id'],token=self.token)[1]['size'],len(HTML))
  self.assertEqual(self.request('GET','/api/jobs/'+out['job_id'])[0],401)
  self.assertEqual(self.request('POST','/api/artifacts/quarantine',{'network':'applovin','filename':'game.html','content_base64':body['content_base64']},self.token)[0],400)
  for i in range(2):self.assertEqual(self.request('POST','/api/artifacts/quarantine',body,self.token)[0],201)
  self.assertEqual(self.request('POST','/api/artifacts/quarantine',body,self.token)[0],400)
if __name__=='__main__':unittest.main(verbosity=2)
