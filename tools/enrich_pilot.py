#!/usr/bin/env python3
import csv, json, os, re, sqlite3, time, random, html, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz

INPUT = Path("data/pilot_1000_input.csv")
OUTDIR = Path("artifacts")
OUTDIR.mkdir(exist_ok=True)
CSV_OUT = OUTDIR / "pilot_1000_enriched.csv"
DB_OUT = OUTDIR / "pilot_1000_enriched.sqlite"
SUMMARY_OUT = OUTDIR / "pilot_1000_summary.json"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36"
HEADERS = {"User-Agent": UA, "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8"}

TRUSTED = [
    "dior.com","chanel.com","giorgioarmanibeauty.com","yslbeauty.com","carolinaherrera.com",
    "givenchybeauty.com","lancome.com.tr","jeanpaulgaultier.com","calvinklein.com.tr","hugoboss.com",
    "bulgari.com","mugler.com","kenzoparfums.com","esteelauder.com.tr","jomalone.com.tr","tomfordbeauty.com",
    "versace.com","dolcegabbana.com","gucci.com","prada.com","burberry.com","valentino-beauty.com",
    "hermes.com","rabanne.com","narcisorodriguezparfums.com","zara.com","victoriassecret.com.tr",
    "bathandbodyworks.com.tr","avon.com.tr","yvesrocher.com.tr","oriflame.com","thebodyshop.com.tr",
    "lush.com.tr","sephora.com.tr","boyner.com.tr","beymen.com","sevil.com.tr","rossmann.com.tr",
    "watsons.com.tr","gratis.com","trendyol.com","hepsiburada.com","amazon.com.tr","n11.com"
]
BAD = ["tester","sample","numune","dekant","decant","muadil","benzeri","açık parfüm","acik parfum","esans"]

session = requests.Session()
session.headers.update(HEADERS)

def norm(s):
    s = html.unescape(str(s or "")).lower()
    s = s.replace("ı","i").replace("ş","s").replace("ğ","g").replace("ü","u").replace("ö","o").replace("ç","c")
    s = re.sub(r"[^a-z0-9]+"," ",s)
    return re.sub(r"\s+"," ",s).strip()

def host(url):
    try:
        h = urllib.parse.urlparse(url).netloc.lower().split(":")[0]
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""

def unwrap_ddg(url):
    try:
        p = urllib.parse.urlparse(url)
        q = urllib.parse.parse_qs(p.query)
        if "uddg" in q: return q["uddg"][0]
    except Exception:
        pass
    return url

def search_ddg(query, limit=8):
    try:
        r = session.get("https://html.duckduckgo.com/html/", params={"q":query,"kl":"tr-tr"}, timeout=18)
        if r.status_code != 200: return []
        s = BeautifulSoup(r.text,"lxml")
        out=[]
        for a in s.select("a.result__a"):
            u=unwrap_ddg(a.get("href",""))
            t=a.get_text(" ",strip=True)
            if u.startswith("http"):
                out.append((t,u))
            if len(out)>=limit: break
        return out
    except Exception:
        return []

def search_bing(query, limit=8):
    try:
        r = session.get("https://www.bing.com/search", params={"q":query,"cc":"tr","setlang":"tr"}, timeout=18)
        if r.status_code != 200: return []
        s=BeautifulSoup(r.text,"lxml")
        out=[]
        for a in s.select("li.b_algo h2 a"):
            u=a.get("href",""); t=a.get_text(" ",strip=True)
            if u.startswith("http"): out.append((t,u))
            if len(out)>=limit: break
        return out
    except Exception:
        return []

def recursively_products(obj):
    found=[]
    if isinstance(obj, dict):
        typ=obj.get("@type")
        if typ=="Product" or (isinstance(typ,list) and "Product" in typ): found.append(obj)
        for v in obj.values(): found.extend(recursively_products(v))
    elif isinstance(obj,list):
        for v in obj: found.extend(recursively_products(v))
    return found

def first_offer_price(offers):
    if isinstance(offers,list):
        for o in offers:
            x=first_offer_price(o)
            if x: return x
        return None
    if not isinstance(offers,dict): return None
    p=offers.get("price") or offers.get("lowPrice")
    cur=offers.get("priceCurrency")
    av=offers.get("availability")
    url=offers.get("url")
    try:
        if p is not None:
            raw=str(p).strip()
            if re.search(r"\d+\.\d{3},\d",raw):
                raw=raw.replace(".","").replace(",",".")
            else:
                raw=raw.replace(",",".")
            return float(re.sub(r"[^0-9.]","",raw)), cur, av, url
    except Exception:
        pass
    return None

