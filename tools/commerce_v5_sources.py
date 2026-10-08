"""Evidence-bearing public discovery; every limit or missing source stays explicit."""
from collections import defaultdict
import hashlib
import json
import re
from urllib.parse import urljoin,urlsplit,parse_qs,unquote
from bs4 import BeautifulSoup
from commerce_v3_http import host,public_url
from commerce_v3_engine import norm,canonical,brand_aliases,name_tokens
from commerce_evidence_v4 import parse_sitemap
from commerce_v5_parser import primary_objects,window_json

REFERENCE_HOSTS={'fragrantica.com','parfumo.com'}
MAX_MAPS=100
MAX_PAGES=500


def source_for(url,brand,registry):
    if not public_url(url):return None
    for source in registry['sources']:
        if host(url)!=source['host']:continue
        brands=source.get('brands') or ([source['brand']] if source.get('brand') else [])
        if brands and norm(brand) not in {norm(b) for b in brands}:continue
        return dict(source,brand=brand) if brands else dict(source)
    return None


class RowsIndex:
    def __init__(self,rows):
        self.rows=rows;self.by_id={str(r['id']):dict(r) for r in rows};self.by_brand=defaultdict(list);self.aliases=defaultdict(set)
        editions=defaultdict(list)
        for r in rows:
            self.by_brand[r['brand_name']].append(r)
            editions[(norm(r['brand_name']),canonical(r['product_name']))].append(r)
        for items in editions.values():
            years=sorted({str(r.get('release_year') or '') for r in items})
            if len(years)>1:
                for r in items:self.by_id[str(r['id'])]['competing_release_years']=years
        for brand in self.by_brand:
            for alias in brand_aliases(brand):self.aliases[alias].add(brand)
    def candidates(self,url,title='',brand=''):
        text=' '+canonical(title+' '+unquote(urlsplit(url).path))+' ';tokens=set(text.split())
        brands=[brand] if brand else {b for alias,bs in self.aliases.items() if ' '+alias+' ' in text for b in bs}
        out=[]
        for b in brands:
            for row in self.by_brand.get(b,[]):
                terms=set(name_tokens(row,row['product_name']))
                if terms and terms<=tokens:out.append(str(row['id']))
        return out


def task_id(task):
    identity={k:task.get(k) for k in ('kind','url','brand')}
    return hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()


def product_task(url,source,ids):
    return {'kind':'product','url':url,'source':source,'product_ids':sorted(set(map(str,ids)))}


def initial_tasks(rows,old_pages,registry):
    idx=RowsIndex(rows);tasks=[]
    ty=next(s for s in registry['sources'] if s['id']=='trendyol')
    tasks.append({'kind':'trendyol_directory','url':'https://www.trendyol.com/s/markalar','source':ty})
    for source in registry['sources']:
        if source.get('root'):tasks.append({'kind':'sitemap','url':source['root'],'source':source,'depth':0})
    for page in old_pages:
        ids=[str(pid) for pid in page['product_ids'] if str(pid) in idx.by_id]
        if not ids:continue
        source=source_for(page['url'],idx.by_id[ids[0]]['brand_name'],registry)
        if source:tasks.append(product_task(page['url'],source,ids))
    for row in rows:
        source=source_for(row.get('source_url',''),row['brand_name'],registry)
        if source:tasks.append(product_task(row['source_url'],source,[row['id']]))
    known={norm(b) for s in registry['sources'] if s['kind']=='official' for b in s.get('brands',[s.get('brand','')])}
    for brand,items in sorted(idx.by_brand.items()):
        if norm(brand) in known:continue
        reference=next((r['source_url'] for r in items if host(r.get('source_url','')) in REFERENCE_HOSTS),items[0].get('source_url',''))
        # Unsupported references are recorded as unconfirmed by the worker without HTTP.
        tasks.append({'kind':'reference','url':reference,'brand':brand,'depth':0})
    merged={}
    for task in tasks:
        key=task_id(task)
        if key in merged and task['kind']=='product':merged[key]['product_ids']=sorted(set(merged[key]['product_ids']+task['product_ids']))
        else:merged[key]=task
    return list(merged.values())


