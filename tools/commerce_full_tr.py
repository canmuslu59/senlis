#!/usr/bin/env python3
import csv,glob,gzip,json,os,sys,time
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
from datetime import datetime,timezone

sys.path.insert(0,str(Path(__file__).resolve().parent))
import overnight_full_enrichment as core
from image_sources import clean_source_url

SHARD_INDEX=int(os.environ.get("COMMERCE_SHARD_INDEX","0"))
SHARD_COUNT=int(os.environ.get("COMMERCE_SHARD_COUNT","18"))
WORKERS=int(os.environ.get("COMMERCE_WORKERS","6"))
OUT=Path("commerce_full_out");OUT.mkdir(exist_ok=True)
OUTCSV=OUT/f"commerce_shard_{SHARD_INDEX:02d}.csv"
OUTJSON=OUT/f"commerce_shard_{SHARD_INDEX:02d}_summary.json"

COLS=["product_id","brand_name","product_name","release_year","commerce_status","price_try","currency",
      "volume_ml","seller_name","purchase_url","stock_status","commerce_image","match_confidence",
      "source_product_name","checked_at","error"]

def load_rows():
    eligible=[];overlay={}
    for p in sorted(glob.glob("data/source_urls/part_*.csv")):
        with open(p,encoding="utf-8-sig",newline="") as f:
            for r in csv.DictReader(f):
                if r.get("source_url"):overlay[str(r.get("id",""))]=r["source_url"]
    for p in sorted(glob.glob("data/master_manifest_174259/part_*.csv*")):
        opener=gzip.open if p.endswith(".gz") else open
        with opener(p,"rt",encoding="utf-8-sig",newline="") as f:
            for r in csv.DictReader(f):
                r["source_url"]=clean_source_url(overlay.get(str(r.get("id",""))) or r.get("source_url",""),r.get("id",""))
                if core.commerce_in_scope(r):eligible.append(r)
    eligible.sort(key=lambda r:int(r["id"]))
    return [r for i,r in enumerate(eligible) if i%SHARD_COUNT==SHARD_INDEX],len(eligible)

def save(rows,assigned,total_scope,start):
    rows.sort(key=lambda r:int(r["product_id"]))
    with OUTCSV.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=COLS,extrasaction="ignore");w.writeheader();w.writerows(rows)
    summary={"shard_index":SHARD_INDEX,"shard_count":SHARD_COUNT,"turkey_scope_total":total_scope,
      "assigned":assigned,"processed":len(rows),"remaining":max(0,assigned-len(rows)),
      "verified":sum(r.get("commerce_status")=="verified" for r in rows),
      "with_price":sum(bool(r.get("price_try")) for r in rows),
      "with_purchase_url":sum(bool(r.get("purchase_url")) for r in rows),
      "worker_errors":sum(r.get("commerce_status")=="worker_error" for r in rows),
      "disabled_hosts":sorted(core.HOST_DISABLED),
      "seconds":round(time.time()-start,1),"generated_at":datetime.now(timezone.utc).isoformat()}
    OUTJSON.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    return summary

def main():
    rows,total_scope=load_rows();start=time.time();results=[]
    print("START",json.dumps({"shard":SHARD_INDEX,"shards":SHARD_COUNT,"assigned":len(rows),"scope":total_scope}),flush=True)
    def one(r):
        c=core.extract_commerce(core.thread_session(),r)
        return {"product_id":r["id"],"brand_name":r["brand_name"],"product_name":r["product_name"],
          "release_year":r.get("release_year",""),**c,"checked_at":datetime.now(timezone.utc).isoformat(),"error":""}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs={ex.submit(one,r):r for r in rows}
        for i,fut in enumerate(as_completed(futs),1):
            r=futs[fut]
            try:results.append(fut.result())
            except Exception as e:
                results.append({"product_id":r["id"],"brand_name":r["brand_name"],"product_name":r["product_name"],
                  "release_year":r.get("release_year",""),"commerce_status":"worker_error","price_try":"","currency":"TRY",
                  "volume_ml":"","seller_name":"","purchase_url":"","stock_status":"unknown","commerce_image":"",
                  "match_confidence":"","source_product_name":"","checked_at":datetime.now(timezone.utc).isoformat(),"error":str(e)[:180]})
            if i%100==0:
                sm=save(results,len(rows),total_scope,start);print("CHECKPOINT",json.dumps(sm,ensure_ascii=False),flush=True)
    print("SUMMARY",json.dumps(save(results,len(rows),total_scope,start),ensure_ascii=False),flush=True)

if __name__=="__main__":main()
