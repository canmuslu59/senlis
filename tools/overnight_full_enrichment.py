#!/usr/bin/env python3
import csv, glob, gzip, html, json, os, re, time, random, sqlite3, threading, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz

SHARD_INDEX=int(os.environ.get("SHARD_INDEX","0"))
SHARD_COUNT=int(os.environ.get("SHARD_COUNT","8"))
WORKERS=int(os.environ.get("WORKERS","4"))
MAX_SECONDS=int(os.environ.get("MAX_SECONDS","18000"))
SEARCH_ENGINE_FALLBACK=os.environ.get("SEARCH_ENGINE_FALLBACK","0")=="1"
COMMERCE_SCOPE=os.environ.get("COMMERCE_SCOPE","tr_retail").strip().lower()
OUT=Path("out"); OUT.mkdir(exist_ok=True)
OUTCSV=OUT/f"shard_{SHARD_INDEX:02d}.csv"
OUTJSON=OUT/f"summary_{SHARD_INDEX:02d}.json"

TR_SELLERS=[
 "sephora.com.tr","boyner.com.tr","beymen.com","sevil.com.tr","rossmann.com.tr",
 "watsons.com.tr","gratis.com","trendyol.com","hepsiburada.com","amazon.com.tr","n11.com",
 "zara.com","victoriassecret.com.tr","bathandbodyworks.com.tr","avon.com.tr","yvesrocher.com.tr",
 "oriflame.com","thebodyshop.com.tr","lush.com.tr"
]
BAD=["tester","sample","numune","dekant","decant","muadil","benzeri","açık parfüm","acik parfum","esans"]
TR_RETAIL_BRANDS_PATH=Path("data/turkiye_retail_brands_501.txt")
OFFICIAL_PRICE_INDEX_PATH=Path("data/official_price_index.csv")

INFO_DOMAINS=[
 "fragrantica.com","parfumo.com","basenotes.com","wikipedia.org","facebook.com","instagram.com",
 "youtube.com","tiktok.com","pinterest.com","reddit.com","duckduckgo.com","bing.com","google.com"
]

def norm(s):
    s=html.unescape(str(s or "")).lower()
    s=s.replace("ı","i").replace("ş","s").replace("ğ","g").replace("ü","u").replace("ö","o").replace("ç","c")
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",s)).strip()

def match_norm(s):
    t=norm(s)
    replacements=[
      ("vucut ve sac parfum misti","body mist"),
      ("sac ve vucut parfum misti","body mist"),
      ("sac parfum misti","body mist"),
      ("vucut parfum misti","body mist"),
      ("parfum misti","body mist"),
      ("vucut misti","body mist"),
      ("body misti","body mist"),
      ("vucut spreyi","body mist"),
      ("body spray","body mist"),
      ("fragrance mist","body mist"),
      ("hair mist","body mist"),
    ]
    for a,b in replacements: t=t.replace(a,b)
    return t


GENERIC_PRODUCT_TOKENS={"eau","de","parfum","perfume","edp","edt","spray","fragrance","ml","the","and","of","erkek","kadin","unisex","parfumu"}
VARIANT_MARKERS={"intense","elixir","flame","energy","absolu","absolut","collector","collectors","limited","edition","sport","night","noir","rouge",
                 "bloom","floral","pour","femme","homme","women","woman","men","man","her","him","le",
                 "gold","silver","black","white","blue","red","pink","green","purple","platinum"}

def load_official_price_index():
    if not OFFICIAL_PRICE_INDEX_PATH.exists(): return {}
    out={}
    try:
        with OFFICIAL_PRICE_INDEX_PATH.open("r",encoding="utf-8-sig",newline="") as f:
            for r in csv.DictReader(f):
                pid=str(r.get("product_id") or "").strip()
                if pid and r.get("price_try"): out[pid]=r
    except Exception:
        return {}
    return out

OFFICIAL_PRICE_INDEX=load_official_price_index()

def load_tr_retail_brands():
    if not TR_RETAIL_BRANDS_PATH.exists(): return set()
    return {norm(x) for x in TR_RETAIL_BRANDS_PATH.read_text(encoding="utf-8-sig").splitlines() if x.strip()}

TR_RETAIL_BRANDS=load_tr_retail_brands()
TR_RETAIL_EXTRA={"versace"}
TR_RETAIL_ALIAS={
 "al haramain perfumes":"al haramain",
 "lattafa perfumes":"lattafa",
 "demeter fragrance":"demeter",
 "demeter fragrance library":"demeter",
 "dior":"christian dior",
 "rabanne":"paco rabanne",
 "giorgio armani":"armani",
 "emporio armani":"armani",
 "salvatore ferragamo":"ferragamo",
 "mad parfumeur":"mad parfum",
 "loris parfum":"loris",
 "aqua di polo":"aqua di polo 1987",
 "hunca":"hunca care",
 "mercedes benz":"mercedes benz parfums",
 "sevilla fragrances":"sevilla",
 "sospiro perfumes":"sospiro",
 "alfaparf milano":"alfaparf",
 "rosemary":"rosemary paris",
 "puccini paris":"puccini",
 "reef perfumes":"reef"
}

def brand_in_tr_retail(brand):
    b=norm(brand)
    if b in TR_RETAIL_BRANDS or b in TR_RETAIL_EXTRA: return True
    a=TR_RETAIL_ALIAS.get(b)
    if a and norm(a) in TR_RETAIL_BRANDS: return True
    return False

def commerce_eligible(row):
    if COMMERCE_SCOPE=="all": return True
    if COMMERCE_SCOPE=="off": return False
    return brand_in_tr_retail(row.get("brand_name",""))

NON_FRAGRANCE_PHRASES={
 "deostick","deo stick","deodorant","body lotion","vucut losyonu","vücut losyonu","shower gel","dus jeli","duş jeli",
 "body wash","yikama jeli","yıkama jeli","hand wash","el ve vucut","el ve vücut","body cream","vucut kremi","vücut kremi",
 "after shave","aftershave","beard oil","sakal yagi","sakal yağı","soap","sabun"
}
SET_PHRASES={"gift set","parfum set","parfüm set","seti","coffret"}

def has_any_phrase(text,phrases):
    t=norm(text)
    return any(norm(p) in t for p in phrases)

def form_compatible(product,candidate):
    tp=match_norm(product); cp=match_norm(candidate)
    if has_any_phrase(candidate,NON_FRAGRANCE_PHRASES) and not has_any_phrase(product,NON_FRAGRANCE_PHRASES):
        return False
    tset=has_any_phrase(product,SET_PHRASES)
    cset=has_any_phrase(candidate,SET_PHRASES)
    if cset and not tset: return False
    tmist=bool(re.search(r"\b(?:body mist|hair body mist|fragrance mist|mist)\b",tp))
    cmist=bool(re.search(r"\b(?:body mist|hair body mist|fragrance mist|mist)\b",cp))
    if tmist != cmist: return False
    return True

def fragrance_type(s):
    raw=str(s or "").lower()
    t=norm(s)
    if re.search(r"\beau de parfum\b|\bedp\b",t): return "edp"
    if re.search(r"\beau de toilette\b|\bedt\b",t): return "edt"
    if "extrait" in t: return "extrait"
    if re.search(r"\beau de cologne\b|\bcologne\b",t): return "edc"
    # Turkish "parfüm" is commonly a generic product-category label, not a Parfum concentration.
    if re.search(r"\bparfum\b",t) and "parfüm" not in raw: return "parfum"
    return ""

