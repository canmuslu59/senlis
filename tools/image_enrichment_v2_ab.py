#!/usr/bin/env python3
"""
SENLIS Image Enrichment V2 A/B
- Never adds/removes master products.
- Uses a deterministic evenly-spaced sample of the 174259 master rows.
- Runs the old direct-source extractor as baseline.
- V2 reuses valid direct hits, rejects known generic/placeholder images,
  then discovers canonical Parfumo and other matching product pages via
  repository search helpers (Bing/DDG) and extracts richer image markup.
- Hugging Face doevent/perfume rows are matched against dataset metadata;
  exact/strong matches are recorded as archive-backed image references.
"""
import csv, glob, gzip, html, json, os, re, time, urllib.parse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz

import image_enrichment as baseline
import overnight_full_enrichment as core
from image_sources import GENERIC_IMAGE_PATTERNS

LIMIT=int(os.environ.get("AB_LIMIT","1000"))
WORKERS=int(os.environ.get("WORKERS","8"))
SEARCH_WORKERS=int(os.environ.get("SEARCH_WORKERS","4"))
MAX_CANDIDATES=int(os.environ.get("MAX_CANDIDATES","5"))
OUT=Path(os.environ.get("V2_OUT","image_v2_out")); OUT.mkdir(exist_ok=True)
OUTCSV=OUT/"image_v2_ab_1000.csv"
OUTJSON=OUT/"image_v2_ab_1000_summary.json"
HF_META_URL="https://huggingface.co/datasets/doevent/perfume/resolve/main/perfumes.csv?download=true"
HF_ZIP_URL="https://huggingface.co/datasets/doevent/perfume/resolve/main/images.zip?download=true"

BAD_IMAGE_PATTERNS=list(GENERIC_IMAGE_PATTERNS)
BAD_PAGE_HOSTS={
    "facebook.com","instagram.com","youtube.com","tiktok.com","pinterest.com",
    "reddit.com","bing.com","google.com","duckduckgo.com"
}
PREFERRED_HOSTS={
    "parfumo.com":12,
    "perfume.com":6,
    "sephora.com.tr":8,"boyner.com.tr":8,"beymen.com":8,"sevil.com.tr":8,
    "rossmann.com.tr":8,"watsons.com.tr":8,"gratis.com":8,
    "trendyol.com":6,"hepsiburada.com":6,"amazon.com.tr":6,"n11.com":6,
}

def norm(s):
    s=html.unescape(str(s or "")).lower()
    s=s.replace("ı","i").replace("ş","s").replace("ğ","g").replace("ü","u").replace("ö","o").replace("ç","c")
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",s)).strip()

def host(url):
    try:
        h=urllib.parse.urlparse(url).netloc.lower().split(":")[0]
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""

def load_all():
    rows=[]
    for p in sorted(glob.glob("data/master_manifest_174259/part_*.csv*")):
        opener=gzip.open if p.endswith(".gz") else open
        with opener(p,"rt",encoding="utf-8-sig",newline="") as f:
            rows.extend(csv.DictReader(f))
    rows.sort(key=lambda r:int(r["id"]))
    return rows

def evenly_spaced(rows,n):
    if n<=0 or n>=len(rows): return rows
    idx=sorted({round(i*(len(rows)-1)/(n-1)) for i in range(n)})
    return [rows[i] for i in idx]

def generic_image(url):
    u=(url or "").lower()
    if not u: return True
    return any(x in u for x in BAD_IMAGE_PATTERNS)

def image_from_json(obj):
    if isinstance(obj,list):
        for x in obj:
            y=image_from_json(x)
            if y: return y
        return ""
    if not isinstance(obj,dict): return ""
    typ=obj.get("@type")
    is_product=typ=="Product" or (isinstance(typ,list) and "Product" in typ)
    if is_product:
        im=obj.get("image")
        if isinstance(im,list): im=im[0] if im else ""
        if isinstance(im,dict): im=im.get("url") or im.get("contentUrl") or ""
        if im: return str(im)
    for v in obj.values():
        y=image_from_json(v)
        if y: return y
    return ""

