#!/usr/bin/env python3
"""Ten existing identities, fresh original-currency evidence and live negative controls."""
import argparse,json,os,time
from pathlib import Path
from commerce_evidence_v4 import Evidence,utc
from commerce_full_v3 import load_rows
from commerce_full_v4 import validated_rows
from commerce_v4_state import read_jsonl
from commerce_v5_sources import source_for,RowsIndex
from commerce_v5_parser import verify_page
from commerce_v5_http import PolicyClient
from commerce_full_v5 import registry,pilot_gate

TARGETS=['2440','60336','77268','77290','77267','36022','36013','90677','100781','113828']
EXTRA={
'77268':['https://www.trendyol.com/innative/e4001-eny-blue-essence-edp-50-ml-temiz-cicekler-kadin-parfumu-p-991091641'],
'77290':['https://www.trendyol.com/innative/e2005-eny-serene-bloom-edp-50-ml-oryantal-ciceksi-kadin-parfumu-p-1043366296'],
'36022':['https://fr.caudalie.com/p/528R1C/the-des-vignes-eau-fraiche-528r1c.html','https://us.caudalie.com/p/528R1/528r1.html']}


def run(args):
    start=time.time();out=Path(args.output);evidence=Evidence(out,retry_attempts=3);client=PolicyClient(out,start+args.seconds-120)
    definitions=json.loads(Path('data/commerce_v3_seeds.json').read_text());all_rows,_=validated_rows(load_rows(),definitions.get('identity_overrides',{}));index=RowsIndex(all_rows);rows={pid:index.by_id[pid] for pid in TARGETS if pid in index.by_id}
    if len(rows)!=10:raise ValueError('pilot identity coverage mismatch')
    previous=Path(args.previous)/'data/commerce_v4/20261005';pages=read_jsonl(previous/'pages.jsonl.gz')
    prior=read_jsonl(previous/'results.jsonl.gz') if (previous/'results.jsonl.gz').exists() else []
    best={r['product_id']:r.get('best_offer',{}).get('purchase_url') for r in prior if r['product_id'] in rows}
    checks=[];controls=[];reg=registry()
    for pid in TARGETS:
        row=rows[pid];urls=list(EXTRA.get(pid,[]));src=source_for(row.get('source_url',''),row['brand_name'],reg)
        if src:urls.append(row['source_url'])
        elif best.get(pid):urls.append(best[pid])
        else:urls.extend(p['url'] for p in pages if pid in p['product_ids'])
        urls=list(dict.fromkeys(urls))[:4]
        for url in urls:
            source=source_for(url,row['brand_name'],reg)
            if not source:continue
            r,event=evidence.fetch(client,url)
            verdict=verify_page(r.text,r.url,row,source) if r.ok else {'offers':[],'observations':[],'reason':'fetch:'+r.error}
            for key in ('offers','observations'):
                for offer in verdict[key]:offer.update(checked_at=event.get('fetched_at'),evidence_sha256=event.get('decoded_sha256'))
            check={'product_id':pid,'url':url,'evidence':event,**verdict};checks.append(check);evidence.save('checks.json',checks)
            print('PILOT_CHECK',json.dumps({'id':pid,'url':url,'reason':verdict['reason'],'offers':verdict['offers']},ensure_ascii=False),flush=True)
            if pid=='77268' and source['id']=='trendyol' and verdict['offers']:
                for kind,name in [('wrong_form','BLUE ESSENCE Body Mist'),('wrong_variant','BLUE ESSENCE Intense (Eau de Parfum)')]:
                    negative=verify_page(r.text,r.url,dict(row,product_name=name),source)
                    controls.append({'control':kind,'passed':not negative['offers'],'reason':negative['reason'],'evidence_sha256':event['decoded_sha256']})
    offers=[o for c in checks for o in c['offers']]
    summary={'method_version':'v5.0-live-pilot','created_at':utc(),'code_sha':os.environ.get('GITHUB_SHA','local'),'targets':len(rows),
             'verified_price_products':len({c['product_id'] for c in checks if c['offers']}),
             'trendyol_verified':sum(bool(c['offers']) and any(o['source_id']=='trendyol' for o in c['offers']) for c in checks),
             'currencies':sorted({o['currency'] for o in offers}),'negative_controls_passed':sum(c['passed'] for c in controls),
             'negative_controls_total':len(controls),'seconds':round(time.time()-start,1),'http_stats':dict(client.stats)}
    summary['gate_passed']=pilot_gate(summary);evidence.save('summary.json',summary);evidence.save('negative_controls.json',controls);evidence.save('targets.json',list(rows.values()))
    print('PILOT_SUMMARY',json.dumps(summary),flush=True);return 0 if summary['gate_passed'] else 2

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--previous',default='previous');p.add_argument('--output',default='commerce_v5_pilot');p.add_argument('--seconds',type=int,default=1800)
    raise SystemExit(run(p.parse_args()))
