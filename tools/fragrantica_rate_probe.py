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

s=requests.Session()
s.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36","Accept-Language":"en-US,en;q=0.9"})
counts={}
images=0
for row in load_rows():
    url=row.get("source_url","")
    if "fragrantica.com" not in url:
        print("SKIP",row["id"],url,flush=True); continue
    code="error"; image=""
    try:
        r=s.get(url,timeout=20,allow_redirects=True)
        code=str(r.status_code)
        if r.status_code==200 and "text/html" in r.headers.get("content-type",""):
            soup=BeautifulSoup(r.text,"lxml")
            m=soup.find("meta",attrs={"property":"og:image"}) or soup.find("meta",attrs={"name":"twitter:image"})
            if m and m.get("content"): image=m["content"]
    except Exception as e:
        code="exception"
    counts[code]=counts.get(code,0)+1
    if image: images+=1
    print("RESULT",json.dumps({"id":row["id"],"status":code,"image":bool(image)},ensure_ascii=False),flush=True)
    time.sleep(0.75)
print("SUMMARY",json.dumps({"tested":sum(counts.values()),"codes":counts,"images":images},ensure_ascii=False),flush=True)
