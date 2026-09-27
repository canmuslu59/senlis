"""Exercise production SQL syntax on an ephemeral CI PostgreSQL instance."""
import os
from service.core import Store
from service.curated import seed

db = Store(os.environ['DATABASE_URL'])
db.migrate()
seed(db)
assert db.health()['catalogue_count'] == 4
product = db.catalogue('Libre')[0]
assert db.product(product['id'])['notes']
user, token = db.register('ci@example.test', 'strong test password')
assert db.authenticate(token) == user
db.rate(user, product['id'], 4)
assert db.rating_summary(product['id'])['average'] == 4.0
db.post(user, None, 'PostgreSQL sohbet denemesi')
assert len(db.messages(None)) == 1
db.preferences(user, 'Europe/Istanbul', True, True, 'test-device')
assert len(db.subscribers()) == 1
db.delete_account(user)
assert db.authenticate(token) is None
print('PostgreSQL schema, source catalogue, accounts, ratings, discussion and deletion passed')
