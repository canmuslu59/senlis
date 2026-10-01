#!/usr/bin/env python3
import csv, glob, json
from datetime import datetime, timezone
from pathlib import Path

OUT=Path("image_final"); OUT.mkdir(exist_ok=True)
rows={}
files=glob.glob("image_inputs/**/*.csv",recursive=True)
for p in files:
    with open(p,encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            pid=r.get("product_id")
            if pid: rows[pid]=r
cols=["product_id","brand_name","product_name","image_url","image_source_url","source_url","image_status","http_status","checked_at"]
with (OUT/"SENLIS_images_full.csv").open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=cols); w.writeheader()
    for pid in sorted(rows,key=lambda x:int(x)): w.writerow({k:rows[pid].get(k,"") for k in cols})
expected=174259
missing=[i for i in range(1,expected+1) if str(i) not in rows]
summary={
 "expected":expected,"processed":len(rows),"remaining":len(missing),
 "progress_pct":round(100*len(rows)/expected,2),
 "with_image":sum(bool(r.get("image_url")) for r in rows.values()),
 "image_coverage_pct":round(100*sum(bool(r.get("image_url")) for r in rows.values())/max(1,len(rows)),2),
 "status_counts":{},"input_files":len(files),"generated_at":datetime.now(timezone.utc).isoformat()
}
for r in rows.values():
    k=r.get("image_status") or ""
    summary["status_counts"][k]=summary["status_counts"].get(k,0)+1
(OUT/"SENLIS_images_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
with (OUT/"SENLIS_images_missing_ids.txt").open("w",encoding="utf-8") as f:
    for x in missing: f.write(str(x)+"\n")
print("SUMMARY",json.dumps(summary,ensure_ascii=False),flush=True)
