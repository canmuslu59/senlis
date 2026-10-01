#!/usr/bin/env python3
import csv, glob, gzip, html, json, os, re, time, unicodedata, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

START_ID=int(os.environ.get("START_ID","1"))
END_ID=int(os.environ.get("END_ID","174259"))
FAST_WORKERS=int(os.environ.get("FAST_WORKERS","6"))
FRAG_WORKERS=int(os.environ.get("FRAG_WORKERS","3"))
FRAG_DELAY=float(os.environ.get("FRAG_DELAY","0.25"))
OUT=Path(os.environ.get("IMAGE_OUT","image_out")); OUT.mkdir(exist_ok=True)
OUTCSV=OUT/f"images_{START_ID:06d}_{END_ID:06d}.csv"
OUTJSON=OUT/f"images_{START_ID:06d}_{END_ID:06d}_summary.json"

COLS=["product_id","brand_name","product_name","image_url","image_source_url","source_url","image_status","http_status","checked_at"]

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
                      "Accept-Language":"en-US,en;q=0.9,tr;q=0.8"})
    return s

def load_rows():
    rows=[]
    for p in sorted(glob.glob("data/master_manifest_174259/part_*.csv*")):
        opener=gzip.open if p.endswith(".gz") else open
        with opener(p,"rt",encoding="utf-8-sig",newline="") as f:
            for r in csv.DictReader(f):
                try: pid=int(r["id"])
                except: continue
                if START_ID<=pid<=END_ID: rows.append(r)
    rows.sort(key=lambda r:int(r["id"]))
    return rows

def parse_image(soup,base_url):
    m=soup.find("meta",attrs={"property":"og:image"}) or soup.find("meta",attrs={"name":"twitter:image"})
    if m and m.get("content"): return urllib.parse.urljoin(base_url,m["content"])
    for tag in soup.find_all("script",attrs={"type":"application/ld+json"}):
        try:
            obj=json.loads(tag.get_text(" ",strip=True))
        except: continue
        stack=[obj]
        while stack:
            x=stack.pop()
            if isinstance(x,list): stack.extend(x); continue
            if not isinstance(x,dict): continue
            stack.extend(x.values())
            typ=x.get("@type")
            if typ=="Product" or (isinstance(typ,list) and "Product" in typ):
                im=x.get("image")
                if isinstance(im,list): im=im[0] if im else ""
                if isinstance(im,dict): im=im.get("url") or im.get("contentUrl") or ""
                if im: return urllib.parse.urljoin(base_url,str(im))
    return ""

def slug(s):
    s=unicodedata.normalize("NFKD",str(s or ""))
    s="".join(ch for ch in s if not unicodedata.combining(ch))
    s=s.replace("&"," and ").replace("'","_").replace("’","_")
    return re.sub(r"_+","_",re.sub(r"[^A-Za-z0-9]+","_",s).strip("_"))

def parfumo_fallback(session,row):
    candidates=[row.get("product_name","")]
    stripped=re.sub(r"\s*\([^)]*\)\s*"," ",row.get("product_name","")).strip()
    if stripped and stripped not in candidates: candidates.append(stripped)
    for product in candidates[:2]:
        url=f"https://www.parfumo.com/Perfumes/{slug(row.get('brand_name',''))}/{slug(product)}"
        try:
            r=session.get(url,timeout=15,allow_redirects=True)
            if r.status_code!=200 or "text/html" not in r.headers.get("content-type",""): continue
            soup=BeautifulSoup(r.text,"lxml")
            title=soup.title.get_text(" ",strip=True) if soup.title else ""
            if norm(row.get("brand_name","")) not in norm(title): continue
            im=parse_image(soup,r.url)
            if im: return im,r.url
        except: pass
    return "",""

def fetch_image(row,frag=False):
    session=make_session()
    url=row.get("source_url","")
    base={"product_id":row.get("id",""),"brand_name":row.get("brand_name",""),"product_name":row.get("product_name",""),
          "image_url":"","image_source_url":"","source_url":url,"image_status":"no_source","http_status":"",
          "checked_at":datetime.now(timezone.utc).isoformat()}
    if not url: return base
    attempts=2 if frag else 1
    for attempt in range(attempts):
        try:
            r=session.get(url,timeout=18,allow_redirects=True)
            base["http_status"]=str(r.status_code)
            if r.status_code==200 and "text/html" in r.headers.get("content-type",""):
                soup=BeautifulSoup(r.text,"lxml")
                im=parse_image(soup,r.url)
                if im:
                    base.update({"image_url":im,"image_source_url":r.url,"image_status":"ok"})
                    if frag: time.sleep(FRAG_DELAY)
                    return base
                base["image_status"]="page_no_image"
                break
            base["image_status"]="http_error"
            if frag and r.status_code in (403,429) and attempt+1<attempts:
                time.sleep(1.0)
                continue
            break
        except Exception:
            base["image_status"]="error"; break
    if frag and not base["image_url"] and base["image_status"] in ("http_error","error"):
        im,src=parfumo_fallback(session,row)
        if im:
            base.update({"image_url":im,"image_source_url":src,"image_status":"parfumo_fallback"})
    if frag: time.sleep(FRAG_DELAY)
    return base

def run_group(rows,workers,frag):
    out=[]
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs=[ex.submit(fetch_image,r,frag) for r in rows]
        done=0
        for fut in as_completed(futs):
            try: out.append(fut.result())
            except Exception: pass
            done+=1
            if done%500==0: print("PROGRESS",("frag" if frag else "fast"),done,"/",len(rows),flush=True)
    return out

def main():
    rows=load_rows()
    frag=[r for r in rows if host(r.get("source_url",""))=="fragrantica.com"]
    fast=[r for r in rows if host(r.get("source_url",""))!="fragrantica.com"]
    print("START",json.dumps({"range":[START_ID,END_ID],"total":len(rows),"fragrantica":len(frag),"fast":len(fast)},ensure_ascii=False),flush=True)
    results=[]
    if fast: results.extend(run_group(fast,FAST_WORKERS,False))
    if frag: results.extend(run_group(frag,FRAG_WORKERS,True))
    results.sort(key=lambda r:int(r["product_id"]))
    with OUTCSV.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=COLS); w.writeheader(); w.writerows(results)
    summary={"start_id":START_ID,"end_id":END_ID,"total":len(rows),"processed":len(results),
             "with_image":sum(bool(r.get("image_url")) for r in results),
             "ok":sum(r.get("image_status")=="ok" for r in results),
             "fallback":sum(r.get("image_status")=="parfumo_fallback" for r in results),
             "status_counts":{},"generated_at":datetime.now(timezone.utc).isoformat()}
    for r in results:
        k=r.get("image_status") or ""
        summary["status_counts"][k]=summary["status_counts"].get(k,0)+1
    summary["coverage_pct"]=round(100*summary["with_image"]/max(1,summary["processed"]),2)
    OUTJSON.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print("SUMMARY",json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