def special_format(s):
    t=match_norm(s)
    if "body mist" in t: return "body_mist"
    if re.search(r"\b(solid perfume|solid parfum|kati parfum|krem parfum|cream perfume|cream parfum)\b",t): return "solid"
    if re.search(r"\b(seyahat boy|travel size|travel|mini parfum|mini perfume)\b",t): return "travel"
    if re.search(r"\b(after shave|aftershave)\b",t): return "aftershave"
    if re.search(r"\b(parfumlu erkek kolonyasi|erkek kolonyasi)\b",t): return "cologne_product"
    if re.search(r"\b(vucut peelingi|body scrub|peeling|scrub)\b",t): return "scrub"
    if re.search(r"\b(body lotion|vucut losyonu|lotion|losyon|nemlendirici|moisturizer)\b",t): return "lotion"
    if re.search(r"\b(shower gel|dus jeli|yikama jeli|body wash|hand wash|sabun|soap)\b",t): return "wash"
    if re.search(r"\b(deodorant|deodorant|stick deodorant)\b",t): return "deodorant"
    if re.search(r"\b(candle|mum|diffuser|oda kokusu|room spray)\b",t): return "home"
    if re.search(r"\b(refill)\b",t): return "refill"
    if re.search(r"\b(gift set|parfum set|perfume set|seti|set)\b",t): return "set"
    return ""

def is_travel_format(s):
    t=match_norm(s)
    return bool(re.search(r"\b(seyahat boy|seyahat boyu|travel size|travel|mini)\b",t))

def variant_compatible(brand,product,candidate):
    tp=match_norm(product); cp=match_norm(candidate); bn=set(match_norm(brand).split())
    if not form_compatible(product,candidate): return False
    ttype=fragrance_type(product); ctype=fragrance_type(candidate)
    if ttype and ctype and ttype!=ctype: return False
    tformat=special_format(product); cformat=special_format(candidate)
    if (tformat or cformat) and tformat!=cformat: return False
    if is_travel_format(product) != is_travel_format(candidate): return False

    tt=[x for x in tp.split() if x not in bn and x not in GENERIC_PRODUCT_TOKENS]
    ct=set(cp.split())
    distinctive=[x for x in tt if len(x)>=5 and not x.isdigit()]
    if distinctive and any(x not in ct for x in distinctive):
        return False
    if tt:
        coverage=sum(x in ct for x in tt)/len(tt)
        if len(tt)<=2 and coverage<1.0: return False
        if len(tt)>2 and coverage<0.75: return False
        for x in tt:
            if (x.isdigit() and len(x)==4) or x in VARIANT_MARKERS:
                if x not in ct: return False

    tm=set(tp.split()) & VARIANT_MARKERS
    cm=set(cp.split()) & VARIANT_MARKERS
    if cm-tm: return False

    # Require the actual fragrance-name tokens to survive the retailer mapping.
    # This blocks base-name collisions such as Coco -> Bombshell Mini,
    # Pure Seduction -> Bombshell Seduction and Vanilla Lace -> Bare Sueded Vanilla.
    alias_tokens=set()
    for a in BRAND_ALIASES.get(norm(brand),[]):
        alias_tokens.update(a.split())
    name_safe=set(GENERIC_PRODUCT_TOKENS) | {
      "body","mist","hair","misti","vucut","sac","seyahat","boy","boyu","travel","size","mini",
      "refillable","refill","refil","notes","note","citrus","vanilla","woody","fresh","floral","amber",
      "oz","fl","natural","alcohol","free","beauty","collection","cok","yakinda","yeniden","stoklarda","yeni","urun"
    }
    tname=[x for x in tp.split() if x not in bn and x not in alias_tokens and x not in name_safe and not x.isdigit()]
    cname=[x for x in cp.split() if x not in bn and x not in alias_tokens and x not in name_safe and not x.isdigit()]
    if tname and any(x not in cname for x in tname): return False
    if 1 <= len(tname) <= 4:
        extras=[x for x in cname if x not in tname]
        if extras: return False

    # Short fragrance names are highly ambiguous: a retailer result may be a flanker
    # with the complete base name plus one or two extra name tokens
    # (e.g. Bombshell -> Bombshell Bronze, Tease -> Tease Sugar Fleur,
    # Cherry Blossom -> Japanese Cherry Blossom). Reject those extras even when
    # both sides share the same concentration.
    if 1 <= len(tt) <= 3:
        alias_tokens=set()
        for a in BRAND_ALIASES.get(norm(brand),[]):
            alias_tokens.update(a.split())
        safe={"refillable","refill","refil","notes","note","citrus","vanilla","woody","fresh","floral","amber",
              "erkek","kadin","unisex","parfumu","parfum","perfume","fragrance","spray","ml","edp","edt","edc",
              "eau","de","the","and","for","oz","fl","natural","alcohol","free"}
        cand_dist=[x for x in cp.split() if x not in bn and x not in alias_tokens and x not in safe and not x.isdigit()]
        extras=[x for x in cand_dist if x not in tt]
        if extras: return False
    return True

BRAND_ALIASES={
 "yves saint laurent":["ysl"],
 "giorgio armani":["armani"],
 "calvin klein":["ck"],
 "dolce gabbana":["d g","dg"],
 "victoria s secret":["victorias secret","vs"]
}

def brand_compatible(brand,candidate):
    b=norm(brand); c=norm(candidate)
    if b and b in c: return True
    for alias in BRAND_ALIASES.get(b,[]):
        if alias in c: return True
    bt=[x for x in b.split() if len(x)>=4]
    return any(x in c.split() for x in bt)

def product_match_score(brand,product,candidate):
    p=match_norm(product); c=match_norm(candidate); b=match_norm(brand)
    ps=fuzz.token_set_ratio(p,c)
    pr=fuzz.ratio(p,c)
    bs=fuzz.token_set_ratio(b,c) if b else 0
    score=.72*ps+.13*pr+.15*bs
    if brand_compatible(brand,candidate): score+=8
    return min(100,score)


def host(url):
    try:
        h=urllib.parse.urlparse(url).netloc.lower().split(":")[0]
        return h[4:] if h.startswith("www.") else h
    except: return ""

def make_session():
    s=requests.Session()
    s.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36",
                      "Accept-Language":"tr-TR,tr;q=0.9,en;q=0.8"})
    return s

def load_rows():
    products=[]
    for p in sorted(glob.glob("data/master_manifest_174259/part_*.csv*")):
        opener = gzip.open if str(p).endswith(".gz") else open
        with opener(p, mode="rt", encoding="utf-8-sig", newline="") as f:
            products.extend(csv.DictReader(f))
    source={}
    for p in sorted(glob.glob("data/source_urls/part_*.csv")):
        with open(p,encoding="utf-8-sig",newline="") as f:
            for r in csv.DictReader(f):
                if r.get("source_url"): source[r["id"]]=r["source_url"]
    # stable sharding by sorted row ordinal
    shard=[r for i,r in enumerate(products) if i % SHARD_COUNT == SHARD_INDEX]
    for r in shard: r["source_url"]=source.get(r["id"]) or r.get("source_url","")
    return shard

def walk_json(obj):
    if isinstance(obj,dict):
        yield obj
        for v in obj.values(): yield from walk_json(v)
    elif isinstance(obj,list):
        for v in obj: yield from walk_json(v)

def parse_jsonld(soup):
    objs=[]
    for tag in soup.find_all("script",attrs={"type":"application/ld+json"}):
        try:
            obj=json.loads(tag.get_text(" ",strip=True))
            objs.extend(walk_json(obj))
        except: pass
    return objs

