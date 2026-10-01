#!/usr/bin/env python3
import csv,glob,gzip,json,sys,time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from datetime import datetime,timezone

sys.path.insert(0,str(Path(__file__).resolve().parent))
import overnight_full_enrichment as core

OUT=Path("commerce_pilot_500"); OUT.mkdir(exist_ok=True)

def load_all():
    rows=[]
    for p in sorted(glob.glob("data/master_manifest_174259/part_*.csv*")):
        opener=gzip.open if p.endswith(".gz") else open
        with opener(p,"rt",encoding="utf-8-sig",newline="") as f:
            rows.extend(csv.DictReader(f))
    return rows

def year(r):
    y=str(r.get("release_year") or "")
    return int(y) if y.isdigit() else 0

def select_balanced(rows,n=500):
    eligible=[r for r in rows if core.brand_in_tr_retail(r.get("brand_name",""))]
    groups=defaultdict(list)
    for r in eligible:
        groups[core.norm(r.get("brand_name",""))].append(r)
    for b in groups:
        groups[b].sort(key=lambda r:(year(r)>=2018,year(r),int(r["id"])),reverse=True)

    brands=sorted(groups,key=lambda b:(-len(groups[b]),b))
    picked=[]; used=set()
    depth=0
    while len(picked)<n:
        added=0
        for b in brands:
            if depth>=len(groups[b]): continue
            r=groups[b][depth]
            if r["id"] in used: continue
            x=dict(r)
            y=year(r)
            x["pilot_cohort"]="recent_2018_plus" if y>=2018 else ("unknown_year" if y==0 else "historical")
            picked.append(x); used.add(r["id"]); added+=1
            if len(picked)>=n: break
        if not added: break
        depth+=1
    return picked,eligible

def main():
    all_rows=load_all()
    selected,eligible=select_balanced(all_rows,500)
    start=time.time()

    def one(r):
        c=core.extract_commerce(core.make_session(),r)
        return {
          "product_id":r["id"],"brand_name":r["brand_name"],"product_name":r["product_name"],
          "release_year":r.get("release_year",""),"pilot_cohort":r["pilot_cohort"],**c
        }

    results=[]
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs={ex.submit(one,r):r for r in selected}
        for i,fut in enumerate(as_completed(futs),1):
            r=futs[fut]
            try: results.append(fut.result())
            except Exception as e:
                results.append({
                  "product_id":r["id"],"brand_name":r["brand_name"],"product_name":r["product_name"],
                  "release_year":r.get("release_year",""),"pilot_cohort":r["pilot_cohort"],
                  "commerce_status":"worker_error","price_try":"","purchase_url":"","seller_name":"",
                  "error":str(e)[:180]
                })
            if i%25==0:
                priced=sum(bool(x.get("price_try")) for x in results)
                print("PROGRESS",json.dumps({"done":i,"total":len(selected),"priced":priced,
                      "pct":round(100*i/max(1,len(selected)),1)},ensure_ascii=False),flush=True)

    results.sort(key=lambda x:int(x["product_id"]))
    cols=["product_id","brand_name","product_name","release_year","pilot_cohort","commerce_status","price_try","currency",
          "volume_ml","seller_name","purchase_url","stock_status","commerce_image","match_confidence","source_product_name"]
    with (OUT/"commerce_pilot_500.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols,extrasaction="ignore"); w.writeheader(); w.writerows(results)

    def stats(rr):
        return {
          "tested":len(rr),
          "verified":sum(x.get("commerce_status")=="verified" for x in rr),
          "with_price":sum(bool(x.get("price_try")) for x in rr),
          "with_purchase_url":sum(bool(x.get("purchase_url")) for x in rr)
        }
    cohorts={}
    for c in sorted(set(x["pilot_cohort"] for x in results)):
        cohorts[c]=stats([x for x in results if x["pilot_cohort"]==c])
    sellers={}
    statuses={}
    brands_priced=set()
    for x in results:
        st=x.get("commerce_status") or ""; statuses[st]=statuses.get(st,0)+1
        se=x.get("seller_name") or ""
        if se: sellers[se]=sellers.get(se,0)+1
        if x.get("price_try"): brands_priced.add(core.norm(x.get("brand_name","")))
    summary={
      "generated_at":datetime.now(timezone.utc).isoformat(),
      "turkey_scope_total":len(eligible),
      "selected":len(selected),
      "brands_tested":len(set(core.norm(x.get("brand_name","")) for x in selected)),
      "brands_with_price":len(brands_priced),
      "overall":stats(results),"cohorts":cohorts,
      "seller_counts":dict(sorted(sellers.items(),key=lambda kv:(-kv[1],kv[0]))),
      "status_counts":statuses,
      "seconds":round(time.time()-start,1)
    }
    (OUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print("SUMMARY",json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
