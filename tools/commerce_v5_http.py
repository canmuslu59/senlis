"""Public requests with per-host pacing and persisted robots evidence."""
import gzip,hashlib,json,time
from pathlib import Path
from urllib.parse import urlsplit
from commerce_v3_http import PoliteClient,Fetch,host,public_url
from commerce_v5_sources import robots_allowed

class PolicyClient(PoliteClient):
    def __init__(self,root,deadline):
        super().__init__(0,1,slot=6,deadline=deadline,retain_error_bodies=True)
        self.root=Path(root);self.policies={}
        for path in (self.root/'policies').glob('*.json'):
            item=json.loads(path.read_text())
            if item.get('checked_at',0)>time.time()-28800 and item.get('ok'):
                try:
                    raw=gzip.decompress((self.root/item['snapshot']).read_bytes())
                    if hashlib.sha256(raw).hexdigest()==item['sha256'] and (item.get('http_status') in (404,410) or raw.decode()==item['rules']):
                        self.policies[item['host']]=item
                except (OSError,KeyError,UnicodeDecodeError):pass
    def _one(self,url):
        if not public_url(url):return Fetch(url,error='non_public_url')
        h=host(url);policy=self.policies.get(h)
        if policy is None:
            parts=urlsplit(url);robots=parts.scheme+'://'+parts.netloc+'/robots.txt'
            r=super()._one(robots)
            # No unvalidated cross-host redirect or silent acceptance of a denied policy.
            if r.location:r=super()._one(r.location) if public_url(r.location) and host(r.location)==h else Fetch(robots,error='robots_redirect_untrusted')
            ok=r.ok or r.status in (404,410)
            raw=r.text.encode();digest=hashlib.sha256(raw).hexdigest();snapshot='responses/'+digest+'.txt.gz'
            (self.root/'responses').mkdir(parents=True,exist_ok=True);(self.root/snapshot).write_bytes(gzip.compress(raw,mtime=0))
            policy={'host':h,'checked_at':time.time(),'ok':ok,'rules':r.text if r.ok else '',
                    'http_status':r.status,'snapshot':snapshot,'sha256':digest,'url':robots,'error':r.error}
            (self.root/'policies').mkdir(exist_ok=True);(self.root/'policies'/(hashlib.sha256(h.encode()).hexdigest()+'.json')).write_text(json.dumps(policy))
            if not ok:return Fetch(url,r.status,error='robots_unavailable',fetched_at=r.fetched_at,retry_at=r.retry_at)
            self.policies[h]=policy
        if not robots_allowed(policy['rules'],url):return Fetch(url,error='robots_disallowed',fetched_at=time.time())
        return super()._one(url)