def extract_static(session,row):
    url=row.get("source_url")
    res={"release_year_candidate":"","image_url_candidate":"","notes_candidate":"",
         "static_status":"no_source","static_http":"","static_source":url or ""}
    if not url: return res
    try:
        r=session.get(url,timeout=18,allow_redirects=True)
        res["static_http"]=str(r.status_code)
        if r.status_code!=200 or "text/html" not in r.headers.get("content-type",""):
            res["static_status"]="http_error"; return res
        soup=BeautifulSoup(r.text,"lxml")
        title=soup.title.get_text(" ",strip=True) if soup.title else ""
        meta=soup.find("meta",attrs={"property":"og:image"}) or soup.find("meta",attrs={"name":"twitter:image"})
        if meta and meta.get("content"): res["image_url_candidate"]=urllib.parse.urljoin(r.url,meta["content"])
        objs=parse_jsonld(soup)
        for o in objs:
            typ=o.get("@type")
            if typ=="Product" or (isinstance(typ,list) and "Product" in typ):
                im=o.get("image")
                if isinstance(im,list): im=im[0] if im else ""
                if isinstance(im,dict): im=im.get("url") or im.get("contentUrl") or ""
                if im and not res["image_url_candidate"]: res["image_url_candidate"]=urllib.parse.urljoin(r.url,str(im))
            for k in ("datePublished","releaseDate","dateCreated"):
                if not row.get("release_year") and o.get(k):
                    m=re.search(r"\b(17\d{2}|18\d{2}|19\d{2}|20[0-2]\d)\b",str(o[k]))
                    if m: res["release_year_candidate"]=m.group(1)
        text=soup.get_text(" ",strip=True)
        if not row.get("release_year") and not res["release_year_candidate"]:
            pats=[
              r"(?:launched|released|introduced|created)\s+(?:in\s+)?(17\d{2}|18\d{2}|19\d{2}|20[0-2]\d)",
              r"(17\d{2}|18\d{2}|19\d{2}|20[0-2]\d)\s+(?:yılında|yilinda)",
              r"\b(17\d{2}|18\d{2}|19\d{2}|20[0-2]\d)\b"
            ]
            for pat in pats:
                m=re.search(pat,text[:25000],re.I)
                if m: res["release_year_candidate"]=m.group(1); break
        # Conservative note extraction: only explicit note sections.
        flat=" ".join(text.split())
        sections=[]
        labels=[("Top Notes","Middle Notes"),("Middle Notes","Base Notes"),("Base Notes","Perfume rating"),
                ("Üst Notalar","Orta Notalar"),("Orta Notalar","Alt Notalar")]
        for a,b in labels:
            m=re.search(re.escape(a)+r"\s*[:\-]?\s*(.{3,500}?)\s*"+re.escape(b),flat,re.I)
            if m: sections.append(f"{a}: {m.group(1).strip()}")
        if not sections:
            m=re.search(r"(?:Notes|Fragrance Notes|Koku Notaları)\s*[:\-]\s*(.{3,600}?)(?:Reviews|Ratings|Accords|$)",flat,re.I)
            if m: sections.append(m.group(1).strip())
        if sections: res["notes_candidate"]=" | ".join(sections)[:1600]
        res["static_source"]=r.url
        res["static_status"]="ok" if (res["image_url_candidate"] or res["release_year_candidate"] or res["notes_candidate"]) else "page_no_extract"
        return res
    except Exception as e:
        res["static_status"]="error"; res["static_error"]=str(e)[:180]; return res

def ddg(session,q):
    try:
        r=session.get("https://html.duckduckgo.com/html/",params={"q":q,"kl":"tr-tr"},timeout=16)
        if r.status_code!=200: return []
        soup=BeautifulSoup(r.text,"lxml"); out=[]
        selectors=["a.result__a","h2.result__title a"]
        seen=set()
        for sel in selectors:
            for a in soup.select(sel):
                u=a.get("href",""); t=a.get_text(" ",strip=True)
                try:
                    p=urllib.parse.urlparse(u); qs=urllib.parse.parse_qs(p.query)
                    if "uddg" in qs: u=qs["uddg"][0]
                except: pass
                if u.startswith("http") and u not in seen:
                    seen.add(u); out.append((t,u))
                if len(out)>=10: return out
        return out
    except: return []

def bing(session,q):
    out=[]; seen=set()
    try:
        r=session.get("https://www.bing.com/search",params={"q":q,"setlang":"tr-tr","cc":"tr"},timeout=16)
        if r.status_code==200:
            soup=BeautifulSoup(r.text,"lxml")
            for a in soup.select("li.b_algo h2 a"):
                u=a.get("href",""); t=a.get_text(" ",strip=True)
                if u.startswith("http") and u not in seen:
                    seen.add(u); out.append((t,u))
                if len(out)>=10: return out
    except: pass
    try:
        r=session.get("https://www.bing.com/search",params={"q":q,"format":"rss","setlang":"tr-tr","cc":"tr"},timeout=16)
        if r.status_code==200:
            soup=BeautifulSoup(r.content,"xml")
            for item in soup.find_all("item"):
                t=item.title.get_text(" ",strip=True) if item.title else ""
                u=item.link.get_text(" ",strip=True) if item.link else ""
                if u.startswith("http") and u not in seen:
                    seen.add(u); out.append((t,u))
                if len(out)>=10: break
    except: pass
    return out

def search_web(session,q):
    out=[]; seen=set()
    for fn in (bing,ddg):
        for title,url in fn(session,q):
            if url not in seen:
                seen.add(url); out.append((title,url))
            if len(out)>=14: return out
    return out


_OFFICIAL_CATALOG_CACHE={}
_OFFICIAL_CATALOG_LOCK=threading.Lock()

def _official_catalog_rows(session,brand):
    b=norm(brand)
    if b=="oriflame":
        key="oriflame"; urls=[
            "https://tr.oriflame.com/fragrance",
            "https://tr.oriflame.com/fragrance/shop-by-product/perfume",
            "https://tr.oriflame.com/men/shop-by-product/fragrance",
            "https://tr.oriflame.com/fragrance/family-type/floral-fragrances",
            "https://tr.oriflame.com/fragrance/family-type/ambery-fragrances",
            "https://tr.oriflame.com/fragrance/family-type/aromatic-fragrances",
            "https://tr.oriflame.com/fragrance/family-type/chypre-fragrances",
            "https://tr.oriflame.com/fragrance/family-type/citrus-fragrances",
            "https://tr.oriflame.com/fragrance/family-type/fruity-fragrances",
            "https://tr.oriflame.com/fragrance/family-type/woody-fragrances"
        ]
    elif b=="bath body works":
        key="bath_body_works"; urls=["https://www.bathandbodyworks.com.tr/tum-vucut-spreyleri-ve-parfumler"]
    elif b=="victoria s secret":
        key="victorias_secret"; urls=[
            "https://www.victoriassecret.com.tr/vs/parfum",
            "https://www.victoriassecret.com.tr/vs/fragrance-vucut-spreyleri"
        ]
    else:
        return []

    with _OFFICIAL_CATALOG_LOCK:
        if key in _OFFICIAL_CATALOG_CACHE:
            return _OFFICIAL_CATALOG_CACHE[key]
        out=[]; seen=set()
        for url in urls:
            try:
                r=session.get(url,timeout=25,allow_redirects=True)
                if r.status_code!=200 or "text/html" not in r.headers.get("content-type",""): continue
                soup=BeautifulSoup(r.text,"lxml")
                for a in soup.find_all("a",href=True):
                    href=urllib.parse.urljoin(r.url,a.get("href",""))
                    raw=" ".join(a.get_text(" ",strip=True).split())
                    if not raw or href in seen: continue
                    title=""; price=None
                    if key=="oriflame":
                        if "/products/product?code=" not in href: continue
                        title=re.sub(r"^\(\s*\d+\s*\)\s*","",raw)
                        title=re.sub(r"\s*₺[\d.,]+.*$","",title).strip()
                        pm=re.search(r"₺\s*(\d{1,3}(?:[.]\d{3})*(?:,\d{2})?)",raw)
                    elif key=="bath_body_works":
                        if "-BBW" not in href: continue
                        title=raw
                        parent=a
                        for _ in range(4):
                            if not getattr(parent,"parent",None): break
                            parent=parent.parent
                        ctx=" ".join(parent.get_text(" ",strip=True).split()) if parent else raw
                        pm=re.search(r"(\d{1,3}(?:[.]\d{3})*,\d{2})\s*₺",ctx)
                    else:
                        if "victoria-s-secret-" not in href or "-VS" not in href: continue
                        title=raw
                        parent=a
                        for _ in range(4):
                            if not getattr(parent,"parent",None): break
                            parent=parent.parent
                        ctx=" ".join(parent.get_text(" ",strip=True).split()) if parent else raw
                        pm=re.search(r"(\d{1,3}(?:[.]\d{3})*,\d{2})\s*TL",ctx,re.I)
                    if not title: continue
                    if pm:
                        try: price=float(pm.group(1).replace(".","").replace(",","."))
                        except: price=None
                    seen.add(href)
                    out.append({"title":title,"url":href,"price_try":price})
            except Exception:
                continue
        _OFFICIAL_CATALOG_CACHE[key]=out
        return out

