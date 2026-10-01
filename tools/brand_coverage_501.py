#!/usr/bin/env python3
import csv,glob,gzip,json,re,unicodedata
from collections import defaultdict
from pathlib import Path

TARGET=Path("data/turkiye_retail_brands_501.txt")
OUT=Path("brand_coverage_501"); OUT.mkdir(exist_ok=True)

def norm(s):
    s=str(s or "").strip().lower()
    repl={"ı":"i","ş":"s","ğ":"g","ü":"u","ö":"o","ç":"c","é":"e","è":"e","á":"a","à":"a","ó":"o","ò":"o","í":"i","ì":"i","ñ":"n","&":" and "}
    for a,b in repl.items(): s=s.replace(a,b)
    s=unicodedata.normalize("NFKD",s)
    s="".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",s)).strip()


SAFE_TARGET_TO_MASTER={
 "abdullah kigili":["kigili"],
 "ac co altinyildiz classics":["altinyildiz classics"],
 "aqua di polo 1987":["aqua di polo"],
 "armani":["giorgio armani"],
 "boss":["hugo boss"],
 "christian dior":["dior"],
 "demeter":["demeter fragrance","demeter fragrance library"],
 "emporio armani":["giorgio armani"],
 "ferragamo":["salvatore ferragamo"],
 "hugo":["hugo boss"],
 "hunca care":["hunca"],
 "l occitane":["l occitane en provence"],
 "mad parfum":["mad parfumeur"],
 "mercedes benz parfums":["mercedes benz"],
 "paco rabanne":["rabanne"],
 "sephora collection":["sephora"],
 "sevilla":["sevilla fragrances"],
 "sospiro":["sospiro perfumes"],
 "alfaparf":["alfaparf milano"],
 "rosemary paris":["rosemary"],
 "puccini":["puccini paris"],
 "reef":["reef perfumes"]
}

ALIASES={
 "ac co altinyildiz classics":["altinyildiz classics","ac co"],
 "aqua di polo 1987":["aqua di polo"],
 "armani":["giorgio armani","emporio armani"],
 "boss":["hugo boss"],
 "christian dior":["dior"],
 "d p perfumum":["d p","d&p perfumum","d p perfumum"],
 "dkny":["donna karan"],
 "dolce gabbana":["dolce and gabbana"],
 "estee lauder":["estée lauder"],
 "ferragamo":["salvatore ferragamo"],
 "giorgio armani":["armani"],
 "hugo":["hugo boss"],
 "innative":["innative eny"],
 "l occitane":["l occitane en provence"],
 "paco rabanne":["rabanne"],
 "rabanne":["paco rabanne"],
 "sephora collection":["sephora"],
 "victoria s secret":["victorias secret"],
 "yves saint laurent":["ysl"],
}
# reverse alias expansion
rev=defaultdict(set)
for k,vals in ALIASES.items():
    rev[norm(k)].add(norm(k))
    for v in vals:
        rev[norm(k)].add(norm(v))
        rev[norm(v)].add(norm(k))
        rev[norm(v)].add(norm(v))

targets=[x.strip() for x in TARGET.read_text(encoding="utf-8-sig").splitlines() if x.strip()]
master_counts=defaultdict(int)
master_examples={}
for p in sorted(glob.glob("data/master_manifest_174259/part_*.csv*")):
    opener=gzip.open if p.endswith(".gz") else open
    with opener(p,"rt",encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            b=r.get("brand_name","").strip()
            if not b: continue
            n=norm(b); master_counts[n]+=1; master_examples.setdefault(n,b)

rows=[]
for t in targets:
    nt=norm(t)
    direct=master_counts.get(nt,0)
    candidates=[]
    if direct:
        status="direct"; matched=nt
    else:
        safe=[x for x in SAFE_TARGET_TO_MASTER.get(nt,[]) if master_counts.get(x,0)>0]
        if safe:
            safe.sort(key=lambda x:(-master_counts[x],x))
            matched=safe[0]; status="safe_alias"
        else:
            pool=set(rev.get(nt,set()))
            # generic normalization aliases
            pool |= {nt.replace(" and "," "), nt.replace("parfums","parfum"), nt.replace("perfumes","perfume")}
            found=[x for x in pool if master_counts.get(x,0)>0]
            if found:
                found.sort(key=lambda x:(-master_counts[x],x))
                matched=found[0]; status="alias"
            else:
                matched=""; status="missing"
    rows.append({
      "target_brand":t,"target_norm":nt,"status":status,
      "master_brand":master_examples.get(matched,"") if matched else "",
      "master_product_count":master_counts.get(matched,0) if matched else 0
    })

cols=["target_brand","target_norm","status","master_brand","master_product_count"]
with (OUT/"brand_coverage_501.csv").open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(rows)

summary={
 "target_brands":len(rows),
 "direct":sum(r["status"]=="direct" for r in rows),
 "alias":sum(r["status"]=="alias" for r in rows),
 "safe_alias":sum(r["status"]=="safe_alias" for r in rows),
 "covered_total":sum(r["status"]!="missing" for r in rows),
 "missing":sum(r["status"]=="missing" for r in rows),
 "missing_brands":[r["target_brand"] for r in rows if r["status"]=="missing"],
 "alias_matches":[{"target":r["target_brand"],"master":r["master_brand"],"status":r["status"]} for r in rows if r["status"] in ("alias","safe_alias")]
}
(OUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
print("COVERAGE_SUMMARY",json.dumps(summary,ensure_ascii=False),flush=True)