def robots_allowed(raw,url,agent='senlis-catalogresearch'):
    groups=[];agents=[];rules=[];seen_rule=False
    for line in raw.splitlines():
        line=line.split('#',1)[0].strip()
        if ':' not in line:continue
        key,value=line.split(':',1);key=key.strip().lower();value=value.strip()
        if key=='user-agent':
            if seen_rule:groups.append((agents,rules));agents=[];rules=[];seen_rule=False
            agents.append(value.lower())
        elif key in ('allow','disallow') and agents:
            seen_rule=True
            if value:rules.append((key,value))
    groups.append((agents,rules))
    exact=[r for names,r in groups if any(a!='*' and a in agent for a in names)]
    chosen=exact or [r for names,r in groups if '*' in names]
    path=urlsplit(url).path or '/'
    if urlsplit(url).query:path+='?'+urlsplit(url).query
    matches=[]
    for rules in chosen:
        for kind,pattern in rules:
            regex=re.escape(pattern).replace(r'\*','.*')
            if pattern.endswith('$'):regex=regex[:-2]+'$'
            if re.match(regex,path):matches.append((len(pattern.replace('*','')),kind=='allow'))
    return max(matches,default=(0,True))[1]


def official_identity(raw,brand,url):
    soup=BeautifulSoup(raw,'lxml');aliases=set(brand_aliases(brand))
    def valid(obj):
        if isinstance(obj,list):return any(valid(x) for x in obj)
        if not isinstance(obj,dict):return False
        typ=obj.get('@type',[]);typ=[typ] if isinstance(typ,str) else typ
        if set(typ)&{'Organization','Brand','OnlineStore','Store'} and norm(obj.get('name')) in aliases:
            return not obj.get('url') or host(urljoin(url,str(obj['url'])))==host(url)
        return valid(obj.get('@graph',[]))
    for s in soup.select('script[type="application/ld+json"]'):
        try:
            if valid(json.loads(s.string or s.get_text())):return True
        except (ValueError,TypeError):pass
    return False