def official_catalog_offer(session,brand,product):
    rows=_official_catalog_rows(session,brand)
    verified=[]
    for item in rows:
        if not item.get("price_try"): continue
        title=item["title"]
        enriched=f"{brand} {title}"
        score=product_match_score(brand,product,enriched)
        if any(x in match_norm(title) for x in BAD) and not any(x in match_norm(product) for x in BAD): score-=30
        if score<82 or not variant_compatible(brand,product,enriched): continue
        volume=""
        m=re.search(r"(?<!\d)(\d{1,4}(?:[.,]\d+)?)\s*ml\b",title,re.I)
        if m:
            try: volume=float(m.group(1).replace(",","."))
            except: volume=""
        verified.append({
            "score":min(100,score),"price_try":item["price_try"],"currency":"TRY",
            "purchase_url":item["url"],"seller_name":host(item["url"]),"stock_status":"unknown",
            "commerce_image":"","source_product_name":title,"volume_ml":volume
        })
    if not verified: return None
    return min(verified,key=lambda x:(float(x.get("price_try") or 1e18),-float(x.get("score") or 0)))

def official_catalog_search(session,brand,product):
    rows=_official_catalog_rows(session,brand)
    if not rows: return []
    out=[]
    for item in rows:
        title=item["title"]
        enriched=f"{brand} {title}"
        score=product_match_score(brand,product,enriched)
        if any(x in match_norm(title) for x in BAD) and not any(x in match_norm(product) for x in BAD): score-=30
        if score>=62 and variant_compatible(brand,product,enriched):
            out.append((score,enriched,item["url"]))
    out.sort(reverse=True)
    return [(title,url) for score,title,url in out[:8]]

def boyner_search(session,brand,product):
    try:
        r=session.get("https://www.boyner.com.tr/search",params={"q":f"{brand} {product}"},timeout=20,allow_redirects=True)
        if r.status_code!=200 or "text/html" not in r.headers.get("content-type",""): return []
        soup=BeautifulSoup(r.text,"lxml")
        target=norm(f"{brand} {product}")
        out=[]; seen=set()
        for a in soup.find_all("a",href=True):
            href=a.get("href","")
            if "-p-" not in href and "/p_" not in href: continue
            title=" ".join(a.get_text(" ",strip=True).split())
            if not title: continue
            url=urllib.parse.urljoin(r.url,href)
            if url in seen: continue
            seen.add(url)
            score=product_match_score(brand,product,title)
            if any(b in norm(title) for b in BAD) and not any(b in norm(product) for b in BAD): score-=30
            if score>=58 and brand_compatible(brand,title) and variant_compatible(brand,product,title): out.append((score,title,url))
        out.sort(reverse=True)
        return [(title,url) for score,title,url in out[:8]]
    except: return []

def gratis_search(session,brand,product):
    try:
        r=session.get("https://www.gratis.com/search",params={"q":f"{brand} {product}"},timeout=20,allow_redirects=True)
        if r.status_code!=200 or "text/html" not in r.headers.get("content-type",""): return []
        soup=BeautifulSoup(r.text,"lxml")
        out=[]; seen=set()
        for a in soup.find_all("a",href=True):
            href=a.get("href","")
            title=" ".join(a.get_text(" ",strip=True).split())
            if not title or "-p-" not in href: continue
            url=urllib.parse.urljoin(r.url,href)
            if url in seen: continue
            seen.add(url)
            score=product_match_score(brand,product,title)
            if any(b in norm(title) for b in BAD) and not any(b in norm(product) for b in BAD): score-=30
            if score>=58 and brand_compatible(brand,title) and variant_compatible(brand,product,title):
                out.append((score,title,url))
        out.sort(reverse=True)
        return [(title,url) for score,title,url in out[:8]]
    except: return []

def n11_search(session,brand,product):
    try:
        r=session.get("https://www.n11.com/arama",params={"q":f"{brand} {product}"},timeout=20,allow_redirects=True)
        if r.status_code!=200 or "text/html" not in r.headers.get("content-type",""): return []
        soup=BeautifulSoup(r.text,"lxml")
        out=[]; seen=set()
        for a in soup.find_all("a",href=True):
            href=a.get("href","")
            title=" ".join(a.get_text(" ",strip=True).split())
            if not title or "/urun/" not in href: continue
            url=urllib.parse.urljoin(r.url,href)
            if url in seen: continue
            seen.add(url)
            score=product_match_score(brand,product,title)
            if any(b in norm(title) for b in BAD) and not any(b in norm(product) for b in BAD): score-=30
            if score>=70 and brand_compatible(brand,title) and variant_compatible(brand,product,title):
                out.append((score,title,url))
        out.sort(reverse=True)
        return [(title,url) for score,title,url in out[:6]]
    except: return []

def beymen_search(session,brand,product):
    try:
        r=session.get("https://www.beymen.com/tr/search",params={"q":f"{brand} {product}"},timeout=20,allow_redirects=True)
        if r.status_code!=200 or "text/html" not in r.headers.get("content-type",""): return []
        soup=BeautifulSoup(r.text,"lxml")
        target=norm(f"{brand} {product}")
        out=[]; seen=set()
        for a in soup.find_all("a",href=True):
            href=a.get("href","")
            if "/tr/p_" not in href: continue
            title=" ".join(a.get_text(" ",strip=True).split())
            if not title: continue
            url=urllib.parse.urljoin(r.url,href)
            if url in seen: continue
            seen.add(url)
            score=product_match_score(brand,product,title)
            if any(b in norm(title) for b in BAD) and not any(b in norm(product) for b in BAD): score-=30
            if score>=58 and brand_compatible(brand,title) and variant_compatible(brand,product,title):
                out.append((score,title,url))
        out.sort(reverse=True)
        return [(title,url) for score,title,url in out[:8]]
    except: return []

