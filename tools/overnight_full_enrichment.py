#!/usr/bin/env python3
import csv, glob, gzip, html, json, os, re, time, random, sqlite3, urllib.parse
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

def norm(s):
    s=html.unescape(str(s or "")).lower()
    s=s.replace("ı","i").replace("ş","s").replace("ğ","g").replace("ü","u").replace("ö","o").replace("ç","c")
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",s)).strip()

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
    for r in shard: r["source_url"]=source.get(r["id"],"")
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
        for a in soup.select("a.result__a"):
            u=a.get("href",""); t=a.get_text(" ",strip=True)
            try:
                p=urllib.parse.urlparse(u); qs=urllib.parse.parse_qs(p.query)
                if "uddg" in qs: u=qs["uddg"][0]
            except: pass
            if u.startswith("http"): out.append((t,u))
            if len(out)>=8: break
        return out
    except: return []

def parse_offer_page(session,url,brand,product):
    try:
        r=session.get(url,timeout=18,allow_redirects=True)
        if r.status_code!=200 or "text/html" not in r.headers.get("content-type",""): return None
        soup=BeautifulSoup(r.text,"lxml"); objs=parse_jsonld(soup)
        title=soup.title.get_text(" ",strip=True) if soup.title else ""
        best=None
        for o in objs:
            typ=o.get("@type")
            if not (typ=="Product" or (isinstance(typ,list) and "Product" in typ)): continue
            name=o.get("name") or title
            score=.65*fuzz.token_set_ratio(norm(f"{brand} {product}"),norm(name))+.35*fuzz.ratio(norm(f"{brand} {product}"),norm(name))
            if norm(brand) in norm(name): score+=8
            offers=o.get("offers"); offers=offers if isinstance(offers,list) else [offers] if isinstance(offers,dict) else []
            im=o.get("image")
            if isinstance(im,list): im=im[0] if im else ""
            if isinstance(im,dict): im=im.get("url") or im.get("contentUrl") or ""
            for off in offers or [{}]:
                price=off.get("price") or off.get("lowPrice")
                cur=off.get("priceCurrency") or "TRY"
                try:
                    if price is not None:
                        raw=str(price).strip()
                        if re.search(r"\d+\.\d{3},\d",raw): raw=raw.replace(".","").replace(",",".")
                        else: raw=raw.replace(",",".")
                        price=float(re.sub(r"[^0-9.]","",raw))
                except: price=None
                if cur not in ("TRY","TL","₺",None): price=None
                rec={"score":min(100,score),"price_try":price,"currency":"TRY","purchase_url":off.get("url") or r.url,
                     "seller_name":host(r.url),"stock_status":"in_stock" if "instock" in str(off.get("availability","")).lower() else
                     ("out_of_stock" if "outofstock" in str(off.get("availability","")).lower() else "unknown"),
                     "commerce_image":urllib.parse.urljoin(r.url,str(im)) if im else "","source_product_name":name}
                if best is None or rec["score"]>best["score"] or (rec["score"]==best["score"] and rec["price_try"] and not best["price_try"]): best=rec
        if best is None:
            return None
        text=soup.get_text(" ",strip=True)
        m=re.search(r"(?<!\d)(\d{1,4}(?:[.,]\d+)?)\s*ml\b",text,re.I)
        if m:
            try: best["volume_ml"]=float(m.group(1).replace(",","."))
            except: pass
        return best
    except: return None

def extract_commerce(session,row):
    brand=row["brand_name"]; product=row["product_name"]
    res={"commerce_status":"not_found","price_try":"","currency":"TRY","volume_ml":"","seller_name":"",
         "purchase_url":"","stock_status":"unknown","commerce_image":"","match_confidence":""}
    # Current products first. Very old products still get searched, but exact-match threshold remains strict.
    q=f'"{brand}" "{product}" parfüm Türkiye'
    results=ddg(session,q)
    candidates=[]
    for title,url in results:
        h=host(url)
        if any(h==d or h.endswith("."+d) for d in TR_SELLERS):
            sc=fuzz.token_set_ratio(norm(f"{brand} {product}"),norm(title))
            if any(b in norm(title) for b in BAD) and not any(b in norm(product) for b in BAD): sc-=30
            candidates.append((sc,title,url))
    candidates.sort(reverse=True)
    for _,title,url in candidates[:2]:
        p=parse_offer_page(session,url,brand,product)
        if p and p["score"]>=78:
            res.update(p)
            res["match_confidence"]=round(p["score"]/100,3)
            res["commerce_status"]="verified" if p.get("price_try") and p["score"]>=86 else "candidate"
            return res
    if results and not candidates: res["commerce_status"]="no_trusted_seller_result"
    return res

def process(row):
    s=make_session()
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
