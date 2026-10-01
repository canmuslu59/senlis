#!/usr/bin/env python3
import json,re,urllib.parse
import requests
from bs4 import BeautifulSoup

tests=[
 ("vs","https://www.victoriassecret.com.tr/vs/parfum",["bombshell","very sexy","tease","bare"]),
 ("bbw","https://www.bathandbodyworks.com.tr/tum-vucut-spreyleri-ve-parfumler",["dark kiss","japanese cherry blossom","very violet"]),
 ("oriflame","https://tr.oriflame.com/fragrance",["giordani","eclat","amber elixir"]),
]
s=requests.Session()
s.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36","Accept-Language":"tr-TR,tr;q=0.9,en;q=0.8"})

for name,url,needles in tests:
    r=s.get(url,timeout=25,allow_redirects=True)
    soup=BeautifulSoup(r.text,"lxml")
    out=[]
    for a in soup.find_all("a",href=True):
        txt=" ".join(a.get_text(" ",strip=True).split())
        low=txt.lower()
        if txt and any(n in low for n in needles):
            parent=a
            for _ in range(4):
                if not getattr(parent,"parent",None): break
                parent=parent.parent
            ctx=" ".join(parent.get_text(" ",strip=True).split()) if parent else ""
            out.append({
              "text":txt[:300],
              "href":urllib.parse.urljoin(r.url,a.get("href","")),
              "class":" ".join(a.get("class",[])),
              "parent":ctx[:700]
            })
    print("DOM",json.dumps({"site":name,"status":r.status_code,"matches":out[:40]},ensure_ascii=False),flush=True)
