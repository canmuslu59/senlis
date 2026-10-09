"""Replayable append-only queue events; the SQLite working index is disposable."""
from collections import Counter,defaultdict
from decimal import Decimal
import gzip,hashlib,json,os,re,sqlite3,time
from pathlib import Path
from commerce_evidence_v4 import utc
from commerce_v4_state import read_jsonl,write_jsonl
from commerce_v5_sources import task_id,MAX_MAPS
from commerce_v3_http import host

BRANCH='data/commerce-v5-20261007'
RELATIVE_ROOT=Path('data/commerce_v5/20261007')
VERSION='v5.0-global-evidence'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def chain(head,digest,count):
    return hashlib.sha256(f'{head}:{digest}:{count}'.encode()).hexdigest()


def activate_runtime(root,code_sha,anchor):
    """Explicit one-time, schema-compatible hotfix; never rewrite old evidence."""
    root=Path(root);path=root/'runtime_revision.json'
    if not re.fullmatch('[0-9a-f]{40}',code_sha) or code_sha==anchor['previous_code_sha']:
        raise ValueError('new runtime code must be a different immutable commit')
    if path.exists():
        revision=json.loads(path.read_text())
        if any(revision.get(k)!=v for k,v in anchor.items()):raise ValueError('runtime revision checkpoint mismatch')
        store=Store(root,code_sha=code_sha);store.close();return revision
    store=Store(root,code_sha=anchor['previous_code_sha'])
    try:
        if (sha(root/'campaign.json')!=anchor['campaign_sha256'] or
            store.manifest['event_count']!=anchor['base_event_count'] or
            store.manifest['head_sha256']!=anchor['base_event_chain_sha256']):
            raise ValueError('unexpected campaign/checkpoint for runtime revision')
    finally:store.close()
    revision={**anchor,'version':1,'code_sha':code_sha,'created_at':utc(),
              'run_id':os.environ.get('GITHUB_RUN_ID','local'),
              'reason':'Authorized nullable related-products hotfix; same campaign and queue'}
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(revision,sort_keys=True,indent=2)+'\n');tmp.replace(path)
    store=Store(root,code_sha=code_sha);store.close();return revision


