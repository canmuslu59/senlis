#!/usr/bin/env python3
# trigger after workflow install
import csv,glob,gzip,json,time,urllib.parse
from pathlib import Path
import requests
from bs4 import BeautifulSoup
TEST_IDS=set(["642","72655","72793","72889","73000","90091","90207","90299","90438","90559","90652","90818","90992","108087","108191","108332","108425","108517","108614","108703","108798","108944","126084","126229","126385","126487","126602","126691","126783","126883","126982","144072","144173","144274","144362","144461","144551","144640","144731","144823","144944","162041","162170","162303","162418","162527","162712","162808","162911","163000"])

def load_rows():
    found={}
    for p in sorted(glob.glob("data/master_manifest_174259/part_*.csv*")):
        opener=gzip.open if p.endswith(".gz") else open
        with opener(p,"rt",encoding="utf-8-sig",newline="") as f:
            for r in csv.DictReader(f):
                if r["id"] in TEST_IDS: found[r["id"]]=r
    return [found[i] for i in sorted(TEST_IDS,key=int) if i in found]

from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_one(row):
    s=requests.Session()
    s.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36","Accept-Language":"en-US,en;q=0.9"})
    url=row.get("source_url","")
    if "fragrantica.com" not in url:
        return {"id":row["id"],"status":"skip","image":False}
    code="error"; image=""
    try:
        r=s.get(url,timeout=20,allow_redirects=True)
        code=str(r.status_code)
        if r.status_code==200 and "text/html" in r.headers.get("content-type",""):
            soup=BeautifulSoup(r.text,"lxml")
            m=soup.find("meta",attrs={"property":"og:image"}) or soup.find("meta",attrs={"name":"twitter:image"})
            if m and m.get("content"): image=m["content"]
    except Exception:
        code="exception"
    time.sleep(0.25)
    return {"id":row["id"],"status":code,"image":bool(image)}

counts={}; images=0
with ThreadPoolExecutor(max_workers=3) as ex:
    futs=[ex.submit(fetch_one,row) for row in load_rows()]
    for fut in as_completed(futs):
        rec=fut.result()
        if rec["status"]=="skip": continue
        counts[rec["status"]]=counts.get(rec["status"],0)+1
        if rec["image"]: images+=1
        print("RESULT",json.dumps(rec,ensure_ascii=False),flush=True)
print("SUMMARY",json.dumps({"tested":sum(counts.values()),"codes":counts,"images":images,"workers":3,"delay":0.25},ensure_ascii=False),flush=True)