def parse_offer_page(session,url,brand,product):
    try:
        r=session.get(url,timeout=18,allow_redirects=True)
        if r.status_code!=200 or "text/html" not in r.headers.get("content-type",""): return None
        soup=BeautifulSoup(r.text,"lxml"); objs=parse_jsonld(soup)
        title=soup.title.get_text(" ",strip=True) if soup.title else ""
        target=norm(f"{brand} {product}")
        best=None
        for o in objs:
            typ=o.get("@type")
            if not (typ=="Product" or (isinstance(typ,list) and "Product" in typ)): continue
            name=o.get("name") or title
            if not brand_compatible(brand,f"{name} {title}") or not variant_compatible(brand,product,name): continue
            score=product_match_score(brand,product,name)
            offers=o.get("offers"); offers=offers if isinstance(offers,list) else [offers] if isinstance(offers,dict) else []
            im=o.get("image")
            if isinstance(im,list): im=im[0] if im else ""
            if isinstance(im,dict): im=im.get("url") or im.get("contentUrl") or ""
            for off in offers or [{}]:
                price=off.get("price") or off.get("lowPrice")
                cur=off.get("priceCurrency") or ""
                try:
                    if price is not None:
                        raw=str(price).strip().replace("\xa0"," ")
                        if re.search(r"\d+[.]\d{3},\d",raw): raw=raw.replace(".","").replace(",",".")
                        else: raw=raw.replace(" ","").replace(",",".")
                        price=float(re.sub(r"[^0-9.]","",raw))
                except: price=None
                if str(cur).upper() not in ("TRY","TL","₺","") and price is not None: price=None
                rec={"score":min(100,score),"price_try":price,"currency":"TRY","purchase_url":urllib.parse.urljoin(r.url,str(off.get("url"))) if off.get("url") else r.url,
                     "seller_name":host(r.url),"stock_status":"in_stock" if "instock" in str(off.get("availability","")).lower() else
                     ("out_of_stock" if "outofstock" in str(off.get("availability","")).lower() else "unknown"),
                     "commerce_image":urllib.parse.urljoin(r.url,str(im)) if im else "","source_product_name":name}
                if best is None or rec["score"]>best["score"] or (rec["score"]==best["score"] and rec["price_try"] and not best.get("price_try")): best=rec

        # Common OpenGraph / product meta price fallback.
        if best is None:
            name=title
            if not brand_compatible(brand,f"{name} {title}") or not variant_compatible(brand,product,name): return None
            score=product_match_score(brand,product,name)
            amount=None; cur=""
            for key in ("product:price:amount","og:price:amount"):
                m=soup.find("meta",attrs={"property":key}) or soup.find("meta",attrs={"name":key})
                if m and m.get("content"): amount=m.get("content"); break
            for key in ("product:price:currency","og:price:currency"):
                m=soup.find("meta",attrs={"property":key}) or soup.find("meta",attrs={"name":key})
                if m and m.get("content"): cur=m.get("content"); break
            price=None
            if amount:
                try: price=float(re.sub(r"[^0-9.]","",str(amount).replace(",",".").replace(" ","")))
                except: pass
            if str(cur).upper() not in ("TRY","TL","₺","") and price is not None: price=None
            if price is not None:
                best={"score":min(100,score),"price_try":price,"currency":"TRY","purchase_url":r.url,
                      "seller_name":host(r.url),"stock_status":"unknown","commerce_image":"",
                      "source_product_name":name}

        # Visible Turkish price fallback for official/local product pages.
        if best is None:
            flat=" ".join(soup.get_text(" ",strip=True).split())
            score=product_match_score(brand,product,title)
            hm=host(r.url)
            localish=hm.endswith(".com.tr") or hm.endswith(".tr") or "/tr/" in r.url.lower()
            if score>=82 and localish and brand_compatible(brand,title) and variant_compatible(brand,product,title):
                pm=re.search(r"(?<!\d)(\d{1,3}(?:[ .\u00a0]\d{3})+|\d{3,6})(?:[,.]\d{1,2})?\s*(?:TRY|TL|₺)",flat,re.I)
                if pm:
                    raw=pm.group(1).replace(" ","").replace("\u00a0","").replace(".","")
                    try: price=float(raw)
                    except: price=None
                    if price:
                        best={"score":min(100,score),"price_try":price,"currency":"TRY","purchase_url":r.url,
                              "seller_name":hm,"stock_status":"unknown","commerce_image":"",
                              "source_product_name":title}

        if best is None: return None
        text=soup.get_text(" ",strip=True)
        m=re.search(r"(?<!\d)(\d{1,4}(?:[.,]\d+)?)\s*ml\b",text,re.I)
        if m:
            try: best["volume_ml"]=float(m.group(1).replace(",","."))
            except: pass
        return best
    except: return None

def extract_commerce(session,row):
    brand=row["brand_name"]; product=row["product_name"]
    if not commerce_eligible(row):
        return {"commerce_status":"skipped_non_tr_brand","price_try":"","currency":"TRY","volume_ml":"","seller_name":"",
                "purchase_url":"","stock_status":"unknown","commerce_image":"","match_confidence":""}
    res={"commerce_status":"not_found","price_try":"","currency":"TRY","volume_ml":"","seller_name":"",
         "purchase_url":"","stock_status":"unknown","commerce_image":"","match_confidence":""}
    indexed=OFFICIAL_PRICE_INDEX.get(str(row.get("id") or ""))
    if indexed:
        try: price=float(indexed.get("price_try") or 0)
        except: price=indexed.get("price_try") or ""
        try:
            volume=float(indexed.get("volume_ml")) if indexed.get("volume_ml") else ""
        except: volume=indexed.get("volume_ml") or ""
        try:
            confidence=float(indexed.get("match_confidence")) if indexed.get("match_confidence") else 1.0
        except: confidence=1.0
        return {
            "commerce_status":"verified","price_try":price,"currency":indexed.get("currency") or "TRY",
            "volume_ml":volume,"seller_name":indexed.get("seller_name") or "",
            "purchase_url":indexed.get("purchase_url") or "","stock_status":"unknown",
            "commerce_image":"","match_confidence":confidence,
            "source_product_name":indexed.get("source_product_name") or product
        }
    official=official_catalog_offer(session,brand,product)
    if official:
        res.update(official)
        res["match_confidence"]=round(official["score"]/100,3)
        res["commerce_status"]="verified"
        return res
    queries=[
      f'"{brand}" "{product}" fiyat TRY',
      f'"{brand}" "{product}" Türkiye parfüm'
    ]
    results=[]; seen=set()
    for title,url in boyner_search(session,brand,product):
        if url not in seen:
            seen.add(url); results.append((title,url))
    for title,url in beymen_search(session,brand,product):
        if url not in seen:
            seen.add(url); results.append((title,url))
    for title,url in gratis_search(session,brand,product):
        if url not in seen:
            seen.add(url); results.append((title,url))
    for title,url in n11_search(session,brand,product):
        if url not in seen:
            seen.add(url); results.append((title,url))
    if SEARCH_ENGINE_FALLBACK:
        for q in queries:
            for title,url in search_web(session,q):
                if url not in seen:
                    seen.add(url); results.append((title,url))
            if len(results)>=12: break

    candidates=[]
    for title,url in results:
        h=host(url)
        if any(h==d or h.endswith("."+d) for d in INFO_DOMAINS): continue
        sc=product_match_score(brand,product,title)
        if any(b in norm(title) for b in BAD) and not any(b in norm(product) for b in BAD): sc-=30
        trusted=any(h==d or h.endswith("."+d) for d in TR_SELLERS)
        localish=h.endswith(".com.tr") or h.endswith(".tr") or "/tr/" in url.lower()
        if sc>=58 and brand_compatible(brand,title) and variant_compatible(brand,product,title) and (trusted or localish or sc>=76):
            candidates.append((sc,title,url))
    candidates.sort(reverse=True)

    best_candidate=None
    verified=[]
    for _,title,url in candidates[:8]:
        p=parse_offer_page(session,url,brand,product)
        if not p: continue
        if best_candidate is None or (p.get("price_try") and not best_candidate.get("price_try")) or p["score"]>best_candidate["score"]:
            best_candidate=p
        if p.get("price_try") and p["score"]>=82:
            verified.append(p)

    if verified:
        direct_hosts={"boyner.com.tr","beymen.com","gratis.com","tr.oriflame.com","victoriassecret.com.tr","bathandbodyworks.com.tr"}
        direct=[x for x in verified if x.get("seller_name") in direct_hosts]
        pool=direct or verified
        p=min(pool,key=lambda x:(float(x.get("price_try") or 1e18),-float(x.get("score") or 0)))
        res.update(p)
        res["match_confidence"]=round(p["score"]/100,3)
        res["commerce_status"]="verified"
        return res

    if best_candidate and best_candidate["score"]>=78:
        res.update(best_candidate)
        res["match_confidence"]=round(best_candidate["score"]/100,3)
        res["commerce_status"]="candidate"
        return res
    if results and not candidates: res["commerce_status"]="search_results_no_candidate"
    elif results: res["commerce_status"]="candidate_pages_no_match"
    return res


# --- 2026-10-01 enrichment safety overrides ---
import unicodedata
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from image_sources import clean_source_url,first_image_url,fragrantica_image,generic_image,image_matches_product,page_image,parfumo_page_verified

COMMERCE_RETAILERS=[x.strip() for x in os.environ.get("COMMERCE_RETAILERS","boyner,beymen,gratis").split(",") if x.strip()]
SOURCE_PAGE_SCOPE=os.environ.get("SOURCE_PAGE_SCOPE","0")=="1"
HOST_MIN_INTERVAL=float(os.environ.get("HOST_MIN_INTERVAL","0.5"))
HOST_COOLDOWN=float(os.environ.get("HOST_COOLDOWN","20"))
HOST_BLOCK_LIMIT=int(os.environ.get("HOST_BLOCK_LIMIT","8"))
PRICE_MIN_TRY=float(os.environ.get("PRICE_MIN_TRY","20"))
PRICE_MAX_TRY=float(os.environ.get("PRICE_MAX_TRY","250000"))
HOST_DISABLED=set();_HOST_STATE={};_HOST_LOCK=threading.Lock();_TLS=threading.local()

