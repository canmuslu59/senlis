#!/usr/bin/env python3
"""Bounded catalogue search with reproducible evidence; never a full-scan queue."""
import argparse
from collections import Counter
import csv
from datetime import datetime,timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import unquote,urlsplit
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from commerce_v3_http import PoliteClient,host,public_url
from commerce_v3_engine import norm,canonical,brand_aliases,name_tokens,parse_page,jsonld
from commerce_full_v3 import load_rows

SOURCES=[
    {'id':'perfumepoint','root':'https://www.perfumepoint.com.tr/xml/sitemap/sitemap.xml','brand':'','prefix':'/','min_entries':100},
    {'id':'yesparfumeri','root':'https://yesparfumeri.com/sitemap.xml','brand':'','prefix':'/products/','min_entries':100},
    {'id':'caudalie','root':'https://tr.caudalie.com/sitemap.xml','brand':'Caudalie','prefix':'/p/','min_entries':10},
    {'id':'mad','root':'https://www.madparfum.com/sitemap.xml','brand':'Mad Parfumeur','prefix':'/urun/','min_entries':10},
    {'id':'innative','root':'https://innativekozmetik.com/sitemap.xml','brand':'INNATIVE','prefix':'/','min_entries':10,'scan_titles':True},
]
CONTROLS=[
    {'id':'negative_decant','brand_name':'Abercrombie & Fitch','product_name':'Fierce Reserve','url':'https://www.dekantparfum.com.tr/urun/abercrombie-fitch-fierce-reserve-edc','expected':'decant'},
    {'id':'negative_dupe','brand_name':'Burberry','product_name':'Burberry Sport Ice for Men','url':'https://www.parfumevi.com.tr/burberry-sport-ice-for-men','expected':'dupe'},
]


def utc():return datetime.now(timezone.utc).isoformat()


def digest(data):return hashlib.sha256(data).hexdigest()


def local_tag(node):return node.tag.rsplit('}',1)[-1]


def parse_sitemap(raw):
    try:root=ET.fromstring(raw)
    except ET.ParseError as exc:raise ValueError('invalid_xml') from exc
    kind=local_tag(root)
    if kind not in ('sitemapindex','urlset'):raise ValueError('not_sitemap_xml')
    expected='sitemap' if kind=='sitemapindex' else 'url';entries=[]
    for item in root:
        if local_tag(item)!=expected:continue
        # Only direct loc is a product/map; image:loc must not become a product.
        loc=next((n.text for n in item if local_tag(n)=='loc'),None)
        if not loc:continue
        titles=list(dict.fromkeys(n.text for n in item.iter() if local_tag(n) in ('title','caption') and n.text))
        entries.append({'url':loc.strip(),'titles':titles})
    if not entries:raise ValueError('empty_sitemap')
    return kind,entries


def catalogue_complete(report):
    return bool(report.get('root_ok') and report.get('expected_maps',0)>0
                and report.get('expected_maps')==report.get('ok_maps')
                and report.get('entry_count',0)>0 and not report.get('errors'))


def entry_matches(row,entry,official_brand=''):
    text=' '+canonical(' '.join(entry.get('titles',[]))+' '+unquote(urlsplit(entry['url']).path))+' '
    if norm(official_brand)!=norm(row['brand_name']):
        if not any(' '+a+' ' in text for a in brand_aliases(row['brand_name'])):return False
    terms=set(name_tokens(row,row['product_name']))
    return bool(terms) and terms.issubset(set(text.split()))


def listing_kind(raw,url):
    soup=BeautifulSoup(raw,'lxml')
    title=' '.join(n.get_text(' ',strip=True) for n in soup.select('title,h1'))
    product_text=' '.join(str(o.get('description','')) for o in jsonld(soup))
    primary=norm(title+' '+product_text)
    plain=norm(soup.get_text(' ',strip=True))
    if re.search(r'\b(muadil\w*|dupe|inspired by|acik parfum)\b',primary) or host(url)=='parfumevi.com.tr':return 'dupe'
    if re.search(r'\b(dekant|decant)\b',primary) or 'dekant sisesinde' in plain or 'orijinal sisesinde gonderilmemektedir' in plain:return 'decant'
    return 'bottle_candidate'


def verify_listing(raw,url,row):
    kind=listing_kind(raw,url)
    if kind in ('decant','dupe'):return None,kind
    if host(url) not in {host(s['root']) for s in SOURCES}:return None,'unapproved_source'
    offer=parse_page(raw,url,row)
    if not offer:return None,'identity_or_price_unproven'
    if not offer.get('volume_ml'):return None,'volume_unproven'
    return offer,'verified'


def search_proven(audits):
    return bool(audits) and all(a.get('complete') and a.get('searched_entries',0)>0 and a.get('catalogue_sha256') for a in audits)


