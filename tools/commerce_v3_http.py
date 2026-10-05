"""Paced, bounded public HTTP reads shared by all workers in one scan lane."""
from collections import Counter, OrderedDict
from dataclasses import dataclass, replace
from datetime import timezone
from email.utils import parsedate_to_datetime
import hashlib
import ipaddress
import math
import random
import re
import socket
import threading
import time
from urllib.parse import urljoin, urlsplit

import requests


def host(url):
    return (urlsplit(url).hostname or '').lower().removeprefix('www.')


def public_url(url):
    try:
        p = urlsplit(url)
        h = (p.hostname or '').lower()
        if p.scheme != 'https' or p.username or p.password or p.port not in (None, 443):
            return False
        if '.' not in h or h.endswith(('.local', '.internal', '.localhost')):
            return False
        try:
            return ipaddress.ip_address(h).is_global
        except ValueError:
            return True
    except ValueError:
        return False


def next_slot(now, lane, lanes=4, slot=2.5):
    n = math.ceil(now / slot - 1e-9)
    n += (lane - n % lanes) % lanes
    return n * slot


def retry_seconds(value, now=None):
    now = time.time() if now is None else now
    try:
        return max(0, float(value))
    except (ValueError, TypeError):
        try:
            d = parsedate_to_datetime(value)
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return max(0, d.timestamp() - now)
        except (ValueError, TypeError, OverflowError):
            return 0


def is_challenge(text):
    t = (text or '')[:150000].lower()
    visible = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', '', t, flags=re.S)
    return any(s in visible for s in ('verify you are human', 'unusual traffic',
               'please complete the captcha', 'access to this page has been denied')) or (
               'anomaly.js' in t and 'challenge-form' in t) or (
               'cf-chl-' in t and 'just a moment' in visible)


@dataclass
class Fetch:
    url: str
    status: int = 0
    text: str = ''
    error: str = ''
    fetched_at: float = 0
    retry_at: float = 0
    location: str = ''
    from_cache: bool = False
    body_limited: bool = False

    @property
    def ok(self):
        return self.status == 200 and not self.error


