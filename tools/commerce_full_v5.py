#!/usr/bin/env python3
"""Immutable all-identity scan with explicit discovery coverage and multi-currency outputs."""
import argparse,csv,gzip,hashlib,json,os,shutil,sqlite3,tempfile,time
from collections import Counter
from pathlib import Path
from commerce_evidence_v4 import Evidence,utc
from commerce_full_v3 import load_rows,TOTAL
from commerce_full_v4 import validated_rows
from commerce_v4_state import GitCheckpoint,read_jsonl,write_jsonl
from commerce_v5_state import Store,BRANCH,RELATIVE_ROOT,VERSION
from commerce_v5_sources import initial_tasks,discover,RowsIndex,source_for,REFERENCE_HOSTS
from commerce_v5_parser import verify_page
from commerce_v5_http import PolicyClient
from commerce_v3_http import host

class Checkpoint(GitCheckpoint):
    def __init__(self,checkout):
        self.checkout=Path(checkout).resolve();self.root=self.checkout/RELATIVE_ROOT;self.root.mkdir(parents=True,exist_ok=True)
    def persist(self):
        if self.git('rev-parse','--show-toplevel').stdout.strip()!=str(self.checkout):raise RuntimeError('checkpoint must have own checkout')
        if self.git('branch','--show-current').stdout.strip()!=BRANCH:raise RuntimeError('wrong checkpoint branch')
        self.git('config','user.name','SENLIS Research');self.git('config','user.email','senlis-research@users.noreply.github.com')
        self.git('add','--',str(RELATIVE_ROOT))
        if self.git('diff','--cached','--quiet',check=False).returncode:self.git('commit','-m','checkpoint: commerce v5 '+utc())
        for attempt in range(3):
            if self.git('push','--quiet','origin','HEAD:refs/heads/'+BRANCH,check=False).returncode==0:return
            if attempt<2:time.sleep(5*(attempt+1))
        raise RuntimeError('checkpoint push failed; recovery artifact required before resuming')


def registry():return json.loads(Path('data/commerce_v5_sources.json').read_text())

def pilot_gate(summary):
    return (summary.get('targets')==10 and summary.get('verified_price_products',0)>=5
            and summary.get('trendyol_verified',0)>=1 and {'TRY','EUR','USD'}<=set(summary.get('currencies',[]))
            and summary.get('negative_controls_passed')==summary.get('negative_controls_total')==2)


