import gzip,hashlib,json,tempfile,time,sys,unittest
import requests
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from commerce_v3_http import PoliteClient,Fetch
from commerce_v5_http import PolicyClient
class PolicyTests(unittest.TestCase):
 def test_turkey_storefront_preferences_are_scoped_to_trendyol(self):
  with tempfile.TemporaryDirectory() as tmp:
   client=PolicyClient(tmp,time.time()+100);session=client._session()
   tr=session.prepare_request(requests.Request('GET','https://www.trendyol.com/innative/test-p-123')).headers.get('Cookie','')
   self.assertIn('countryCode=TR',tr);self.assertIn('storefrontId=1',tr);self.assertIn('language=tr',tr)
   foreign=session.prepare_request(requests.Request('GET','https://fr.caudalie.com/p/test')).headers.get('Cookie','')
   self.assertEqual(foreign,'');self.assertNotIn('Authorization',session.headers)
 def test_changed_cached_rules_require_fresh_verified_policy(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'policies').mkdir();(root/'responses').mkdir()
   raw=b'User-agent: *\nDisallow: /sr/\n';digest=hashlib.sha256(raw).hexdigest();(root/'responses'/'x.gz').write_bytes(gzip.compress(raw))
   policy={'host':'trendyol.com','checked_at':time.time(),'ok':True,'rules':'User-agent: *\nAllow: /','snapshot':'responses/x.gz','sha256':digest}
   (root/'policies'/'x.json').write_text(json.dumps(policy))
   def one(client,url):return Fetch(url,200,raw.decode() if url.endswith('/robots.txt') else '<h1>Forbidden search content</h1>',fetched_at=time.time())
   with patch.object(PoliteClient,'_one',one):
    client=PolicyClient(root,time.time()+100);r=client.fetch('https://www.trendyol.com/sr/innative-x-b1992600')
   self.assertFalse(r.ok);self.assertEqual(r.error,'robots_disallowed')
if __name__=='__main__':unittest.main()
