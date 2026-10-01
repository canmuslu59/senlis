#!/usr/bin/env python3
import csv,glob,gzip,json,re,sys,requests
from pathlib import Path
from datetime import datetime,timezone

sys.path.insert(0,str(Path(__file__).resolve().parent))
import overnight_full_enrichment as core

OUT=Path("loris_price_index"); OUT.mkdir(exist_ok=True)

def canon_code(s):
    m=re.search(r"(?i)(?:^|\b)([EKU])\s*-\s*0*(\d{1,3})(?:\b|\s)",str(s or ""))
    return f"{m.group(1).upper()}-{int(m.group(2))}" if m else ""

def load_master():
    out=[]
    for p in sorted(glob.glob("data/master_manifest_174259/part_*.csv*")):
        opener=gzip.open if p.endswith(".gz") else open
        with opener(p,"rt",encoding="utf-8-sig",newline="") as f:
            for r in csv.DictReader(f):
                if core.norm(r.get("brand_name",""))=="loris": out.append(r)
    return out

def fetch_catalog():
    s=requests.Session()
    s.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36",
                      "Accept-Language":"tr-TR,tr;q=0.9,en;q=0.8","Accept":"application/json"})
    products=[]
    for page in range(1,8):
        r=s.get("https://lorisparfum.com/products.json",params={"limit":250,"page":page},timeout=35)
        r.raise_for_status()
        js=r.json(); batch=js.get("products",[])
        if not batch: break
        products.extend(batch)
        if len(batch)<250: break
    return products

def price_of(p):
    variants=p.get("variants") or []
    vals=[]
    for v in variants:
        try:
            price=float(v.get("price"))
        except: continue
        if price>0:
            vals.append((0 if v.get("available") else 1,price,v))
    if not vals: return None,"unknown"
    vals.sort(key=lambda x:(x[0],x[1]))
    _,price,v=vals[0]
    return price,("in_stock" if v.get("available") else "out_of_stock")

master=load_master(); catalog=fetch_catalog()
official=[]
for p in catalog:
    title=p.get("title") or ""; handle=p.get("handle") or ""
    price,stock=price_of(p)
    if not title or not handle or price is None: continue
    official.append({
      "title":title,"code":canon_code(title),"price_try":price,"stock_status":stock,
      "purchase_url":f"https://lorisparfum.com/products/{handle}"
    })

by_code={}
for x in official:
    if x["code"]: by_code.setdefault(x["code"],[]).append(x)

results=[]; misses=[]; ambiguous=[]
for m in master:
    product=m.get("product_name",""); code=canon_code(product)
    candidates=[]
    if code:
        for x in by_code.get(code,[]):
            enriched=f"Loris {x['title']}"
            if core.variant_compatible("Loris",product,enriched):
                candidates.append((100.0,x))
    else:
        for x in official:
            enriched=f"Loris {x['title']}"
            if not core.variant_compatible("Loris",product,enriched): continue
            score=core.product_match_score("Loris",product,enriched)
            if score>=88: candidates.append((score,x))
    candidates.sort(key=lambda z:(-z[0],z[1]["price_try"]))
    if not candidates:
        misses.append(m); continue
    top_score=candidates[0][0]
    tied=[x for sc,x in candidates if abs(sc-top_score)<0.001]
    # Same code may exist as multi-pack/set vs single; strict form filter normally removes sets.
    if len({x["purchase_url"] for x in tied})>1 and not code:
        ambiguous.append({"master":m,"candidates":tied[:5]}); continue
    score,x=candidates[0]
    results.append({
      "product_id":m["id"],"brand_name":"Loris","product_name":product,
      "price_try":x["price_try"],"currency":"TRY","seller_name":"lorisparfum.com",
      "purchase_url":x["purchase_url"],"volume_ml":"","stock_status":x["stock_status"],
      "match_confidence":round(score/100,3),"source_product_name":x["title"],
      "checked_at":datetime.now(timezone.utc).isoformat()
    })

results.sort(key=lambda r:int(r["product_id"]))
cols=["product_id","brand_name","product_name","price_try","currency","seller_name","purchase_url",
      "volume_ml","stock_status","match_confidence","source_product_name","checked_at"]
with (OUT/"loris_price_index.csv").open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(results)
summary={
 "generated_at":datetime.now(timezone.utc).isoformat(),
 "master_loris":len(master),"official_products":len(official),
 "matched":len(results),"match_pct":round(100*len(results)/max(1,len(master)),2),
 "coded_master":sum(bool(canon_code(x.get("product_name",""))) for x in master),
 "misses":len(misses),"ambiguous":len(ambiguous),
 "in_stock":sum(r["stock_status"]=="in_stock" for r in results),
 "out_of_stock":sum(r["stock_status"]=="out_of_stock" for r in results)
}
(OUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
(OUT/"ambiguous.json").write_text(json.dumps(ambiguous,ensure_ascii=False,indent=2),encoding="utf-8")
print("SUMMARY",json.dumps(summary,ensure_ascii=False),flush=True)
for r in results[:30]: print("MATCH",json.dumps(r,ensure_ascii=False),flush=True)