class Evidence:
    def __init__(self,root):
        self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True)
        (self.root/'responses').mkdir(exist_ok=True);(self.root/'catalogues').mkdir(exist_ok=True)
        self.requests=[]

    def fetch(self,client,url):
        started=time.monotonic();r=client.fetch(url)
        raw=r.text.encode('utf-8');sha=digest(raw) if raw else None
        snapshot='responses/'+sha+'.txt.gz' if raw else None
        if snapshot and not (self.root/snapshot).exists():(self.root/snapshot).write_bytes(gzip.compress(raw,mtime=0))
        event={'requested_url':url,'final_url':r.url,'http_status':r.status,'error':r.error,
               'fetched_at':datetime.fromtimestamp(r.fetched_at,timezone.utc).isoformat() if r.fetched_at else None,
               'observed_at':utc(),'seconds':round(time.monotonic()-started,3),'decoded_utf8_bytes':len(raw),
               'decoded_sha256':sha,'snapshot':snapshot,'retry_at':r.retry_at,'from_cache':r.from_cache,
               'body_limited':r.body_limited}
        self.requests.append(event)
        with (self.root/'http_requests.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
        return r,event

    def save(self,name,value):
        (self.root/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')


def collect_catalogue(source,client,evidence):
    report={'source_id':source['id'],'root_url':source['root'],'brand':source['brand'],
            'root_ok':False,'expected_maps':0,'ok_maps':0,'entry_count':0,'errors':[],'map_evidence':[],
            'title_pages_expected':0,'title_pages_ok':0}
    entries=[]
    def read(url):
        r,event=evidence.fetch(client,url);report['map_evidence'].append(event)
        if not r.ok:raise ValueError('fetch:'+r.error)
        if host(r.url)!=host(source['root']):raise ValueError('cross_source_redirect')
        return parse_sitemap(r.text)
    try:
        kind,root_entries=read(source['root']);report['root_ok']=True
        if kind=='urlset':
            report.update(expected_maps=1,ok_maps=1);entries=root_entries
        else:
            maps=[e['url'] for e in root_entries if re.search(r'products?',urlsplit(e['url']).path,re.I)]
            maps=list(dict.fromkeys(maps));report['expected_maps']=len(maps)
            if not maps or len(maps)>20:raise ValueError('product_map_count_out_of_bounds')
            for url in maps:
                if not public_url(url) or host(url)!=host(source['root']):
                    report['errors'].append('untrusted_product_map');continue
                try:
                    typ,items=read(url)
                    if typ!='urlset':raise ValueError('nested_product_index_unhandled')
                    entries.extend(items);report['ok_maps']+=1
                except ValueError as exc:report['errors'].append(str(exc))
    except ValueError as exc:report['errors'].append(str(exc))
    unique={e['url']:e for e in entries if public_url(e['url']) and host(e['url'])==host(source['root'])
            and urlsplit(e['url']).path.startswith(source['prefix']) and urlsplit(e['url']).path not in ('','/')}
    entries=list(unique.values())
    if len(entries)<source['min_entries']:report['errors'].append('catalogue_below_minimum')
    if source.get('scan_titles'):
        report['title_pages_expected']=len(entries)
        if len(entries)>100:report['errors'].append('title_scan_limit')
        else:
            for entry in entries:
                r,event=evidence.fetch(client,entry['url']);entry['title_page_evidence']=event
                if not r.ok or host(r.url)!=host(source['root']):
                    report['errors'].append('title_page_unavailable');continue
                soup=BeautifulSoup(r.text,'lxml');h=soup.find('h1')
                names=[str(o.get('name','')) for o in jsonld(soup) if o.get('name')]
                if h:names.insert(0,h.get_text(' ',strip=True))
                if not names:report['errors'].append('title_page_identity_missing');continue
                entry['titles']=list(dict.fromkeys(entry.get('titles',[])+names));report['title_pages_ok']+=1
    entries.sort(key=lambda e:e['url']);report['entry_count']=len(entries)
    payload=('\n'.join(json.dumps(e,ensure_ascii=False,sort_keys=True) for e in entries)+'\n').encode()
    report['catalogue_sha256']=digest(payload);report['catalogue_file']='catalogues/'+source['id']+'.jsonl.gz'
    (evidence.root/report['catalogue_file']).write_bytes(gzip.compress(payload,mtime=0))
    report['complete']=catalogue_complete(report)
    evidence.save('catalogue_'+source['id']+'_summary.json',report)
    print('CATALOGUE',json.dumps({k:v for k,v in report.items() if k!='map_evidence'},ensure_ascii=False),flush=True)
    return report,entries


def discover(row,catalogues,client,evidence):
    audits=[];candidates=[]
    for source,report,entries in catalogues:
        if source['brand'] and norm(source['brand'])!=norm(row['brand_name']):continue
        matches=[e for e in entries if entry_matches(row,e,source['brand'])]
        audits.append({'source_id':source['id'],'complete':report['complete'],'searched_entries':len(entries),
                       'catalogue_sha256':report['catalogue_sha256'],'query_brand':row['brand_name'],
                       'query_name':row['product_name'],'query_tokens':sorted(set(name_tokens(row,row['product_name']))),
                       'matched_urls':[e['url'] for e in matches],'match_count':len(matches)})
        # Every match is disclosed; page checks are bounded and truncation explicit.
        candidates.extend((source,e) for e in matches[:8])
    checks=[];offers=[];seen=set()
    for source,entry in candidates:
        if entry['url'] in seen:continue
        seen.add(entry['url']);r,event=evidence.fetch(client,entry['url'])
        offer=None;reason='fetch:'+r.error if not r.ok else ''
        if r.ok:offer,reason=verify_listing(r.text,r.url,row)
        check={'source_id':source['id'],'discovered_url':entry['url'],'catalogue_titles':entry['titles'],
               'verdict':reason,'page_evidence':event}
        if offer:
            offer.update(checked_at=event['fetched_at'],evidence_sha256=event['decoded_sha256'],
                         source_id=source['id'],checkout_verified=False)
            check['offer']=offer;offers.append(offer)
        checks.append(check)
    proven=search_proven(audits)
    if offers:status='verified_offer'
    elif not proven:status='search_unproven'
    elif any(c['verdict'].startswith('fetch:') for c in checks):status='page_unavailable'
    elif candidates:status='no_accepted_offer'
    else:status='no_catalog_match'
    result={'product_id':str(row['id']),'brand_name':row['brand_name'],'product_name':row['product_name'],
            'status':status,'search_proven':proven,'scope':'named_source_product_catalogues_only',
            'search_audits':audits,'candidate_checks':checks,'offers':offers,
            'candidate_checks_limited':any(a['match_count']>8 for a in audits),'checked_at':utc()}
    if offers:result['best_offer']=min(offers,key=lambda o:({'in_stock':0,'unknown':1,'out_of_stock':2}.get(o['stock_status'],1),o['price_try']))
    return result


def run(args):
    start=time.time();evidence=Evidence(args.output)
    client=PoliteClient(0,1,slot=6,deadline=start+args.seconds-60,retain_error_bodies=True)
    definitions=json.loads(Path('data/commerce_v3_seeds.json').read_text())
    ids=set(definitions['canary_ids']);rows=[]
    for r in load_rows():
        if r['id'] in ids:rows.append(dict(r,**definitions.get('identity_overrides',{}).get(r['id'],{})))
    if len(rows)!=10:raise ValueError('pilot must contain exactly 10 targets')
    evidence.save('targets.json',rows)
    catalogues=[];results=[];controls=[]
    for source in SOURCES:
        report,entries=collect_catalogue(source,client,evidence);catalogues.append((source,report,entries))
    for row in rows:
        result=discover(row,catalogues,client,evidence);results.append(result)
        evidence.save('results.json',results)
        print('RESULT',json.dumps({k:result[k] for k in ('product_id','product_name','status','search_proven')},ensure_ascii=False),flush=True)
    for row in CONTROLS:
        r,event=evidence.fetch(client,row['url'])
        offer,reason=verify_listing(r.text,r.url,row) if r.ok else (None,'fetch:'+r.error)
        controls.append({'id':row['id'],'expected':row['expected'],'verdict':reason,'passed':r.ok and offer is None and reason==row['expected'],'evidence':event})
    summary={'method':'v4_catalogue_evidence_pilot','created_at':utc(),'targets':len(rows),
             'proven_searches':sum(r['search_proven'] for r in results),'verified_price_products':sum(bool(r['offers']) for r in results),
             'status_counts':dict(Counter(r['status'] for r in results)),
             'sources_complete':sum(report['complete'] for _,report,_ in catalogues),'sources_total':len(SOURCES),
             'negative_controls_passed':sum(c['passed'] for c in controls),'negative_controls_total':len(CONTROLS),
             'catalogue_entries':sum(len(es) for _,_,es in catalogues),'seconds':round(time.time()-start,1),
             'http_stats':dict(client.stats),'full_scan_scheduled':False,'global_absence_proven':False}
    summary['gate_passed']=summary['proven_searches']==10 and summary['negative_controls_passed']==len(CONTROLS) and summary['verified_price_products']>=2
    evidence.save('summary.json',summary);evidence.save('negative_controls.json',controls)
    with (evidence.root/'results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        cols=['product_id','brand_name','product_name','status','search_proven','price_try','volume_ml','stock_status','purchase_url']
        writer=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');writer.writeheader()
        for r in results:writer.writerow(dict(r,**r.get('best_offer',{})))
    evidence.save('source_reports.json',[r for _,r,_ in catalogues])
    (evidence.root/'README.txt').write_text('This is a bounded 10-product catalogue search, not a full Internet search.\nVerify decoded response hashes against responses/*.txt.gz and catalogue hashes against catalogues/*.jsonl.gz.\nresults.json contains the exact query, per-source search evidence, all candidate URLs and every checked-page verdict.\nNo old price or purchase URL seeds were used for discovery. No full scan or database merge is scheduled.\n')
    print('PILOT_SUMMARY',json.dumps(summary),flush=True)
    return 0 if summary['gate_passed'] else 2


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='commerce_v4_evidence')
    parser.add_argument('--seconds',type=int,default=1200)
    raise SystemExit(run(parser.parse_args()))
