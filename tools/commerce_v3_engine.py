"""Autonomous discovery; verify offers from live product pages, never snippets."""
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import base64
import html
import json
import re
import threading
import time
import unicodedata
from urllib.parse import parse_qs, parse_qsl, unquote, urljoin, urlsplit

from bs4 import BeautifulSoup
import overnight_full_enrichment as core
from commerce_v3_http import host, public_url

ALIASES = {'mad parfumeur': ['mad parfum','mad'], 'dsquared2': ['dsquared 2'],
           'giorgio armani':['armani'], 'christian dior':['dior'], 'dolce gabbana':['dolce and gabbana']}
DOMAINS = set(core.TR_SELLERS) | {'madparfum.com','lorisparfum.com','bargello.com.tr',
    'innativekozmetik.com','tr.caudalie.com','perfumepoint.com.tr','yesparfumeri.com',
    'nisparfumeri.com','dermoeczanem.com','sachane.com','dermoailem.com','kozvit.com'}
INFO = set(core.INFO_DOMAINS) | {'fragrantica.tr','parfumo.de','akakce.com','epey.com','cimri.com'}
NOISE = set('edp edt edc extrait parfum perfume parfumu fragrance spray sprey spreyi ml '
            'kadin erkek bayan unisex for men women man woman him her body mist hair misti vucut sac '
            'after shave aftershave roll on refillable fl oz'.split())
SAFE = set('orijinal original natural yeni urun fiyat fiyati fiyatlari yorum yorumlari '
           'ozellikleri online satin al eny sulu armut ve taze cicekler kalici aromali '
           'ciceksi meyveli odunsu oryantal aromatik yumsak baharatli fresh floral notes '
           'citrus vanilla woody amber notalar'.split())
VARIANTS = set(core.VARIANT_MARKERS) | set('essentielle fraiche eclat absolute absolue exquise profondo prive elixir original'.split())
PROVIDERS = {
    'ddg': ('https://html.duckduckgo.com/html/', {'kl':'tr-tr'}),
    'bing': ('https://www.bing.com/search', {'setlang':'tr-tr','cc':'tr'}),
    'yahoo': ('https://search.yahoo.com/search', {})}


def norm(value):
    text = unicodedata.normalize('NFKD', html.unescape(str(value or '')).casefold().replace('ı','i'))
    return ' '.join(re.sub(r'[^\w]+',' ',''.join(c for c in text if not unicodedata.combining(c)),flags=re.UNICODE).replace('_',' ').split())


def canonical(value):
    text = norm(value)
    for a,b in [('eau de parfum','edp'),('eau de toilette','edt'),('eau de cologne','edc'),
                ('mediterrano','mediterraneo')]: text=text.replace(a,b)
    return text


def brand_aliases(brand):
    name=norm(brand)
    return sorted(set([name]+ALIASES.get(name,[])+[norm(x) for x in core.BRAND_ALIASES.get(core.norm(brand),[])]),key=len,reverse=True)


def concentration(text):
    t=canonical(text)
    for c in ('extrait','edp','edt','edc'):
        if re.search(r'\b'+c+r'\b',t):return c
    return ''


def gender(text):
    t=canonical(text)
    if 'unisex' in t:return 'unisex'
    female=bool(re.search(r'\b(kadin|bayan|women|woman|femme)\b|for her',t))
    male=bool(re.search(r'\b(erkek|men|man|homme)\b|for him',t))
    return 'female' if female and not male else 'male' if male and not female else ''


def name_tokens(row,text):
    raw=re.sub(r'\b\d+(?:[.,]\d+)?\s*(?:ml|fl\.?\s*oz)\b',' ',str(text),flags=re.I)
    t=' '+canonical(raw)+' '
    for b in brand_aliases(row.get('brand_name','')):t=t.replace(' '+b+' ',' ')
    out=[w for w in t.split() if w not in NOISE]
    year=str(row.get('release_year') or '')
    if len(out)>1:out=[w for w in out if w!=year]
    return out


