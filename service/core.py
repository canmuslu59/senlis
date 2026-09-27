"""SENLIS persistence and source-preserving catalogue rules.

SQLite supports local verification; DATABASE_URL selects PostgreSQL in deployment.
No catalogue row is created from an unverified or nameless source record.
"""
import hashlib
import json
import os
import re
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def now():
    return datetime.now(timezone.utc).isoformat()


def normalize_obf(raw):
    code = str(raw.get('code') or '').strip()
    name = str(raw.get('product_name') or '').strip()
    brand = str(raw.get('brands') or '').split(',')[0].strip()
    tags = set(raw.get('categories_tags') or [])
    if not (re.fullmatch(r'\d{8,14}', code) and 2 <= len(name) <= 180 and 2 <= len(brand) <= 120):
        return None
    # A source category is required: words in a name are not proof of product type.
    mist = {'en:body-mists', 'en:fragrance-mists', 'en:body-sprays'}
    perfume = {'en:perfumes', 'en:eaux-de-parfum', 'en:eaux-de-toilette', 'en:eaux-de-cologne'}
    if tags & mist:
        kind = 'body_mist'
    elif tags & perfume:
        kind = 'perfume'
    else:
        return None
    modified = raw.get('last_modified_t')
    try:
        observed = datetime.fromtimestamp(int(modified), timezone.utc).isoformat() if modified else now()
    except (TypeError, ValueError, OverflowError):
        observed = now()
    return {'code': code, 'name': name, 'brand': brand, 'kind': kind,
            'source_url': f'https://world.openbeautyfacts.org/product/{code}', 'observed_at': observed}


def local_day_due(zone, utc_iso, hour):
    try:
        instant = datetime.fromisoformat(utc_iso).astimezone(ZoneInfo(zone))
    except (ValueError, KeyError):
        return None
    if 9 <= instant.hour < 21 and instant.hour >= hour:
        return instant.date().isoformat()
    return None


SCHEMA = '''
CREATE TABLE IF NOT EXISTS users (
 id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL,
 display_name TEXT NOT NULL,
 created_at TEXT NOT NULL, timezone TEXT NOT NULL DEFAULT 'Europe/Istanbul',
 reminder INTEGER NOT NULL DEFAULT 0, news_push INTEGER NOT NULL DEFAULT 0,
 fcm_token TEXT, last_post_at TEXT);
CREATE TABLE IF NOT EXISTS sessions (
 token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 expires_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS login_attempts (
 email TEXT PRIMARY KEY, attempts INTEGER NOT NULL, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS products (
 id TEXT PRIMARY KEY, code TEXT UNIQUE, name TEXT NOT NULL, brand TEXT NOT NULL,
 kind TEXT NOT NULL, reviewed INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS products_name ON products(name);
CREATE TABLE IF NOT EXISTS product_variants (
 id TEXT PRIMARY KEY, product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
 size_ml INTEGER, concentration TEXT, label TEXT NOT NULL,
 source_url TEXT NOT NULL, observed_at TEXT NOT NULL,
 UNIQUE(product_id,label));
CREATE TABLE IF NOT EXISTS product_sources (
 product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
 field TEXT NOT NULL, source_name TEXT NOT NULL, source_url TEXT NOT NULL,
 observed_at TEXT NOT NULL, license TEXT NOT NULL,
 PRIMARY KEY(product_id, field));
CREATE TABLE IF NOT EXISTS product_facts (
 product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
 field TEXT NOT NULL, value TEXT NOT NULL, source_url TEXT NOT NULL,
 source_name TEXT NOT NULL, verified_at TEXT NOT NULL,
 PRIMARY KEY(product_id,field));
CREATE TABLE IF NOT EXISTS import_runs (
 id TEXT PRIMARY KEY, source TEXT NOT NULL, started_at TEXT NOT NULL,
 finished_at TEXT, accepted INTEGER NOT NULL DEFAULT 0, rejected INTEGER NOT NULL DEFAULT 0,
 error TEXT);
CREATE TABLE IF NOT EXISTS corrections (
 id TEXT PRIMARY KEY, product_id TEXT NOT NULL REFERENCES products(id),
 user_id TEXT REFERENCES users(id) ON DELETE SET NULL, description TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ratings (
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
 stars INTEGER NOT NULL CHECK(stars BETWEEN 1 AND 5), updated_at TEXT NOT NULL,
 PRIMARY KEY(user_id, product_id));
CREATE TABLE IF NOT EXISTS messages (
 id TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
 product_id TEXT REFERENCES products(id) ON DELETE CASCADE,
 parent_id TEXT REFERENCES messages(id) ON DELETE SET NULL,
 body TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'visible', created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS messages_room ON messages(product_id, created_at);
CREATE TABLE IF NOT EXISTS reports (
 id TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
 message_id TEXT NOT NULL REFERENCES messages(id), reason TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS articles (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, url TEXT NOT NULL UNIQUE,
 source_name TEXT NOT NULL, published_at TEXT NOT NULL,
 reviewed INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS news_candidates (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, url TEXT NOT NULL UNIQUE,
 source_name TEXT NOT NULL, discovered_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending');
CREATE TABLE IF NOT EXISTS deliveries (
 user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 kind TEXT NOT NULL, local_date TEXT NOT NULL, status TEXT NOT NULL,
 article_id TEXT REFERENCES articles(id), updated_at TEXT NOT NULL,
 attempts INTEGER NOT NULL DEFAULT 1,
 PRIMARY KEY(user_id, kind, local_date));
'''


