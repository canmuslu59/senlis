#!/usr/bin/env python3
import csv,glob,gzip,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import overnight_full_enrichment as core

master={}
for p in sorted(glob.glob("data/master_manifest_174259/part_*.csv*")):
    opener=gzip.open if p.endswith(".gz") else open
    with opener(p,"rt",encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f): master[str(r["id"])]=r

with open("data/official_price_index.csv",encoding="utf-8-sig",newline="") as f:
    idx=list(csv.DictReader(f))

allowed={"tr.oriflame.com","victoriassecret.com.tr","bathandbodyworks.com.tr"}
seen=set(); errors=[]
for r in idx:
    pid=str(r.get("product_id") or "")
    if pid in seen: errors.append(f"duplicate id {pid}")
    seen.add(pid)
    m=master.get(pid)
    if not m:
        errors.append(f"missing master id {pid}"); continue
    if core.norm(m.get("brand_name"))!=core.norm(r.get("brand_name")):
        errors.append(f"brand mismatch {pid}: {m.get('brand_name')} != {r.get('brand_name')}")
    if core.norm(m.get("product_name"))!=core.norm(r.get("product_name")):
        errors.append(f"product mismatch {pid}: {m.get('product_name')} != {r.get('product_name')}")
    try:
        if float(r.get("price_try") or 0)<=0: errors.append(f"bad price {pid}")
    except: errors.append(f"bad price {pid}")
    if r.get("seller_name") not in allowed:
        errors.append(f"bad seller {pid}: {r.get('seller_name')}")
    try:
        if float(r.get("match_confidence") or 0)<0.82: errors.append(f"low confidence {pid}")
    except: errors.append(f"bad confidence {pid}")
    if not str(r.get("purchase_url") or "").startswith("https://"):
        errors.append(f"bad url {pid}")

print("INDEX_VALIDATE",{"rows":len(idx),"unique_ids":len(seen),"errors":len(errors)})
for e in errors[:50]: print("ERROR",e)
if errors: raise SystemExit(1)
print("OFFICIAL_PRICE_INDEX_OK",len(idx))
