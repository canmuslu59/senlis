#!/usr/bin/env python3
"""Full catalogue CLI, append-only checkpoints and resumable GitHub batches."""
import argparse
import base64
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import time
from urllib.parse import quote

import requests
from commerce_v3_http import PoliteClient
from commerce_v3_engine import Engine, PROVIDERS

VERSION='v3.1'
TOTAL=174259
SHARDS=192
COLS=['product_id','brand_name','product_name','release_year','link_status','price_status',
      'price_try','currency','volume_ml','seller_name','purchase_url','stock_status',
      'source_product_name','discovery_source','price_source','page_verified','match_confidence',
      'checked_at','method_version','checkout_verified','error']


def terminal(row):
    return row.get('method_version')==VERSION and row.get('link_status') in ('verified_link','not_found','candidate')


def latest_records(records):
    out={}
    for row in records:
        pid=str(row.get('product_id') or '')
        if not pid:continue
        old=out.get(pid)
        if old is None or (row.get('checked_at',''),terminal(row))>=(old.get('checked_at',''),terminal(old)):
            out[pid]=row
    return out


def load_rows():
    rows=[]
    for p in sorted(Path('data/master_manifest_174259').glob('part_*')):
        op=gzip.open if p.suffix=='.gz' else open
        with op(p,'rt',encoding='utf-8-sig',newline='') as f:rows.extend(csv.DictReader(f))
    rows.sort(key=lambda r:int(r['id']))
    if len(rows)!=TOTAL or len({r['id'] for r in rows})!=TOTAL:
        raise RuntimeError(f'manifest integrity error: {len(rows)} rows')
    return rows


def assign(rows,shard,shards=SHARDS):
    if not 0<=shard<shards:raise ValueError('invalid shard')
    return rows[shard::shards]


def merge_records(rows,records):
    latest=latest_records(records)
    return [latest.get(str(r['id']),{'product_id':str(r['id']),'brand_name':r['brand_name'],
             'product_name':r['product_name'],'release_year':r.get('release_year',''),
             'link_status':'pending','price_status':'not_checked','method_version':VERSION,
             'checkout_verified':False}) for r in rows]


def summarize(records,assigned,seconds):
    completed=sum(terminal(r) for r in records)
    statuses=Counter(r.get('link_status','pending') for r in records)
    elapsed=max(seconds,0.001)
    return {'method_version':VERSION,'assigned':assigned,'observed':len(records),'completed':completed,
            'remaining':assigned-completed,'progress_pct':round(100*completed/assigned,3) if assigned else 100,
            'verified_links':sum(r.get('link_status')=='verified_link' for r in records),
            'verified_prices':sum(r.get('price_status')=='verified_price' and r.get('price_try') is not None for r in records),
            'status_counts':dict(statuses),'seconds':round(seconds,1),
            'rows_per_hour':round(completed/elapsed*3600,2),'complete':completed==assigned,
            'generated_at':datetime.now(timezone.utc).isoformat()}


def read_chunks(root):
    rows=[]
    for p in sorted(root.glob('*.jsonl.gz')):
        with gzip.open(p,'rt',encoding='utf-8') as f:
            rows.extend(json.loads(line) for line in f if line.strip())
    journal=root/'journal.jsonl'
    if journal.exists():
        lines=journal.read_text(encoding='utf-8').splitlines()
        for i,line in enumerate(lines):
            if not line.strip():continue
            try:rows.append(json.loads(line))
            except ValueError:
                if i!=len(lines)-1:raise
    return list(latest_records(rows).values())


def retry_at(result,now):
    deadlines=[e.get('retry_at',0) for e in result.get('events',[]) if e.get('retry_at',0)>now]
    return max(now+120,min(deadlines)) if deadlines else now+120