def matches(row,title,strict=False):
    product=row.get('product_name',''); b=row.get('brand_name','')
    cand=' '+canonical(title)+' '
    if not any(' '+alias+' ' in cand for alias in brand_aliases(b)):return False
    if not core.form_compatible(product,title):return False
    a,bb=core.special_format(product),core.special_format(title)
    if (a or bb) and a!=bb:return False
    if core.is_travel_format(product)!=core.is_travel_format(title):return False
    wanted=(row.get('concentration') or concentration(product)).lower()
    got=concentration(title)
    if wanted and ((got and wanted!=got) or (strict and not got)):return False
    expected_gender=row.get('gender') or gender(product)
    actual_gender=gender(title)
    if expected_gender and actual_gender and expected_gender!=actual_gender:return False
    if strict and row.get('gender') and not actual_gender:return False
    expected=set(name_tokens(row,product));actual=set(name_tokens(row,title))
    # Eponymous products (Chloe, Chanel, etc.) still need their base name.
    if not expected:
        base=norm(b)
        expected={base}
        if not actual:actual={base}
    if not expected.issubset(actual):return False
    if (actual & VARIANTS)-(expected & VARIANTS):return False
    extras=actual-expected-SAFE
    extras={x for x in extras if not re.fullmatch(r'[a-z]+\d+',x)}
    if extras:return False
    for bad in core.BAD:
        if norm(bad) in norm(title) and norm(bad) not in norm(product):return False
    return True


def queries(row):
    brand=brand_aliases(row['brand_name'])
    name=' '.join(name_tokens(row,row['product_name'])) or norm(row['product_name'])
    preferred='mad parfum' if norm(row['brand_name'])=='mad parfumeur' else norm(row['brand_name'])
    return [f'"{preferred}" "{name}" parfüm TL',f'{preferred} {name} Türkiye satın al']


def price_number(value,structured=False):
    if isinstance(value,(int,float)):return float(value) if 1<=float(value)<=1000000 else None
    t=re.sub(r'(TRY|TL|₺|\s)','',str(value or ''),flags=re.I)
    if not re.fullmatch(r'\d[\d.,]*',t):return None
    if structured and re.fullmatch(r'\d+\.\d{1,4}',t):pass
    elif ',' in t and '.' in t:
        sep=',' if t.rfind(',')>t.rfind('.') else '.'
        t=t.replace('.' if sep==',' else ',','').replace(sep,'.')
    elif ',' in t or '.' in t:
        sep=',' if ',' in t else '.';parts=t.split(sep)
        if all(len(p)==3 for p in parts[1:]):t=''.join(parts)
        elif len(parts)==2 and len(parts[1]) in (1,2):t='.'.join(parts)
        else:return None
    try:
        v=Decimal(t)
        return float(v) if v.is_finite() and 1<=v<=1000000 else None
    except InvalidOperation:return None


def volume(text):
    m=re.search(r'(?<!\d)(\d{1,4}(?:[.,]\d+)?)\s*ml\b',text,re.I)
    return float(m.group(1).replace(',','.')) if m else None


def product_url_key(url):
    p=urlsplit(url)
    # Tracking parameters and anchors do not select a different product; variant
    # and SKU parameters do, so retain all unrecognized parameters.
    query=tuple(sorted((k,v) for k,v in parse_qsl(p.query) if not k.lower().startswith('utm_')
                       and k not in ('_pos','_sid','_ss')))
    return host(url),p.path.rstrip('/'),query


def jsonld(soup):
    out=[]
    def walk(x):
        if isinstance(x,list):
            for item in x:walk(item)
        elif isinstance(x,dict):
            typ=x.get('@type',[]);typ=[typ] if isinstance(typ,str) else typ
            if 'Product' in typ:out.append(x)
            if '@graph' in x:walk(x['@graph'])
            if 'mainEntity' in x:walk(x['mainEntity'])
    for s in soup.find_all('script',attrs={'type':re.compile('ld\\+json',re.I)}):
        try:walk(json.loads(s.string or s.get_text()))
        except (ValueError,TypeError):pass
    return out


