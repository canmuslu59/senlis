#!/usr/bin/env python3
"""Continue the existing campaign after an explicitly authorized code hotfix."""
import argparse,gzip,hashlib,json,os
from pathlib import Path
from commerce_full_v5 import Checkpoint,registry
from commerce_v5_state import Store,activate_runtime,BRANCH
from commerce_v5_sources import RowsIndex,discover
from commerce_v5_parser import verify_page


def saved_failure_gate(store,spec):
    digest=spec['snapshot_sha256']
    raw=gzip.decompress((store.root/'responses'/f'{digest}.txt.gz').read_bytes()).decode()
    if hashlib.sha256(raw.encode()).hexdigest()!=digest:raise ValueError('failed response hash mismatch')
    row=store.db.execute('SELECT * FROM tasks WHERE url=? AND kind=?',(spec['failed_url'],'product')).fetchone()
    if row is None:raise ValueError('failed page absent from existing queue')
    task=json.loads(row['payload']);idx=RowsIndex(store.rows)
    task['product_ids']=[r[0] for r in store.db.execute('SELECT product FROM task_products WHERE task=? ORDER BY product',(row['id'],))]
    decisions=[verify_page(raw,task['url'],idx.by_id[pid],task['source']) for pid in task['product_ids']]
    discovered,audit=discover(task,raw,task['url'],idx,registry())
    if not decisions or not audit['complete']:raise ValueError('saved failure regression gate failed')
    return {'snapshot_sha256':digest,'task_id':row['id'],'decisions':len(decisions),
            'verified_offers':sum(len(d['offers']) for d in decisions),'discovered_candidates':len(discovered),
            'prior_status':row['status'],'prior_attempts':row['attempts']}


def resume(state,spec_path):
    spec=json.loads(Path(spec_path).read_text());anchor=spec['anchor'];cp=Checkpoint(state)
    if cp.git('rev-parse','--show-toplevel').stdout.strip()!=str(cp.checkout):raise ValueError('state must have its own checkout')
    if cp.git('branch','--show-current').stdout.strip()!=BRANCH:raise ValueError('wrong checkpoint branch')
    if cp.git('status','--porcelain','--untracked-files=all').stdout.strip():raise ValueError('unpublished checkpoint changes; recovery required')
    code_sha=os.environ['GITHUB_SHA'];revised=(cp.root/'runtime_revision.json').exists()
    if not revised and cp.git('rev-parse','HEAD').stdout.strip()!=anchor['base_state_commit']:
        raise ValueError('unexpected durable checkpoint commit; review recovery before activation')
    store=Store(cp.root,code_sha=code_sha if revised else anchor['previous_code_sha'])
    try:
        before=store.summary();proof=saved_failure_gate(store,spec)
    finally:store.close()
    revision=activate_runtime(cp.root,code_sha,anchor)
    store=Store(cp.root,code_sha=code_sha)
    try:after=store.summary()
    finally:store.close()
    if {k:v for k,v in before.items() if k!='updated_at'}!={k:v for k,v in after.items() if k!='updated_at'}:
        raise ValueError('queue changed during runtime activation')
    if not revised:
        (cp.root/'resume_validation.json').write_text(json.dumps({'before':before,'after':after,'saved_failure':proof,'runtime_revision':revision},indent=2)+'\n')
    cp.persist()
    print('RESUME_VALIDATED',json.dumps({'code_sha':code_sha,'event_boundary':revision['base_event_count'],
          'completed_pages':after['completed_pages'],'pending_pages':after['pending_pages'],
          'verified_price_products':after['verified_price_products'],'saved_failure':proof}),flush=True)
    return 0


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',default='state');p.add_argument('--spec',default='tools/commerce_v5_resume_checkpoint.json')
    args=p.parse_args();raise SystemExit(resume(args.state,args.spec))
