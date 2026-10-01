#!/usr/bin/env python3
import json,re,unicodedata,urllib.parse

GENERIC_IMAGE_PATTERNS=(
 "social-thumbnails/datasets/","perfume-social-cards/","/mdimg/perfume/social.",
 "/perfume_social/","/assets/images/perfume_bottle/480.png","placeholder",
 "no-image","no_image","default-image","default_image","favicon","sprite","logo."
)

def norm(s):
    s=unicodedata.normalize("NFKD",str(s or "").lower())
    s="".join(ch for ch in s if not unicodedata.combining(ch))
    s=s.replace("ı","i").replace("ş","s").replace("ğ","g").replace("ü","u").replace("ö","o").replace("ç","c")
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",s)).strip()

def host(url):
    try:
        h=urllib.parse.urlparse(str(url or "")).netloc.lower().split(":")[0]
        return h[4:] if h.startswith("www.") else h
    except Exception:return ""

def clean_source_url(url,product_id):
    u=str(url or "").strip()
    try:pid=int(product_id)
    except Exception:return u
    if pid%1000==0 and u.endswith(str(pid+1)):
        cut=u[:-len(str(pid+1))]
        if cut.endswith(".html") or re.search(r"/[^/]+$",cut):u=cut
    return u

def fragrantica_image(url):
    u=str(url or "")
    m=re.search(r"-(\d+)\.html(?:\d+)?(?:[?#].*)?$",u,re.I)
    return f"https://fimgs.net/mdimg/perfume/375x500.{m.group(1)}.jpg" if m else ""

def normalize_image(url):
    u=str(url or "").strip()
    if not u:return ""
    if "media.parfumo.com/perfume_social/" in u:
        u=u.replace("/perfume_social/","/perfumes/")
        if "?" not in u:u+="?width=720&aspect_ratio=1:1"
    return u

def first_image_url(im):
    if isinstance(im,str):return im.strip()
    if isinstance(im,list):
        for x in im:
            u=first_image_url(x)
            if u:return u
        return ""
    if isinstance(im,dict):
        for k in ("url","contentUrl","image","src"):
            if k in im:
                u=first_image_url(im.get(k))
                if u:return u
    return ""

def generic_image(url):
    u=str(url or "").lower()
    return (not u) or any(x in u for x in GENERIC_IMAGE_PATTERNS)

def image_matches_product(url,brand,product):
    u=str(url or "")
    if host(u)!="media.parfumo.com":return True
    path=urllib.parse.urlparse(u).path.lower()
    base=path.rsplit("/",1)[-1]
    if not base:return False
    tokens=[x for x in norm(f"{brand} {product}").split() if len(x)>=3 and x not in {"eau","parfum","perfume","edp","edt","spray","the","and","for"}]
    if not tokens:return True
    bnorm=norm(base)
    return any(t in bnorm for t in tokens)

def parfumo_page_verified(soup,brand,product):
    im=soup.find("img",attrs={"itemprop":"image"})
    if not im:return False
    u=im.get("src") or im.get("data-src") or ""
    if not u or generic_image(u):return False
    return image_matches_product(u,brand,product)

def _json_images(obj):
    if isinstance(obj,list):
        for x in obj:yield from _json_images(x)
    elif isinstance(obj,dict):
        typ=obj.get("@type")
        if typ=="Product" or (isinstance(typ,list) and "Product" in typ):
            u=first_image_url(obj.get("image"))
            if u:yield u
        for v in obj.values():yield from _json_images(v)

def page_image(soup,base_url,brand="",product=""):
    candidates=[]
    im=soup.find("img",attrs={"itemprop":"image"})
    if im:
        candidates += [im.get("src"),im.get("data-src"),im.get("data-original")]
    m=soup.find("meta",attrs={"itemprop":"image"})
    if m:candidates.append(m.get("content"))
    for tag in soup.find_all("script",attrs={"type":"application/ld+json"}):
        try:candidates.extend(_json_images(json.loads(tag.get_text(" ",strip=True))))
        except Exception:pass
    for attrs in ({"property":"og:image"},{"name":"twitter:image"},{"name":"twitter:image:src"}):
        m=soup.find("meta",attrs=attrs)
        if m:candidates.append(m.get("content"))
    for raw in candidates:
        if not raw:continue
        u=normalize_image(urllib.parse.urljoin(base_url,str(raw)))
        if generic_image(u):continue
        if not image_matches_product(u,brand,product):continue
        return u
    return ""
