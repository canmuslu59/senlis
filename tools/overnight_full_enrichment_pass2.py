#!/usr/bin/env python3
import csv, glob, json, os, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import overnight_full_enrichment as core

def load_previous():
    rows=[]
    for p in glob.glob("previous/**/*.csv",recursive=True):
        try:
            with open(p,encoding="utf-8-sig",newline="") as f:
                for r in csv.DictReader(f):
                    if r.get("product_id") and r["product_id"]!="0": rows.append(r)
        except Exception:
            pass
    # one row per product
    return list({r["product_id"]:r for r in rows}.values())

def main():
    assigned=core.load_rows()
    previous=load_previous()
    seen={r["product_id"] for r in previous}
    remaining=[r for r in assigned if r["id"] not in seen]
    done=list(previous)
    start=time.time()
    max_seconds=int(os.environ.get("MAX_SECONDS","9600"))
    workers=int(os.environ.get("WORKERS","4"))
    idx=0
    print(json.dumps({"assigned":len(assigned),"already_done":len(previous),"remaining_start":len(remaining)},ensure_ascii=False),flush=True)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        while idx<len(remaining) and time.time()-start < max_seconds-120:
            batch=remaining[idx:idx+workers*4]; idx+=len(batch)
            futs=[ex.submit(core.process,r) for r in batch]
            for fut in as_completed(futs):
                try: done.append(fut.result())
                except Exception as e:
                    pass
            if len(done)%100 < workers*4:
                print("CHECKPOINT",json.dumps(core.save(done,len(assigned),start),ensure_ascii=False),flush=True)
    print("FINAL",json.dumps(core.save(done,len(assigned),start),ensure_ascii=False),flush=True)

if __name__=="__main__": main()