def save_summary(store,start=None,initial=0):
    summary=store.summary()
    if start is not None:
        elapsed=time.time()-start;gained=summary['tasks_completed']-initial
        summary.update(worker_seconds=round(elapsed,1),worker_completed_tasks=gained)
        if gained:summary['measured_remaining_hours_current_queue']=round(summary['tasks_pending']*elapsed/gained/3600,2)
        summary['eta_includes_undiscovered_pages']=False
    (store.root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    print('CHECKPOINT',json.dumps(summary,ensure_ascii=False),flush=True)
    path=os.environ.get('GITHUB_STEP_SUMMARY')
    if path:
        with open(path,'a') as f:f.write(f"\nV5: {summary['tasks_completed']}/{summary['tasks_total']} tasks; {summary['completed_pages']}/{summary['total_pages']} pages. Verified products {summary['verified_price_products']}; Turkish in-stock {summary['turkey_in_stock_products']}. Currencies {summary['currency_products']}. Partial discovery {summary['partial_discovery_tasks']}.\n")
    return summary


def prepare(args):
    cp=Checkpoint(args.state)
    if (cp.root/'campaign.json').exists():
        store=Store(cp.root);save_summary(store);store.close();return 0
    pilot=Path(args.evidence);sm=json.loads((pilot/'summary.json').read_text())
    if not pilot_gate(sm):raise ValueError('live 10-product gate failed')
    if sm.get('code_sha')!=os.environ.get('GITHUB_SHA','local'):raise ValueError('pilot code mismatch')
    previous=Path(args.previous)/'data/commerce_v4/20261005';meta=json.loads((previous/'campaign.json').read_text())
    if meta['code_sha']!='dcd5720087962bc0aaa540dbad3fcf223403e7e9':raise ValueError('unexpected previous campaign')
    if hashlib.sha256((previous/'pages.jsonl.gz').read_bytes()).hexdigest()!=meta['pages_file_sha256']:raise ValueError('previous plan hash mismatch')
    definitions=json.loads(Path('data/commerce_v3_seeds.json').read_text());rows,repairs=validated_rows(load_rows(),definitions.get('identity_overrides',{}))
    if len(rows)!=TOTAL:raise ValueError('scope mismatch')
    tasks=initial_tasks(rows,read_jsonl(previous/'pages.jsonl.gz'),registry())
    # Explicit new-region canaries are also queued as normal full-scan pages.
    for check in json.loads((pilot/'checks.json').read_text()):
        src=source_for(check['url'],next(r['brand_name'] for r in rows if r['id']==check['product_id']),registry())
        if src:tasks.append({'kind':'product','url':check['url'],'product_ids':[check['product_id']],'source':src})
    store=Store(cp.root,rows,tasks);shutil.copytree(pilot,cp.root/'pilot',dirs_exist_ok=True)
    (cp.root/'manifest_repairs.json').write_text(json.dumps(repairs,indent=2)+'\n');(cp.root/'source_registry.json').write_text(json.dumps(registry(),ensure_ascii=False,indent=2)+'\n')
    save_summary(store);cp.persist();store.close();return 0


def worker(args):
    cp=Checkpoint(args.state);store=Store(cp.root);reg=registry();index=RowsIndex(store.rows);start=time.time();initial=store.summary()['tasks_completed']
    if not store.pending():store.close();return 0
    client=PolicyClient(cp.root,start+args.seconds-180);evidence=Evidence(cp.root);flushed=time.time();since_flush=0
    for r in store.db.execute('SELECT host,retry_at FROM hosts'):client.cooldowns[r[0]]=r[1]
    def flush():
        nonlocal flushed,since_flush
        store.flush();summary=save_summary(store,start,initial);cp.persist();flushed=time.time();since_flush=0;return summary
    try:
        while time.time()<client.deadline-60:
            task=store.next_task()
            if task is None:
                if not store.pending():break
                if time.time()-flushed>=300:flush()
                due=max(store.next_due(),time.time()+1)
                if due>=client.deadline-60:break
                time.sleep(min(20,max(.1,due-time.time())));continue
            if task['kind']=='reference' and host(task['url']) not in REFERENCE_HOSTS:
                store.record(task,{},[],[],{'complete':False,'reason':'official_site_unconfirmed'},success=False,error='unsupported_reference');since_flush+=1
            else:
                if task['reuse_evidence']:
                    event=task['prior_evidence'];path=cp.root/event['snapshot'];raw=gzip.decompress(path.read_bytes()).decode()
                    if hashlib.sha256(raw.encode()).hexdigest()!=event['decoded_sha256']:raise ValueError('cached response hash mismatch')
                    final_url=event['final_url'];success=True;error='';status=200;retry_at=0
                else:
                    r,event=evidence.fetch(client,task['url']);raw=r.text;final_url=r.url;success=r.ok;error=r.error;status=r.status;retry_at=r.retry_at
                    if error in ('host_cooldown','deadline'):
                        if error=='deadline':break
                        store.db.execute('INSERT INTO hosts(host,retry_at) VALUES(?,?) ON CONFLICT(host) DO UPDATE SET retry_at=MAX(hosts.retry_at,excluded.retry_at)',(host(task['url']),retry_at));continue
                decisions=[];new_tasks=[];audit={'complete':False,'reason':error or 'not_parsed'}
                if success:
                    if task['kind']=='product':
                        for pid in task['product_ids']:
                            verdict=verify_page(raw,final_url,index.by_id[pid],task['source'])
                            for key in ('offers','observations'):
                                for offer in verdict[key]:offer.update(checked_at=event.get('fetched_at'),evidence_sha256=event.get('decoded_sha256'))
                            decisions.append(dict(verdict,product_id=pid))
                    try:new_tasks,audit=discover(task,raw,final_url,index,reg)
                    except ValueError as exc:audit={'complete':False,'reason':'discovery_parse_error','detail':str(exc)[:150]}
                store.record(task,event,decisions,new_tasks,audit,success=success,error=error,retry_at=retry_at or (time.time()+60 if not success else 0))
                since_flush+=1
            if since_flush>=50 or time.time()-flushed>=300:flush()
    finally:
        # Failed pushes raise, stop later serial workers and preserve unpublished
        # local events/snapshots in the workflow's recovery artifact.
        flush();store.close()
    return 0


def export(store):
    root=store.root;results=list(store.results());write_jsonl(root/'results.jsonl.gz',results)
    fields=['product_id','brand_name','product_name','status','currency','market','amount','volume_ml','stock_status','purchase_url','seller_name','seller_id','checked_at','evidence_sha256']
    with tempfile.TemporaryDirectory() as tmp:
        dbpath=Path(tmp)/'commerce_v5.sqlite';db=sqlite3.connect(dbpath)
        db.execute('CREATE TABLE products(product_id TEXT PRIMARY KEY,brand_name TEXT,product_name TEXT,status TEXT,evidence_json TEXT)')
        db.execute('CREATE TABLE offers('+','.join('"'+c+'" TEXT' for c in fields)+')')
        with gzip.open(root/'offers.csv.gz','wt',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader()
            for result in results:
                db.execute('INSERT INTO products VALUES(?,?,?,?,?)',(result['product_id'],result['brand_name'],result['product_name'],result['status'],json.dumps(result,ensure_ascii=False)))
                for offer in result['offers']:
                    row={**result,**offer};writer.writerow(row);db.execute('INSERT INTO offers VALUES('+','.join('?' for _ in fields)+')',[row.get(c) for c in fields])
        db.commit();db.close()
        with dbpath.open('rb') as src,gzip.open(root/'commerce_v5.sqlite.gz','wb') as dst:shutil.copyfileobj(src,dst)
    errors=[dict(r) for r in store.db.execute("SELECT kind,url,brand,source,status,reason,audit FROM tasks WHERE status IN ('error','restricted','unavailable') OR (status='done' AND kind!='product')")]
    write_jsonl(root/'source_audits.jsonl.gz',errors)
    summary=save_summary(store);summary['status_counts']=dict(Counter(r['status'] for r in results));(root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    return summary


def report(args):
    cp=Checkpoint(args.state);store=Store(cp.root);export(store);store.flush();cp.persist();store.close();return 0


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','worker','report']);p.add_argument('--state',default='state');p.add_argument('--previous',default='previous');p.add_argument('--evidence',default='commerce_v5_pilot');p.add_argument('--seconds',type=int,default=5400)
    args=p.parse_args();raise SystemExit(globals()[args.command](args))