_old_variant_compatible=variant_compatible
GENERIC_PRODUCT_TOKENS.discard("eau");GENERIC_PRODUCT_TOKENS.add("edc")
BRAND_NAME_TOKENS={"giorgio armani":{"ga"}}

def norm(s):
    s=html.unescape(str(s or "")).lower()
    s=s.replace("ı","i").replace("ş","s").replace("ğ","g").replace("ü","u").replace("ö","o").replace("ç","c")
    s=unicodedata.normalize("NFKD",s)
    s="".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",s)).strip()

def match_norm(s):
    t=norm(s)
    t=re.sub(r"(\d)\s*ml\b",r"\1 ml",t)
    repl=[
      ("eau de parfum","edp"),("eau de perfume","edp"),("eau de toilette","edt"),("eau de cologne","edc"),
      ("vucut ve sac parfum misti","body mist"),("sac ve vucut parfum misti","body mist"),("sac parfum misti","body mist"),
      ("vucut parfum misti","body mist"),("parfum misti","body mist"),("vucut misti","body mist"),("body misti","body mist"),
      ("vucut spreyi","body mist"),("body spray","body mist"),("fragrance mist","body mist"),("hair mist","body mist")
    ]
    for a,b in repl:t=t.replace(a,b)
    t=re.sub(r"\beau\s+(?=(?:de|du)\s+[a-z])","",t)
    return re.sub(r"\s+"," ",t).strip()

def variant_compatible(brand,product,candidate):
    cp=match_norm(candidate)
    for tok in BRAND_NAME_TOKENS.get(norm(brand),set()):
        cp=re.sub(rf"\b{re.escape(tok)}\b"," ",cp)
    return _old_variant_compatible(brand,product,re.sub(r"\s+"," ",cp).strip())

def make_session():
    s=requests.Session()
    retry=Retry(total=2,connect=2,read=2,status=2,backoff_factor=1.5,status_forcelist=(429,500,502,503,504),
                allowed_methods=frozenset(["GET","HEAD"]),respect_retry_after_header=False,raise_on_status=False)
    a=HTTPAdapter(max_retries=retry,pool_connections=16,pool_maxsize=16)
    s.mount("http://",a);s.mount("https://",a)
    s.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36",
                      "Accept-Language":"tr-TR,tr;q=0.9,en;q=0.8"})
    return s

def thread_session():
    s=getattr(_TLS,"session",None)
    if s is None:s=make_session();_TLS.session=s
    return s

def fetch(session,url,**kw):
    h=host(url)
    if not h:return None
    now=time.monotonic()
    with _HOST_LOCK:
        st=_HOST_STATE.setdefault(h,{"last":0.0,"until":0.0,"blocks":0})
        if h in HOST_DISABLED:return None
        if now<st["until"]:return None
        wait=max(0.0,HOST_MIN_INTERVAL-(now-st["last"]))
    if wait:time.sleep(wait)
    try:r=session.get(url,**kw)
    except Exception:return None
    blocked=r.status_code in (403,429) or "attention required" in r.text[:5000].lower() or "cloudflare" in r.text[:5000].lower()
    with _HOST_LOCK:
        st=_HOST_STATE.setdefault(h,{"last":0.0,"until":0.0,"blocks":0});st["last"]=time.monotonic()
        if blocked:
            st["blocks"]+=1
            st["until"]=time.monotonic()+min(600.0,HOST_COOLDOWN*(2**max(0,st["blocks"]-1)))
            print("HOST_PAUSED",h,r.status_code,st["blocks"],flush=True)
            if st["blocks"]>=HOST_BLOCK_LIMIT:
                HOST_DISABLED.add(h);print("HOST_DISABLED",h,flush=True)
        elif r.status_code<400:st["blocks"]=0
    return None if blocked else r

def source_is_shop_page(row):
    u=str(row.get("source_url") or "");h=host(u)
    if not h or h=="huggingface.co":return False
    if any(h==d or h.endswith("."+d) for d in INFO_DOMAINS):return False
    return True

def commerce_in_scope(row):
    return brand_in_tr_retail(row.get("brand_name","")) or (SOURCE_PAGE_SCOPE and source_is_shop_page(row))

def commerce_eligible(row):
    if COMMERCE_SCOPE=="all":return True
    if COMMERCE_SCOPE=="off":return False
    return commerce_in_scope(row)

def load_rows():
    products=[];source={}
    for p in sorted(glob.glob("data/source_urls/part_*.csv")):
        with open(p,encoding="utf-8-sig",newline="") as f:
            for r in csv.DictReader(f):
                if r.get("source_url"):source[str(r.get("id",""))]=r["source_url"]
    for p in sorted(glob.glob("data/master_manifest_174259/part_*.csv*")):
        opener=gzip.open if str(p).endswith(".gz") else open
        with opener(p,mode="rt",encoding="utf-8-sig",newline="") as f:products.extend(csv.DictReader(f))
    shard=[r for i,r in enumerate(products) if i%SHARD_COUNT==SHARD_INDEX]
    for r in shard:r["source_url"]=clean_source_url(source.get(str(r.get("id",""))) or r.get("source_url",""),r.get("id",""))
    return shard

def extract_static(session,row):
    url=row.get("source_url") or "";h=host(url)
    res={"release_year_candidate":"","image_url_candidate":"","notes_candidate":"","static_status":"no_source","static_http":"","static_source":url}
    if not url:return res
    if h=="huggingface.co":
        res["static_status"]="hf_archive";return res
    if h=="fragrantica.com":
        im=fragrantica_image(url)
        if im:res["image_url_candidate"]=im
    r=fetch(session,url,timeout=18,allow_redirects=True)
    if r is None:
        res["static_status"]="http_error" if not res["image_url_candidate"] else "ok";return res
    res["static_http"]=str(r.status_code)
    if r.status_code!=200 or "text/html" not in r.headers.get("content-type",""):
        res["static_status"]="http_error" if not res["image_url_candidate"] else "ok";return res
    soup=BeautifulSoup(r.text,"lxml")
    if h=="parfumo.com" and not parfumo_page_verified(soup,row.get("brand_name",""),row.get("product_name","")):
        res["static_status"]="parfumo_unverified";return res
    if not res["image_url_candidate"]:
        res["image_url_candidate"]=page_image(soup,r.url,row.get("brand_name",""),row.get("product_name",""))
    objs=parse_jsonld(soup)
    shop=source_is_shop_page(row)
    if not row.get("release_year") and not shop:
        for o in objs:
            for k in ("releaseDate",):
                if o.get(k):
                    m=re.search(r"\b(17\d{2}|18\d{2}|19\d{2}|20[0-2]\d)\b",str(o[k]))
                    if m:res["release_year_candidate"]=m.group(1);break
            if res["release_year_candidate"]:break
    text=soup.get_text(" ",strip=True)
    if not row.get("release_year") and not res["release_year_candidate"] and not shop:
        for pat in (r"(?:launched|released|introduced|created)\s+(?:in\s+)?(17\d{2}|18\d{2}|19\d{2}|20[0-2]\d)",
                    r"(17\d{2}|18\d{2}|19\d{2}|20[0-2]\d)\s+(?:yılında|yilinda)"):
            m=re.search(pat,text[:25000],re.I)
            if m:res["release_year_candidate"]=m.group(1);break
    flat=" ".join(text.split());sections=[]
    for a,b in [("Top Notes","Middle Notes"),("Middle Notes","Base Notes"),("Base Notes","Perfume rating"),("Üst Notalar","Orta Notalar"),("Orta Notalar","Alt Notalar")]:
        m=re.search(re.escape(a)+r"\s*[:\-]?\s*(.{3,500}?)\s*"+re.escape(b),flat,re.I)
        if m:sections.append(f"{a}: {m.group(1).strip()}")
    if sections:res["notes_candidate"]=" | ".join(sections)[:1600]
    res["static_source"]=r.url
    res["static_status"]="ok" if (res["image_url_candidate"] or res["release_year_candidate"] or res["notes_candidate"]) else "page_no_extract"
    return res