def extract_page(url):
    try:
        r=session.get(url,timeout=20,allow_redirects=True)
        if r.status_code!=200 or "text/html" not in r.headers.get("content-type",""):
            return None
        final=r.url
        s=BeautifulSoup(r.text,"lxml")
        title=(s.title.get_text(" ",strip=True) if s.title else "")
        ogimg=s.find("meta",attrs={"property":"og:image"}) or s.find("meta",attrs={"name":"twitter:image"})
        ogimage=ogimg.get("content") if ogimg else None
        ogprice=s.find("meta",attrs={"property":"product:price:amount"})
        ogcur=s.find("meta",attrs={"property":"product:price:currency"})
        products=[]
        for tag in s.find_all("script",attrs={"type":"application/ld+json"}):
            try:
                products.extend(recursively_products(json.loads(tag.get_text(strip=True))))
            except Exception:
                continue
        cand=[]
        for p in products:
            name=p.get("name") or title
            image=p.get("image")
            if isinstance(image,list): image=image[0] if image else None
            if isinstance(image,dict): image=image.get("url") or image.get("contentUrl")
            op=first_offer_price(p.get("offers"))
            price=currency=availability=offerurl=None
            if op: price,currency,availability,offerurl=op
            cand.append({"name":name,"image":image or ogimage,"price":price,"currency":currency,"availability":availability,"offer_url":offerurl})
        if not cand:
            price=None
            if ogprice:
                try: price=float(str(ogprice.get("content")).replace(",","."))
                except Exception: pass
            cand=[{"name":title,"image":ogimage,"price":price,"currency":ogcur.get("content") if ogcur else None,"availability":None,"offer_url":None}]
        text=s.get_text(" ",strip=True)
        return {"url":final,"title":title,"products":cand,"text":text[:120000]}
    except Exception:
        return None

def score_candidate(brand, product, year, search_title, page, prod):
    target=norm(f"{brand} {product}")
    name=norm(prod.get("name") or page.get("title") or search_title)
    score=0.65*fuzz.token_set_ratio(target,name)+0.35*fuzz.ratio(target,name)
    brandn=norm(brand)
    if brandn and brandn in name: score+=8
    phost=host(page["url"])
    if any(phost==d or phost.endswith("."+d) for d in TRUSTED): score+=6
    original=norm(product)
    badname=" ".join([name,norm(page.get("title"))])
    if not any(b in original for b in BAD) and any(b in badname for b in BAD): score-=25
    if year and str(year) in (prod.get("name") or ""): score+=3
    return max(0,min(100,score))

def parse_volume(text):
    vals=[]
    for m in re.finditer(r"(?<!\d)(\d{1,4}(?:[.,]\d+)?)\s*m[lL]\b",text or ""):
        try:
            v=float(m.group(1).replace(",","."))
            if 1<=v<=1000: vals.append(v)
        except Exception: pass
    if not vals: return None
    return int(vals[0]) if vals[0].is_integer() else vals[0]

