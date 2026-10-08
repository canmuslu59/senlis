import importlib.util,json,gzip,sys,tempfile,unittest,subprocess
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
class CliTests(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(importlib.util.find_spec('commerce_full_v5'),'v5 runner missing')
  import commerce_full_v5
  self.api=commerce_full_v5
 def test_export_preserves_all_products_and_every_currency(self):
  from commerce_v5_state import Store
  with tempfile.TemporaryDirectory() as tmp:
   rows=[{'id':'1','brand_name':'A','product_name':'One'},{'id':'2','brand_name':'A','product_name':'Two'}]
   task={'kind':'product','url':'https://shop.example/a','source':{'id':'s','host':'shop.example'},'product_ids':['1']};s=Store(tmp,rows,[task],code_sha='abc');t=s.next_task(1)
   offers=[{'amount':'40.00','currency':c,'market':m,'volume_ml':50,'stock_status':'in_stock','purchase_url':t['url'],'seller_name':'s'} for c,m in [('USD','US'),('EUR','FR')]]
   s.record(t,{},[{'product_id':'1','reason':'verified','offers':offers,'observations':offers}],[],{'complete':True},success=True)
   self.api.export(s);out=[json.loads(x) for x in gzip.decompress((Path(tmp)/'results.jsonl.gz').read_bytes()).splitlines()]
   self.assertEqual(len(out),2);self.assertEqual({x['currency'] for x in out[0]['offers']},{'USD','EUR'});self.assertTrue((Path(tmp)/'commerce_v5.sqlite.gz').exists());s.close()
 def test_checkpoint_round_trip_and_wrong_branch_fail_closed(self):
  from commerce_v5_state import BRANCH
  def git(path,*args):return subprocess.run(['git','-C',str(path),*args],check=True,capture_output=True,text=True).stdout.strip()
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);remote=base/'remote.git';remote.mkdir();git(remote,'init','--bare','-q');checkout=base/'checkout';checkout.mkdir();git(checkout,'init','-q','-b',BRANCH);git(checkout,'config','user.name','Test');git(checkout,'config','user.email','test@example.invalid');git(checkout,'remote','add','origin',str(remote))
   cp=self.api.Checkpoint(checkout);(cp.root/'proof.json').write_text('{"proof":true}');cp.persist()
   self.assertEqual(json.loads(git(remote,'show',BRANCH+':data/commerce_v5/20261007/proof.json')),{'proof':True})
   git(checkout,'switch','-q','-c','wrong')
   with self.assertRaisesRegex(RuntimeError,'branch'):cp.persist()
 def test_failed_push_never_claims_persistence(self):
  with tempfile.TemporaryDirectory() as tmp:
   cp=self.api.Checkpoint(tmp)
   from commerce_v5_state import BRANCH
   class R:
    def __init__(self,stdout='',rc=0):self.stdout=stdout;self.returncode=rc
   def fake(*args,**kw):
    if args[0]=='rev-parse':return R(str(Path(tmp).resolve()))
    if args[0]=='branch':return R(BRANCH)
    return R(rc=1 if args[0]=='push' else 0)
   with patch.object(cp,'git',side_effect=fake),patch('commerce_full_v5.time.sleep'):
    with self.assertRaisesRegex(RuntimeError,'push failed'):cp.persist()
 def test_worker_checkpoint_restore_and_export_end_to_end(self):
  from commerce_v5_state import Store,BRANCH,RELATIVE_ROOT
  from commerce_v3_http import Fetch
  from types import SimpleNamespace
  def git(path,*args):return subprocess.run(['git','-C',str(path),*args],check=True,capture_output=True,text=True).stdout.strip()
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);remote=base/'remote';remote.mkdir();git(remote,'init','--bare','-q');co=base/'co';co.mkdir();git(co,'init','-q','-b',BRANCH);git(co,'config','user.name','Test');git(co,'config','user.email','test@example.invalid');git(co,'remote','add','origin',str(remote))
   source={'id':'test','host':'shop.example','kind':'retailer','market':'US'}
   row={'id':'1','brand_name':'Lalique','product_name':'Amethyst','concentration':'EDP'}
   task={'kind':'product','url':'https://shop.example/p','source':source,'product_ids':['1']}
   st=Store(co/RELATIVE_ROOT,[row],[task]);st.close()
   obj={'@type':'Product','name':'Lalique Amethyst EDP 100 ml','brand':{'name':'Lalique'},'offers':{'price':'60','priceCurrency':'USD','availability':'https://schema.org/InStock'}}
   raw='<h1>Lalique Amethyst EDP 100 ml</h1><script type="application/ld+json">'+json.dumps(obj)+'</script>'
   class Client:
    calls=0
    def __init__(self,root,deadline):self.deadline=deadline;self.cooldowns={}
    def fetch(self,url):Client.calls+=1;return Fetch(url,200,raw,fetched_at=100)
   args=SimpleNamespace(state=str(co),seconds=600)
   with patch.object(self.api,'PolicyClient',Client):self.api.worker(args);self.api.worker(args)
   self.assertEqual(Client.calls,1)
   clone=base/'clone';subprocess.run(['git','clone','-q','-b',BRANCH,str(remote),str(clone)],check=True,capture_output=True)
   restored=Store(clone/RELATIVE_ROOT);self.assertEqual(restored.summary()['verified_price_products'],1);self.assertEqual(restored.summary()['turkey_in_stock_products'],0)
   self.api.export(restored);self.assertTrue((clone/RELATIVE_ROOT/'commerce_v5.sqlite.gz').exists());restored.close()
 def test_live_gate_needs_trendyol_eur_usd_and_correct_controls(self):
  result={'targets':10,'verified_price_products':7,'currencies':['TRY','EUR','USD'],'trendyol_verified':2,'negative_controls_passed':2,'negative_controls_total':2}
  self.assertTrue(self.api.pilot_gate(result));self.assertFalse(self.api.pilot_gate(dict(result,trendyol_verified=0)));self.assertFalse(self.api.pilot_gate(dict(result,currencies=['TRY','EUR'])));self.assertFalse(self.api.pilot_gate(dict(result,negative_controls_passed=1)))
if __name__=='__main__':unittest.main()
