#!/usr/bin/env python3
import json,re,requests,urllib.parse

PAGE="https://www.zara.com/tr/tr/search"
TERM="Red Temptation"
s=requests.Session()
s.headers.update({
 "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36",
 "Accept-Language":"tr-TR,tr;q=0.9,en;q=0.8",
 "Accept":"text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8"
})

r=s.get(PAGE,params={"searchTerm":TERM},timeout=25,allow_redirects=True)
raw=r.text
def grab(pat):
    m=re.search(pat,raw,re.I)
    return m.group(1) if m else ""
cfg={
 "page_status":r.status_code,
 "page_bytes":len(raw),
 "colbensonUrl":grab(r'"colbensonUrl"\s*:\s*"([^"]+)"'),
 "storeId":grab(r'"storeId"\s*:\s*"?([0-9]+)"?'),
 "catalogId":grab(r'"catalogId"\s*:\s*"?([0-9]+)"?'),
 "searchLang":grab(r'"searchLang"\s*:\s*"([^"]+)"'),
 "storeCode":grab(r'"storeCode"\s*:\s*"([^"]+)"'),
 "langCode":grab(r'"langCode"\s*:\s*"([^"]+)"'),
 "storeCountryCode":grab(r'"storeCountryCode"\s*:\s*"([^"]+)"')
}
print("CONFIG",json.dumps(cfg,ensure_ascii=False),flush=True)

base=cfg["colbensonUrl"].rstrip("/")
if not base:
    raise SystemExit("NO_COLBENSON")

langs=[]
for v in [cfg["searchLang"],cfg["langCode"],"tr_TR","tr"]:
    if v and v not in langs: langs.append(v)

tests=[]
for qkey in ["q","query"]:
    for lang in langs:
        params={qkey:TERM,"lang":lang,"start":"0","rows":"12"}
        tests.append((base+"/search",params))
        if cfg["catalogId"]:
            p=dict(params); p["catalog"]=cfg["catalogId"]; tests.append((base+"/search",p))
        if cfg["storeId"]:
            p=dict(params); p["store"]=cfg["storeId"]; tests.append((base+"/search",p))

seen=set()
for url,params in tests:
    key=(url,tuple(sorted(params.items())))
    if key in seen: continue
    seen.add(key)
    try:
        rr=s.get(url,params=params,timeout=20,allow_redirects=True,headers={"Accept":"application/json,text/plain,*/*","Referer":r.url})
        body=rr.text
        print("API",json.dumps({
          "status":rr.status_code,"url":rr.url,"content_type":rr.headers.get("content-type",""),
          "bytes":len(body),"head":body[:1600]
        },ensure_ascii=False),flush=True)
        if rr.status_code==200 and "json" in rr.headers.get("content-type","").lower() and len(body)>100:
            try:
                data=rr.json()
                print("JSON_KEYS",json.dumps(list(data.keys()) if isinstance(data,dict) else type(data).__name__,ensure_ascii=False),flush=True)
                print("JSON_HEAD",json.dumps(data,ensure_ascii=False)[:5000],flush=True)
                break
            except Exception: pass
    except Exception as e:
        print("API_ERROR",repr(e),flush=True)