def enrich(row):
    brand=row["brand_name"]; product=row["product_name"]; year=row.get("release_year") or ""
    query=f'"{brand}" "{product}" parfüm Türkiye fiyat'
    results=search_ddg(query,8)
    if len(results)<3:
        results += search_bing(query,8)
    seen=set(); ranked=[]
    for t,u in results:
        h=host(u)
        if not h or u in seen: continue
        seen.add(u)
        pri=1 if any(h==d or h.endswith("."+d) for d in TRUSTED) else 0
        ranked.append((pri,t,u))
    ranked.sort(key=lambda x:x[0],reverse=True)
    best=None
    for _, st, url in ranked[:6]:
        page=extract_page(url)
        if not page: continue
        for prod in page["products"][:5]:
            sc=score_candidate(brand,product,year,st,page,prod)
            cur=prod.get("currency")
            price=prod.get("price") if cur in (None,"TRY","TL","₺") else None
            rec={"score":sc,"source_page":page["url"],"product_name_found":prod.get("name") or page["title"],
                 "price_try":price,"currency":cur or ("TRY" if price else None),
                 "image_url":prod.get("image"),"purchase_url":prod.get("offer_url") or page["url"],
                 "availability_raw":prod.get("availability"),"seller_domain":host(page["url"]),
                 "volume_ml":parse_volume(" ".join([str(prod.get("name") or ""), page.get("text","")[:8000]]))}
            if best is None or rec["score"]>best["score"] or (rec["score"]==best["score"] and rec["price_try"] and not best["price_try"]):
                best=rec
        if best and best["score"]>=90 and best["price_try"] and best["image_url"]:
            break
        time.sleep(random.uniform(0.10,0.30))
    base=dict(row)
    checked=datetime.now(timezone.utc).isoformat()
    if best and best["score"]>=72:
        av=str(best.get("availability_raw") or "").lower()
        stock="in_stock" if "instock" in av else ("out_of_stock" if "outofstock" in av else "unknown")
        complete=bool(best.get("price_try") and best.get("purchase_url") and best.get("image_url"))
        status="verified_complete" if complete and best["score"]>=85 else "partial_candidate"
        base.update({
            "volume_ml":best.get("volume_ml"),"price_try":best.get("price_try"),"currency":best.get("currency") or "TRY",
            "seller_name":best.get("seller_domain"),"purchase_url":best.get("purchase_url"),"image_url":best.get("image_url"),
            "stock_status":stock,"checked_at":checked,"match_confidence":round(best["score"]/100,3),
            "enrichment_status":status,"source_page":best.get("source_page"),"product_name_found":best.get("product_name_found")
        })
    else:
        base.update({"volume_ml":None,"price_try":None,"currency":"TRY","seller_name":None,"purchase_url":None,"image_url":None,
                     "stock_status":"unknown","checked_at":checked,"match_confidence":round((best["score"]/100),3) if best else 0,
                     "enrichment_status":"not_found_or_low_confidence","source_page":best.get("source_page") if best else None,
                     "product_name_found":best.get("product_name_found") if best else None})
    return base

def save(rows):
    cols=["pilot_id","master_product_id","brand_name","product_name","release_year","volume_ml","price_try","currency",
          "seller_name","purchase_url","image_url","stock_status","checked_at","match_confidence","enrichment_status",
          "source_page","product_name_found"]
    rows=sorted(rows,key=lambda x:int(x["pilot_id"]))
    with CSV_OUT.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
        for r in rows: w.writerow({k:r.get(k) for k in cols})
    if DB_OUT.exists(): DB_OUT.unlink()
    db=sqlite3.connect(DB_OUT)
    db.execute("""CREATE TABLE pilot_products(
      pilot_id INTEGER PRIMARY KEY, master_product_id INTEGER, brand_name TEXT, product_name TEXT, release_year TEXT,
      volume_ml REAL, price_try REAL, currency TEXT, seller_name TEXT, purchase_url TEXT, image_url TEXT,
      stock_status TEXT, checked_at TEXT, match_confidence REAL, enrichment_status TEXT, source_page TEXT, product_name_found TEXT)""")
    db.executemany("INSERT INTO pilot_products VALUES("+",".join(["?"]*len(cols))+")", [[r.get(k) for k in cols] for r in rows])
    db.commit(); db.close()
    counts={}
    for r in rows: counts[r["enrichment_status"]]=counts.get(r["enrichment_status"],0)+1
    summary={"total":len(rows),"statuses":counts,
             "with_price":sum(bool(r.get("price_try")) for r in rows),
             "with_image":sum(bool(r.get("image_url")) for r in rows),
             "with_purchase_url":sum(bool(r.get("purchase_url")) for r in rows),
             "generated_at":datetime.now(timezone.utc).isoformat()}
    SUMMARY_OUT.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    return summary

def main():
    with INPUT.open(encoding="utf-8-sig") as f: items=list(csv.DictReader(f))
    lim=int(os.environ.get("PILOT_LIMIT","0") or 0)
    if lim: items=items[:lim]
    done=[]
    workers=int(os.environ.get("WORKERS","6"))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures={ex.submit(enrich,r):r for r in items}
        for i,fut in enumerate(as_completed(futures),1):
            r=futures[fut]
            try: done.append(fut.result())
            except Exception as e:
                x=dict(r); x.update({"currency":"TRY","stock_status":"unknown","checked_at":datetime.now(timezone.utc).isoformat(),
                    "match_confidence":0,"enrichment_status":"error","source_page":None,"product_name_found":str(e)})
                done.append(x)
            if i%25==0 or i==len(items):
                s=save(done)
                print(f"PROGRESS {i}/{len(items)} {s}",flush=True)
    print(json.dumps(save(done),ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
