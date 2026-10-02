#!/usr/bin/env python3
import csv,glob,gzip,json,os,re,sys,time,html,urllib.parse
from collections import Counter,defaultdict
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent))
import overnight_full_enrichment as core

MODE=os.environ.get('COMMERCE_V2_MODE','worker')
OUT=Path('commerce_link_v2_out');OUT.mkdir(exist_ok=True)
TRUSTED=[
 'trendyol.com','hepsiburada.com','amazon.com.tr','n11.com','pttavm.com','boyner.com.tr','beymen.com',
 'sephora.com.tr','sevil.com.tr','gratis.com','watsons.com.tr','rossmann.com.tr','zara.com',
 'victoriassecret.com.tr','bathandbodyworks.com.tr','yvesrocher.com.tr','oriflame.com','thebodyshop.com.tr',
 'lush.com.tr','avon.com.tr','madparfum.com','lorisparfum.com','bargello.com.tr']
MARKETS=['trendyol.com','hepsiburada.com','amazon.com.tr','n11.com','pttavm.com']
DIRECT=[x for x in TRUSTED if x not in MARKETS]
NOISE={'kadin','erkek','unisex','parfum','perfume','eau','de','edp','edt','edc','spray','sprey','ml','body','mist','fragrance','hair','vucut','sac','orijinal','original','ithal','yeni','urun','fiyat','online','kozmetik'}
SAFE_EXTRA={'fiyatlari','ozellikleri','diger','fresh','ciceksi','meyveli','odunsu','oryantal','aromatik','baharat','misk','kahve','floral','amber','kalici','ozel','seri','natural','bayan','notalar','nota','onu','pesinden','kosturacak','imza','koku','square','kare'}
CONFLICT=set(getattr(core,'VARIANT_MARKERS',set()))|{'intense','elixir','absolu','absolute','noir','rouge','night','sport','flame','energy','limited','collector','edition','extreme','extrait','profondo','prive','sunshine','shimmer','viola','motion','stellar','neon','sueded','exquise','floral'}
NONFRAG={'rollerball','roll on','roll-on','balm','hand cream','el kremi','bakim kremi','lotion','losyon','sunscreen','gunes kremi','sampuan','shampoo','dus jeli','shower gel','tiras','after shave','aftershave','deodorant','sutyen','corap','lastik','boya','etiketi','kitap','canta','ceket','anahtarlik','kalem','yem','sabun','soap','mum','candle'}
SCENT_MARKERS={'parfum','perfume','edp','edt','edc','eau de','cologne','kolonya','body mist','fragrance mist','vucut spreyi','sac ve vucut','parfumlu'}
HINTS={'trendyol.com':['-p-'],'hepsiburada.com':['-p-','/p-'],'amazon.com.tr':['/dp/','/gp/product/'],'n11.com':['/urun/'],'pttavm.com':['-p-','/urun/'],'boyner.com.tr':['-p-','/p_'],'beymen.com':['/p_','/tr/p_'],'gratis.com':['-p-'],'sephora.com.tr':['/p/']}
COLS=['product_id','brand_name','product_name','release_year','link_status','price_status','price_try','currency','volume_ml','seller_name','purchase_url','stock_status','match_confidence','source_product_name','discovery_source','page_verified','checked_at','error']

def norm(s):return core.norm(s)
def host(u):
 try:return urllib.parse.urlparse(u).netloc.lower().split(':')[0].removeprefix('www.')
 except:return ''
def trusted(h):return any(h==d or h.endswith('.'+d) for d in TRUSTED)
def clean(s):
 s=html.unescape(str(s or ''));s=re.sub(r'\b\d{1,4}(?:[.,]\d+)?\s*ml\b',' ',s,flags=re.I);return ' '.join(s.split())
def product_url(u):
 h=host(u);low=u.lower()
 if not trusted(h):return False
 d=next((d for d in TRUSTED if h==d or h.endswith('.'+d)),'')
 if d in HINTS:return any(x in low for x in HINTS[d])
 return not any(x in low for x in ['/search','/arama','/kategori','/category','?q='])
def tokens(brand,text):
 b=set(norm(brand).split());g=set(getattr(core,'GENERIC_PRODUCT_TOKENS',set()))
 raw=[x for x in core.match_norm(clean(text)).split() if x not in b and x not in NOISE and x not in g]
 lexical=[x for x in raw if not x.isdigit() and len(x)>1]
 out=[]
 for x in raw:
  if x.isdigit() and len(x)==4 and lexical:continue
  if len(x)>1 or x.isdigit():out.append(x)
 return out

