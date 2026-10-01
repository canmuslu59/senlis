#!/usr/bin/env python3
import csv,glob,gzip,json,sys
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parent))
import overnight_full_enrichment as core

OUT=Path("official_price_index"); OUT.mkdir(exist_ok=True)
TARGETS=["Oriflame","Bath & Body Works","Victoria's Secret"]
target_norm={core.norm(x):x for x in TARGETS}

rows=[]
for p in sorted(glob.glob("data/master_manifest_174259/part_*.csv*")):
    opener=gzip.open if p.endswith(".gz") else open
    with opener(p,"rt",encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            if core.norm(r.get("brand_name","")) in target_norm:
                rows.append(r)

s=core.make_session()
results=[]
by_brand={}
for brand in TARGETS:
    br=[r for r in rows if core.norm(r.get("brand_name",""))==core.norm(brand)]
    matched=0
    for i,r in enumerate(br,1):
        off=core.official_catalog_offer(s,brand,r.get("product_name",""))
        if not off: continue
        matched+=1
        results.append({
            "product_id":r["id"],"brand_name":r["brand_name"],"product_name":r["product_name"],
            "price_try":off.get("price_try",""),"currency":"TRY","seller_name":off.get("seller_name",""),
            "purchase_url":off.get("purchase_url",""),"volume_ml":off.get("volume_ml",""),
            "match_confidence":round(float(off.get("score") or 0)/100,3),
            "source_product_name":off.get("source_product_name",""),
            "checked_at":datetime.now(timezone.utc).isoformat()
        })
    by_brand[brand]={"master_rows":len(br),"matched":matched,"match_pct":round(100*matched/max(1,len(br)),2)}
    print("BRAND_DONE",brand,json.dumps(by_brand[brand],ensure_ascii=False),flush=True)

results.sort(key=lambda r:int(r["product_id"]))
cols=["product_id","brand_name","product_name","price_try","currency","seller_name","purchase_url","volume_ml","match_confidence","source_product_name","checked_at"]
with (OUT/"official_price_index.csv").open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(results)
summary={
  "generated_at":datetime.now(timezone.utc).isoformat(),
  "matched_products":len(results),
  "by_brand":by_brand,
  "seller_counts":{}
}
for r in results:
    k=r["seller_name"]; summary["seller_counts"][k]=summary["seller_counts"].get(k,0)+1
(OUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
print("SUMMARY",json.dumps(summary,ensure_ascii=False),flush=True)
