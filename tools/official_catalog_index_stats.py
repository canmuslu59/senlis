#!/usr/bin/env python3
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import overnight_full_enrichment as core

s=core.make_session()
out={}
for brand in ["Oriflame","Bath & Body Works","Victoria's Secret"]:
    rows=core._official_catalog_rows(s,brand)
    out[brand]={
      "rows":len(rows),
      "with_price":sum(bool(r.get("price_try")) for r in rows),
      "sample":[{"title":r.get("title"),"price":r.get("price_try"),"url":r.get("url")} for r in rows[:5]]
    }
print("INDEX_STATS",json.dumps(out,ensure_ascii=False),flush=True)