def rich_image(soup,base_url,product):
    metas=[
        soup.find("meta",attrs={"property":"og:image"}),
        soup.find("meta",attrs={"name":"twitter:image"}),
        soup.find("meta",attrs={"itemprop":"image"}),
    ]
    for m in metas:
        if m and m.get("content"):
            u=urllib.parse.urljoin(base_url,m["content"])
            if not generic_image(u): return u,"meta"
    for tag in soup.find_all("script",attrs={"type":"application/ld+json"}):
        try:
            u=image_from_json(json.loads(tag.get_text(" ",strip=True)))
        except Exception:
            u=""
        if u:
            u=urllib.parse.urljoin(base_url,u)
            if not generic_image(u): return u,"jsonld"
    target=set(norm(product).split())
    ranked=[]
    for im in soup.find_all("img"):
        vals=[]
        for attr in ("src","data-src","data-original","data-lazy-src","data-image"):
            if im.get(attr): vals.append(im.get(attr))
        if im.get("srcset"):
            vals.extend(x.strip().split(" ")[0] for x in im.get("srcset").split(",") if x.strip())
        if not vals: continue
        alt=norm((im.get("alt") or "")+" "+(im.get("title") or ""))
        overlap=len(target & set(alt.split()))
        for raw in vals:
            u=urllib.parse.urljoin(base_url,raw)
            if not u.startswith("http") or generic_image(u): continue
            lu=u.lower()
            if any(x in lu for x in ("icon","avatar","badge","payment","flag","loader","banner")): continue
            score=overlap*8
            try:
                w=int(re.sub(r"\D","",str(im.get("width") or "0")) or 0)
                h=int(re.sub(r"\D","",str(im.get("height") or "0")) or 0)
                if w>=250 or h>=250: score+=3
            except Exception: pass
            if any(x in lu for x in ("product","perfume","parfum","fragrance","media.")): score+=2
            ranked.append((score,u))
    if ranked:
        ranked.sort(reverse=True)
        if ranked[0][0]>=2: return ranked[0][1],"img"
    return "",""

def title_compatible(row,title):
    if not title: return False,0.0
    try:
        score=float(core.product_match_score(row.get("brand_name",""),row.get("product_name",""),title))
        ok=core.brand_compatible(row.get("brand_name",""),title) and core.variant_compatible(
            row.get("brand_name",""),row.get("product_name",""),title)
        return bool(ok and score>=72),score
    except Exception:
        target=norm(f'{row.get("brand_name","")} {row.get("product_name","")}')
        score=fuzz.token_set_ratio(target,norm(title))
        return score>=78,float(score)

def extract_candidate(session,row,url):
    h=host(url)
    if not h or h in BAD_PAGE_HOSTS or h=="fragrantica.com": return None
    try:
        r=session.get(url,timeout=18,allow_redirects=True)
        if r.status_code!=200 or "text/html" not in r.headers.get("content-type",""): return None
        soup=BeautifulSoup(r.text,"lxml")
        title=soup.title.get_text(" ",strip=True) if soup.title else ""
        ok,score=title_compatible(row,title)
        if not ok: return None
        im,method=rich_image(soup,r.url,row.get("product_name",""))
        if not im: return None
        bonus=PREFERRED_HOSTS.get(host(r.url),0)
        return {
            "image_url":im,"image_source_url":r.url,"image_method":method,
            "image_status":"v2_web","match_score":round(min(100,score+bonus),1),
            "source_host":host(r.url)
        }
    except Exception:
        return None

def parfumo_slug_variants(row):
    brand=row.get("brand_name",""); product=row.get("product_name","")
    variants=[product]
    stripped=re.sub(r"\s*\([^)]*\)\s*"," ",product).strip()
    if stripped and stripped not in variants: variants.append(stripped)
    for suffix in [" Eau de Parfum"," Eau de Toilette"," Parfum"," EDT"," EDP"]:
        if stripped.lower().endswith(suffix.lower()):
            x=stripped[:-len(suffix)].strip()
            if x and x not in variants: variants.append(x)
    def slug(s):
        import unicodedata
        s=unicodedata.normalize("NFKD",str(s or ""))
        s="".join(ch for ch in s if not unicodedata.combining(ch))
        s=s.replace("&"," and ").replace("'","_").replace("’","_")
        return re.sub(r"_+","_",re.sub(r"[^A-Za-z0-9]+","_",s).strip("_"))
    return [f"https://www.parfumo.com/Perfumes/{slug(brand)}/{slug(v)}" for v in variants[:4]]

