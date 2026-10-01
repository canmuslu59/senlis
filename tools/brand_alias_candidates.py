#!/usr/bin/env python3
import csv,glob,gzip,json,re,unicodedata
from collections import Counter
from pathlib import Path
from rapidfuzz import fuzz,process

def norm(s):
    s=str(s or "").strip().lower()
    repl={"ı":"i","ş":"s","ğ":"g","ü":"u","ö":"o","ç":"c","é":"e","è":"e","á":"a","à":"a","ó":"o","ò":"o","í":"i","ì":"i","ñ":"n","&":" and "}
    for a,b in repl.items(): s=s.replace(a,b)
    s=unicodedata.normalize("NFKD",s)
    s="".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",s)).strip()

targets=[x.strip() for x in Path("data/turkiye_retail_brands_501.txt").read_text(encoding="utf-8-sig").splitlines() if x.strip()]
counts=Counter()
display={}
for p in sorted(glob.glob("data/master_manifest_174259/part_*.csv*")):
    opener=gzip.open if p.endswith(".gz") else open
    with opener(p,"rt",encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            b=r.get("brand_name","").strip()
            if b:
                n=norm(b); counts[n]+=1; display.setdefault(n,b)

master=list(counts)
rows=[]
for t in targets:
    nt=norm(t)
    if nt in counts: continue
    scored=[]
    for m in master:
        s1=fuzz.ratio(nt,m)
        s2=fuzz.token_sort_ratio(nt,m)
        s3=fuzz.token_set_ratio(nt,m)
        contain=100 if (nt in m or m in nt) and min(len(nt),len(m))>=4 else 0
        score=max(s1,s2,s3,contain)
        if score>=65:
            scored.append((score,m))
    scored.sort(key=lambda z:(-z[0],-counts[z[1]],z[1]))
    best=[{"master":display[m],"count":counts[m],"score":round(sc,1)} for sc,m in scored[:8]]
    rows.append({"target":t,"best":best})

high=[]
for r in rows:
    if r["best"] and r["best"][0]["score"]>=88:
        high.append({"target":r["target"],**r["best"][0]})
summary={"missing_targets":len(rows),"high_confidence_candidates":len(high),"high":high}
print("ALIAS_CANDIDATES",json.dumps(summary,ensure_ascii=False),flush=True)