def compatible(brand,product,candidate):
 pn=norm(product);cn=norm(candidate)
 for bad in NONFRAG:
  if bad in cn and bad not in pn:return False
 if not core.form_compatible(product,candidate):return False
 a,b=core.fragrance_type(product),core.fragrance_type(candidate)
 if a and b and a!=b:return False
 a,b=core.special_format(product),core.special_format(candidate)
 if (a or b) and a!=b:return False
 if core.is_travel_format(product)!=core.is_travel_format(candidate):return False
 tt=tokens(brand,product);ct=set(tokens(brand,candidate))
 if not tt:return False
 if any(x not in ct for x in tt):return False
 extras={x for x in ct-set(tt) if x not in SAFE_EXTRA and not x.isdigit() and not any(ch.isdigit() for ch in x)}
 if extras:return False
 if (ct&CONFLICT)-(set(tt)&CONFLICT):return False
 score=core.product_match_score(brand,product,clean(candidate))
 return score>=(86 if len(tt)<=2 else 76)

def marketplace_guard(brand,product,title,url):
 h=host(url)
 if not any(h==d or h.endswith('.'+d) for d in MARKETS):return True
 t=norm(title)
 if not any(x in t for x in SCENT_MARKERS):return False
 bw=[x for x in norm(brand).split() if x not in {'parfum','perfumes','fragrance','fragrances','cosmetics','kozmetik'} and len(x)>1]
 if bw:
  hits=sum(x in t.split() for x in bw)
  if hits<min(2,len(bw)):return False
 return compatible(brand,product,title)
core.variant_compatible=compatible

def score(brand,product,title,url):
 s=core.product_match_score(brand,product,clean(title));h=host(url)
 if trusted(h):s+=6
 if product_url(url):s+=4
 nt,np=norm(title),norm(product)
 for bad in getattr(core,'BAD',[]):
  if norm(bad) in nt and norm(bad) not in np:s-=35
 return max(0,min(100,s))

def serper(session,q):
 key=os.environ.get('SERPER_API_KEY','').strip()
 if not key:return []
 try:
  r=session.post('https://google.serper.dev/search',headers={'X-API-KEY':key,'Content-Type':'application/json'},json={'q':q,'gl':'tr','hl':'tr','num':10},timeout=20)
  if r.status_code!=200:return []
  return [(x.get('title',''),x.get('link',''),'serper') for x in r.json().get('organic',[]) if x.get('title') and x.get('link')]
 except:return []
def websearch(session,q):
 out=serper(session,q)
 if os.environ.get('SEARCH_ENGINE_FALLBACK','1')=='1':
  try:out += [(t,u,'web_fallback') for t,u in core.search_web(session,q)]
  except:pass
 return out
def queries(brand,product):
 ex=f'"{brand}" "{product}"';mk=' OR '.join('site:'+d for d in MARKETS);dr=' OR '.join('site:'+d for d in DIRECT[:10])
 return [f'{ex} ({mk})',f'{ex} ({dr})',f'{ex} Türkiye parfüm',f'{brand} {product} Türkiye satın al']
def retailer_results(session,brand,product):
 out=[]
 for k in ['boyner','beymen','gratis','n11']:
  fn=getattr(core,'RETAILER_SEARCH',{}).get(k)
  if not fn:continue
  try:out += [(t,u,'retailer:'+k) for t,u in fn(session,brand,product)]
  except:pass
 return out
def reachable(session,url):
 try:
  r=session.get(url,timeout=14,allow_redirects=True,stream=True);ok=r.status_code==200;u=r.url or url;r.close();return ok,u
 except:return False,url
def parse_offer(session,url,brand,product):
 try:return core.parse_offer_page(session,url,brand,product,trusted=trusted(host(url)))
 except TypeError:return core.parse_offer_page(session,url,brand,product)
 except:return None

