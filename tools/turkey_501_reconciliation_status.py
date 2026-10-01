#!/usr/bin/env python3
import csv,glob,gzip,json,re,unicodedata
from pathlib import Path

def norm(s):
    s=str(s or "").strip().lower()
    repl={"ı":"i","ş":"s","ğ":"g","ü":"u","ö":"o","ç":"c","é":"e","è":"e","á":"a","à":"a","ó":"o","ò":"o","í":"i","ì":"i","ñ":"n","&":" and "}
    for a,b in repl.items(): s=s.replace(a,b)
    s=unicodedata.normalize("NFKD",s)
    s="".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",s)).strip()

targets=[x.strip() for x in Path("data/turkiye_retail_brands_501.txt").read_text(encoding="utf-8-sig").splitlines() if x.strip()]
target_by_norm={norm(x):x for x in targets}

# Current master labels.
master=set()
for p in sorted(glob.glob("data/master_manifest_174259/part_*.csv*")):
    opener=gzip.open if p.endswith(".gz") else open
    with opener(p,"rt",encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            if r.get("brand_name"): master.add(norm(r["brand_name"]))

# Explicit target -> master aliases. Keep this synchronized with verified audit mappings only.
safe_alias={
 "abdullah kigili":"kigili",
 "ac and co altinyildiz classics":"altinyildiz classics",
 "aqua di polo 1987":"aqua di polo",
 "armani":"giorgio armani",
 "boss":"hugo boss",
 "carmina":"hunca",
 "christian dior":"dior",
 "damat":"d s damat",
 "demeter":"demeter fragrance",
 "emporio armani":"giorgio armani",
 "ferragamo":"salvatore ferragamo",
 "hugo":"hugo boss",
 "hunca care":"hunca",
 "jagler":"hunca",
 "l occitane":"l occitane en provence",
 "mad parfum":"mad parfumeur",
 "manly":"morfose",
 "manly sport":"morfose",
 "mercedes benz parfums":"mercedes benz",
 "paco rabanne":"rabanne",
 "puccini":"puccini paris",
 "reef":"reef perfumes",
 "rosemary paris":"rosemary",
 "sephora collection":"sephora",
 "sevilla":"sevilla fragrances",
 "sospiro":"sospiro perfumes",
 "viva cappio":"hunca",
 "alfaparf":"alfaparf milano",
}

staged={}
for p in sorted(glob.glob("data/turkey_missing_brand_staging/batch_*_brand_status.csv")):
    with open(p,encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            staged[norm(r["brand"])]=r

# Tudors pages use TDRS as the product label; resolve the target label to the same current official family.
if "tudors" in staged:
    staged["tdrs"]={
      "brand":"TDRS","status":"verified_subbrand_of_tudors","in_scope_personal_fragrance":"yes",
      "official_source":staged["tudors"].get("official_source",""),"catalog_note":"TDRS is the product label used on Tudors official perfume listings"
    }

rows=[]
counts={"master_direct":0,"master_safe_alias":0,"staged_in_scope":0,"resolved_no_current_personal_fragrance":0,"research_pending":0,"unresolved":0}
for t in targets:
    n=norm(t)
    if n in master:
        bucket="master_direct"
    elif n in safe_alias and safe_alias[n] in master:
        bucket="master_safe_alias"
    elif n in staged:
        st=staged[n]
        ins=norm(st.get("in_scope_personal_fragrance",""))
        status=norm(st.get("status",""))
        if ins=="yes":
            bucket="staged_in_scope"
        elif ins=="no" and ("no current" in status or "out of scope" in status):
            bucket="resolved_no_current_personal_fragrance"
        elif "pending" in status:
            bucket="research_pending"
        else:
            bucket="research_pending"
    else:
        bucket="unresolved"
    counts[bucket]+=1
    rows.append({"target_brand":t,"bucket":bucket})

resolved=counts["master_direct"]+counts["master_safe_alias"]+counts["staged_in_scope"]+counts["resolved_no_current_personal_fragrance"]
summary={
 "target_labels":len(targets),
 **counts,
 "resolved_total":resolved,
 "resolved_pct":round(100*resolved/len(targets),2),
 "needs_research":counts["research_pending"]+counts["unresolved"],
 "needs_research_pct":round(100*(counts["research_pending"]+counts["unresolved"])/len(targets),2),
}
print("RECONCILIATION_SUMMARY",json.dumps(summary,ensure_ascii=False),flush=True)

out=Path("turkey_501_reconciliation"); out.mkdir(exist_ok=True)
with (out/"status.csv").open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=["target_brand","bucket"]); w.writeheader(); w.writerows(rows)
(out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
