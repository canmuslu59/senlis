import importlib.util,json,tempfile,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))

class RunnerTests(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(importlib.util.find_spec('commerce_v5_state'),'v5 state missing')
  import commerce_v5_state
  self.api=commerce_v5_state;self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.rows=[{'id':'1','brand_name':'A','product_name':'One'},{'id':'2','brand_name':'A','product_name':'Two'}]
  self.task={'kind':'product','url':'https://shop.example/p','source':{'id':'shop','host':'shop.example','market':'TR','kind':'retailer'},'product_ids':['1']}
 def create(self):return self.api.Store(self.root,self.rows,[self.task],code_sha='abc')
 def finish(self,s,t,**kw):
  return s.record(t,{'snapshot':None,'decoded_sha256':'h','fetched_at':'2026-10-07T00:00:00Z','http_status':200},[{'product_id':pid,'reason':'price_unproven','offers':[],'observations':[]} for pid in t['product_ids']],[],{'complete':True},success=True,**kw)
 def test_resume_never_fetches_finished_page(self):
  s=self.create();t=s.next_task(100);self.finish(s,t);s.flush();s.close();r=self.api.Store(self.root,code_sha='abc')
  self.assertIsNone(r.next_task(200));self.assertEqual(r.summary()['completed_pages'],1);r.close()
 def test_new_identity_on_finished_url_reuses_evidence(self):
  s=self.create();t=s.next_task(100)
  s.record(t,{'snapshot':'responses/x.txt.gz','decoded_sha256':'h','fetched_at':'x'},[{'product_id':'1','reason':'price_unproven','offers':[],'observations':[]}],[dict(self.task,product_ids=['2'])],{'complete':True},success=True)
  t=s.next_task(200);self.assertIsNotNone(t);self.assertTrue(t['reuse_evidence']);self.assertEqual(t['product_ids'],['1','2']);s.close()
 def test_attempt_cap_and_retry_after_survive_restart(self):
  s=self.create()
  for attempt in range(3):
   t=s.next_task(1000+attempt*100);s.record(t,{'http_status':503},[],[],{},success=False,error='http_backoff',retry_at=1100+attempt*100)
   self.assertIsNone(s.next_task(1001+attempt*100))
  s.flush();s.close();s=self.api.Store(self.root,code_sha='abc');self.assertIsNone(s.next_task(9000));self.assertEqual(s.summary()['unresolved_pages'],1);s.close()
 def test_cooldown_is_host_wide_and_durable(self):
  s=self.api.Store(self.root,self.rows,[self.task,dict(self.task,url='https://shop.example/q')],code_sha='abc')
  s.record(s.next_task(100),{'http_status':429},[],[],{},success=False,error='http_backoff',retry_at=400)
  s.flush();s.close();s=self.api.Store(self.root,code_sha='abc');self.assertIsNone(s.next_task(399));self.assertIsNotNone(s.next_task(400));s.close()
 def test_manifest_or_code_change_fails_closed(self):
  s=self.create();s.close()
  with self.assertRaisesRegex(ValueError,'code'):self.api.Store(self.root,code_sha='other')
  with (self.root/'scope.jsonl.gz').open('ab') as f:f.write(b'bad')
  with self.assertRaisesRegex(ValueError,'hash'):self.api.Store(self.root,code_sha='abc')
 def test_no_old_or_missing_identity_can_be_added(self):
  with self.assertRaisesRegex(ValueError,'identity'):self.api.Store(self.root,self.rows,[dict(self.task,product_ids=['3'])],code_sha='abc')
 def test_currency_and_domestic_availability_are_separate(self):
  s=self.create();t=s.next_task(100)
  def offer(cur,market,stock):return {'amount':'10.00','currency':cur,'market':market,'stock_status':stock,'volume_ml':50,'purchase_url':t['url'],'seller_name':'s'}
  offers=[offer('USD','US','in_stock'),offer('EUR','FR','out_of_stock')]
  s.record(t,{'fetched_at':'x'},[{'product_id':'1','offers':offers,'observations':offers,'reason':'verified'}],[],{'complete':True},success=True)
  sm=s.summary();self.assertEqual(sm['verified_price_products'],1);self.assertEqual(sm['turkey_in_stock_products'],0);self.assertEqual(sm['currency_products'],{'EUR':1,'USD':1})
  results=list(s.results());self.assertEqual(len(results),2);self.assertEqual(len(results[0]['best_offers']),2);s.close()
 def test_404_is_unavailable_not_transient_failure(self):
  s=self.create();s.record(s.next_task(100),{'http_status':404},[],[],{},success=False,error='http_error');sm=s.summary()
  self.assertTrue(sm['finished']);self.assertEqual(sm['unavailable_pages'],1);self.assertEqual(sm['unresolved_pages'],0);s.close()
 def test_partial_source_is_not_complete_or_global_absence(self):
  task={'kind':'reference','url':'https://www.fragrantica.com/p','brand':'A'}
  s=self.api.Store(self.root,self.rows,[task],code_sha='abc');s.record(s.next_task(100),{'http_status':200},[],[],{'complete':False,'reason':'official_site_unconfirmed'},success=True)
  sm=s.summary();self.assertTrue(sm['finished']);self.assertFalse(sm['complete']);self.assertEqual(sm['proven_searches'],0);self.assertFalse(sm['global_absence_proven']);s.close()
 def test_missing_product_decision_cannot_be_marked_done(self):
  s=self.create()
  with self.assertRaisesRegex(ValueError,'missing product decision'):
   s.record(s.next_task(100),{'http_status':200},[],[],{'complete':True},success=True)
  s.close()
 def test_event_corruption_is_detected(self):
  s=self.create();self.finish(s,s.next_task(100));s.flush();s.close();p=next((self.root/'events').glob('*.jsonl.gz'));p.write_bytes(b'corrupt')
  with self.assertRaises(ValueError):self.api.Store(self.root,code_sha='abc')

 def test_missing_event_segment_or_manifest_fails_closed(self):
  s=self.create();self.finish(s,s.next_task(100));s.flush();s.close()
  path=next((self.root/'events').glob('*.jsonl.gz'));path.unlink()
  with self.assertRaisesRegex(ValueError,'event|segment|checkpoint'):self.api.Store(self.root,code_sha='abc')
 def test_lost_campaign_manifest_cannot_reinitialize_residual_state(self):
  s=self.create();s.close();(self.root/'campaign.json').unlink()
  with self.assertRaisesRegex(ValueError,'residual'):self.create()
 def test_missing_event_manifest_fails_closed_even_before_first_page(self):
  s=self.create();s.close();(self.root/'event_manifest.json').unlink(missing_ok=True)
  with self.assertRaisesRegex(ValueError,'event|manifest|checkpoint'):self.api.Store(self.root,code_sha='abc')
 def test_missing_last_segment_cannot_silently_rewind(self):
  s=self.api.Store(self.root,self.rows,[self.task,dict(self.task,url='https://shop.example/q')],code_sha='abc')
  self.finish(s,s.next_task(100));s.flush();self.finish(s,s.next_task(200));s.flush();s.close()
  sorted((self.root/'events').glob('*.jsonl.gz'))[-1].unlink()
  with self.assertRaisesRegex(ValueError,'event|segment|checkpoint'):self.api.Store(self.root,code_sha='abc')
 def test_rejected_event_does_not_leave_half_applied_queue_changes(self):
  s=self.create();t=s.next_task(100)
  with self.assertRaisesRegex(ValueError,'identity'):
   s.record(t,{},[{'product_id':'1','reason':'price_unproven','offers':[]},{'product_id':'2','reason':'price_unproven','offers':[]}],[dict(self.task,url='https://shop.example/next')],{},success=True)
  self.assertEqual(s.summary()['tasks_total'],1);self.assertEqual(list(s.results())[0]['decision_reasons'],{});s.close()
 def test_discovery_404_cannot_claim_complete(self):
  task={'kind':'sitemap','url':'https://shop.example/sitemap.xml','source':{'id':'s','host':'shop.example'}}
  s=self.api.Store(self.root,self.rows,[task],code_sha='abc');s.record(s.next_task(100),{'http_status':404},[],[],{},success=False,error='http_error')
  self.assertTrue(s.summary()['finished']);self.assertFalse(s.summary()['complete']);s.close()

if __name__=='__main__':unittest.main()