def discover(row):
 brand,product=row.get('brand_name',''),row.get('product_name','');s=core.thread_session();now=datetime.now(timezone.utc).isoformat()
 base={'product_id':row.get('id',''),'brand_name':brand,'product_name':product,'release_year':row.get('release_year',''),'link_status':'not_found','price_status':'not_found','price_try':'','currency':'TRY','volume_ml':'','seller_name':'','purchase_url':'','stock_status':'unknown','match_confidence':'','source_product_name':'','discovery_source':'','page_verified':'0','checked_at':now,'error':''}
 idx=getattr(core,'OFFICIAL_PRICE_INDEX',{}).get(str(row.get('id') or ''))
 if idx and idx.get('purchase_url'):
  base.update(link_status='verified_link',price_status='verified_price' if idx.get('price_try') else 'link_only',price_try=idx.get('price_try') or '',currency=idx.get('currency') or 'TRY',volume_ml=idx.get('volume_ml') or '',seller_name=idx.get('seller_name') or host(idx.get('purchase_url','')),purchase_url=idx.get('purchase_url') or '',match_confidence=idx.get('match_confidence') or '1.0',source_product_name=idx.get('source_product_name') or product,discovery_source='official_price_index',page_verified='1');return base
 try:o=core.official_catalog_offer(s,brand,product)
 except:o=None
 if o and o.get('purchase_url'):
  base.update(link_status='verified_link',price_status='verified_price' if o.get('price_try') else 'link_only',price_try=o.get('price_try') or '',currency=o.get('currency') or 'TRY',volume_ml=o.get('volume_ml') or '',seller_name=o.get('seller_name') or host(o.get('purchase_url','')),purchase_url=o.get('purchase_url') or '',stock_status=o.get('stock_status') or 'unknown',match_confidence=round(float(o.get('score') or 100)/100,3),source_product_name=o.get('source_product_name') or product,discovery_source='official_catalog',page_verified='1');return base
 results=retailer_results(s,brand,product)
 for q in queries(brand,product):
  results+=websearch(s,q)
  if len(results)>=int(os.environ.get('PILOT_MAX_RESULTS','18')):break
 ded={}
 for title,url,src in results:
  if not url or not trusted(host(url)):continue
  sc=score(brand,product,title,url);key=url.split('#',1)[0]
  if key not in ded or sc>ded[key][0]:ded[key]=(sc,title,src)
 ranked=sorted([(v[0],v[1],u,v[2]) for u,v in ded.items()],reverse=True);best_offer=None;best_link=None
 for sc,title,url,src in ranked[:10]:
  if sc<72 or not core.brand_compatible(brand,f'{title} {core.slug_title(url)}') or not marketplace_guard(brand,product,title,url):continue
  p=parse_offer(s,url,brand,product)
  if p and p.get('purchase_url') and float(p.get('score') or sc)>=78:
   cand=(float(p.get('score') or sc),title,p,src)
   if best_offer is None or cand[0]>best_offer[0] or (p.get('price_try') and not best_offer[2].get('price_try')):best_offer=cand
   if p.get('price_try') and cand[0]>=82:break
  if best_link is None and sc>=80 and product_url(url):
   ok,fu=reachable(s,url)
   if ok and product_url(fu):best_link=(sc,title,fu,src)
 if best_offer:
  sc,title,p,src=best_offer;base.update(link_status='verified_link',price_status='verified_price' if p.get('price_try') else 'link_only',price_try=p.get('price_try') or '',currency=p.get('currency') or 'TRY',volume_ml=p.get('volume_ml') or '',seller_name=p.get('seller_name') or host(p.get('purchase_url','')),purchase_url=p.get('purchase_url') or '',stock_status=p.get('stock_status') or 'unknown',match_confidence=round(sc/100,3),source_product_name=p.get('source_product_name') or title,discovery_source=src,page_verified='1');return base
 if best_link:
  sc,title,url,src=best_link;base.update(link_status='verified_link',price_status='link_only',seller_name=host(url),purchase_url=url,match_confidence=round(sc/100,3),source_product_name=title,discovery_source=src,page_verified='1');return base
 if ranked and ranked[0][0]>=78:
  sc,title,url,src=ranked[0]
  if marketplace_guard(brand,product,title,url):base.update(link_status='candidate',seller_name=host(url),purchase_url=url,match_confidence=round(sc/100,3),source_product_name=title,discovery_source=src)
 return base

def load_rows():
 rows=[]
 for p in sorted(glob.glob('data/master_manifest_174259/part_*.csv*')):
  op=gzip.open if p.endswith('.gz') else open
  with op(p,'rt',encoding='utf-8-sig',newline='') as f:
   for r in csv.DictReader(f):
    if core.commerce_in_scope(r):rows.append(r)
 rows.sort(key=lambda r:(norm(r.get('brand_name','')),int(r['id'])));return rows
def pilot(rows,n):
 b=defaultdict(list)
 for r in rows:b[norm(r.get('brand_name',''))].append(r)
 brands=sorted(b);out=[];i=0
 while len(out)<min(n,len(rows)):
  added=0
  for x in brands:
   if i<len(b[x]):out.append(b[x][i]);added+=1
   if len(out)>=n:break
  if not added:break
  i+=1
 return sorted(out,key=lambda r:int(r['id']))
