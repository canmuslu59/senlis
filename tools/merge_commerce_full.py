#!/usr/bin/env python3
import csv,glob,json,sqlite3
from pathlib import Path
from datetime import datetime,timezone

OUT=Path("commerce_final"); OUT.mkdir(exist_ok=True)
files=sorted(glob.glob("commerce_inputs/**/commerce_shard_*.csv",recursive=True))
rows_by_id={}
for p in files:
    with open(p,encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            pid=r.get("product_id")
            if pid and pid!="0": rows_by_id[pid]=r
rows=sorted(rows_by_id.values(),key=lambda r:int(r["product_id"]))
cols=["product_id","brand_name","product_name","release_year","commerce_status","price_try","currency",
      "volume_ml","seller_name","purchase_url","stock_status","commerce_image","match_confidence",
      "source_product_name","checked_at","error"]
csv_path=OUT/"SENLIS_commerce_tr_full.csv"
with csv_path.open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=cols,extrasaction="ignore"); w.writeheader(); w.writerows(rows)

db=sqlite3.connect(OUT/"SENLIS_commerce_tr_full.sqlite")
db.execute("""CREATE TABLE IF NOT EXISTS commerce(
 product_id INTEGER PRIMARY KEY, brand_name TEXT, product_name TEXT, release_year TEXT,
 commerce_status TEXT, price_try REAL, currency TEXT, volume_ml REAL, seller_name TEXT,
 purchase_url TEXT, stock_status TEXT, commerce_image TEXT, match_confidence REAL,
 source_product_name TEXT, checked_at TEXT, error TEXT)""")
for r in rows:
    vals=[]
    for c in cols:
        v=r.get(c,"")
        if c in ("price_try","volume_ml","match_confidence"):
            try: v=float(v) if v not in ("",None) else None
            except: v=None
        elif c=="product_id":
            v=int(v)
        vals.append(v)
    db.execute("INSERT OR REPLACE INTO commerce VALUES("+",".join("?" for _ in cols)+")",vals)
db.commit(); db.close()

summary={
 "generated_at":datetime.now(timezone.utc).isoformat(),"input_files":len(files),
 "unique_products":len(rows),
 "verified":sum(r.get("commerce_status")=="verified" for r in rows),
 "with_price":sum(bool(r.get("price_try")) for r in rows),
 "with_purchase_url":sum(bool(r.get("purchase_url")) for r in rows),
 "worker_errors":sum(r.get("commerce_status")=="worker_error" for r in rows)
}
(OUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
print("FINAL",json.dumps(summary,ensure_ascii=False))
