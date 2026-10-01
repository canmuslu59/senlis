#!/usr/bin/env python3
import csv,glob,gzip,json,os,re,threading,time,unicodedata,urllib.parse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime,timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from image_sources import clean_source_url,fragrantica_image,generic_image,host,page_image,parfumo_page_verified

START_ID=int(os.environ.get("START_ID","1"))
END_ID=int(os.environ.get("END_ID","174259"))
FAST_WORKERS=int(os.environ.get("FAST_WORKERS","6"))
FRAG_WORKERS=int(os.environ.get("FRAG_WORKERS","6"))
VERIFY_CDN=os.environ.get("VERIFY_CDN","1")=="1"
PAGE_MIN_INTERVAL=float(os.environ.get("PAGE_MIN_INTERVAL","1.0"))
MAX_SECONDS=int(os.environ.get("MAX_SECONDS","0"))
CHECKPOINT_EVERY=int(os.environ.get("CHECKPOINT_EVERY","1000"))
OUT=Path(os.environ.get("IMAGE_OUT","image_out"));OUT.mkdir(exist_ok=True)
OUTCSV=OUT/f"images_{START_ID:06d}_{END_ID:06d}.csv"
OUTJSON=OUT/f"images_{START_ID:06d}_{END_ID:06d}_summary.json"
COLS=["product_id","brand_name","product_name","image_url","image_source_url","source_url","image_status","http_status","checked_at"]

_last={};_lock=threading.Lock()

def norm(s):
    s=unicodedata.normalize("NFKD",str(s or "").lower())
    s="".join(ch for ch in s if not unicodedata.combining(ch))
    s=s.replace("ı","i").replace("ş","s").replace("ğ","g").replace("ü","u").replace("ö","o").replace("ç","c")
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",s)).strip()

def make_session():
    s=requests.Session()
    s.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36","Accept-Language":"en-US,en;q=0.9,tr;q=0.8"})
    return s

def throttle(url):
    h=host(url)
    if not h:return
    with _lock:
        now=time.monotonic();wait=max(0,PAGE_MIN_INTERVAL-(now-_last.get(h,0)))
        if wait:time.sleep(wait)
        _last[h]=time.monotonic()

def load_rows():
    rows=[];overlay={}
    for p in sorted(glob.glob("data/source_urls/part_*.csv")):
        with open(p,encoding="utf-8-sig",newline="") as f:
            for r in csv.DictReader(f):
                if r.get("source_url"):overlay[str(r.get("id",""))]=r["source_url"]
    for p in sorted(glob.glob("data/master_manifest_174259/part_*.csv*")):
        opener=gzip.open if p.endswith(".gz") else open
        with opener(p,"rt",encoding="utf-8-sig",newline="") as f:
            for r in csv.DictReader(f):
                try:pid=int(r["id"])
                except Exception:continue
                if START_ID<=pid<=END_ID:
                    r["source_url"]=clean_source_url(overlay.get(str(pid)) or r.get("source_url",""),pid)
                    rows.append(r)
    rows.sort(key=lambda r:int(r["id"]))
    return rows

def base_row(row):
    return {"product_id":row.get("id",""),"brand_name":row.get("brand_name",""),"product_name":row.get("product_name",""),
            "image_url":"","image_source_url":"","source_url":row.get("source_url",""),"image_status":"no_source",
            "http_status":"","checked_at":datetime.now(timezone.utc).isoformat()}

def fetch_page(session,row,url):
    b=base_row(row)
    if not url:return b
    try:
        throttle(url)
        r=session.get(url,timeout=18,allow_redirects=True)
        b["http_status"]=str(r.status_code)
        if r.status_code!=200 or "text/html" not in r.headers.get("content-type",""):
            b["image_status"]="http_error";return b
        soup=BeautifulSoup(r.text,"lxml")
        if host(r.url)=="parfumo.com" and not parfumo_page_verified(soup,row.get("brand_name",""),row.get("product_name","")):
            b.update({"image_status":"parfumo_unverified","image_source_url":r.url});return b
        im=page_image(soup,r.url,row.get("brand_name",""),row.get("product_name",""))
        if im:
            b.update({"image_url":im,"image_source_url":r.url,"image_status":"ok"});return b
        b.update({"image_status":"page_no_image","image_source_url":r.url});return b
    except Exception:
        b["image_status"]="error";return b