def parse_page(raw,url,row):
    soup=BeautifulSoup(raw,'lxml')
    plain=soup.get_text(' ',strip=True)
    if 'not salable in turkey' in plain.lower() or 'türkiye’de satışa sunulmamaktadır' in plain.lower():return None
    h1=soup.find('h1');heading=h1.get_text(' ',strip=True) if h1 else ''
    title=soup.title.get_text(' ',strip=True) if soup.title else ''
    brand=row['brand_name']
    aliases=brand_aliases(brand)
    def has_brand(s):
        text=' '+norm(s)+' '
        return any(' '+a+' ' in text for a in aliases)
    def named(s,evidence=False):
        return brand+' '+s if evidence and not has_brand(s) else s
    products=jsonld(soup)
    # Caudalie places the category label inside its primary H1. Remove only
    # the exact category+name combination of its sole Product object.
    if host(url)=='tr.caudalie.com' and len(products)==1:
        obj=products[0];category=obj.get('category');name=obj.get('name')
        if isinstance(category,str) and isinstance(name,str) and category and name:
            if norm(heading)==norm(category+' '+name):heading=name
    # A recommendation's Product object must never override a different page heading.
    if heading and not matches(row,named(heading,True)):return None
    descriptions=[]
    expected=set(name_tokens(row,row['product_name']))
    for node in soup.select('.html-content, .product-description, [itemprop="description"], #description'):
        text=node.get_text(' ',strip=True)
        if len(text)<=3500 and expected.issubset(set(canonical(text).split())):descriptions.append(text)
    selected_volumes={volume(n.get_text(' ',strip=True)) for n in soup.select('p.selected, option[selected], [data-selected="true"]')
                      if re.fullmatch(r'\s*\d+(?:[.,]\d+)?\s*ml\s*',n.get_text(' ',strip=True),re.I)}
    selected_volume=next(iter(selected_volumes)) if len(selected_volumes)==1 else None
    offers=[];brand_conflict=False;main_brand_evidence=False
    for obj in products:
        name=obj.get('name') or heading
        obj_brand=obj.get('brand',{})
        if isinstance(obj_brand,dict):obj_brand=obj_brand.get('name','')
        explicit_brand=isinstance(obj_brand,str) and bool(obj_brand)
        brand_agrees=explicit_brand and norm(obj_brand) in aliases
        if explicit_brand and not brand_agrees:
            if matches(row,named(name,True)):brand_conflict=True
            continue
        candidate=named(name,brand_agrees)
        if not matches(row,candidate):continue
        if not heading and len(products)!=1:continue
        page_volume=volume(heading) or selected_volume
        if page_volume and volume(candidate) and page_volume!=volume(candidate):continue
        main_brand_evidence|=bool(brand_agrees or has_brand(name))
        main_volume=volume(candidate) or volume(heading) or selected_volume
        off=obj.get('offers',[]);off=off if isinstance(off,list) else [off]
        for offer in off:
            if not isinstance(offer,dict):continue
            offer_name=str(offer.get('name') or '')
            offer_volume=volume(offer_name)
            if offer_volume and main_volume and offer_volume!=main_volume:continue
            if offer.get('url'):
                offer_key=product_url_key(urljoin(url,str(offer['url'])));page_key=product_url_key(url)
                same_single_variant=(host(url)=='innativekozmetik.com' and len(off)==1
                    and len(products)==1 and main_volume is not None and bool(obj.get('productId'))
                    and page_key[:2]==offer_key[:2] and not page_key[2]
                    and offer_key[2]==(('vid',str(obj['productId'])),))
                if offer_key!=page_key and not same_single_variant:continue
            if offer_name and not re.fullmatch(r'\s*\d+(?:[.,]\d+)?\s*ml\s*',offer_name,re.I):
                if not matches(row,named(offer_name,main_brand_evidence)):continue
            # A variant-specific amount without a confirmed page volume must not
            # inherit a different or unknown bottle size.
            if offer_volume and not main_volume:continue
            currency=str(offer.get('priceCurrency') or '').upper()
            if currency not in ('TRY','TL','₺'):continue
            if offer.get('@type')=='AggregateOffer' and offer.get('price') is None:continue
            amount=offer.get('price')
            if amount is None and isinstance(offer.get('priceSpecification'),dict):
                spec=offer['priceSpecification']
                if spec.get('eligibleCustomerType') or spec.get('validForMemberTier'):continue
                amount=spec.get('price')
            price=price_number(amount,structured=True)
            if price is None:continue
            wanted=(row.get('concentration') or concentration(row['product_name'])).lower()
            found_concentration=concentration(candidate)
            if not found_concentration:
                types=set(re.findall(r'\b(edp|edt|edc|extrait)\b',canonical(str(obj.get('description',''))+' '+' '.join(descriptions))))
                if len(types)==1:found_concentration=next(iter(types))
            if wanted and found_concentration!=wanted:continue
            if row.get('gender') and gender(candidate)!=row['gender']:continue
            availability=str(offer.get('availability','')).lower()
            stock='out_of_stock' if 'outofstock' in availability or 'soldout' in availability else 'in_stock' if 'instock' in availability else 'unknown'
            offers.append({'price_try':price,'currency':'TRY','purchase_url':url,'seller_name':host(url),
                'source_product_name':candidate,'stock_status':stock,'volume_ml':main_volume,
                'price_source':'product_jsonld','match_confidence':0.98})
    if offers:return min(offers,key=lambda x:({'in_stock':0,'unknown':1,'out_of_stock':2}[x['stock_status']],x['price_try']))
    if brand_conflict:return None
    # Conservative main-product microdata/OpenGraph fallback; never scan every price in the page.
    main=None
    scopes=soup.select('[itemtype*="/Product"]')
    if len(scopes)==1:
        node=scopes[0];name_node=node.select_one('[itemprop="name"]')
        brand_node=node.select_one('[itemprop="brand"]')
        scope_name=(name_node.get('content') or name_node.get_text(' ',strip=True)) if name_node else ''
        scope_brand=(brand_node.get('content') or brand_node.get_text(' ',strip=True)) if brand_node else ''
        if scope_brand and norm(scope_brand) not in aliases:return None
        scope_name=named(scope_name,bool(scope_brand))
        if scope_name and matches(row,scope_name):
            if volume(heading) and volume(scope_name) and volume(heading)!=volume(scope_name):return None
            main=node;main_brand_evidence=True
    name=named(heading or title.split('|')[0],main_brand_evidence)
    if not matches(row,name):return None
    def meta(key):
        m=soup.find('meta',attrs={'property':key}) or soup.find('meta',attrs={'name':key})
        return m.get('content','') if m else ''
    cur=meta('product:price:currency') or meta('og:price:currency')
    amount=meta('product:price:amount') or meta('og:price:amount')
    if main:
        m=main.select_one('[itemprop="price"]')
        c=main.select_one('[itemprop="priceCurrency"]')
        if m:amount=m.get('content') or m.get_text(' ',strip=True)
        if c:cur=c.get('content') or c.get_text(' ',strip=True)
    if cur.upper() not in ('TRY','TL','₺'):return None
    price=price_number(amount,structured=True)
    if price is None:return None
    wanted=(row.get('concentration') or concentration(row['product_name'])).lower()
    if wanted and concentration(name)!=wanted:return None
    if row.get('gender') and gender(name)!=row['gender']:return None
    return {'price_try':price,'currency':'TRY','purchase_url':url,'seller_name':host(url),'source_product_name':name,
            'stock_status':'unknown','volume_ml':volume(name),'price_source':'main_product_meta','match_confidence':0.95}