class Publisher:
    def __init__(self,branch='data/commerce-v3-20261004'):
        self.token=os.environ.get('GITHUB_TOKEN','')
        self.repo=os.environ.get('GITHUB_REPOSITORY','canmuslu59/senlis')
        if self.repo!='canmuslu59/senlis':raise ValueError('unexpected checkpoint repository')
        self.branch=branch
        self.session=requests.Session()
        self.session.headers.update({'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
        if self.token:self.session.headers['Authorization']='Bearer '+self.token

    def _url(self,path):
        return f'https://api.github.com/repos/{self.repo}/contents/'+quote(path,safe='/')

    def load(self,shard):
        path=f'data/commerce_v3_checkpoints/{VERSION}/part_{shard:03d}'
        r=self.session.get(self._url(path),params={'ref':self.branch},timeout=30)
        if r.status_code==404:return []
        r.raise_for_status();rows=[]
        for item in r.json():
            if not item['name'].endswith('.jsonl.gz'):continue
            f=self.session.get(self._url(path+'/'+item['name']),params={'ref':self.branch},timeout=30)
            f.raise_for_status();obj=f.json()
            raw=gzip.decompress(base64.b64decode(obj['content']))
            rows.extend(json.loads(line) for line in raw.decode().splitlines() if line)
        return rows

    def chunk(self,shard,name,data):
        if not self.token:return False
        path=f'data/commerce_v3_checkpoints/{VERSION}/part_{shard:03d}/{name}'
        body={'message':f'checkpoint: commerce v3 shard {shard:03d}',
              'content':base64.b64encode(data).decode(),'branch':self.branch}
        for attempt in range(6):
            r=self.session.put(self._url(path),json=body,timeout=30)
            if r.status_code in (200,201):return True
            if r.status_code in (409,422):
                current=self.session.get(self._url(path),params={'ref':self.branch},timeout=30)
                if current.status_code==200:
                    if base64.b64decode(current.json()['content'])!=data:raise RuntimeError('checkpoint hash collision')
                    return True
            if r.status_code not in (409,422,429,500,502,503,504):
                raise RuntimeError(f'checkpoint write HTTP {r.status_code}')
            time.sleep(min(20,2**attempt))
        raise RuntimeError('checkpoint write retries exhausted')


class Journal:
    def __init__(self,root,shard,publisher=None):
        self.root=root;self.root.mkdir(parents=True,exist_ok=True)
        self.shard=shard;self.publisher=publisher;self.buffer=[];self.last_flush=time.time()
        self.remote_errors=0

    def append(self,row):
        self.buffer.append(row)
        # An append-only local journal survives process termination between uploads.
        with (self.root/'journal.jsonl').open('a',encoding='utf-8') as f:
            f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())

    def flush(self):
        if not self.buffer:return
        raw=('\n'.join(json.dumps(r,ensure_ascii=False,sort_keys=True) for r in self.buffer)+'\n').encode()
        compressed=gzip.compress(raw,mtime=0)
        name=hashlib.sha256(compressed).hexdigest()+'.jsonl.gz'
        path=self.root/name;temp=path.with_suffix('.tmp');temp.write_bytes(compressed);temp.replace(path)
        if self.publisher:
            try:
                if not self.publisher.chunk(self.shard,name,compressed):raise RuntimeError('checkpoint token unavailable')
            except Exception as exc:
                self.remote_errors+=1
                print('CHECKPOINT_RETRY',type(exc).__name__,str(exc)[:100],flush=True)
                # Retain the buffer: a later flush retries all unacknowledged records.
                self.last_flush=time.time();return
        self.buffer=[];self.last_flush=time.time()


def save_outputs(root,rows,summary,stem):
    root.mkdir(parents=True,exist_ok=True)
    with (root/(stem+'.jsonl')).open('w',encoding='utf-8') as f:
        for r in rows:f.write(json.dumps(r,ensure_ascii=False)+'\n')
    with (root/(stem+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=COLS,extrasaction='ignore');w.writeheader();w.writerows(rows)
    (root/(stem+'_summary.json')).write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:
            f.write(f"\n### {stem}\n\nCompleted: {summary['completed']}/{summary['assigned']} ({summary['progress_pct']}%). Verified prices: {summary['verified_prices']}. Remaining/deferred: {summary['remaining']}.\n")


def worker(args):
    start=time.time();rows=assign(load_rows(),args.shard)
    ids={r['id'] for r in rows};root=Path(args.output);chunkroot=root/f'chunks_{args.shard:03d}'
    publisher=Publisher() if os.environ.get('GITHUB_TOKEN') else None
    previous=[]
    if publisher:previous=publisher.load(args.shard)
    previous+=read_chunks(chunkroot)
    previous=[r for r in previous if str(r['product_id']) in ids]
    results=latest_records(previous)
    journal=Journal(chunkroot,args.shard,publisher)
    seeds=json.loads(Path('data/commerce_v3_seeds.json').read_text())
    client=PoliteClient(args.shard%4,4,deadline=start+args.seconds-90)
    engine=Engine(client,seeds)
    print('START',json.dumps({'scope_total':TOTAL,'shard':args.shard,'shards':SHARDS,'assigned':len(rows),
          'resumed':sum(terminal(r) for r in results.values()),'lane':args.shard%4,'host_slot_seconds':2.5,'workers':2}),flush=True)
    attempts=Counter();last_progress=time.time();retry_times={}
    while time.time()<client.deadline-60:
        remaining=[r for r in rows if not terminal(results.get(r['id'],{})) and attempts[r['id']]<3]
        todo=[r for r in remaining if retry_times.get(r['id'],0)<=time.time()]
        if not todo and remaining:
            due=min(retry_times.get(r['id'],0) for r in remaining)
            time.sleep(min(30,max(0.1,due-time.time())))
            continue
        if not todo:break
        # If all discovery providers are cooling down, wait instead of bulk-labeling rows.
        ready=min(client.available_at(url) for url,_ in PROVIDERS.values())
        if ready>time.time():
            while time.time()<min(ready,client.deadline-60):time.sleep(min(30,max(0.1,ready-time.time())))
        iterator=iter(todo)
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending={}
            def submit_one():
                if time.time()>=client.deadline-60:return
                try:r=next(iterator)
                except StopIteration:return
                attempts[r['id']]+=1;pending[pool.submit(engine.discover,r)]=r
            submit_one();submit_one()
            while pending:
                done,_=wait(pending,timeout=15,return_when=FIRST_COMPLETED)
                for fut in done:
                    row=pending.pop(fut)
                    try:result=fut.result()
                    except Exception as exc:
                        result={'product_id':row['id'],'brand_name':row['brand_name'],'product_name':row['product_name'],
                                'link_status':'worker_error','price_status':'not_checked','method_version':VERSION,
                                'checked_at':datetime.now(timezone.utc).isoformat(),'error':type(exc).__name__+': '+str(exc)[:120]}
                    results[row['id']]=result;journal.append(result)
                    if not terminal(result):retry_times[row['id']]=retry_at(result,time.time())
                    if len(journal.buffer)>=50 or time.time()-journal.last_flush>=300:journal.flush()
                    submit_one()
                if time.time()-last_progress>=60:
                    summary=summarize(list(results.values()),len(rows),time.time()-start)
                    summary.update(shard=args.shard,scope_total=TOTAL,http_stats=dict(client.stats),search_stats=dict(engine.stats))
                    save_outputs(root,list(results.values()),summary,f'shard_{args.shard:03d}')
                    print('CHECKPOINT',json.dumps(summary),flush=True);last_progress=time.time()
                if journal.buffer and time.time()-journal.last_flush>=300:journal.flush()
        if any(not terminal(results.get(r['id'],{})) for r in rows) and time.time()<client.deadline-60:
            time.sleep(min(30,max(0,client.deadline-time.time()-60)))
    journal.flush()
    merged=merge_records(rows,list(results.values()))
    summary=summarize(merged,len(rows),time.time()-start)
    summary.update(shard=args.shard,scope_total=TOTAL,http_stats=dict(client.stats),search_stats=dict(engine.stats),remote_checkpoint_errors=journal.remote_errors)
    save_outputs(root,merged,summary,f'shard_{args.shard:03d}')
    print('SUMMARY',json.dumps(summary),flush=True)
    # Deferred remains visible; later waves still run and final merge flags incompleteness.
    return 0


def canary(args):
    start=time.time();seeds=json.loads(Path('data/commerce_v3_seeds.json').read_text())
    ids=set(seeds['canary_ids']);rows=[r for r in load_rows() if r['id'] in ids]
    client=PoliteClient(0,1,deadline=start+args.seconds-30);engine=Engine(client,seeds)
    search_ready=False
    for pid in ('36013','90677','113828'):
        row=next(r for r in rows if r['id']==pid)
        from commerce_v3_engine import queries
        links,ok,events=engine.search(row,queries(row)[0]);search_ready|=ok and bool(links)
        print('SEARCH_PROBE',json.dumps({'id':pid,'events':events,'relevant_results':len(links)}),flush=True)
        if search_ready:break
    results=[]
    for r in rows:
        result=engine.discover(r);results.append(result)
        print('CANARY',json.dumps({k:v for k,v in result.items() if k!='events'},ensure_ascii=False),flush=True)
    summary=summarize(results,len(rows),time.time()-start)
    summary.update(search_ready=search_ready,gate_passed=search_ready and summary['verified_prices']>=2,
                   http_stats=dict(client.stats),search_stats=dict(engine.stats),scope_total=TOTAL)
    save_outputs(Path(args.output),results,summary,'canary')
    print('CANARY_SUMMARY',json.dumps(summary),flush=True)
    return 0 if summary['gate_passed'] else 2


def merge(args):
    start=time.time();rows=load_rows();records=[]
    for p in Path(args.inputs).glob('**/shard_*.jsonl'):
        with p.open(encoding='utf-8') as f:records.extend(json.loads(line) for line in f if line.strip())
    merged=merge_records(rows,records);summary=summarize(merged,TOTAL,time.time()-start)
    summary.pop('rows_per_hour',None)
    root=Path(args.output);save_outputs(root,merged,summary,'SENLIS_commerce_full_v3')
    with sqlite3.connect(root/'SENLIS_commerce_full_v3.sqlite') as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS commerce (product_id TEXT PRIMARY KEY, record_json TEXT NOT NULL)')
        conn.executemany('INSERT OR REPLACE INTO commerce VALUES (?,?)',[(r['product_id'],json.dumps(r,ensure_ascii=False)) for r in merged])
        conn.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)')
        conn.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)',('summary',json.dumps(summary)))
    print('FINAL',json.dumps(summary),flush=True)
    return 0 if summary['complete'] else 2


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['canary','worker','merge'])
    p.add_argument('--shard',type=int,default=0);p.add_argument('--seconds',type=int,default=18000)
    p.add_argument('--output',default='commerce_v3_out');p.add_argument('--inputs',default='commerce_v3_inputs')
    args=p.parse_args();return {'canary':canary,'worker':worker,'merge':merge}[args.mode](args)


if __name__=='__main__':raise SystemExit(main())
