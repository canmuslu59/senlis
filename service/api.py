"""Small WSGI JSON API. No secrets or upstream calls are made from read requests."""
import json
import logging
import os
import re
import sqlite3
from urllib.parse import parse_qs

from .core import Store


db = Store()
db.migrate()


class ApiError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


def handle(method, path, query, data, headers):
    qs = parse_qs(query)
    param = lambda key, default='': qs.get(key, [default])[0]
    user = db.authenticate(headers.get('HTTP_AUTHORIZATION', '').removeprefix('Bearer ').strip())

    def require_user():
        if not user:
            raise ApiError(401, 'Oturum açman gerekiyor')
        return user

    def require_editor():
        secret = os.getenv('EDITOR_TOKEN', '')
        if not secret or headers.get('HTTP_X_EDITOR_TOKEN', '') != secret:
            raise ApiError(403, 'Editör yetkisi gerekiyor')

    if method == 'GET' and path == '/v1/health':
        return db.health()
    if method == 'GET' and path == '/v1/products':
        return {'items': db.catalogue(param('q'), param('limit', '20'), param('offset', '0'))}
    product_match = re.fullmatch(r'/v1/products/([a-f0-9]{32})', path)
    if method == 'GET' and product_match:
        product = db.product(product_match[1])
        if not product:
            raise ApiError(404, 'Koku bulunamadı')
        return product
    if method == 'POST' and path == '/v1/accounts':
        user_id, token = db.register(data.get('email', ''), data.get('password', ''))
        return {'user_id': user_id, 'token': token}
    if method == 'POST' and path == '/v1/sessions':
        session = db.login(data.get('email', ''), data.get('password', ''))
        if not session:
            raise ApiError(401, 'E-posta veya şifre yanlış')
        return {'user_id': session[0], 'token': session[1]}
    if method == 'DELETE' and path == '/v1/me':
        db.delete_account(require_user())
        return {'deleted': True}
    if method == 'PUT' and path == '/v1/me/notifications':
        db.preferences(require_user(), data.get('timezone', 'Europe/Istanbul'),
                       data.get('reminder', False), data.get('news', False), data.get('fcm_token'))
        return {'saved': True}
    if method == 'GET' and path == '/v1/community':
        return {'items': db.messages(None, param('limit', '20'), param('offset', '0'))}
    if method == 'POST' and path == '/v1/community':
        return {'id': db.post(require_user(), None, data.get('body', ''), data.get('parent_id'))}
    room_match = re.fullmatch(r'/v1/products/([a-f0-9]{32})/(messages|rating|corrections)', path)
    if room_match:
        product_id, subresource = room_match.groups()
        if not db.product(product_id):
            raise ApiError(404, 'Koku bulunamadı')
        if subresource == 'messages':
            if method == 'GET':
                return {'items': db.messages(product_id, param('limit', '20'), param('offset', '0'))}
            if method == 'POST':
                return {'id': db.post(require_user(), product_id, data.get('body', ''), data.get('parent_id'))}
        if subresource == 'rating' and method == 'PUT':
            db.rate(require_user(), product_id, data.get('stars'))
            return db.rating_summary(product_id)
        if subresource == 'corrections' and method == 'POST':
            db.correction(require_user(), product_id, data.get('description', ''))
            return {'queued': True}
    report_match = re.fullmatch(r'/v1/messages/([a-f0-9]{32})/reports', path)
    if method == 'POST' and report_match:
        db.report(require_user(), report_match[1], data.get('reason', ''))
        return {'queued': True}
    if method == 'GET' and path == '/v1/news':
        return {'items': db.news(param('limit', '20'))}
    if method == 'POST' and path == '/v1/editor/news':
        require_editor()
        return {'id': db.publish_news(data.get('title', ''), data.get('url', ''),
                                      data.get('source_name', ''), data.get('reviewed') is True,
                                      data.get('published_at'))}
    if method == 'GET' and path == '/v1/editor/candidates':
        require_editor()
        return {'items': db.candidate_queue()}
    if method == 'GET' and path == '/v1/editor/products':
        require_editor()
        return {'items': db.product_queue()}
    if method == 'POST' and path == '/v1/editor/products':
        require_editor()
        return {'id': db.import_brand_verified(data.get('name'), data.get('brand'),
            data.get('kind'), data.get('source_url', ''), data.get('notes'),
            data.get('family'), data.get('verified_at'), data.get('variants'))}
    if method == 'GET' and path == '/v1/editor/reports':
        require_editor()
        return {'items': db.report_queue()}
    if method == 'GET' and path == '/v1/editor/corrections':
        require_editor()
        return {'items': db.correction_queue()}
    review = re.fullmatch(r'/v1/editor/products/([a-f0-9]{32})/review', path)
    if method == 'PUT' and review:
        require_editor()
        db.review_product(review[1], data.get('approved') is True)
        return {'saved': True}
    fact = re.fullmatch(r'/v1/editor/products/([a-f0-9]{32})/facts', path)
    if method == 'PUT' and fact:
        require_editor()
        db.verified_fact(fact[1], data.get('field'), data.get('value'),
                         data.get('source_url', ''), data.get('source_name', ''))
        return {'saved': True}
    moderation = re.fullmatch(r'/v1/editor/messages/([a-f0-9]{32})', path)
    if method == 'PUT' and moderation:
        require_editor()
        db.moderate(moderation[1], data.get('status'))
        return {'saved': True}
    raise ApiError(404, 'Yol bulunamadı')


def application(environ, start_response):
    status = 200
    try:
        content_length = int(environ.get('CONTENT_LENGTH') or 0)
        if content_length > 16384:
            raise ApiError(413, 'İstek çok büyük')
        raw = environ['wsgi.input'].read(content_length) if content_length else b''
        data = json.loads(raw) if raw else {}
        if not isinstance(data, dict):
            raise ApiError(400, 'JSON nesnesi gerekiyor')
        result = handle(environ['REQUEST_METHOD'], environ.get('PATH_INFO', ''),
                        environ.get('QUERY_STRING', ''), data, environ)
    except ApiError as exc:
        status, result = exc.status, {'error': exc.message}
    except json.JSONDecodeError:
        status, result = 400, {'error': 'Geçersiz JSON'}
    except (ValueError, KeyError, TypeError, sqlite3.IntegrityError) as exc:
        status, result = 400, {'error': str(exc)[:200]}
    except Exception:
        logging.exception('Unhandled SENLIS API error')
        status, result = 500, {'error': 'Sunucu hatası'}
    body = json.dumps(result, ensure_ascii=False).encode('utf-8')
    status_name = {200: 'OK', 400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden',
                   404: 'Not Found', 413: 'Content Too Large', 500: 'Internal Server Error'}[status]
    start_response(f'{status} {status_name}', [('Content-Type', 'application/json; charset=utf-8'),
                    ('Content-Length', str(len(body))), ('Cache-Control', 'no-store')])
    return [body]


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    make_server('0.0.0.0', int(os.getenv('PORT', '8000')), application).serve_forever()
