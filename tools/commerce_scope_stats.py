#!/usr/bin/env python3
import csv,glob,gzip,json,sys
from collections import Counter
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent))
import overnight_full_enrichment as core

rows=[]
for p in sorted(glob.glob("data/master_manifest_174259/part_*.csv*")):
    opener=gzip.open if p.endswith(".gz") else open
    with opener(p,"rt",encoding="utf-8-sig",newline="") as f:
        rows.extend(csv.DictReader(f))

e=[r for r in rows if core.brand_in_tr_retail(r.get("brand_name",""))]
recent=[r for r in e if str(r.get("release_year") or "").isdigit() and int(r["release_year"])>=2018]
recent2023=[r for r in e if str(r.get("release_year") or "").isdigit() and int(r["release_year"])>=2023]
unknown=[r for r in e if not str(r.get("release_year") or "").isdigit()]
counts=Counter(core.norm(r.get("brand_name","")) for r in e)
ids=sorted(int(r["id"]) for r in rows if str(r.get("id","")).isdigit())
expected=set(range(1,174260)); present=set(ids); missing=sorted(expected-present)
summary={
 "catalog_total":len(rows),
 "turkey_scope_products":len(e),
 "turkey_scope_pct":round(100*len(e)/max(1,len(rows)),2),
 "turkey_scope_2018_plus":len(recent),
 "turkey_scope_2023_plus":len(recent2023),
 "turkey_scope_unknown_year":len(unknown),
 "eligible_brands_present":len(counts),
 "manifest_min_id":min(ids) if ids else None,
 "manifest_max_id":max(ids) if ids else None,
 "manifest_unique_ids":len(present),
 "manifest_missing_ids_count":len(missing),
 "manifest_missing_ids":missing[:500],
 "top_20_brands":counts.most_common(20)
}
print("SCOPE_SUMMARY",json.dumps(summary,ensure_ascii=False),flush=True)