def slug_title(url):
    try:s=urllib.parse.unquote(urllib.parse.urlparse(url).path.rsplit("/",1)[-1])
    except Exception:s=""
    s=re.sub(r"^(?:p_|p-)|[_-]\d{5,}$"," ",s)
    return re.sub(r"\s+"," ",re.sub(r"[_-]+"," ",s)).strip()

def link_title(a,url):
    t=" ".join(a.get_text(" ",strip=True).split())
    if t:return t
    for k in ("title","aria-label"):
        if a.get(k):return " ".join(str(a.get(k)).split())
    im=a.find("img")
    if im and im.get("alt"):return " ".join(str(im.get("alt")).split())
    return slug_title(url)

def retailer_search(session,brand,product,search_url,params,path_test,threshold=58):
    r=fetch(session,search_url,params=params,timeout=20,allow_redirects=True)
    if r is None or r.status_code!=200 or "text/html" not in r.headers.get("content-type",""):return []
    soup=BeautifulSoup(r.text,"lxml");out=[];seen=set()
    for a in soup.find_all("a",href=True):
        href=a.get("href","")
        if not path_test(href):continue
        url=urllib.parse.urljoin(r.url,href)
        if url in seen:continue
        seen.add(url);title=link_title(a,url)
        if not title:continue
        st=slug_title(url)
        if not brand_compatible(brand,title) and brand_compatible(brand,st):title=f"{brand} {title}"
        score=product_match_score(brand,product,title)
        if any(b in norm(title) for b in BAD) and not any(b in norm(product) for b in BAD):score-=30
        if score>=threshold and brand_compatible(brand,title) and variant_compatible(brand,product,title):out.append((score,title,url))
    out.sort(reverse=True);return [(t,u) for _,t,u in out[:8]]

def boyner_search(session,brand,product):
    return retailer_search(session,brand,product,"https://www.boyner.com.tr/search",{"q":f"{brand} {product}"},lambda x:"-p-" in x or "/p_" in x)

def beymen_search(session,brand,product):
    return retailer_search(session,brand,product,"https://www.beymen.com/tr/search",{"q":f"{brand} {product}"},lambda x:"/tr/p_" in x)

def gratis_search(session,brand,product):
    return retailer_search(session,brand,product,"https://www.gratis.com/search",{"q":f"{brand} {product}"},lambda x:"-p-" in x)

def n11_search(session,brand,product):
    return retailer_search(session,brand,product,"https://www.n11.com/arama",{"q":f"{brand} {product}"},lambda x:"/urun/" in x,70)

RETAILER_SEARCH={"boyner":boyner_search,"beymen":beymen_search,"gratis":gratis_search,"n11":n11_search}

def parse_try_price(value):
    if value is None:return None
    s=str(value).strip().replace("\xa0"," ").replace("₺","").replace("TRY","").replace("TL","")
    m=re.search(r"\d[\d .]*(?:,\d{1,2})?",s)
    if not m:return None
    raw=m.group(0).replace(" ","")
    if "," in raw:raw=raw.replace(".","").replace(",",".")
    elif raw.count(".")==1 and len(raw.rsplit(".",1)[1])==3:raw=raw.replace(".","")
    elif raw.count(".")>1:raw=raw.replace(".","")
    try:p=float(raw)
    except Exception:return None
    return p if PRICE_MIN_TRY<=p<=PRICE_MAX_TRY else None

def visible_price(flat,anchor=""):
    text=" ".join(str(flat or "").split());start=0
    if anchor:
        i=norm(text).find(norm(anchor))
        if i>=0:start=i
    scan=text[start:start+7000]
    pat=re.compile(r"(?:₺\s*)?(\d{1,3}(?:[ .]\d{3})+|\d{2,6})(?:[,.](\d{1,2}))?\s*(?:TRY|TL|₺)",re.I)
    for m in pat.finditer(scan):
        ctx=scan[max(0,m.start()-45):min(len(scan),m.end()+55)].lower()
        if re.search(r"\b\d+\s*x\s*",ctx) or any(x in ctx for x in ("üzeri","uzeri","alışveriş","alisveris","kupon","puan","kazan")):continue
        raw=m.group(1)+((","+m.group(2)) if m.group(2) else "")
        p=parse_try_price(raw)
        if p:return p
    return None

def volume_ml(*texts):
    for text in texts:
        m=re.search(r"(?<!\d)(\d{1,4}(?:[.,]\d+)?)\s*ml\b",str(text or ""),re.I)
        if m:
            try:return float(m.group(1).replace(",","."))
            except Exception:pass
    return ""

def tr_priced_host(h):
    h=str(h or "").lower()
    return h.endswith(".tr") or h.endswith(".com.tr") or any(h==x or h.endswith("."+x) for x in TR_SELLERS)

def _offer_price(off):
    v=off.get("price") or off.get("lowPrice")
    ps=off.get("priceSpecification")
    if v is None and isinstance(ps,dict):v=ps.get("price") or ps.get("lowPrice")
    return parse_try_price(v)

def _offer_stock(off):
    a=str(off.get("availability") or "").lower()
    if "instock" in a:return "in_stock"
    if "outofstock" in a:return "out_of_stock"
    return "unknown"

def _meta_content(soup,*keys):
    for key in keys:
        m=soup.find("meta",attrs={"property":key}) or soup.find("meta",attrs={"name":key})
        if m and m.get("content"):return m.get("content")
    return ""

STOCK_RANK={"in_stock":0,"unknown":1,"out_of_stock":2}

def parse_offer_page(session,url,brand,product,trusted=False):
    r=fetch(session,url,timeout=18,allow_redirects=True)
    if r is None or r.status_code!=200 or "text/html" not in r.headers.get("content-type",""):return None
    soup=BeautifulSoup(r.text,"lxml");objs=parse_jsonld(soup);title=soup.title.get_text(" ",strip=True) if soup.title else ""
    products=[o for o in objs if o.get("@type")=="Product" or (isinstance(o.get("@type"),list) and "Product" in o.get("@type"))]
    if trusted:
        ogt=_meta_content(soup,"og:type").lower()
        trusted=host(r.url)==host(url) and (bool(products) or ogt=="product")
    best=None
    for o in products:
        name=o.get("name") or title
        full=f"{name} {title} {slug_title(r.url)}"
        if not brand_compatible(brand,full) or not variant_compatible(brand,product,name):continue
        score=product_match_score(brand,product,name);offers=o.get("offers")
        offers=offers if isinstance(offers,list) else [offers] if isinstance(offers,dict) else [{}]
        im=first_image_url(o.get("image"))
        for off in offers:
            cur=str(off.get("priceCurrency") or "").upper()
            price=_offer_price(off)
            if price is not None and cur not in ("TRY","TL","₺") and not (not cur and tr_priced_host(host(r.url))):price=None
            rec={"score":min(100,score),"price_try":price,"currency":"TRY","purchase_url":urllib.parse.urljoin(r.url,str(off.get("url"))) if off.get("url") else r.url,
                 "seller_name":host(r.url),"stock_status":_offer_stock(off),"commerce_image":urllib.parse.urljoin(r.url,im) if im else page_image(soup,r.url,brand,product),
                 "source_product_name":name}
            if best is None or (STOCK_RANK.get(rec["stock_status"],1),rec["price_try"] or 1e18,-rec["score"])<(STOCK_RANK.get(best["stock_status"],1),best["price_try"] or 1e18,-best["score"]):best=rec
    if best is None:
        name=title;full=f"{title} {slug_title(r.url)}"
        if brand_compatible(brand,full) and variant_compatible(brand,product,name):
            score=product_match_score(brand,product,name)
            cur=_meta_content(soup,"product:price:currency","og:price:currency").upper()
            price=parse_try_price(_meta_content(soup,"product:price:amount","og:price:amount"))
            if price is not None and cur not in ("TRY","TL","₺") and not (not cur and tr_priced_host(host(r.url))):price=None
            if price is None and (trusted or tr_priced_host(host(r.url))):price=visible_price(soup.get_text(" ",strip=True),title)
            if price is not None:
                best={"score":min(100,score),"price_try":price,"currency":"TRY","purchase_url":r.url,"seller_name":host(r.url),
                      "stock_status":"unknown","commerce_image":page_image(soup,r.url,brand,product),"source_product_name":name}
    if best is None:return None
    best["volume_ml"]=volume_ml(product,r.url,title)
    return best

