from entitlements import *
import tempfile,os
f=tempfile.NamedTemporaryFile(delete=False);p=f.name;f.close()
db=connect(p)
db.execute("INSERT INTO users VALUES('u','free',NULL,NULL,0)")
assert not can_convert(db,'u')
for _ in range(3):
 j,_=reserve_export(db,'u','unity')
 assert finish_export(db,'u',j,True)=='completed'
try:
 reserve_export(db,'u','unity')
 raise AssertionError("Quota not enforced")
except EntitlementError: pass
db.execute("INSERT INTO users VALUES('p','pro',100,200,0)")
assert can_convert(db,'p',150)
for _ in range(30): reserve_export(db,'p','pangle',now=150)
try:
 reserve_export(db,'p','pangle',now=150)
 raise AssertionError("Pro quota not enforced")
except EntitlementError: pass
try:
 reserve_export(db,'p','applovin',now=150)
 raise AssertionError("Network not blocked")
except EntitlementError: pass
db.execute("INSERT INTO users VALUES('b','business',NULL,NULL,0)")
assert can_convert(db,'b')
reserve_export(db,'b','applovin')
db.close();os.unlink(p)
print("PASS: free lifetime quota, pro monthly quota, converter gating, restricted network, business network")
