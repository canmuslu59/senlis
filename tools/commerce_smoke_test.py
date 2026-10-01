#!/usr/bin/env python3
import csv, glob, gzip, json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import overnight_full_enrichment as core

TEST_IDS={"36578","36581","47794","66459","159972","163927","33963","171509","172855","172858"}

def load_test_rows():
    found={}
    paths=sorted(glob.glob("data/master_manifest_174259/part_*.csv") + glob.glob("data/master_manifest_174259/part_*.csv.gz"))
    for p in paths:
        opener=gzip.open if p.endswith(".gz") else open
        with opener(p,"rt",encoding="utf-8-sig",newline="") as f:
            for r in csv.DictReader(f):
                if r.get("id") in TEST_IDS:
                    found[r["id"]]=r
    return [found[i] for i in sorted(TEST_IDS,key=int) if i in found]

# smoke rerun: Boyner+Beymen exact pricing
def main():
    out=Path("commerce_smoke"); out.mkdir(exist_ok=True)
    rows=load_test_rows()
    results=[]
    for r in rows:
        print("TEST",r["id"],r["brand_name"],r["product_name"],flush=True)
        if r["id"] in {"36578","47794"}:
            q=f'"{r["brand_name"]}" "{r["product_name"]}" fiyat TRY'
            dbg=core.search_web(core.make_session(),q)
            print("SEARCH_DEBUG",r["id"],json.dumps(dbg[:10],ensure_ascii=False),flush=True)
        if r["id"]=="47794":
            ss=core.make_session()
            try:
                rr=ss.get("https://www.boyner.com.tr/search",params={"q":f'{r["brand_name"]} {r["product_name"]}'},timeout=20)
                soup=core.BeautifulSoup(rr.text,"lxml")
                links=[]
                for a in soup.find_all("a",href=True):
                    href=a.get("href","")
                    txt=" ".join(a.get_text(" ",strip=True).split())
                    if ("-p-" in href or "/p_" in href) and txt:
                        links.append((txt,href))
                    if len(links)>=12: break
                print("BOYNER_DEBUG",rr.status_code,len(rr.text),soup.title.get_text(" ",strip=True) if soup.title else "",json.dumps(links,ensure_ascii=False),flush=True)
            except Exception as e:
                print("BOYNER_DEBUG_ERROR",repr(e),flush=True)
            probes=[
                ("SEVIL","https://www.sevil.com.tr/catalogsearch/result/",{"q":f'{r["brand_name"]} {r["product_name"]}'}),
                ("SEPHORA","https://www.sephora.com.tr/search",{"q":f'{r["brand_name"]} {r["product_name"]}'}),
                ("BEYMEN","https://www.beymen.com/tr/search",{"q":f'{r["brand_name"]} {r["product_name"]}'})
            ]
            for label,url,params in probes:
                try:
                    pr=ss.get(url,params=params,timeout=20,allow_redirects=True)
                    ps=core.BeautifulSoup(pr.text,"lxml")
                    pl=[]
                    for a in ps.find_all("a",href=True):
                        href=a.get("href",""); txt=" ".join(a.get_text(" ",strip=True).split())
                        if txt and any(k in href.lower() for k in ("product","-p-","/p_","/p/")):
                            pl.append((txt,href))
                        if len(pl)>=8: break
                    print(label+"_DEBUG",pr.status_code,len(pr.text),pr.url,ps.title.get_text(" ",strip=True) if ps.title else "",json.dumps(pl,ensure_ascii=False),flush=True)
                except Exception as e:
                    print(label+"_DEBUG_ERROR",repr(e),flush=True)
        x=core.process(r)
        results.append(x)
        print("RESULT",json.dumps({
            "product_id":x.get("product_id"),
            "commerce_status":x.get("commerce_status"),
            "price_try":x.get("price_try"),
            "seller_name":x.get("seller_name"),
            "purchase_url":x.get("purchase_url"),
            "match_confidence":x.get("match_confidence")
        },ensure_ascii=False),flush=True)

    cols=core.COLS
    with (out/"commerce_smoke.csv").open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols,extrasaction="ignore"); w.writeheader(); w.writerows(results)
    summary={
        "tested":len(results),
        "verified":sum(r.get("commerce_status")=="verified" for r in results),
        "candidate":sum(r.get("commerce_status")=="candidate" for r in results),
        "with_price":sum(bool(r.get("price_try")) for r in results),
        "with_purchase_url":sum(bool(r.get("purchase_url")) for r in results),
        "statuses":{}
    }
    for r in results:
        k=r.get("commerce_status") or ""
        summary["statuses"][k]=summary["statuses"].get(k,0)+1
    (out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print("SUMMARY",json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