class Store:
    def __init__(self, path=None):
        self.path = path or os.getenv('DATABASE_URL', 'senlis.sqlite')
        self.pg = self.path.startswith(('postgres://', 'postgresql://'))

    @contextmanager
    def connect(self):
        if self.pg:
            import psycopg
            from psycopg.rows import dict_row
            conn = psycopg.connect(self.path, row_factory=dict_row)
        else:
            conn = sqlite3.connect(self.path)
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA foreign_keys=ON')
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def query(self, conn, sql, args=()):
        return conn.execute(sql.replace('?', '%s') if self.pg else sql, args)

    @staticmethod
    def one(cursor):
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def many(cursor):
        return [dict(row) for row in cursor.fetchall()]

    def migrate(self):
        with self.connect() as conn:
            for statement in SCHEMA.split(';'):
                if statement.strip():
                    conn.execute(statement)

    def import_obf(self, row):
        if row is None:
            raise ValueError('invalid source record')
        with self.connect() as conn:
            existing = self.one(self.query(conn, 'SELECT id FROM products WHERE code=?', (row['code'],)))
            product_id = existing['id'] if existing else uuid.uuid4().hex
            self.query(conn, '''INSERT INTO products(id,code,name,brand,kind,updated_at)
                VALUES(?,?,?,?,?,?) ON CONFLICT(code) DO UPDATE SET
                reviewed=CASE WHEN products.name=excluded.name AND products.brand=excluded.brand
                    AND products.kind=excluded.kind THEN products.reviewed ELSE 0 END,
                name=excluded.name,brand=excluded.brand,kind=excluded.kind,updated_at=excluded.updated_at''',
                (product_id, row['code'], row['name'], row['brand'], row['kind'], now()))
            for field in ('name', 'brand', 'kind', 'code'):
                self.query(conn, '''INSERT INTO product_sources(product_id,field,source_name,source_url,observed_at,license)
                    VALUES(?,?,?,?,?,?) ON CONFLICT(product_id,field) DO UPDATE SET
                    source_url=excluded.source_url,observed_at=excluded.observed_at''',
                    (product_id, field, 'Open Beauty Facts', row['source_url'], row['observed_at'], 'ODbL'))
            return product_id

    def review_product(self, product_id, approved):
        with self.connect() as conn:
            cursor = self.query(conn, 'UPDATE products SET reviewed=? WHERE id=?',
                                (int(bool(approved)), product_id))
            if cursor.rowcount != 1:
                raise ValueError('product missing')

    def product_queue(self):
        with self.connect() as conn:
            return self.many(self.query(conn, '''SELECT p.id,p.code,p.name,p.brand,p.kind,p.updated_at,
                s.source_url FROM products p JOIN product_sources s
                ON s.product_id=p.id AND s.field='name' WHERE p.reviewed=0
                ORDER BY p.updated_at DESC LIMIT 100'''))

    def import_brand_verified(self, name, brand, kind, source_url, notes, family=None,
                              verified_at=None, variants=None):
        """Human-reviewed official brand facts; no invented barcode, price or imagery."""
        if kind not in ('perfume', 'body_mist') or not source_url.startswith('https://') or not name or not brand:
            raise ValueError('official product identity required')
        if not verified_at:
            raise ValueError('human verification timestamp required')
        product_id = uuid.uuid5(uuid.NAMESPACE_URL, source_url).hex
        with self.connect() as conn:
            self.query(conn, '''INSERT INTO products(id,code,name,brand,kind,reviewed,updated_at)
                VALUES(?,NULL,?,?,?,1,?) ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,brand=excluded.brand,kind=excluded.kind''',
                (product_id, name, brand, kind, verified_at))
            for field in ('name', 'brand', 'kind'):
                self.query(conn, '''INSERT INTO product_sources(product_id,field,source_name,source_url,observed_at,license)
                    VALUES(?,?,?,?,?,?) ON CONFLICT(product_id,field) DO NOTHING''',
                    (product_id, field, brand, source_url, verified_at, 'brand product page'))
        if notes:
            self.verified_fact(product_id, 'notes', notes, source_url, brand, verified_at)
        if family:
            self.verified_fact(product_id, 'family', family, source_url, brand, verified_at)
        for variant in variants or []:
            size = variant.get('size_ml')
            concentration = variant.get('concentration')
            label = variant.get('label', '')
            if not isinstance(size, int) or size <= 0 or not label:
                raise ValueError('verified variant needs size and label')
            with self.connect() as conn:
                self.query(conn, '''INSERT INTO product_variants(id,product_id,size_ml,concentration,label,source_url,observed_at)
                    VALUES(?,?,?,?,?,?,?) ON CONFLICT(product_id,label) DO NOTHING''',
                    (uuid.uuid5(uuid.NAMESPACE_URL, source_url + '#' + label).hex, product_id,
                     size, concentration, label, source_url, verified_at))
        return product_id

    def catalogue(self, search='', limit=20, offset=0):
        limit, offset = max(1, min(int(limit), 50)), max(0, int(offset))
        with self.connect() as conn:
            products = self.many(self.query(conn, '''SELECT id,code,name,brand,kind,updated_at
                FROM products WHERE reviewed=1 AND (lower(name) LIKE ? OR lower(brand) LIKE ?)
                ORDER BY name,id LIMIT ? OFFSET ?''',
                ('%' + search.lower() + '%', '%' + search.lower() + '%', limit, offset)))
            for product in products:
                facts = self.many(self.query(conn, 'SELECT field,value FROM product_facts WHERE product_id=?',
                                             (product['id'],)))
                product.update(notes=None, family=None, intensity=None)
                for fact in facts:
                    product[fact['field']] = json.loads(fact['value'])
            return products

    def product(self, product_id):
        with self.connect() as conn:
            result = self.one(self.query(conn, 'SELECT * FROM products WHERE id=? AND reviewed=1', (product_id,)))
            if not result:
                return None
            source = self.one(self.query(conn, '''SELECT source_name,url,observed_at,license FROM
                (SELECT source_name,source_url AS url,observed_at,license FROM product_sources
                WHERE product_id=? AND field='name')''', (product_id,)))
            facts = self.many(self.query(conn, '''SELECT field,value,source_url,source_name,verified_at
                FROM product_facts WHERE product_id=?''', (product_id,)))
            mapped = {fact['field']: json.loads(fact['value']) for fact in facts}
            result.update(source=source, notes=mapped.get('notes'), family=mapped.get('family'),
                          intensity=mapped.get('intensity'), price=None,
                          rating=self.rating_summary(product_id))
            result['provenance'] = self.many(self.query(conn, '''SELECT field,source_name,source_url,
                observed_at,license FROM product_sources WHERE product_id=?''', (product_id,)))
            result['provenance'] += [{'field': f['field'], 'source_name': f['source_name'],
                'source_url': f['source_url'], 'observed_at': f['verified_at'], 'license': 'source-linked fact'}
                for f in facts]
            result['variants'] = self.many(self.query(conn, '''SELECT id,label,size_ml,concentration,
                source_url,observed_at FROM product_variants WHERE product_id=? ORDER BY size_ml''',
                (product_id,)))
            return result

    def verified_fact(self, product_id, field, value, source_url, source_name, verified_at=None):
        if field not in ('notes', 'family', 'intensity') or not source_url.startswith('https://'):
            raise ValueError('unsupported or unlinked product fact')
        if field == 'notes' and (not isinstance(value, list) or not all(isinstance(x, str) and x.strip() for x in value)):
            raise ValueError('notes must be a nonempty string list')
        if field == 'family' and (not isinstance(value, str) or not value.strip()):
            raise ValueError('family required')
        if field == 'intensity' and value not in (1, 2, 3):
            raise ValueError('intensity must be 1–3')
        with self.connect() as conn:
            self.query(conn, '''INSERT INTO product_facts(product_id,field,value,source_url,source_name,verified_at)
                VALUES(?,?,?,?,?,?) ON CONFLICT(product_id,field) DO UPDATE SET value=excluded.value,
                source_url=excluded.source_url,source_name=excluded.source_name,
                verified_at=excluded.verified_at''',
                (product_id, field, json.dumps(value, ensure_ascii=False), source_url,
                 source_name.strip(), verified_at or now()))

    def register(self, email, password, display_name=None):
        email = email.strip().lower()
        if not re.fullmatch(r'[^@\s]{1,80}@[^@\s]{2,150}', email) or len(password) < 12:
            raise ValueError('invalid account details')
        salt = secrets.token_bytes(16)
        digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
        user_id = uuid.uuid4().hex
        display_name = (display_name or ('Üye ' + user_id[:6])).strip()
        if not 2 <= len(display_name) <= 40:
            raise ValueError('display name length 2–40')
        with self.connect() as conn:
            self.query(conn, 'INSERT INTO users(id,email,password_hash,display_name,created_at) VALUES(?,?,?,?,?)',
                       (user_id, email, salt.hex() + ':' + digest.hex(), display_name, now()))
        return user_id, self.session(user_id)

    def login(self, email, password):
        email = email.strip().lower()
        with self.connect() as conn:
            attempts = self.one(self.query(conn, 'SELECT attempts,updated_at FROM login_attempts WHERE email=?', (email,)))
            if attempts and attempts['attempts'] >= 5 and datetime.fromisoformat(attempts['updated_at']) > datetime.now(timezone.utc) - timedelta(minutes=15):
                return None
            user = self.one(self.query(conn, 'SELECT id,password_hash FROM users WHERE email=?',
                                       (email,)))
        valid = False
        if user:
            salt, expected = user['password_hash'].split(':')
            calculated = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**14, r=8, p=1)
            valid = secrets.compare_digest(calculated, bytes.fromhex(expected))
        with self.connect() as conn:
            if valid:
                self.query(conn, 'DELETE FROM login_attempts WHERE email=?', (email,))
            else:
                reset = not attempts or datetime.fromisoformat(attempts['updated_at']) < datetime.now(timezone.utc) - timedelta(minutes=15)
                self.query(conn, '''INSERT INTO login_attempts(email,attempts,updated_at) VALUES(?,?,?)
                    ON CONFLICT(email) DO UPDATE SET attempts=excluded.attempts,updated_at=excluded.updated_at''',
                    (email, 1 if reset else attempts['attempts'] + 1, now()))
        if not valid:
            return None
        return user['id'], self.session(user['id'])

    def session(self, user_id):
        token = secrets.token_urlsafe(32)
        expiry = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        with self.connect() as conn:
            self.query(conn, 'INSERT INTO sessions(token_hash,user_id,expires_at) VALUES(?,?,?)',
                       (hashlib.sha256(token.encode()).hexdigest(), user_id, expiry))
        return token

    def authenticate(self, token):
        if not token:
            return None
        with self.connect() as conn:
            row = self.one(self.query(conn, 'SELECT user_id,expires_at FROM sessions WHERE token_hash=?',
                                      (hashlib.sha256(token.encode()).hexdigest(),)))
        return row['user_id'] if row and row['expires_at'] > now() else None

    def delete_account(self, user_id):
        with self.connect() as conn:
            self.query(conn, 'UPDATE messages SET user_id=NULL,body=? WHERE user_id=?',
                       ('[silinen kullanıcı içeriği]', user_id))
            self.query(conn, 'DELETE FROM users WHERE id=?', (user_id,))

    def rate(self, user_id, product_id, stars):
        if not isinstance(stars, int) or stars not in range(1, 6):
            raise ValueError('stars must be 1–5')
        with self.connect() as conn:
            self.query(conn, '''INSERT INTO ratings(user_id,product_id,stars,updated_at) VALUES(?,?,?,?)
                ON CONFLICT(user_id,product_id) DO UPDATE SET stars=excluded.stars,
                updated_at=excluded.updated_at''', (user_id, product_id, stars, now()))

    def rating_summary(self, product_id):
        with self.connect() as conn:
            row = self.one(self.query(conn, 'SELECT COUNT(*) AS count,AVG(stars) AS average FROM ratings WHERE product_id=?',
                                      (product_id,)))
        return {'count': row['count'], 'average': round(row['average'], 1) if row['average'] is not None else None}

    def post(self, user_id, product_id, body, parent_id=None):
        body = body.strip()
        if not 3 <= len(body) <= 2000:
            raise ValueError('message length 3–2000')
        message_id = uuid.uuid4().hex
        with self.connect() as conn:
            user = self.one(self.query(conn, 'SELECT last_post_at FROM users WHERE id=?', (user_id,)))
            if not user:
                raise ValueError('account missing')
            if user['last_post_at'] and datetime.fromisoformat(user['last_post_at']) > datetime.now(timezone.utc) - timedelta(seconds=10):
                raise ValueError('slow down')
            if parent_id:
                parent = self.one(self.query(conn, 'SELECT product_id FROM messages WHERE id=? AND status=?', (parent_id, 'visible')))
                if not parent or parent['product_id'] != product_id:
                    raise ValueError('parent outside room')
            self.query(conn, 'INSERT INTO messages(id,user_id,product_id,parent_id,body,created_at) VALUES(?,?,?,?,?,?)',
                       (message_id, user_id, product_id, parent_id, body, now()))
            self.query(conn, 'UPDATE users SET last_post_at=? WHERE id=?', (now(), user_id))
        return message_id

    def messages(self, product_id, limit=20, offset=0):
        where = 'm.product_id IS NULL' if product_id is None else 'm.product_id=?'
        args = () if product_id is None else (product_id,)
        with self.connect() as conn:
            return self.many(self.query(conn, '''SELECT m.id,m.parent_id,m.body,m.created_at,
                CASE WHEN m.user_id IS NULL THEN 'Silinmiş kullanıcı' ELSE u.display_name END AS author
                FROM messages m LEFT JOIN users u ON u.id=m.user_id
                WHERE ''' + where + ''' AND m.status='visible' ORDER BY m.created_at DESC,m.id DESC
                LIMIT ? OFFSET ?''', args + (min(50, max(1, int(limit))), max(0, int(offset)))))

    def report(self, user_id, message_id, reason):
        if not 3 <= len(reason.strip()) <= 500:
            raise ValueError('report reason required')
        with self.connect() as conn:
            self.query(conn, 'INSERT INTO reports(id,user_id,message_id,reason,created_at) VALUES(?,?,?,?,?)',
                       (uuid.uuid4().hex, user_id, message_id, reason.strip(), now()))

    def moderate(self, message_id, status):
        if status not in ('visible', 'hidden'):
            raise ValueError('invalid status')
        with self.connect() as conn:
            self.query(conn, 'UPDATE messages SET status=? WHERE id=?', (status, message_id))
            self.query(conn, "UPDATE reports SET status='resolved' WHERE message_id=?", (message_id,))

    def correction(self, user_id, product_id, description):
        if not 10 <= len(description.strip()) <= 1000:
            raise ValueError('correction length 10–1000')
        with self.connect() as conn:
            self.query(conn, 'INSERT INTO corrections(id,product_id,user_id,description,created_at) VALUES(?,?,?,?,?)',
                       (uuid.uuid4().hex, product_id, user_id, description.strip(), now()))

    def correction_queue(self):
        with self.connect() as conn:
            return self.many(self.query(conn, '''SELECT c.id,c.product_id,p.name,c.description,c.created_at
                FROM corrections c JOIN products p ON p.id=c.product_id
                WHERE c.status='pending' ORDER BY c.created_at LIMIT 100'''))

    def report_queue(self):
        with self.connect() as conn:
            return self.many(self.query(conn, '''SELECT r.id,r.message_id,r.reason,r.created_at,m.body
                FROM reports r JOIN messages m ON m.id=r.message_id
                WHERE r.status='pending' ORDER BY r.created_at LIMIT 100'''))

    def preferences(self, user_id, zone, reminder, news_push, fcm_token=None):
        ZoneInfo(zone)  # reject invalid IANA zones
        with self.connect() as conn:
            self.query(conn, '''UPDATE users SET timezone=?,reminder=?,news_push=?,fcm_token=? WHERE id=?''',
                       (zone, int(bool(reminder)), int(bool(news_push)), fcm_token, user_id))

    def subscribers(self):
        with self.connect() as conn:
            return self.many(self.query(conn, 'SELECT id,timezone,reminder,news_push,fcm_token FROM users WHERE reminder=1 OR news_push=1'))

    def publish_news(self, title, url, source_name, reviewed, published_at=None):
        if not reviewed or len(title.strip()) < 8 or not url.startswith('https://') or len(source_name.strip()) < 3:
            raise ValueError('editorial review and HTTPS source required')
        publication = datetime.fromisoformat(published_at) if published_at else datetime.now(timezone.utc)
        if publication.tzinfo is None or publication > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError('valid published_at timestamp required')
        article_id = uuid.uuid4().hex
        with self.connect() as conn:
            self.query(conn, '''INSERT INTO articles(id,title,url,source_name,published_at,reviewed,created_at)
                VALUES(?,?,?,?,?,1,?) ON CONFLICT(url) DO NOTHING''',
                (article_id, title.strip(), url, source_name.strip(), publication.isoformat(), now()))
        return article_id

    def news_candidate(self, title, url, source_name):
        if not title.strip() or not url.startswith('https://'):
            return
        with self.connect() as conn:
            self.query(conn, '''INSERT INTO news_candidates(id,title,url,source_name,discovered_at)
                VALUES(?,?,?,?,?) ON CONFLICT(url) DO NOTHING''',
                (uuid.uuid4().hex, title.strip()[:300], url, source_name, now()))

    def candidate_queue(self):
        with self.connect() as conn:
            return self.many(self.query(conn, '''SELECT id,title,url,source_name,discovered_at
                FROM news_candidates WHERE status='pending' ORDER BY discovered_at DESC LIMIT 100'''))

    def news(self, limit=20):
        with self.connect() as conn:
            return self.many(self.query(conn, '''SELECT id,title,url,source_name,published_at FROM articles
                WHERE reviewed=1 ORDER BY published_at DESC LIMIT ?''', (max(1, min(50, int(limit))),)))

    def unsent_news(self, user_id, utc_iso):
        cutoff = (datetime.fromisoformat(utc_iso) - timedelta(days=7)).isoformat()
        with self.connect() as conn:
            return self.one(self.query(conn, '''SELECT a.id,a.title,a.url,a.source_name,a.published_at
                FROM articles a WHERE a.reviewed=1 AND a.published_at>=? AND a.published_at<=?
                AND NOT EXISTS (SELECT 1 FROM deliveries d WHERE d.user_id=? AND d.kind='news'
                AND d.article_id=a.id AND d.status IN ('claimed','sent'))
                ORDER BY a.published_at DESC LIMIT 1''', (cutoff, utc_iso, user_id)))

    def claim_delivery(self, user_id, kind, local_date, article_id=None):
        with self.connect() as conn:
            cursor = self.query(conn, '''INSERT INTO deliveries(user_id,kind,local_date,status,article_id,updated_at)
                VALUES(?,?,?,?,?,?) ON CONFLICT(user_id,kind,local_date) DO NOTHING''',
                (user_id, kind, local_date, 'claimed', article_id, now()))
            if cursor.rowcount == 1:
                return True
            retry = self.query(conn, '''UPDATE deliveries SET status='claimed',attempts=attempts+1,
                updated_at=? WHERE user_id=? AND kind=? AND local_date=? AND status='failed' AND attempts<3''',
                (now(), user_id, kind, local_date))
            return retry.rowcount == 1

    def delivery_status(self, user_id, kind, local_date, status):
        with self.connect() as conn:
            self.query(conn, '''UPDATE deliveries SET status=?,updated_at=?
                WHERE user_id=? AND kind=? AND local_date=?''', (status, now(), user_id, kind, local_date))

    def health(self):
        with self.connect() as conn:
            last = self.one(self.query(conn, '''SELECT finished_at,accepted,rejected,error FROM import_runs
                WHERE source='OBF' ORDER BY started_at DESC LIMIT 1'''))
            count = self.one(self.query(conn, 'SELECT COUNT(*) AS count FROM products WHERE reviewed=1'))
            queue = self.one(self.query(conn, 'SELECT COUNT(*) AS count FROM products WHERE reviewed=0'))
        return {'catalogue_count': count['count'], 'review_queue_count': queue['count'], 'last_import': last}