def search_links(provider,raw):
    soup=BeautifulSoup(raw,'lxml');out=[];seen=set()
    selectors={'ddg':'a.result__a','bing':'li.b_algo h2 a','yahoo':'h3 a, .compTitle a'}
    for a in soup.select(selectors[provider]):
        u=a.get('href','');q=parse_qs(urlsplit(urljoin(PROVIDERS[provider][0],u)).query)
        if 'uddg' in q:u=q['uddg'][0]
        elif provider=='bing' and 'u' in q:
            token=q['u'][0]
            if token.startswith('a1'):
                try:u=base64.urlsafe_b64decode(token[2:]+'===').decode()
                except (ValueError,UnicodeDecodeError):continue
        elif provider=='yahoo' and '/RU=' in u:
            u=unquote(u.split('/RU=',1)[1].split('/RK=',1)[0])
        if public_url(u) and u not in seen:
            seen.add(u);out.append((a.get_text(' ',strip=True),u))
    return out[:10]


def eligible_url(url):
    if not public_url(url):return False
    h=host(url)
    if any(h==d or h.endswith('.'+d) for d in INFO):return False
    p=urlsplit(url)
    return not any(x in p.path.lower() for x in ('/search','/arama','/kategori','/category','/collections','/catalogsearch'))


class Engine:
    def __init__(self,client,seeds=None):
        self.client=client;self.seeds=seeds or {};self.stats=Counter();self.lock=threading.Lock()

    def search(self,row,q):
        events=[]
        # DDG was verified in preflight. Other free HTML providers are fallbacks.
        for provider in ('ddg','bing','yahoo'):
            url,params=PROVIDERS[provider];params=dict(params)
            params['p' if provider=='yahoo' else 'q']=q
            fetched=self.client.fetch(url,params)
            if not fetched.ok:
                events.append({'provider':provider,'status':fetched.error,'retry_at':fetched.retry_at});continue
            links=search_links(provider,fetched.text)
            # HTTP 200 with an unrecognized/irrelevant page is not a completed search.
            relevant=[(t,u) for t,u in links if any(a in norm(t+' '+unquote(u)) for a in brand_aliases(row['brand_name']))]
            explicit_empty=any(t in fetched.text.lower() for t in ('no results found','no results.','did not match any documents','no results for'))
            events.append({'provider':provider,'status':'ok' if relevant else 'no_results' if explicit_empty else 'unrecognized','links':len(relevant)})
            with self.lock:self.stats['search:'+provider+':'+events[-1]['status']]+=1
            if relevant or explicit_empty:return relevant,True,events
        return [],False,events

    def _page(self,row,url,source):
        fetched=self.client.fetch(url)
        if not fetched.ok:return None,{'url':url,'status':fetched.error,'http':fetched.status,'retry_at':fetched.retry_at}
        offer=parse_page(fetched.text,fetched.url,row)
        if not offer:return None,{'url':url,'status':'page_no_verified_offer','http':200}
        # TRY alone on an unknown global storefront is insufficient for domestic availability.
        domestic=host(fetched.url).endswith('.tr') or host(fetched.url) in DOMAINS
        offer.update(discovery_source=source,checked_at=datetime.fromtimestamp(fetched.fetched_at,timezone.utc).isoformat(),
                     link_status='verified_link' if domestic else 'candidate',price_status='verified_price' if domestic else 'candidate_price',
                     page_verified='1',stock_checked='schema_or_unknown',checkout_verified=False)
        return offer,{'url':url,'status':'verified_offer' if domestic else 'foreign_market_review','http':200}

    def discover(self,raw):
        row=dict(raw);pid=str(row['id'])
        row.update(self.seeds.get('identity_overrides',{}).get(pid,{}))
        base={'product_id':pid,'brand_name':row['brand_name'],'product_name':row['product_name'],
              'release_year':row.get('release_year',''),'link_status':'not_found','price_status':'not_found',
              'currency':'TRY','price_try':None,'purchase_url':'','stock_status':'unknown','page_verified':'0',
              'checked_at':datetime.now(timezone.utc).isoformat(),'checkout_verified':False,'method_version':'v3.1'}
        offers=[];events=[];seen=set();seeds=list(self.seeds.get('urls_by_id',{}).get(pid,[]))
        source=row.get('source_url','')
        if eligible_url(source):seeds.insert(0,source)
        for url in dict.fromkeys(seeds):
            if not eligible_url(url):continue
            seen.add(url);offer,event=self._page(row,url,'source_or_previous_link');events.append(event)
            if offer:offers.append(offer)
            if offer and offer['link_status']=='verified_link' and offer['stock_status']!='out_of_stock':break
        if not any(o['link_status']=='verified_link' and o['stock_status']!='out_of_stock' for o in offers):
            valid_search=False
            qs=queries(row)
            # Every record gets a primary query. Turkey-brand records get an alternate query if needed.
            query_count=2 if core.brand_in_tr_retail(row['brand_name']) else 1
            for q in qs[:query_count]:
                links,ok,search_events=self.search(row,q);events.extend(search_events);valid_search|=ok
                for title,url in links:
                    if url in seen or not eligible_url(url):continue
                    # Require actual name tokens before spending a product-page request.
                    expected=set(name_tokens(row,row['product_name']))
                    combined=canonical(title+' '+unquote(url))
                    if expected and not all(t in combined.split() for t in expected):continue
                    seen.add(url);offer,event=self._page(row,url,'web_search');events.append(event)
                    if offer:offers.append(offer)
                    if len(seen)>=6 or (offer and offer['link_status']=='verified_link' and offer['stock_status']!='out_of_stock'):break
                if any(o['link_status']=='verified_link' and o['stock_status']!='out_of_stock' for o in offers):break
            if not valid_search and not offers:
                base.update(link_status='deferred_search',price_status='not_checked')
            elif not offers and any(e.get('status') not in ('page_no_verified_offer','verified_offer','foreign_market_review')
                    and not (e.get('status')=='http_error' and e.get('http') in (404,410)) for e in events if 'url' in e):
                base.update(link_status='deferred_page',price_status='not_checked')
        if offers:
            best=min(offers,key=lambda o:(o['link_status']!='verified_link',{'in_stock':0,'unknown':1,'out_of_stock':2}.get(o['stock_status'],1),o.get('price_try') or float('inf')))
            base.update(best)
        base['events']=events
        return base
