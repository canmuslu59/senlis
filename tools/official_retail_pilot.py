#!/usr/bin/env python3
# trigger official retail pilot 20261001
import csv,glob,gzip,json,sys
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from datetime import datetime,timezone

sys.path.insert(0,str(Path(__file__).resolve().parent))
import overnight_full_enrichment as core

OUT=Path("official_retail_pilot"); OUT.mkdir(exist_ok=True)
TARGETS={"oriflame":30,"bath body works":30,"victoria s secret":30}

def load_rows():
    rows=[]
    for p in sorted(glob.glob("data/master_manifest_174259/part_*.csv*")):
        opener=gzip.open if p.endswith(".gz") else open
        with opener(p,"rt",encoding="utf-8-sig",newline="") as f:
            rows.extend(csv.DictReader(f))
    return rows

def main():
    all_rows=load_rows()
    selected=[]
    for brand,n in TARGETS.items():
        rows=[r for r in all_rows if core.norm(r.get("brand_name",""))==brand]
        rows.sort(key=lambda r:(
            int(r.get("release_year") or 0) if str(r.get("release_year") or "").isdigit() else 0,
            int(r["id"])
        ),reverse=True)
        # Bias to recent/current products, then unknown-year products if needed.
        recent=[r for r in rows if str(r.get("release_year") or "").isdigit() and int(r["release_year"])>=2020]
        unknown=[r for r in rows if not str(r.get("release_year") or "").isdigit()]
        ordered=recent+unknown+[r for r in rows if r not in recent and r not in unknown]
        seen=set()
        for r in ordered:
            if r["id"] in seen: continue
            x=dict(r); x["pilot_brand"]=brand
            selected.append(x); seen.add(r["id"])
            if len(seen)>=n: break

    def one(r):
        s=core.make_session()
        c=core.extract_commerce(s,r)
        return {"product_id":r["id"],"brand_name":r["brand_name"],"product_name":r["product_name"],
                "release_year":r.get("release_year",""),**c}

    results=[]
    with ThreadPoolExecutor(max_workers=6) as ex:
        futs={ex.submit(one,r):r for r in selected}
        for i,fut in enumerate(as_completed(futs),1):
            r=futs[fut]
            try: results.append(fut.result())
            except Exception as e:
                results.append({"product_id":r["id"],"brand_name":r["brand_name"],"product_name":r["product_name"],
                                "release_year":r.get("release_year",""),"commerce_status":"worker_error","error":str(e)[:180]})
            if i%10==0: print("PROGRESS",i,"/",len(selected),flush=True)

    results.sort(key=lambda r:(r["brand_name"],int(r["product_id"])))
    cols=["product_id","brand_name","product_name","release_year","commerce_status","price_try","currency","volume_ml",
          "seller_name","purchase_url","stock_status","commerce_image","match_confidence","source_product_name"]
    with (OUT/"official_retail_pilot.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols,extrasaction="ignore"); w.writeheader(); w.writerows(results)
    by_brand={}
    for brand in TARGETS:
        rr=[x for x in results if core.norm(x.get("brand_name",""))==brand]
        by_brand[brand]={
          "tested":len(rr),"verified":sum(x.get("commerce_status")=="verified" for x in rr),
          "with_price":sum(bool(x.get("price_try")) for x in rr),
          "official":sum(x.get("seller_name") in {"tr.oriflame.com","victoriassecret.com.tr","bathandbodyworks.com.tr"} for x in rr)
        }
    summary={"generated_at":datetime.now(timezone.utc).isoformat(),"tested":len(results),
             "verified":sum(x.get("commerce_status")=="verified" for x in results),
             "with_price":sum(bool(x.get("price_try")) for x in results),
             "by_brand":by_brand,"seller_counts":{},"status_counts":{}}
    for x in results:
        seller=x.get("seller_name") or ""
        if seller: summary["seller_counts"][seller]=summary["seller_counts"].get(seller,0)+1
        st=x.get("commerce_status") or ""
        summary["status_counts"][st]=summary["status_counts"].get(st,0)+1
    (OUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print("SUMMARY",json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=="__main__": main()
