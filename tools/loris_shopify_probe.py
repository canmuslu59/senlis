#!/usr/bin/env python3
import json,requests

URLS=[
 "https://lorisparfum.com/collections/parfum/products.json?limit=250&page=1",
 "https://lorisparfum.com/collections/parfum/products.json?limit=250&page=2",
 "https://lorisparfum.com/products.json?limit=250&page=1"
]
s=requests.Session()
s.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36",
                  "Accept-Language":"tr-TR,tr;q=0.9,en;q=0.8","Accept":"application/json,text/plain,*/*"})
for url in URLS:
    try:
        r=s.get(url,timeout=30,allow_redirects=True)
        info={"url":r.url,"status":r.status_code,"content_type":r.headers.get("content-type",""),"bytes":len(r.content)}
        try:
            data=r.json()
            products=data.get("products",[]) if isinstance(data,dict) else []
            info["products"]=len(products)
            info["sample"]=[{
              "id":p.get("id"),"title":p.get("title"),"handle":p.get("handle"),
              "variants":[{"title":v.get("title"),"price":v.get("price"),"available":v.get("available")} for v in (p.get("variants") or [])[:3]]
            } for p in products[:5]]
        except Exception:
            info["head"]=r.text[:1000]
        print("LORIS_JSON",json.dumps(info,ensure_ascii=False),flush=True)
    except Exception as e:
        print("LORIS_ERROR",json.dumps({"url":url,"error":repr(e)},ensure_ascii=False),flush=True)