def slug(s):
    s=unicodedata.normalize("NFKD",str(s or ""))
    s="".join(ch for ch in s if not unicodedata.combining(ch))
    s=s.replace("&"," and ").replace("'","_").replace("’","_")
    return re.sub(r"_+","_",re.sub(r"[^A-Za-z0-9]+","_",s).strip("_"))

def parfumo_fallback(session,row):
    products=[row.get("product_name","")]
    stripped=re.sub(r"\s*\([^)]*\)\s*"," ",row.get("product_name","")).strip()
    if stripped and stripped not in products:products.append(stripped)
    for product in products[:2]:
        u=f"https://www.parfumo.com/Perfumes/{slug(row.get('brand_name',''))}/{slug(product)}"
        rec=fetch_page(session,row,u)
        if rec.get("image_url"):
            rec["image_status"]="parfumo_fallback";return rec
    return None

def fetch_image(row,frag=False):
    s=make_session();url=row.get("source_url","");b=base_row(row)
    h=host(url)
    if h=="huggingface.co":
        b["image_status"]="hf_archive";return b
    if frag or h=="fragrantica.com":
        cdn=fragrantica_image(url)
        if cdn:
            if not VERIFY_CDN:
                b.update({"image_url":cdn,"image_source_url":url,"image_status":"cdn"});return b
            try:
                r=s.head(cdn,timeout=12,allow_redirects=True)
                b["http_status"]=str(r.status_code)
                ctype=r.headers.get("content-type","").lower()
                if r.status_code==200 and ctype.startswith("image/"):
                    b.update({"image_url":cdn,"image_source_url":url,"image_status":"cdn"});return b
                if r.status_code not in (404,410) and (r.status_code in (403,429) or r.status_code>=500):
                    b.update({"image_url":cdn,"image_source_url":url,"image_status":"cdn"});return b
            except Exception:
                b.update({"image_url":cdn,"image_source_url":url,"image_status":"cdn"});return b
        page=fetch_page(s,row,url)
        if page.get("image_url"):return page
        pf=parfumo_fallback(s,row)
        return pf or page
    return fetch_page(s,row,url)

def save(results,total,start):
    results.sort(key=lambda r:int(r["product_id"]))
    with OUTCSV.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=COLS,extrasaction="ignore");w.writeheader();w.writerows(results)
    sc=Counter(r.get("image_status","") for r in results)
    summary={"start_id":START_ID,"end_id":END_ID,"total":total,"processed":len(results),"remaining":max(0,total-len(results)),
             "with_image":sum(bool(r.get("image_url")) for r in results),"ok":sum(r.get("image_status") in ("cdn","ok","parfumo_fallback") for r in results),
             "fallback":sum(r.get("image_status")=="parfumo_fallback" for r in results),"status_counts":dict(sc),
             "coverage_pct":round(100*sum(bool(r.get("image_url")) for r in results)/max(1,len(results)),2),
             "seconds":round(time.time()-start,1),"generated_at":datetime.now(timezone.utc).isoformat()}
    OUTJSON.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    return summary

def run_group(rows,workers,results,start,total):
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs={ex.submit(fetch_image,r,host(r.get("source_url",""))=="fragrantica.com"):r for r in rows}
        for i,fut in enumerate(as_completed(futs),1):
            if MAX_SECONDS and time.time()-start>=MAX_SECONDS:
                for x in futs:x.cancel()
                break
            r=futs[fut]
            try:results.append(fut.result())
            except Exception:
                b=base_row(r);b["image_status"]="error";results.append(b)
            if CHECKPOINT_EVERY and len(results)%CHECKPOINT_EVERY==0:
                print("CHECKPOINT",json.dumps(save(results,total,start),ensure_ascii=False),flush=True)

def main():
    rows=load_rows();total=len(rows);start=time.time();results=[]
    frag=[r for r in rows if host(r.get("source_url",""))=="fragrantica.com"]
    other=[r for r in rows if host(r.get("source_url",""))!="fragrantica.com"]
    run_group(frag,FRAG_WORKERS,results,start,total)
    if not MAX_SECONDS or time.time()-start<MAX_SECONDS:run_group(other,FAST_WORKERS,results,start,total)
    print("SUMMARY",json.dumps(save(results,total,start),ensure_ascii=False),flush=True)

if __name__=="__main__":main()