def discover_v2(row,baseline_rec):
    # Keep only a quality-screened baseline image.
    if baseline_rec.get("image_url") and not generic_image(baseline_rec.get("image_url")):
        return {
            "image_url":baseline_rec["image_url"],
            "image_source_url":baseline_rec.get("image_source_url") or row.get("source_url",""),
            "image_method":"baseline_verified","image_status":"v2_reuse",
            "match_score":100.0,"source_host":host(baseline_rec.get("image_source_url") or row.get("source_url",""))
        }
    # HF is handled by metadata index before network discovery.
    if host(row.get("source_url",""))=="huggingface.co":
        return None
    s=core.make_session()
    candidates=[]
    seen=set()
    # Canonical Parfumo guesses are cheap and often recover source URL case/slug drift.
    for u in parfumo_slug_variants(row):
        if u in seen: continue
        seen.add(u); candidates.append(u)
    brand=row.get("brand_name",""); product=row.get("product_name","")
    queries=[
        f'site:parfumo.com/Perfumes "{brand}" "{product}"',
        f'"{brand}" "{product}" perfume',
    ]
    for q in queries:
        try:
            for title,u in core.search_web(s,q):
                if u.startswith("http") and u not in seen:
                    seen.add(u); candidates.append(u)
                if len(candidates)>=14: break
        except Exception: pass
        if len(candidates)>=14: break
    best=None
    for u in candidates[:MAX_CANDIDATES+4]:
        rec=extract_candidate(s,row,u)
        if not rec: continue
        if best is None or rec["match_score"]>best["match_score"]: best=rec
        if rec["match_score"]>=90 and rec["source_host"]=="parfumo.com": break
    return best

def load_hf_index():
    try:
        r=requests.get(HF_META_URL,timeout=60)
        if r.status_code!=200: return []
        text=r.content.decode("utf-8-sig","replace").splitlines()
        rows=list(csv.DictReader(text))
        return [x for x in rows if x.get("brand") and x.get("name_perfume") and x.get("image_name")]
    except Exception:
        return []

def hf_match(row,hf_rows):
    brand=norm(row.get("brand_name","")); product=norm(row.get("product_name",""))
    if not brand or not product: return None
    best=None
    for x in hf_rows:
        xb=norm(x.get("brand",""))
        if fuzz.ratio(brand,xb)<82 and fuzz.token_set_ratio(brand,xb)<88: continue
        xp=norm(x.get("name_perfume",""))
        ps=fuzz.ratio(product,xp)*0.45+fuzz.token_set_ratio(product,xp)*0.55
        if ps<84: continue
        score=0.35*max(fuzz.ratio(brand,xb),fuzz.token_set_ratio(brand,xb))+0.65*ps
        if best is None or score>best[0]: best=(score,x)
    if not best or best[0]<87: return None
    x=best[1]
    return {
        "image_url":"",
        "image_source_url":HF_ZIP_URL,
        "image_method":"hf_images_zip",
        "image_status":"v2_hf_archive",
        "match_score":round(best[0],1),
        "source_host":"huggingface.co",
        "hf_image_name":x.get("image_name","")
    }

