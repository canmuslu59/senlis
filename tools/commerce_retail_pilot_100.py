#!/usr/bin/env python3
import csv, glob, gzip, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime, timezone
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import overnight_full_enrichment as core

OUT=Path("commerce_retail_pilot_100"); OUT.mkdir(exist_ok=True)
FOCUS_BRANDS=[
 "Calvin Klein","Dior","Giorgio Armani","Tom Ford","Versace","Rabanne","Yves Saint Laurent",
 "Givenchy","Gucci","Burberry","Carolina Herrera","Hugo Boss","Lancôme","Jean Paul Gaultier",
 "Narciso Rodriguez","Dolce & Gabbana","Prada","Valentino","Issey Miyake","Montblanc","Bvlgari",
 "Coach","Marc Jacobs","Chloé","Elie Saab","Mugler","Azzaro","Davidoff","Diesel","Lacoste",
 "Kenzo","Jimmy Choo","Michael Kors","Moschino","Roberto Cavalli","Ferragamo","Lattafa Perfumes",
 "Armaf","Afnan","Al Haramain Perfumes"
]

def load_all():
    rows=[]
    for p in sorted(glob.glob("data/master_manifest_174259/part_*.csv") + glob.glob("data/master_manifest_174259/part_*.csv.gz")):
        opener=gzip.open if p.endswith(".gz") else open
        with opener(p,"rt",encoding="utf-8-sig",newline="") as f:
            rows.extend(csv.DictReader(f))
    return rows

def main():
    all_rows=load_all()
    by_brand={}
    focus_norm={core.norm(x):x for x in FOCUS_BRANDS}
    for r in all_rows:
        nb=core.norm(r.get("brand_name",""))
        if nb not in focus_norm: continue
        y=str(r.get("release_year") or "")
        if y.isdigit() and int(y)>=2018:
            by_brand.setdefault(nb,[]).append(r)
    selected=[]
    for nb in [core.norm(x) for x in FOCUS_BRANDS]:
        rows=sorted(by_brand.get(nb,[]),key=lambda r:(int(r.get("release_year") or 0),int(r["id"])),reverse=True)
        for r in rows[:3]:
            x=dict(r); x["pilot_cohort"]="retail_recent"
            selected.append(x)
            if len(selected)>=100: break
        if len(selected)>=100: break
    if len(selected)<100:
        used={r["id"] for r in selected}
        rest=[]
        for nb,rows in by_brand.items():
            for r in rows:
                if r["id"] not in used: rest.append(r)
        rest.sort(key=lambda r:(int(r.get("release_year") or 0),int(r["id"])),reverse=True)
        for r in rest:
            x=dict(r); x["pilot_cohort"]="retail_recent_fill"; selected.append(x)
            if len(selected)>=100: break

    def run_one(r):
        s=core.make_session()
        c=core.extract_commerce(s,r)
        return {"product_id":r["id"],"brand_name":r["brand_name"],"product_name":r["product_name"],
                "release_year":r.get("release_year",""),"pilot_cohort":r["pilot_cohort"],**c}

    results=[]
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs={ex.submit(run_one,r):r for r in selected}
        done=0
        for fut in as_completed(futs):
            r=futs[fut]
            try: x=fut.result()
            except Exception as e:
                x={"product_id":r["id"],"brand_name":r["brand_name"],"product_name":r["product_name"],
                   "release_year":r.get("release_year",""),"pilot_cohort":r["pilot_cohort"],
                   "commerce_status":"worker_error","price_try":"","purchase_url":"","seller_name":"","error":str(e)[:180]}
            results.append(x); done+=1
            if done%10==0: print("PROGRESS",done,"/",len(selected),flush=True)

    results.sort(key=lambda x:(x["brand_name"],-int(x.get("release_year") or 0),int(x["product_id"])))
    cols=["product_id","brand_name","product_name","release_year","pilot_cohort","commerce_status","price_try","currency",
          "volume_ml","seller_name","purchase_url","stock_status","commerce_image","match_confidence","source_product_name"]
    with (OUT/"commerce_retail_pilot_100.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols,extrasaction="ignore"); w.writeheader(); w.writerows(results)
    summary={
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "tested":len(results),
        "verified":sum(r.get("commerce_status")=="verified" for r in results),
        "with_price":sum(bool(r.get("price_try")) for r in results),
        "with_purchase_url":sum(bool(r.get("purchase_url")) for r in results),
        "seller_counts":{},
        "status_counts":{}
    }
    for r in results:
        s=r.get("seller_name") or ""
        if s: summary["seller_counts"][s]=summary["seller_counts"].get(s,0)+1
        k=r.get("commerce_status") or ""
        summary["status_counts"][k]=summary["status_counts"].get(k,0)+1
    (OUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print("SUMMARY",json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