def save(rows,assigned,total,start,shard):
 rows.sort(key=lambda r:int(r.get('product_id') or 0));p=OUT/f'commerce_link_v2_shard_{shard:02d}.csv'
 with p.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=COLS,extrasaction='ignore');w.writeheader();w.writerows(rows)
 sm={'shard':shard,'scope_total':total,'assigned':assigned,'processed':len(rows),'verified_links':sum(r.get('link_status')=='verified_link' for r in rows),'all_links':sum(bool(r.get('purchase_url')) for r in rows),'with_price':sum(bool(r.get('price_try')) for r in rows),'errors':sum(r.get('link_status')=='worker_error' for r in rows),'serper_enabled':bool(os.environ.get('SERPER_API_KEY','').strip()),'seconds':round(time.time()-start,1),'generated_at':datetime.now(timezone.utc).isoformat()}
 (OUT/f'commerce_link_v2_shard_{shard:02d}_summary.json').write_text(json.dumps(sm,ensure_ascii=False,indent=2),encoding='utf-8');return sm

def worker():
 si=int(os.environ.get('PILOT_SHARD_INDEX','0'));sc=int(os.environ.get('PILOT_SHARD_COUNT','4'));n=int(os.environ.get('PILOT_SIZE','1000'));workers=int(os.environ.get('PILOT_WORKERS','4'))
 allr=load_rows();sample=pilot(allr,n);assigned=[r for i,r in enumerate(sample) if i%sc==si];start=time.time();done=[]
 print('START',json.dumps({'scope':len(allr),'pilot':len(sample),'shard':si,'assigned':len(assigned)}),flush=True)
 with ThreadPoolExecutor(max_workers=workers) as ex:
  futs={ex.submit(discover,r):r for r in assigned}
  for i,f in enumerate(as_completed(futs),1):
   r=futs[f]
   try:done.append(f.result())
   except Exception as e:done.append({'product_id':r['id'],'brand_name':r.get('brand_name',''),'product_name':r.get('product_name',''),'release_year':r.get('release_year',''),'link_status':'worker_error','price_status':'not_found','currency':'TRY','stock_status':'unknown','page_verified':'0','checked_at':datetime.now(timezone.utc).isoformat(),'error':str(e)[:220]})
   if i%50==0:print('CHECKPOINT',json.dumps(save(done,len(assigned),len(allr),start,si),ensure_ascii=False),flush=True)
 print('SUMMARY',json.dumps(save(done,len(assigned),len(allr),start,si),ensure_ascii=False),flush=True)

def merge():
 final=[];seen={}
 for p in sorted(glob.glob('commerce_link_v2_inputs/**/commerce_link_v2_shard_*.csv',recursive=True)):
  with open(p,encoding='utf-8-sig',newline='') as f:
   for r in csv.DictReader(f):seen[str(r.get('product_id') or '')]=r
 final=sorted([r for k,r in seen.items() if k],key=lambda r:int(r['product_id']));dest=Path('commerce_link_v2_final');dest.mkdir(exist_ok=True)
 with (dest/'SENLIS_commerce_link_pilot_v2.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=COLS,extrasaction='ignore');w.writeheader();w.writerows(final)
 st=Counter(r.get('link_status') or '' for r in final);src=Counter(r.get('discovery_source') or '' for r in final if r.get('purchase_url'));sell=Counter(r.get('seller_name') or '' for r in final if r.get('purchase_url'))
 n=len(final);vl=sum(r.get('link_status')=='verified_link' for r in final);al=sum(bool(r.get('purchase_url')) for r in final);wp=sum(bool(r.get('price_try')) for r in final)
 sm={'generated_at':datetime.now(timezone.utc).isoformat(),'unique_products':n,'verified_links':vl,'all_links':al,'with_price':wp,'verified_link_pct':round(100*vl/n,2) if n else 0,'all_link_pct':round(100*al/n,2) if n else 0,'price_pct':round(100*wp/n,2) if n else 0,'baseline_old_link_pct':2.46,'link_status_counts':dict(st),'source_counts':dict(src),'seller_counts':dict(sell)}
 (dest/'summary.json').write_text(json.dumps(sm,ensure_ascii=False,indent=2),encoding='utf-8');print('FINAL',json.dumps(sm,ensure_ascii=False),flush=True)

if __name__=='__main__':merge() if MODE=='merge' else worker()
