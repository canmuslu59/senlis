"""Read-only smoke check for the deployed SENLIS API.

Usage: SENLIS_BASE_URL=https://senlis-api.example python -m ci.live_smoke
No account, rating, message or product is written by this check.
"""
import json
import os
import urllib.parse
import urllib.request


BASE = os.environ.get('SENLIS_BASE_URL', '').rstrip('/')
if not BASE.startswith('https://') and not BASE.startswith('http://localhost:'):
    raise SystemExit('SENLIS_BASE_URL must be HTTPS (localhost is allowed for development)')


def get(path):
    request = urllib.request.Request(BASE + path, headers={'Accept': 'application/json'})
    with urllib.request.urlopen(request, timeout=15) as response:
        if response.status != 200 or 'application/json' not in response.headers.get('Content-Type', ''):
            raise AssertionError('unexpected API response: ' + path)
        return json.load(response)


health = get('/v1/health')
if health['catalogue_count'] < 4:
    raise AssertionError('reviewed official catalogue is missing')
items = get('/v1/products?limit=50')['items']
if len(items) < 4:
    raise AssertionError('catalogue pagination or reviewed seed is missing')
for item in items:
    if item['kind'] not in ('perfume', 'body_mist') or not item['name'] or not item['brand']:
        raise AssertionError('incomplete reviewed identity')
    detail = get('/v1/products/' + urllib.parse.quote(item['id']))
    source = detail.get('source') or {}
    if not source.get('url', '').startswith('https://') or not source.get('observed_at'):
        raise AssertionError('source attribution missing: ' + item['id'])
    for field in ('notes', 'family', 'intensity'):
        if detail.get(field) is not None and not any(p['field'] == field and
            p['source_url'].startswith('https://') for p in detail['provenance']):
            raise AssertionError('unattributed fact: ' + item['id'] + '/' + field)
    if detail.get('price') is not None:
        raise AssertionError('unexpected unverified price')
get('/v1/community?limit=1')
get('/v1/news?limit=1')
print('Live API, reviewed catalogue, provenance, community and news endpoints passed (' +
      str(len(items)) + ' products checked on this page)')