def extract_commerce(session,row):
    brand=row["brand_name"];product=row["product_name"]
    if not commerce_eligible(row):
        return {"commerce_status":"skipped_non_tr_brand","price_try":"","currency":"TRY","volume_ml":"","seller_name":"","purchase_url":"","stock_status":"unknown","commerce_image":"","match_confidence":"","source_product_name":""}
    res={"commerce_status":"not_found","price_try":"","currency":"TRY","volume_ml":"","seller_name":"","purchase_url":"","stock_status":"unknown","commerce_image":"","match_confidence":"","source_product_name":""}
    indexed=OFFICIAL_PRICE_INDEX.get(str(row.get("id") or ""))
    if indexed:
        p=parse_try_price(indexed.get("price_try"))
        return {"commerce_status":"verified","price_try":p or indexed.get("price_try") or "","currency":indexed.get("currency") or "TRY",
                "volume_ml":volume_ml(indexed.get("volume_ml")) or indexed.get("volume_ml") or "","seller_name":indexed.get("seller_name") or "",
                "purchase_url":indexed.get("purchase_url") or "","stock_status":"unknown","commerce_image":"","match_confidence":float(indexed.get("match_confidence") or 1.0),
                "source_product_name":indexed.get("source_product_name") or product}
    official=official_catalog_offer(session,brand,product)
    if official:
        res.update(official);res["match_confidence"]=round(official["score"]/100,3);res["commerce_status"]="verified";return res
    if source_is_shop_page(row):
        p=parse_offer_page(session,row.get("source_url",""),brand,product,trusted=True)
        if p:
            res.update(p);res["match_confidence"]=round(p["score"]/100,3)
            res["commerce_status"]="verified" if p.get("price_try") and p.get("stock_status")!="out_of_stock" and p["score"]>=82 else "candidate"
            if res["commerce_status"]=="verified":return res
    results=[];seen=set()
    for retailer in COMMERCE_RETAILERS:
        fn=RETAILER_SEARCH.get(retailer)
        if not fn:continue
        for title,url in fn(session,brand,product):
            if url not in seen:seen.add(url);results.append((title,url))
    if SEARCH_ENGINE_FALLBACK:
        for q in (f'"{brand}" "{product}" fiyat TRY',f'"{brand}" "{product}" Türkiye parfüm'):
            for title,url in search_web(session,q):
                if url not in seen:seen.add(url);results.append((title,url))
            if len(results)>=12:break
    candidates=[]
    for title,url in results:
        h=host(url)
        if any(h==d or h.endswith("."+d) for d in INFO_DOMAINS):continue
        sc=product_match_score(brand,product,title)
        if any(b in norm(title) for b in BAD) and not any(b in norm(product) for b in BAD):sc-=30
        if sc>=58 and brand_compatible(brand,f"{title} {slug_title(url)}") and variant_compatible(brand,product,title):candidates.append((sc,title,url))
    verified=[];best_candidate=None
    for _,title,url in sorted(candidates,reverse=True)[:8]:
        p=parse_offer_page(session,url,brand,product)
        if not p:continue
        if best_candidate is None or (STOCK_RANK.get(p.get("stock_status"),1),p.get("price_try") or 1e18,-p.get("score",0))<(STOCK_RANK.get(best_candidate.get("stock_status"),1),best_candidate.get("price_try") or 1e18,-best_candidate.get("score",0)):best_candidate=p
        if p.get("price_try") and p.get("score",0)>=82:verified.append(p)
    if verified:
        p=min(verified,key=lambda x:(STOCK_RANK.get(x.get("stock_status"),1),float(x.get("price_try") or 1e18),-float(x.get("score") or 0)))
        res.update(p);res["match_confidence"]=round(p["score"]/100,3);res["commerce_status"]="verified";return res
    if best_candidate and best_candidate.get("score",0)>=78:
        res.update(best_candidate);res["match_confidence"]=round(best_candidate["score"]/100,3);res["commerce_status"]="candidate";return res
    if results and not candidates:res["commerce_status"]="search_results_no_candidate"
    elif results:res["commerce_status"]="candidate_pages_no_match"
    return res


def process(row):
    s=thread_session()
    base={"product_id":row["id"],"brand_name":row["brand_name"],"product_name":row["product_name"],
          "existing_release_year":row.get("release_year",""),"checked_at":datetime.now(timezone.utc).isoformat()}
    static=extract_static(s,row)
    # modest jitter reduces synchronized bursts across shards
    time.sleep(random.uniform(0.05,0.18))
    commerce=extract_commerce(s,row)
    base.update(static); base.update(commerce)
    if not base.get("image_url_candidate") and base.get("commerce_image"):
        base["image_url_candidate"]=base["commerce_image"]
        base["image_source_url"]=base.get("purchase_url","")
    else:
        base["image_source_url"]=base.get("static_source","")
    return base

COLS=["product_id","brand_name","product_name","existing_release_year","release_year_candidate","notes_candidate",
      "image_url_candidate","image_source_url","static_status","static_http","static_source","commerce_status",
      "volume_ml","price_try","currency","seller_name","purchase_url","stock_status","commerce_image",
      "match_confidence","source_product_name","checked_at","static_error"]

def save(rows,total,start_time):
    rows=sorted(rows,key=lambda x:int(x["product_id"]))
    with OUTCSV.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=COLS,extrasaction="ignore"); w.writeheader()
        for r in rows: w.writerow(r)
    summary={
      "shard_index":SHARD_INDEX,"shard_count":SHARD_COUNT,"assigned":total,"processed":len(rows),
      "remaining":max(0,total-len(rows)),
      "with_image":sum(bool(r.get("image_url_candidate")) for r in rows),
      "with_year_candidate":sum(bool(r.get("release_year_candidate")) for r in rows),
      "with_notes_candidate":sum(bool(r.get("notes_candidate")) for r in rows),
      "with_price":sum(bool(r.get("price_try")) for r in rows),
      "with_purchase_url":sum(bool(r.get("purchase_url")) for r in rows),
      "seconds":round(time.time()-start_time,1),"generated_at":datetime.now(timezone.utc).isoformat()
    }
    OUTJSON.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    return summary

def main():
    items=load_rows(); total=len(items); start=time.time(); done=[]
    # Submit bounded batches so the script can stop cleanly before GitHub's job timeout.
    idx=0
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        while idx<total and time.time()-start < MAX_SECONDS-120:
            batch=items[idx:idx+WORKERS*4]; idx+=len(batch)
            futs=[ex.submit(process,r) for r in batch]
            for fut in as_completed(futs):
                try: done.append(fut.result())
                except Exception as e:
                    done.append({"product_id":"0","brand_name":"","product_name":"","static_status":"worker_error","commerce_status":"worker_error",
                                 "checked_at":datetime.now(timezone.utc).isoformat(),"static_error":str(e)[:180]})
            if len(done)%100 < WORKERS*4:
                sm=save(done,total,start)
                print("CHECKPOINT",json.dumps(sm,ensure_ascii=False),flush=True)
    print("FINAL",json.dumps(save(done,total,start),ensure_ascii=False),flush=True)

if __name__=="__main__": main()
