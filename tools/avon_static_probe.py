#!/usr/bin/env python3
import json,re,urllib.parse,requests
from bs4 import BeautifulSoup

URLS=[
 "https://kozmetik.avon.com.tr/301-307/parfum/kadin-parfum/",
 "https://kozmetik.avon.com.tr/301-308/parfum/erkek-parfum/",
 "https://kozmetik.avon.com.tr/301/parfum/"
]
s=requests.Session()
s.headers.update({
 "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36",
 "Accept-Language":"tr-TR,tr;q=0.9,en;q=0.8",
 "Accept":"text/html,application/xhtml+xml,*/*;q=0.8"
})
for url in URLS:
    try:
        r=s.get(url,timeout=30,allow_redirects=True)
        soup=BeautifulSoup(r.text,"lxml")
        matches=[]; seen=set()
        for a in soup.find_all("a",href=True):
            href=urllib.parse.urljoin(r.url,a.get("href",""))
            txt=" ".join(a.get_text(" ",strip=True).split())
            if not txt or href in seen: continue
            hay=(txt+" "+href).lower()
            if not any(k in hay for k in ["parfum","parfüm","edp","edt","far-away","attraction","little-black","today"]):
                continue
            parent=a
            for _ in range(5):
                if not getattr(parent,"parent",None): break
                parent=parent.parent
            ctx=" ".join(parent.get_text(" ",strip=True).split()) if parent else txt
            if len(ctx)>1500: ctx=ctx[:1500]
            seen.add(href)
            matches.append({"text":txt[:300],"href":href,"ctx":ctx})
            if len(matches)>=30: break
        raw=r.text
        price_samples=re.findall(r"(?:₺|TL)\s*\d[\d.,]*|\d[\d.,]*\s*(?:₺|TL)",raw,re.I)[:20]
        print("AVON_STATIC",json.dumps({
          "status":r.status_code,"bytes":len(r.content),"url":r.url,
          "title":soup.title.get_text(" ",strip=True) if soup.title else "",
          "matches":matches,"price_samples":price_samples,
          "has_jsonld":bool(soup.find("script",attrs={"type":"application/ld+json"}))
        },ensure_ascii=False),flush=True)
    except Exception as e:
        print("AVON_STATIC_ERROR",json.dumps({"url":url,"error":repr(e)},ensure_ascii=False),flush=True)
