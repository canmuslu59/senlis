#!/usr/bin/env python3
import csv, glob, gzip, json, re, unicodedata, urllib.parse
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import overnight_full_enrichment as core

TEST_IDS=set(["642","72655","72793","72889","73000","90091","90207","90299","90438","90559","90652","90818","90992","108087","108191","108332","108425","108517","108614","108703","108798","108944","126084","126229","126385","126487","126602","126691","126783","126883","126982","144072","144173","144274","144362","144461","144551","144640","144731","144823","144944","162041","162170","162303","162418","162527","162712","162808","162911","163000"])
def slug(s):
    s=unicodedata.normalize("NFKD",str(s or ""))
    s="".join(ch for ch in s if not unicodedata.combining(ch))
    s=s.replace("&"," and ").replace("'","_").replace("’","_")
    s=re.sub(r"[^A-Za-z0-9]+","_",s).strip("_")
    return re.sub(r"_+","_",s)

def variants(product):
    out=[product]
    stripped=re.sub(r"\s*\([^)]*\)\s*"," ",product).strip()
    if stripped and stripped not in out: out.append(stripped)
    for suffix in [" Eau de Parfum"," Eau de Toilette"," Parfum"," EDT"," EDP"]:
        if stripped.lower().endswith(suffix.lower()):
            x=stripped[:-len(suffix)].strip()
            if x and x not in out: out.append(x)
    return out[:4]

def load_rows():
    found={}
    for p in sorted(glob.glob("data/master_manifest_174259/part_*.csv*")):
        opener=gzip.open if p.endswith(".gz") else open
        with opener(p,"rt",encoding="utf-8-sig",newline="") as f:
            for r in csv.DictReader(f):
                if r["id"] in TEST_IDS: found[r["id"]]=r
    return [found[i] for i in sorted(TEST_IDS,key=int) if i in found]

def main():
    s=core.make_session()
    results=[]
    for row in load_rows():
        brand=row["brand_name"]; product=row["product_name"]
        hit=None; tried=[]
        for pv in variants(product):
            url=f"https://www.parfumo.com/Perfumes/{slug(brand)}/{slug(pv)}"
            tried.append(url)
            try:
                r=s.get(url,timeout=15,allow_redirects=True)
                if r.status_code!=200 or "text/html" not in r.headers.get("content-type",""): continue
                soup=BeautifulSoup(r.text,"lxml")
                title=soup.title.get_text(" ",strip=True) if soup.title else ""
                meta=soup.find("meta",attrs={"property":"og:image"}) or soup.find("meta",attrs={"name":"twitter:image"})
                image=meta.get("content","") if meta else ""
                if core.brand_compatible(brand,title) and core.variant_compatible(brand,product,title) and core.product_match_score(brand,product,title)>=78 and image:
                    hit={"url":r.url,"title":title,"image":urllib.parse.urljoin(r.url,image)}
                    break
            except Exception:
                pass
        rec={"id":row["id"],"brand":brand,"product":product,"hit":bool(hit),"hit_url":hit["url"] if hit else "","title":hit["title"] if hit else "","tried":tried}
        results.append(rec)
        print("RESULT",json.dumps(rec,ensure_ascii=False),flush=True)
    summary={"tested":len(results),"hits":sum(x["hit"] for x in results)}
    summary["hit_pct"]=round(100*summary["hits"]/max(1,summary["tested"]),1)
    print("SUMMARY",json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
