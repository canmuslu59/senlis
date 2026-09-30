#!/usr/bin/env python3
import csv, glob, json, sqlite3
from datetime import datetime, timezone
from pathlib import Path

OUT=Path("final"); OUT.mkdir(exist_ok=True)
rows={}
for p in glob.glob("final_inputs/**/*.csv",recursive=True):
    with open(p,encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            pid=r.get("product_id")
            if pid and pid!="0": rows[pid]=r

manifest={}
for p in sorted(glob.glob("data/full_manifest/part_*.csv")):
    with open(p,encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f): manifest[r["id"]]=r

cols=["product_id","brand_name","product_name","existing_release_year","release_year_candidate","notes_candidate",
      "image_url_candidate","image_source_url","static_status","static_http","static_source","commerce_status",
      "volume_ml","price_try","currency","seller_name","purchase_url","stock_status","commerce_image",
      "match_confidence","source_product_name","checked_at","static_error"]

csvout=OUT/"SENLIS_overnight_enrichment.csv"
with csvout.open("w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
    for pid in sorted(rows,key=lambda x:int(x)): w.writerow({k:rows[pid].get(k,"") for k in cols})

remaining=[manifest[k] for k in sorted(manifest,key=lambda x:int(x)) if k not in rows]
with (OUT/"SENLIS_overnight_remaining.csv").open("w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f,fieldnames=["id","brand_name","product_name","release_year"]);w.writeheader();w.writerows(remaining)

db=sqlite3.connect(OUT/"SENLIS_overnight_enrichment.sqlite")
db.execute("""CREATE TABLE enrichment_results(
 product_id INTEGER PRIMARY KEY, brand_name TEXT, product_name TEXT, existing_release_year TEXT,
 release_year_candidate TEXT, notes_candidate TEXT, image_url_candidate TEXT, image_source_url TEXT,
 static_status TEXT, static_http TEXT, static_source TEXT, commerce_status TEXT, volume_ml REAL,
 price_try REAL, currency TEXT, seller_name TEXT, purchase_url TEXT, stock_status TEXT, commerce_image TEXT,
 match_confidence REAL, source_product_name TEXT, checked_at TEXT, static_error TEXT)""")
for pid in sorted(rows,key=lambda x:int(x)):
    r=rows[pid]
    vals=[r.get(k) or None for k in cols]
    db.execute("INSERT OR REPLACE INTO enrichment_results VALUES("+",".join(["?"]*len(cols))+")",vals)
db.commit();db.close()

summary={
 "catalog_total":len(manifest),"processed":len(rows),"remaining":len(remaining),
 "progress_pct":round(100*len(rows)/max(1,len(manifest)),2),
 "with_image":sum(bool(r.get("image_url_candidate")) for r in rows.values()),
 "with_year_candidate":sum(bool(r.get("release_year_candidate")) for r in rows.values()),
 "with_notes_candidate":sum(bool(r.get("notes_candidate")) for r in rows.values()),
 "with_price":sum(bool(r.get("price_try")) for r in rows.values()),
 "with_purchase_url":sum(bool(r.get("purchase_url")) for r in rows.values()),
 "generated_at":datetime.now(timezone.utc).isoformat()
}
(OUT/"SENLIS_overnight_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))
