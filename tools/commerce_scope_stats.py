#!/usr/bin/env python3
import csv, glob, gzip, json, re, html
from collections import Counter

def norm(s):
    s=html.unescape(str(s or "")).lower()
    s=s.replace("ı","i").replace("ş","s").replace("ğ","g").replace("ü","u").replace("ö","o").replace("ç","c")
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",s)).strip()

brands={norm(x) for x in open("data/turkiye_retail_brands_501.txt",encoding="utf-8-sig") if x.strip()}
aliases={
 "giorgio armani":"armani",
 "empirio armani":"armani",
 "paco rabanne":"rabanne",
 "lattafa perfumes":"lattafa",
 "salvatore ferragamo":"ferragamo",
}
rows=[]
for p in sorted(glob.glob("data/master_manifest_174259/part_*.csv*")):
    opener=gzip.open if p.endswith(".gz") else open
    with opener(p,"rt",encoding="utf-8-sig",newline="") as f:
        rows.extend(csv.DictReader(f))

def eligible(r):
    b=norm(r.get("brand_name",""))
    return b in brands or aliases.get(b,"") in brands

e=[r for r in rows if eligible(r)]
recent=[r for r in e if str(r.get("release_year") or "").isdigit() and int(r["release_year"])>=2018]
recent2023=[r for r in e if str(r.get("release_year") or "").isdigit() and int(r["release_year"])>=2023]
unknown=[r for r in e if not str(r.get("release_year") or "").isdigit()]
counts=Counter(norm(r.get("brand_name","")) for r in e)
summary={
 "catalog_total":len(rows),
 "turkey_scope_products":len(e),
 "turkey_scope_pct":round(100*len(e)/max(1,len(rows)),2),
 "turkey_scope_2018_plus":len(recent),
 "turkey_scope_2023_plus":len(recent2023),
 "turkey_scope_unknown_year":len(unknown),
 "eligible_brands_present":len(counts),
 "top_20_brands":counts.most_common(20)
}
print("SCOPE_SUMMARY",json.dumps(summary,ensure_ascii=False),flush=True)