def discover(task,raw,final_url,rows,registry):
    idx=rows if isinstance(rows,RowsIndex) else RowsIndex(rows)
    kind=task['kind'];source=task.get('source',{});soup=None;out=[]
    audit={'kind':kind,'url':final_url,'complete':True,'reason':'searched','brand':task.get('brand',''),'entries':0}
    def emit_product(url,title='',all_brand=False):
        if not public_url(url) or host(url)!=source.get('host'):return
        if source.get('prefix') and not urlsplit(url).path.startswith(source['prefix']):return
        if source.get('id')=='trendyol' and not re.search(r'-p-\d+$',urlsplit(url).path):return
        if re.search(r'\.(jpg|png|webp|pdf|css|js)$',urlsplit(url).path,re.I):return
        brand=source.get('brand') or task.get('brand','')
        ids=idx.candidates(url,title,brand)
        if all_brand and brand and not ids:ids=[str(r['id']) for r in idx.by_brand.get(brand,[])]
        if ids:out.append(product_task(url,source,ids))
    if kind=='sitemap':
        typ,entries=parse_sitemap(raw);audit['entries']=len(entries)
        if typ=='sitemapindex':
            for entry in entries[:MAX_MAPS]:
                u=entry['url']
                if host(u)!=source['host'] or not public_url(u):audit.update(complete=False,reason='untrusted_map');continue
                if task.get('depth',0)>=3:audit.update(complete=False,reason='sitemap_depth_limit');continue
                out.append({'kind':'sitemap','url':u,'source':source,'depth':task.get('depth',0)+1})
            if len(entries)>MAX_MAPS:audit.update(complete=False,reason='sitemap_map_limit')
        else:
            for entry in entries:emit_product(entry['url'],' '.join(entry.get('titles',[])),source.get('kind')=='official' and (source.get('host')=='innativekozmetik.com' or bool(re.search(r'/(p|products|urun)/',urlsplit(entry['url']).path))))
    elif kind=='trendyol_directory':
        soup=BeautifulSoup(raw,'lxml');brands=set();links=0
        for a in soup.select('a[href]'):
            url=urljoin(final_url,a['href']);name=norm(a.get_text(' ',strip=True))
            if host(url)!='trendyol.com' or not re.search(r'-x-b\d+(?:$|\?)',url):continue
            links+=1
            for brand in idx.aliases.get(name,[]):
                brands.add(brand);out.append({'kind':'trendyol_brand','url':url,'brand':brand,'source':source,'page':1})
        audit.update(entries=links,matched_brands=len(brands),unmatched_brands=len(idx.by_brand)-len(brands),matched_brand_names=sorted(brands))
        if links<100:audit.update(complete=False,reason='brand_directory_incomplete')
    elif kind=='trendyol_brand':
        soup=BeautifulSoup(raw,'lxml');urls=set()
        for a in soup.select('a[href]'):
            u=urljoin(final_url,a['href'])
            if re.search(r'-p-\d+$',urlsplit(u).path):urls.add(u);emit_product(u,a.get_text(' ',strip=True))
        audit['entries']=len(urls)
        # Only explicit next-page navigation is followed; without a terminal
        # page count the source remains partial, even if some offers are found.
        nxt=soup.select_one('a[rel="next"][href]')
        if nxt and task.get('page',1)<MAX_PAGES:
            u=urljoin(final_url,nxt['href'])
            if host(u)==host(final_url):out.append(dict(task,url=u,page=task.get('page',1)+1))
        audit.update(complete=False,reason='catalogue_extent_unproven')
    elif kind=='product':
        # Related links are discovery hints only. Every match requires its own
        # fresh main-product verification, never a recommendation's price.
        if source.get('id')=='trendyol':
            soup=BeautifulSoup(raw,'lxml')
            for a in soup.select('a[href]'):emit_product(urljoin(final_url,a['href']),a.get_text(' ',strip=True))
            for obj in primary_objects(soup):
                for u in obj.get('isRelatedTo',[]):
                    if isinstance(u,str):emit_product(u)
    elif kind=='reference':
        if host(final_url) not in REFERENCE_HOSTS:return [],dict(audit,complete=False,reason='official_site_unconfirmed')
        soup=BeautifulSoup(raw,'lxml')
        for a in soup.select('a[href]'):
            u=urljoin(final_url,a['href']);label=norm(a.get_text(' ',strip=True)+' '+str(a.get('title','')))
            if not public_url(u):continue
            if label in {'official website','official site','website','web site','homepage','site officiel','web sitesi'} and host(u) not in REFERENCE_HOSTS:
                out.append({'kind':'official_home','url':u,'brand':task['brand'],'reference_url':final_url})
            elif task.get('depth',0)==0 and host(u)==host(final_url) and re.search(r'/(designers|Brands)/',urlsplit(u).path):
                out.append(dict(task,url=u,depth=1))
        if not out:audit.update(complete=False,reason='official_site_unconfirmed')
    elif kind=='official_home':
        confirmed=official_identity(raw,task['brand'],final_url);audit['official_confirmed']=confirmed
        if confirmed:
            origin=urlsplit(final_url);root=origin.scheme+'://'+origin.netloc
            src={'id':'official_'+hashlib.sha256((host(root)+task['brand']).encode()).hexdigest()[:12],
                 'host':host(root),'kind':'official','brand':task['brand'],'market':'unknown','reference_url':task.get('reference_url'),'confirmation_url':final_url}
            soup=BeautifulSoup(raw,'lxml');lang=(soup.html.get('lang','') if soup.html else '').lower()
            src['language']=lang  # Translation is not proof of a sales market.
            out.append({'kind':'sitemap','url':root+'/sitemap.xml','source':src,'depth':0})
        else:audit.update(complete=False,reason='official_home_identity_unproven')
    else:raise ValueError('unknown discovery kind '+kind)
    unique={}
    for item in out:
        key=task_id(item)
        if key in unique and item['kind']=='product':unique[key]['product_ids']=sorted(set(unique[key]['product_ids']+item['product_ids']))
        else:unique[key]=item
    return list(unique.values()),audit