def main():
    all_rows=load_all()
    rows=evenly_spaced(all_rows,LIMIT)
    print("SAMPLE",json.dumps({
        "master_total":len(all_rows),"sample_total":len(rows),
        "source_hosts":dict(Counter(host(r.get("source_url","")) for r in rows))
    },ensure_ascii=False),flush=True)

    # Baseline: same extractor used by the current full image workflow.
    baseline_results={}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs={ex.submit(baseline.fetch_image,r,host(r.get("source_url",""))=="fragrantica.com"):r for r in rows}
        for i,fut in enumerate(as_completed(futs),1):
            r=futs[fut]
            try: rec=fut.result()
            except Exception as e:
                rec={"product_id":r["id"],"image_url":"","image_status":"error","http_status":"","image_source_url":"","source_url":r.get("source_url","")}
            baseline_results[str(r["id"])]=rec
            if i%100==0: print("BASELINE_PROGRESS",i,"/",len(rows),flush=True)

    # Repeated generic images are counted as invalid even when URL pattern was unknown.
    image_counts=Counter(x.get("image_url","") for x in baseline_results.values() if x.get("image_url"))
    for rec in baseline_results.values():
        u=rec.get("image_url","")
        rec["quality_ok"]=bool(u and not generic_image(u) and image_counts[u]<=10)

    hf_rows=load_hf_index()
    final={}
    # Exact/strong HF archive matches first.
    for r in rows:
        if host(r.get("source_url",""))=="huggingface.co":
            hit=hf_match(r,hf_rows)
            if hit: final[str(r["id"])]=hit

    todo=[r for r in rows if str(r["id"]) not in final]
    with ThreadPoolExecutor(max_workers=SEARCH_WORKERS) as ex:
        futs={ex.submit(discover_v2,r,baseline_results[str(r["id"])]):r for r in todo}
        for i,fut in enumerate(as_completed(futs),1):
            r=futs[fut]
            try: rec=fut.result()
            except Exception: rec=None
            if rec: final[str(r["id"])]=rec
            if i%50==0: print("V2_PROGRESS",i,"/",len(todo),flush=True)

    cols=[
        "product_id","brand_name","product_name","release_year","source_url","source_host",
        "baseline_status","baseline_http","baseline_image_url","baseline_quality_ok",
        "v2_status","v2_method","v2_image_url","v2_image_source_url","v2_source_host",
        "v2_match_score","hf_image_name"
    ]
    outrows=[]
    for r in rows:
        b=baseline_results.get(str(r["id"]),{})
        v=final.get(str(r["id"]),{})
        outrows.append({
            "product_id":r["id"],"brand_name":r.get("brand_name",""),"product_name":r.get("product_name",""),
            "release_year":r.get("release_year",""),"source_url":r.get("source_url",""),"source_host":host(r.get("source_url","")),
            "baseline_status":b.get("image_status",""),"baseline_http":b.get("http_status",""),
            "baseline_image_url":b.get("image_url",""),"baseline_quality_ok":bool(b.get("quality_ok")),
            "v2_status":v.get("image_status",""),"v2_method":v.get("image_method",""),
            "v2_image_url":v.get("image_url",""),"v2_image_source_url":v.get("image_source_url",""),
            "v2_source_host":v.get("source_host",""),"v2_match_score":v.get("match_score",""),
            "hf_image_name":v.get("hf_image_name","")
        })
    with OUTCSV.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(outrows)

    baseline_raw=sum(bool(x.get("image_url")) for x in baseline_results.values())
    baseline_verified=sum(bool(x.get("quality_ok")) for x in baseline_results.values())
    v2_web=sum(bool(x.get("image_url")) and x.get("image_status")!="v2_hf_archive" for x in final.values())
    v2_hf=sum(x.get("image_status")=="v2_hf_archive" and bool(x.get("hf_image_name")) for x in final.values())
    v2_verified=v2_web+v2_hf
    status_counts=Counter(x.get("image_status","not_found") for x in final.values())
    method_counts=Counter(x.get("image_method","") for x in final.values())
    summary={
        "master_total":len(all_rows),"sample_total":len(rows),
        "sample_source_hosts":dict(Counter(host(r.get("source_url","")) for r in rows)),
        "baseline_raw_with_image":baseline_raw,
        "baseline_raw_pct":round(100*baseline_raw/max(1,len(rows)),2),
        "baseline_verified_with_image":baseline_verified,
        "baseline_verified_pct":round(100*baseline_verified/max(1,len(rows)),2),
        "v2_verified_with_image":v2_verified,
        "v2_verified_pct":round(100*v2_verified/max(1,len(rows)),2),
        "v2_web_image":v2_web,"v2_hf_archive_image":v2_hf,
        "absolute_point_lift":round(100*(v2_verified-baseline_verified)/max(1,len(rows)),2),
        "relative_lift_pct":round(100*(v2_verified-baseline_verified)/max(1,baseline_verified),2) if baseline_verified else None,
        "v2_status_counts":dict(status_counts),"v2_method_counts":dict(method_counts),
        "hf_metadata_rows":len(hf_rows),
        "generated_at":datetime.now(timezone.utc).isoformat()
    }
    OUTJSON.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print("SUMMARY",json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