class PoliteClient:
    def __init__(self, lane=0, lanes=4, slot=2.5, deadline=None, retain_error_bodies=False):
        if not 0 <= lane < lanes or lanes < 1 or slot < 2.5:
            raise ValueError('invalid polite lane configuration')
        self.lane, self.lanes, self.slot = lane, lanes, slot
        self.deadline = deadline or time.time() + 18000
        self.guard = threading.RLock()
        self.locks, self.cooldowns, self.failures, self.dns = {}, {}, {}, {}
        self.last_starts = {}
        self.cache = OrderedDict()
        self.stats = Counter()
        self.local = threading.local()
        self.retain_error_bodies = retain_error_bodies

    def _error_body(self, response):
        if not self.retain_error_bodies:return '',False
        raw=bytearray();limited=False;started=time.monotonic()
        try:
            for chunk in response.iter_content(16384):
                remaining=131072-len(raw)
                raw.extend(chunk[:remaining])
                if len(chunk)>remaining or time.monotonic()-started>5:
                    limited=True;break
        except requests.RequestException:limited=True
        encoding=response.encoding if response.encoding and response.encoding.lower()!='iso-8859-1' else 'utf-8'
        return raw.decode(encoding,errors='replace'),limited

    def _session(self):
        if not hasattr(self.local, 'session'):
            self.local.session = requests.Session()
            self.local.session.headers.update({'User-Agent': 'SENLIS-CatalogResearch/3.0 (+https://github.com/canmuslu59/senlis)',
                                              'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.5'})
        return self.local.session

    def available_at(self, url):
        with self.guard:
            return self.cooldowns.get(host(url), 0)

    def _cooldown(self, h, response=None, challenge=False):
        with self.guard:
            self.failures[h] = self.failures.get(h, 0) + 1
            duration = min(900, 30 * 2 ** min(self.failures[h] - 1, 5))
            if challenge:
                duration = max(duration, 900)
            if response is not None:
                duration = max(duration, retry_seconds(response.headers.get('Retry-After')))
                if response.status_code == 429:
                    duration = max(duration, 60)
            self.cooldowns[h] = time.time() + duration + random.uniform(0, 2)
            return self.cooldowns[h]

    def _public_dns(self, h):
        # In a managed egress environment the configured HTTP CONNECT proxy
        # resolves public hostnames. Keep lexical URL restrictions in all modes;
        # direct GitHub runners also validate resolved addresses below.
        proxies = requests.utils.get_environ_proxies('https://' + h)
        if proxies.get('https') or proxies.get('all'):
            return True
        with self.guard:
            cached = self.dns.get(h)
        if cached and cached[0] > time.time():
            return cached[1]
        try:
            addresses = {a[4][0] for a in socket.getaddrinfo(h, 443, type=socket.SOCK_STREAM)}
            result = bool(addresses) and all(ipaddress.ip_address(a).is_global for a in addresses)
        except (socket.gaierror, ValueError):
            result = False
        with self.guard:
            self.dns[h] = (time.time() + 120, result)
        return result

    def _pace(self, h):
        offset = int(hashlib.sha256(h.encode()).hexdigest()[:8], 16) % self.lanes
        lane = (self.lane + offset) % self.lanes
        while True:
            now = time.time()
            due = next_slot(now, lane, self.lanes, self.slot)
            due = max(due, self.last_starts.get(h, -self.slot) + self.slot)
            if due + 0.4 >= self.deadline:
                return False
            time.sleep(max(0, due - now) + random.uniform(0, 0.4))
            # Do not send late in a neighbouring lane's slot after scheduler delays.
            if time.time() <= due + 0.45:
                self.last_starts[h] = time.time()
                return True

    def _one(self, url):
        if not public_url(url):
            return Fetch(url, error='non_public_url')
        h = host(url)
        with self.guard:
            lock = self.locks.setdefault(h, threading.Lock())
            cached = self.cache.get(url)
        if cached and cached.fetched_at > time.time() - 1800:
            return replace(cached, from_cache=True)
        with lock:
            if time.time() >= self.deadline:
                return Fetch(url, error='deadline')
            retry_at = self.available_at(url)
            if retry_at > time.time():
                return Fetch(url, error='host_cooldown', retry_at=retry_at)
            if not self._public_dns(h):
                return Fetch(url, error='non_public_or_unresolved_host')
            if not self._pace(h):
                return Fetch(url, error='deadline')
            started = time.time()
            self.last_starts[h] = started
            try:
                with self.guard:
                    self.stats['requests'] += 1
                    self.stats['host:' + h] += 1
                with self._session().get(url, timeout=(10, 25), allow_redirects=False, stream=True) as r:
                    if r.status_code in (301, 302, 303, 307, 308):
                        return Fetch(url, r.status_code, fetched_at=started, location=urljoin(url, r.headers.get('Location', '')))
                    if r.status_code in (403, 429) or r.status_code >= 500:
                        until = self._cooldown(h, r, challenge=r.status_code == 403)
                        with self.guard: self.stats['http:' + str(r.status_code)] += 1
                        body,limited=self._error_body(r)
                        return Fetch(url, r.status_code, text=body, error='http_backoff', fetched_at=started, retry_at=until,body_limited=limited)
                    if r.status_code != 200:
                        body,limited=self._error_body(r)
                        return Fetch(url, r.status_code, text=body,error='http_error', fetched_at=started,body_limited=limited)
                    content_type = r.headers.get('Content-Type', '').lower()
                    if content_type and not any(t in content_type for t in ('text/', 'json', 'xml', 'javascript')):
                        return Fetch(url, r.status_code, error='not_text', fetched_at=started)
                    chunks, size = [], 0
                    for chunk in r.iter_content(65536):
                        size += len(chunk)
                        if size > 6 * 1024 * 1024 or time.time() - started > 45:
                            return Fetch(url, r.status_code, error='body_limit', fetched_at=started)
                        chunks.append(chunk)
                    raw = b''.join(chunks)
                    encoding = r.encoding if r.encoding and r.encoding.lower() != 'iso-8859-1' else 'utf-8'
                    text = raw.decode(encoding, errors='replace')
                    if is_challenge(text):
                        until = self._cooldown(h, r, challenge=True)
                        body=text[:131072] if self.retain_error_bodies else ''
                        return Fetch(url, r.status_code, text=body,error='challenge', fetched_at=started, retry_at=until,
                                     body_limited=self.retain_error_bodies and len(text)>131072)
                    result = Fetch(url, 200, text, fetched_at=started)
                    with self.guard:
                        self.failures[h] = 0
                        self.stats['ok'] += 1
                        self.cache[url] = result
                        while len(self.cache) > 96: self.cache.popitem(last=False)
                    return result
            except requests.RequestException as exc:
                until = self._cooldown(h)
                with self.guard: self.stats['network_errors'] += 1
                return Fetch(url, error=type(exc).__name__, fetched_at=started, retry_at=until)

    def fetch(self, url, params=None):
        url = requests.Request('GET', url, params=params).prepare().url
        for _ in range(5):
            result = self._one(url)
            if result.location:
                url = result.location
                continue
            return result
        return Fetch(url, error='redirect_limit')
