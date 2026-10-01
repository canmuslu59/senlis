#!/usr/bin/env python3
import csv, glob, gzip, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime, timezone
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import overnight_full_enrichment as core

OUT=Path("commerce_pilot_100")
OUT.mkdir(exist_ok=True)

def load_all():
    rows=[]
    for p in sorted(glob.glob("data/master_manifest_174259/part_*.csv") + glob.glob("data/master_manifest_174259/part_*.csv.gz")):
        opener=gzip.open if p.endswith(".gz") else open
        with opener(p,"rt",encoding="utf-8-sig",newline="") as f:
            rows.extend(csv.DictReader(f))
    return rows

def evenly_pick(rows,n):
    if len(rows)<=n: return rows[:]
    out=[]
    for i in range(n):
        idx=round(i*(len(rows)-1)/(n-1))
        out.append(rows[idx])
    return out

def main():
    all_rows=load_all()
    recent=[r for r in all_rows if str(r.get("release_year") or "").isdigit() and int(r["release_year"])>=2018]
    selected=[]
    seen=set()
    for cohort,rows,n in [("recent_2018_plus",recent,50),("catalog_all",all_rows,50)]:
        for r in evenly_pick(rows,n):
            if r["id"] in seen: continue
            x=dict(r); x["pilot_cohort"]=cohort
            selected.append(x); seen.add(r["id"])
    if len(selected)<100:
        for r in all_rows:
            if r["id"] not in seen:
                x=dict(r); x["pilot_cohort"]="fill"
                selected.append(x); seen.add(r["id"])
                if len(selected)>=100: break

    def run_one(r):
        s=core.make_session()
        c=core.extract_commerce(s,r)
        return {
            "product_id":r["id"],"brand_name":r["brand_name"],"product_name":r["product_name"],
            "release_year":r.get("release_year",""),"pilot_cohort":r["pilot_cohort"],
            **c
        }

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
            if done%10==0:
                print("PROGRESS",done,"/",len(selected),flush=True)

    results.sort(key=lambda x:int(x["product_id"]))
    cols=["product_id","brand_name","product_name","release_year","pilot_cohort","commerce_status","price_try","currency",
          "volume_ml","seller_name","purchase_url","stock_status","commerce_image","match_confidence","source_product_name"]
    with (OUT/"commerce_pilot_100.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols,extrasaction="ignore"); w.writeheader(); w.writerows(results)

    def stats(rows):
        return {
            "tested":len(rows),
            "verified":sum(r.get("commerce_status")=="verified" for r in rows),
            "with_price":sum(bool(r.get("price_try")) for r in rows),
            "with_purchase_url":sum(bool(r.get("purchase_url")) for r in rows),
        }

    cohorts={}
    for name in sorted(set(r["pilot_cohort"] for r in results)):
        cohorts[name]=stats([r for r in results if r["pilot_cohort"]==name])
    summary={
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "overall":stats(results),
        "cohorts":cohorts,
        "statuses":{}
    }
    for r in results:
        k=r.get("commerce_status") or ""
        summary["statuses"][k]=summary["statuses"].get(k,0)+1
    (OUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print("SUMMARY",json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
