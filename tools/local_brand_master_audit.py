#!/usr/bin/env python3
import csv,glob,gzip,json,re,unicodedata
from collections import Counter,defaultdict

TARGETS=["Loris","Mad Parfüm","Bargello","D&P Perfumum","Eyfel","Sansiro","Frederic Patric","Ixora","Harrem","İmaj","Farmasi","Avon","Oriflame","LC Waikiki","Zara","INNATIVE"]

def norm(s):
    s=str(s or "").strip().lower()
    repl={"ı":"i","ş":"s","ğ":"g","ü":"u","ö":"o","ç":"c","é":"e","è":"e","á":"a","à":"a","ó":"o","ò":"o","í":"i","ì":"i","ñ":"n","&":" and "}
    for a,b in repl.items(): s=s.replace(a,b)
    s=unicodedata.normalize("NFKD",s)
    s="".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",s)).strip()

counts=Counter()
examples=defaultdict(list)
for p in sorted(glob.glob("data/master_manifest_174259/part_*.csv*")):
    opener=gzip.open if p.endswith(".gz") else open
    with opener(p,"rt",encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            b=r.get("brand_name","").strip()
            counts[b]+=1
            if len(examples[b])<5:
                examples[b].append({"id":r.get("id"),"product":r.get("product_name"),"year":r.get("release_year")})

all_brands=list(counts)
out={}
for t in TARGETS:
    nt=norm(t)
    matches=[]
    for b in all_brands:
        nb=norm(b)
        score=0
        if nb==nt: score=100
        elif nt in nb or nb in nt: score=90
        else:
            ts=set(nt.split()); bs=set(nb.split())
            inter=len(ts&bs); union=len(ts|bs)
            if union: score=round(100*inter/union)
        if score>=45:
            matches.append({"brand":b,"count":counts[b],"score":score,"examples":examples[b]})
    matches.sort(key=lambda x:(-x["score"],-x["count"],x["brand"]))
    out[t]=matches[:12]

print("LOCAL_BRAND_AUDIT",json.dumps(out,ensure_ascii=False),flush=True)