class Store:
    def __init__(self,root,rows=None,tasks=None,code_sha=None):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True);self.buffer=[]
        self.code_sha=code_sha or os.environ.get('GITHUB_SHA','local')
        path=self.root/'campaign.json'
        if rows is not None:
            if path.exists():raise ValueError('campaign exists; never overwrite')
            if any(self.root.iterdir()):raise ValueError('residual checkpoint without campaign; recovery required')
            ids={str(r['id']) for r in rows}
            if len(ids)!=len(rows):raise ValueError('duplicate identity')
            if any(not set(map(str,t.get('product_ids',[])))<=ids for t in tasks):raise ValueError('unknown identity')
            write_jsonl(self.root/'scope.jsonl.gz',rows);write_jsonl(self.root/'initial_tasks.jsonl.gz',tasks)
            meta={'method_version':VERSION,'code_sha':self.code_sha,'created_at':utc(),'scope_total':len(rows),
                  'run_id':os.environ.get('GITHUB_RUN_ID','local'),'scope_sha256':sha(self.root/'scope.jsonl.gz'),
                  'tasks_sha256':sha(self.root/'initial_tasks.jsonl.gz')}
            path.write_text(json.dumps(meta,indent=2)+'\n')
            self._write_manifest({'version':1,'campaign_sha256':sha(path),'segments':[],
                                  'event_count':0,'head_sha256':sha(path)})
        self.campaign=json.loads(path.read_text())
        self.revision=None;self.revision_sha=None
        revision_path=self.root/'runtime_revision.json'
        if revision_path.exists():
            self.revision=json.loads(revision_path.read_text());rev=self.revision
            if (rev.get('version')!=1 or rev.get('campaign_sha256')!=sha(path) or
                rev.get('previous_code_sha')!=self.campaign['code_sha'] or
                rev.get('code_sha')!=self.code_sha or self.code_sha==self.campaign['code_sha'] or
                not re.fullmatch('[0-9a-f]{40}',self.code_sha) or
                type(rev.get('base_event_count')) is not int or rev['base_event_count']<0):
                raise ValueError('runtime revision identity/code mismatch')
            self.revision_sha=sha(revision_path)
        elif self.campaign['code_sha']!=self.code_sha:raise ValueError('campaign code mismatch')
        for f,k in [('scope.jsonl.gz','scope_sha256'),('initial_tasks.jsonl.gz','tasks_sha256')]:
            if sha(self.root/f)!=self.campaign[k]:raise ValueError('campaign hash mismatch')
        try:
            self.manifest=json.loads((self.root/'event_manifest.json').read_text())
            segments=self.manifest['segments'];names=[s['file'] for s in segments]
            if self.manifest['version']!=1 or self.manifest['campaign_sha256']!=sha(path):raise ValueError('event manifest identity mismatch')
            actual=sorted(p.name for p in (self.root/'events').glob('*.jsonl.gz'))
            if names!=actual or len(set(names))!=len(names):raise ValueError('missing or unindexed event segment')
        except (OSError,ValueError,KeyError,TypeError) as e:raise ValueError('invalid event manifest; checkpoint recovery required') from e
        self.rows=rows if rows is not None else read_jsonl(self.root/'scope.jsonl.gz')
        self.identities={str(r['id']):r for r in self.rows}
        if len(self.identities)!=self.campaign['scope_total']:raise ValueError('scope identity mismatch')
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        self.db.executescript('''
        CREATE TABLE tasks(id TEXT PRIMARY KEY,kind TEXT,url TEXT,brand TEXT,source TEXT,host TEXT,payload TEXT,status TEXT DEFAULT 'pending',attempts INTEGER DEFAULT 0,retry_at REAL DEFAULT 0,success INTEGER DEFAULT 0,evidence TEXT DEFAULT '{}',audit TEXT DEFAULT '{}',reason TEXT DEFAULT '',priority INTEGER);
        CREATE TABLE task_products(task TEXT,product TEXT,PRIMARY KEY(task,product));
        CREATE TABLE decisions(task TEXT,product TEXT,payload TEXT,PRIMARY KEY(task,product));
        CREATE TABLE hosts(host TEXT PRIMARY KEY,retry_at REAL DEFAULT 0,blocked INTEGER DEFAULT 0,failures INTEGER DEFAULT 0);
        CREATE INDEX ready ON tasks(status,priority,retry_at);
        CREATE INDEX product_tasks ON task_products(product);
        ''')
        for task in tasks if tasks is not None else read_jsonl(self.root/'initial_tasks.jsonl.gz'):self._enqueue(task)
        head=self.manifest['campaign_sha256'];event_count=0;boundaries={(0,head)}
        for segment in segments:
            path=self.root/'events'/segment['file']
            try:
                raw=gzip.decompress(path.read_bytes())
                digest=hashlib.sha256(raw).hexdigest();lines=raw.splitlines()
                if digest!=segment['sha256'] or digest!=path.name.split('-')[-1].removesuffix('.jsonl.gz'):raise ValueError('event hash mismatch')
                if len(lines)!=segment['event_count']:raise ValueError('event count mismatch')
                head=chain(head,digest,len(lines))
                if head!=segment['chain_sha256']:raise ValueError('event chain mismatch')
                for line in lines:
                    event=json.loads(line)
                    if self.revision and event_count>=self.revision['base_event_count']:
                        if event.get('code_sha')!=self.code_sha or event.get('runtime_revision_sha256')!=self.revision_sha:
                            raise ValueError('event runtime revision mismatch')
                    elif event.get('code_sha',self.campaign['code_sha'])!=self.campaign['code_sha'] or event.get('runtime_revision_sha256'):
                        raise ValueError('unexpected event runtime before revision')
                    self._apply(event);event_count+=1
                boundaries.add((event_count,head))
            except (OSError,ValueError,KeyError) as e:raise ValueError('invalid durable event '+path.name) from e
        if head!=self.manifest['head_sha256'] or event_count!=self.manifest['event_count']:raise ValueError('event checkpoint head mismatch')
        if self.revision and (self.revision['base_event_count'],self.revision.get('base_event_chain_sha256')) not in boundaries:
            raise ValueError('runtime revision is not a verified event boundary')
        self.db.commit()

    def _write_manifest(self,manifest):
        path=self.root/'event_manifest.json';tmp=path.with_suffix('.tmp')
        tmp.write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n');tmp.replace(path)

    def _enqueue(self,task):
        key=task_id(task);ids=list(map(str,task.get('product_ids',[])))
        if not set(ids)<=self.identities.keys():raise ValueError('unknown queue identity')
        priority={'official_home':0,'trendyol_directory':0,'sitemap':0,'product':1,'trendyol_brand':2,'reference':3}[task['kind']]
        h=host(task['url']);source=task.get('source',{}).get('id','reference')
        self.db.execute('INSERT OR IGNORE INTO tasks(id,kind,url,brand,source,host,payload,priority) VALUES(?,?,?,?,?,?,?,?)',
                        (key,task['kind'],task['url'],task.get('brand',''),source,h,json.dumps(task,ensure_ascii=False),priority))
        old_ids={r[0] for r in self.db.execute('SELECT product FROM task_products WHERE task=?',(key,))}
        self.db.executemany('INSERT OR IGNORE INTO task_products VALUES(?,?)',[(key,p) for p in ids])
        if set(ids)-old_ids:
            self.db.execute("UPDATE tasks SET status='pending' WHERE id=? AND success=1",(key,))
        blocked=self.db.execute('SELECT blocked FROM hosts WHERE host=?',(h,)).fetchone()
        if blocked and blocked[0]:self.db.execute("UPDATE tasks SET status='error',reason='host_access_blocked' WHERE id=? AND status='pending'",(key,))
        return key

    def next_task(self,now=None):
        now=time.time() if now is None else now
        row=self.db.execute("SELECT t.* FROM tasks t LEFT JOIN hosts h ON t.host=h.host WHERE t.status='pending' AND t.retry_at<=? AND COALESCE(h.retry_at,0)<=? AND COALESCE(h.blocked,0)=0 ORDER BY t.priority,t.rowid LIMIT 1",(now,now)).fetchone()
        if not row:return None
        task=json.loads(row['payload']);task['id']=row['id'];task['attempts']=row['attempts'];task['prior_evidence']=json.loads(row['evidence'])
        task['product_ids']=[r[0] for r in self.db.execute('SELECT product FROM task_products WHERE task=? ORDER BY product',(row['id'],))]
        task['reuse_evidence']=bool(row['success'] and task['prior_evidence'].get('snapshot'))
        return task

    def pending(self):return self.db.execute("SELECT COUNT(*) FROM tasks WHERE status='pending'").fetchone()[0]
    def next_due(self):
        row=self.db.execute("SELECT MIN(MAX(t.retry_at,COALESCE(h.retry_at,0))) FROM tasks t LEFT JOIN hosts h ON t.host=h.host WHERE t.status='pending' AND COALESCE(h.blocked,0)=0").fetchone()
        return row[0] or 0

    def record(self,task,evidence,decisions,new_tasks,audit,success,error='',retry_at=0,skipped=False):
        if skipped:return
        if success and task['kind']=='product' and set(task['product_ids'])-{d['product_id'] for d in decisions}:
            raise ValueError('missing product decision')
        prior=self.db.execute('SELECT attempts FROM tasks WHERE id=?',(task['id'],)).fetchone()
        if not prior:raise ValueError('unknown completed task')
        attempts=prior[0]+(0 if task.get('reuse_evidence') else 1)
        status='done' if success else 'unavailable' if evidence.get('http_status') in (404,410) else 'restricted' if error in ('robots_disallowed','challenge','unsupported_reference') or evidence.get('http_status')==403 else 'error' if attempts>=3 else 'pending'
        audit=dict(audit);accepted=[];counts=Counter()
        for new in new_tasks:
            sid=new.get('source',{}).get('id','reference');kind=new['kind'];key=task_id(new)
            if self.db.execute('SELECT 1 FROM tasks WHERE id=?',(key,)).fetchone():accepted.append(new);continue
            count=self.db.execute('SELECT COUNT(*) FROM tasks WHERE source=? AND kind=?',(sid,kind)).fetchone()[0]+counts[(sid,kind)]
            cap=MAX_MAPS if kind=='sitemap' else 200000
            if count>=cap:audit.update(complete=False,reason='source_task_limit');continue
            accepted.append(new);counts[(sid,kind)]+=1
        event={'task_id':task['id'],'attempts':attempts,'status':status,'success':success,'error':error,
               'retry_at':retry_at if not success else 0,'evidence':evidence,'decisions':decisions,
               'next_tasks':accepted,'audit':audit,'observed_at':utc()}
        if self.revision:event.update(code_sha=self.code_sha,runtime_revision_sha256=self.revision_sha)
        self.db.execute('SAVEPOINT record_event')
        try:self._apply(event)
        except Exception:
            self.db.execute('ROLLBACK TO record_event');self.db.execute('RELEASE record_event');raise
        self.db.execute('RELEASE record_event');self.db.commit();self.buffer.append(event)

    def _apply(self,event):
        key=event['task_id'];task=self.db.execute('SELECT * FROM tasks WHERE id=?',(key,)).fetchone()
        if not task:raise ValueError('event references missing task')
        for new in event['next_tasks']:self._enqueue(new)
        valid={r[0] for r in self.db.execute('SELECT product FROM task_products WHERE task=?',(key,))}
        for d in event['decisions']:
            if d['product_id'] not in valid:raise ValueError('decision identity mismatch')
            self.db.execute('INSERT OR REPLACE INTO decisions VALUES(?,?,?)',(key,d['product_id'],json.dumps(d,ensure_ascii=False)))
        status=event['status']
        decided={r[0] for r in self.db.execute('SELECT product FROM decisions WHERE task=?',(key,))}
        if event['success'] and task['kind']=='product' and valid-decided:
            # A successful check with no row decisions is only valid for a page
            # with no additional identity discovered in the same transaction.
            if event['next_tasks']:status='pending'
        reason=event['error'] or event['audit'].get('reason','')
        self.db.execute('UPDATE tasks SET status=?,attempts=?,retry_at=?,success=?,evidence=?,audit=?,reason=? WHERE id=?',
                        (status,event['attempts'],event['retry_at'],int(event['success']),json.dumps(event['evidence']),json.dumps(event['audit']),reason,key))
        h=task['host'];prior=self.db.execute('SELECT failures FROM hosts WHERE host=?',(h,)).fetchone()
        limited=event['evidence'].get('http_status') in (403,429) or event['error']=='challenge'
        failures=(prior[0] if prior else 0)+1 if limited else 0
        blocked=event['evidence'].get('http_status')==403 or event['error']=='challenge' or (limited and failures>=3)
        self.db.execute('INSERT INTO hosts(host,retry_at,blocked,failures) VALUES(?,?,?,?) ON CONFLICT(host) DO UPDATE SET retry_at=MAX(hosts.retry_at,excluded.retry_at),blocked=MAX(hosts.blocked,excluded.blocked),failures=excluded.failures',
                        (h,event['retry_at'],int(blocked),failures))
        if blocked:self.db.execute("UPDATE tasks SET status='error',reason='host_access_blocked' WHERE host=? AND status='pending'",(h,))

    def flush(self):
        if not self.buffer:return
        raw=''.join(json.dumps(e,ensure_ascii=False,sort_keys=True)+'\n' for e in self.buffer).encode()
        directory=self.root/'events';directory.mkdir(exist_ok=True)
        digest=hashlib.sha256(raw).hexdigest();count=len(self.buffer)
        path=directory/(f"{len(self.manifest['segments']):08d}-"+digest+'.jsonl.gz')
        if path.exists():raise ValueError('unindexed event segment; checkpoint recovery required')
        tmp=path.with_suffix('.tmp');tmp.write_bytes(gzip.compress(raw,mtime=0));tmp.replace(path)
        head=chain(self.manifest['head_sha256'],digest,count)
        segment={'file':path.name,'sha256':digest,'event_count':count,'chain_sha256':head}
        manifest={**self.manifest,'segments':self.manifest['segments']+[segment],
                  'event_count':self.manifest['event_count']+count,'head_sha256':head}
        self._write_manifest(manifest);self.manifest=manifest;self.buffer=[]

    def source_coverage(self):
        out=[]
        for sid, in self.db.execute("SELECT DISTINCT source FROM tasks WHERE kind='sitemap'"):
            ts=list(self.db.execute("SELECT status,audit,payload FROM tasks WHERE source=? AND kind='sitemap'",(sid,)))
            audits=[json.loads(t['audit']) for t in ts];src=json.loads(ts[0]['payload'])['source']
            complete=all(t['status']=='done' and a.get('complete') for t,a in zip(ts,audits)) and any(a.get('entries',0)>0 for a in audits)
            out.append({'source_id':sid,'complete':complete,'brand':src.get('brand',''),'market':src.get('market','unknown'),'maps':len(ts),'completed_maps':sum(t['status']=='done' for t in ts)})
        return out

    def summary(self):
        counts=Counter({r[0]:r[1] for r in self.db.execute('SELECT status,COUNT(*) FROM tasks GROUP BY status')})
        pages=Counter({r[0]:r[1] for r in self.db.execute("SELECT status,COUNT(*) FROM tasks WHERE kind='product' GROUP BY status")})
        priced=set();stocked=set();tr=set();currencies=defaultdict(set);reasons=Counter()
        for r in self.db.execute('SELECT product,payload FROM decisions'):
            d=json.loads(r['payload']);reasons[d['reason']]+=1
            for offer in d.get('offers',[]):
                priced.add(r['product']);currencies[offer['currency']].add(r['product'])
                if offer['stock_status']=='in_stock':
                    stocked.add(r['product'])
                    if offer['market']=='TR' and offer['currency']=='TRY':tr.add(r['product'])
        coverage=self.source_coverage();general=any(c['complete'] and not c['brand'] for c in coverage)
        proven=len(self.rows) if general else len({r['id'] for c in coverage if c['complete'] and c['brand'] for r in self.rows if r['brand_name']==c['brand']})
        partial=sum(r['status']!='done' or not json.loads(r['audit']).get('complete',False)
                    for r in self.db.execute("SELECT status,audit FROM tasks WHERE kind!='product' AND status!='pending'"))
        total=sum(pages.values());done=total-pages['pending'];total_tasks=sum(counts.values());terminal=total_tasks-counts['pending']
        return {'method_version':VERSION,'updated_at':utc(),'scope_total':len(self.rows),'proven_searches':proven,
                'search_scope':'successfully_read_named_catalogues_only','total_pages':total,'completed_pages':done,'pending_pages':pages['pending'],
                'page_progress_pct':round(100*done/total,3) if total else 100,'unresolved_pages':pages['error']+pages['restricted'],
                'unavailable_pages':pages['unavailable'],'tasks_total':total_tasks,'tasks_completed':terminal,'tasks_pending':counts['pending'],
                'task_progress_pct':round(100*terminal/total_tasks,3) if total_tasks else 100,'verified_price_products':len(priced),
                'in_stock_price_products':len(stocked),'turkey_in_stock_products':len(tr),'currency_products':{k:len(v) for k,v in sorted(currencies.items())},
                'partial_discovery_tasks':partial,'task_status_counts':dict(counts),'decision_reasons':dict(reasons),'source_coverage':coverage,
                'finished':not counts['pending'],'complete':not counts['pending'] and not counts['error'] and not counts['restricted'] and not partial and all(c['complete'] for c in coverage),
                'global_absence_proven':False}

    def results(self):
        all_decisions=defaultdict(list)
        for r in self.db.execute('SELECT product,payload FROM decisions'):all_decisions[r['product']].append(json.loads(r['payload']))
        states=defaultdict(list)
        for r in self.db.execute('SELECT p.product,t.status FROM task_products p JOIN tasks t ON p.task=t.id'):states[r['product']].append(r['status'])
        for row in self.rows:
            pid=str(row['id']);ds=all_decisions.get(pid,[]);offers=[o for d in ds for o in d.get('offers',[])];observations=[o for d in ds for o in d.get('observations',[])]
            offers=list({json.dumps(o,sort_keys=True):o for o in offers}.values());best={}
            for o in offers:
                key=':'.join(map(str,(o['currency'],o['market'],o['volume_ml'])))
                rank=lambda x:({'in_stock':0,'unknown':1,'out_of_stock':2}.get(x['stock_status'],1),Decimal(x['amount']))
                if key not in best or rank(o)<rank(best[key]):best[key]=o
            status='verified_offer' if offers else 'pending_pages' if 'pending' in states[pid] else 'page_unavailable' if set(states[pid])&{'error','restricted','unavailable'} else 'no_accepted_offer' if ds else 'no_match_in_scanned_sources'
            yield {'product_id':pid,'brand_name':row['brand_name'],'product_name':row['product_name'],'release_year':row.get('release_year',''),
                   'status':status,'offers':offers,'best_offers':best,'observations':observations,'decision_reasons':dict(Counter(d['reason'] for d in ds)),
                   'candidate_pages':len(states[pid]),'global_absence_proven':False,'method_version':VERSION}

    def close(self):self.db.close()
