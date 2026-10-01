#!/usr/bin/env python3
import csv,glob,gzip,json,re,unicodedata
from collections import Counter,defaultdict
from pathlib import Path

def norm(s):
    s=str(s or "").strip().lower()
    repl={"ı":"i","ş":"s","ğ":"g","ü":"u","ö":"o","ç":"c","é":"e","è":"e","á":"a","à":"a","ó":"o","ò":"o","í":"i","ì":"i","ñ":"n","&":" and "}
    for a,b in repl.items(): s=s.replace(a,b)
    s=unicodedata.normalize("NFKD",s)
    s="".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",s)).strip()

targets=[x.strip() for x in Path("data/turkiye_retail_brands_501.txt").read_text(encoding="utf-8-sig").splitlines() if x.strip()]
rows=[]
brand_norms=set()
for p in sorted(glob.glob("data/master_manifest_174259/part_*.csv*")):
    opener=gzip.open if p.endswith(".gz") else open
    with opener(p,"rt",encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            b=r.get("brand_name","").strip()
            pn=r.get("product_name","").strip()
            rows.append((b,norm(b),pn,norm(pn)))
            if b: brand_norms.add(norm(b))

missing=[t for t in targets if norm(t) not in brand_norms]
out=[]
for t in missing:
    nt=norm(t)
    toks=[x for x in nt.split() if len(x)>=3]
    if not toks: continue
    hits=Counter()
    examples=defaultdict(list)
    for b,nb,p,np in rows:
        matched=False
        if len(nt)>=5 and nt in np:
            matched=True
        elif len(toks)>=2 and all(x in np.split() for x in toks):
            matched=True
        if matched:
            hits[b]+=1
            if len(examples[b])<4: examples[b].append(p)
    if hits:
        top=hits.most_common(6)
        total=sum(hits.values())
        out.append({
          "target":t,"total_product_name_hits":total,
          "top_master_brands":[{"brand":b,"hits":c,"examples":examples[b]} for b,c in top]
        })

out.sort(key=lambda x:(-x["total_product_name_hits"],x["target"]))
print("PRODUCT_ALIAS_CANDIDATES",json.dumps({"candidate_targets":len(out),"rows":out},ensure_ascii=False),flush=True)
