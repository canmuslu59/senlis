import gzip,hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from commerce_v5_state import Store,sha,chain

OLD='a'*40
NEW='b'*40

class ResumeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  rows=[{'id':'1','brand_name':'A','product_name':'One'}]
  task={'kind':'product','url':'https://shop.example/p','source':{'id':'shop','host':'shop.example'},'product_ids':['1']}
  s=Store(self.root,rows,[task,dict(task,url='https://shop.example/q')],code_sha=OLD)
  s.record(s.next_task(),{},[{'product_id':'1','reason':'price_unproven','offers':[]}],[],{'complete':True},success=True)
  s.record(s.next_task(),{'http_status':503},[],[],{},success=False,error='http_backoff',retry_at=900)
  s.flush();self.before=s.summary();self.anchor={'campaign_sha256':sha(self.root/'campaign.json'),'previous_code_sha':OLD,'base_state_commit':'c'*40,'base_event_count':s.manifest['event_count'],'base_event_chain_sha256':s.manifest['head_sha256']};s.close()
  self.immutable={str(p.relative_to(self.root)):p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
 def activate(self,anchor=None):
  from commerce_v5_state import activate_runtime
  return activate_runtime(self.root,NEW,anchor or self.anchor)
 def test_revision_preserves_campaign_finished_pages_attempts_and_cooldowns(self):
  self.activate()
  for name,raw in self.immutable.items():self.assertEqual((self.root/name).read_bytes(),raw)
  s=Store(self.root,code_sha=NEW)
  self.assertEqual(s.summary()['completed_pages'],1);self.assertIsNone(s.next_task(899))
  task=s.next_task(901);self.assertEqual(task['url'],'https://shop.example/q');self.assertEqual(task['attempts'],1)
  s.record(task,{},[{'product_id':'1','reason':'price_unproven','offers':[]}],[],{'complete':True},success=True);s.flush();s.close()
  self.activate()  # An idempotent retry must retain the original transition point.
  s=Store(self.root,code_sha=NEW);self.assertIsNone(s.next_task());self.assertEqual(s.summary()['completed_pages'],2);s.close()
 def test_new_runtime_requires_explicit_revision_and_retires_previous_runtime(self):
  with self.assertRaisesRegex(ValueError,'code'):Store(self.root,code_sha=NEW)
  self.activate()
  with self.assertRaisesRegex(ValueError,'code|runtime'):Store(self.root,code_sha=OLD)
 def test_activation_rejects_unexpected_checkpoint_without_writing_revision(self):
  for change in [{'base_event_count':0},{'base_event_chain_sha256':'0'*64},{'campaign_sha256':'0'*64}]:
   with self.subTest(change=change):
    with self.assertRaisesRegex(ValueError,'checkpoint|campaign'):self.activate(dict(self.anchor,**change))
    self.assertFalse((self.root/'runtime_revision.json').exists())
 def test_revision_cannot_claim_a_different_event_boundary(self):
  self.activate();p=self.root/'runtime_revision.json';data=json.loads(p.read_text());data['base_event_count']=1;p.write_text(json.dumps(data))
  with self.assertRaisesRegex(ValueError,'boundary|revision|event'):Store(self.root,code_sha=NEW)
 def test_new_events_must_name_the_approved_runtime_and_revision(self):
  self.activate();s=Store(self.root,code_sha=NEW);t=s.next_task(901)
  s.record(t,{'http_status':404},[],[],{},success=False,error='http_error');s.flush();s.close()
  manifest=json.loads((self.root/'event_manifest.json').read_text());last=manifest['segments'][-1];p=self.root/'events'/last['file']
  event=json.loads(gzip.decompress(p.read_bytes()).decode());self.assertEqual(event['code_sha'],NEW)
  self.assertEqual(event['runtime_revision_sha256'],sha(self.root/'runtime_revision.json'))
  # Even a structurally valid hash chain cannot accept an old-runtime event
  # after the transition boundary.
  event['code_sha']=OLD;raw=(json.dumps(event)+'\n').encode();digest=hashlib.sha256(raw).hexdigest();new=p.with_name('00000001-'+digest+'.jsonl.gz');p.unlink();new.write_bytes(gzip.compress(raw,mtime=0))
  head=chain(manifest['segments'][-2]['chain_sha256'],digest,1)
  last.update(file=new.name,sha256=digest,chain_sha256=head);manifest['head_sha256']=head
  (self.root/'event_manifest.json').write_text(json.dumps(manifest))
  with self.assertRaisesRegex(ValueError,'event|runtime'):Store(self.root,code_sha=NEW)
 def test_cannot_delete_a_revision_after_new_events(self):
  self.activate();s=Store(self.root,code_sha=NEW);s.record(s.next_task(901),{'http_status':404},[],[],{},success=False,error='http_error');s.flush();s.close()
  (self.root/'runtime_revision.json').unlink()
  with self.assertRaisesRegex(ValueError,'event|runtime'):Store(self.root,code_sha=OLD)

class ResumeCliTests(unittest.TestCase):
 def test_checked_checkpoint_and_saved_null_page_resume_without_reinitializing(self):
  from commerce_full_v5 import Checkpoint
  from commerce_v5_resume import resume
  from commerce_v5_state import BRANCH
  def git(path,*args):return subprocess.run(['git','-C',str(path),*args],check=True,capture_output=True,text=True).stdout.strip()
  with tempfile.TemporaryDirectory() as tmp:
   base=Path(tmp);remote=base/'remote';remote.mkdir();git(remote,'init','--bare','-q')
   co=base/'co';co.mkdir();git(co,'init','-q','-b',BRANCH);git(co,'remote','add','origin',str(remote))
   cp=Checkpoint(co);url='https://www.trendyol.com/innative/blue-essence-edp-50-ml-p-555'
   row={'id':'1','brand_name':'INNATIVE','product_name':'BLUE ESSENCE (Eau de Parfum)'}
   task={'kind':'product','url':url,'product_ids':['1'],'source':{'id':'trendyol','host':'trendyol.com','market':'TR','kind':'marketplace'}}
   st=Store(cp.root,[row],[task],code_sha=OLD);st.close()
   raw='<script type="application/ld+json">'+json.dumps({'@type':'Product','name':'INNATIVE BLUE ESSENCE EDP 50 ml','offers':{'price':99,'priceCurrency':'TRY'},'isRelatedTo':None})+'</script>'
   digest=hashlib.sha256(raw.encode()).hexdigest();(cp.root/'responses').mkdir();(cp.root/'responses'/f'{digest}.txt.gz').write_bytes(gzip.compress(raw.encode()))
   cp.persist();manifest=json.loads((cp.root/'event_manifest.json').read_text())
   spec={'anchor':{'campaign_sha256':sha(cp.root/'campaign.json'),'previous_code_sha':OLD,'base_state_commit':git(co,'rev-parse','HEAD'),'base_event_count':0,'base_event_chain_sha256':manifest['head_sha256']},'failed_url':url,'snapshot_sha256':digest}
   specpath=base/'spec.json';specpath.write_text(json.dumps(spec))
   initial={p.name:p.read_bytes() for p in cp.root.iterdir() if p.is_file()}
   with patch.dict(os.environ,{'GITHUB_SHA':NEW}):
    self.assertEqual(resume(co,specpath),0);first=git(co,'rev-parse','HEAD')
    self.assertEqual(resume(co,specpath),0);self.assertEqual(git(co,'rev-parse','HEAD'),first)
   for name,raw in initial.items():self.assertEqual((cp.root/name).read_bytes(),raw)
   clone=base/'clone';subprocess.run(['git','clone','-q','-b',BRANCH,str(remote),str(clone)],check=True,capture_output=True)
   st=Store(Checkpoint(clone).root,code_sha=NEW);self.assertEqual(st.next_task()['attempts'],0);self.assertEqual(st.summary()['scope_total'],1);st.close()
   (co/'unpublished').write_text('not checkpointed')
   with patch.dict(os.environ,{'GITHUB_SHA':NEW}),self.assertRaisesRegex(ValueError,'unpublished'):resume(co,specpath)

if __name__=='__main__':unittest.main()
