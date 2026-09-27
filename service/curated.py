"""Small, manually checked official-brand starting set.

Facts paraphrased and translated, with source links; no copied photos, prices,
ratings, or inferred concentration. Recheck links before each editorial update.
"""
from .core import Store

OFFICIAL_PRODUCTS = [
    {
        'name': 'Cheirosa 62 Perfume Mist', 'brand': 'Sol de Janeiro', 'kind': 'body_mist',
        'source_url': 'https://soldejaneiro.com/products/cheirosa-62-hair-body-fragrance-mist',
        'notes': ['antep fıstığı', 'badem', 'heliotrop', 'yasemin', 'vanilya', 'tuzlu karamel', 'sandal ağacı'],
        'family': None,
        'verified_at': '2026-09-27T00:00:00+00:00',
    },
    {
        'name': 'Cheirosa 68 Beija Flor Perfume Mist', 'brand': 'Sol de Janeiro', 'kind': 'body_mist',
        'source_url': 'https://soldejaneiro.com/products/cheirosa-68-perfume-mist',
        'notes': ['ejder meyvesi', 'liçi', 'yasemin', 'hibiskus', 'vanilya', 'misk'],
        'family': 'çiçeksi',
        'verified_at': '2026-09-27T00:00:00+00:00',
    },
    {
        'name': 'Libre Eau de Parfum', 'brand': 'Yves Saint Laurent Beauty', 'kind': 'perfume',
        'source_url': 'https://www.yslbeautyus.com/fragrance/womens-fragrances/libre/libre-eau-de-parfum/109YSL.html',
        'notes': ['lavanta', 'portakal çiçeği', 'misk', 'vanilya'],
        'family': 'çiçeksi',
        'verified_at': '2026-09-27T00:00:00+00:00',
    },
    {
        'name': 'Peony & Blush Suede Cologne', 'brand': 'Jo Malone London', 'kind': 'perfume',
        'source_url': 'https://www.jomalone.com/product/25946/27028/colognes/peony-blush-suede-cologne',
        'notes': ['şakayık', 'kırmızı elma', 'yasemin', 'gül', 'süet'],
        'family': 'çiçeksi',
        'verified_at': '2026-09-27T00:00:00+00:00',
    },
]


def seed(db):
    for product in OFFICIAL_PRODUCTS:
        db.import_brand_verified(**product)


if __name__ == '__main__':
    db = Store()
    db.migrate()
    seed(db)
    print(db.health())
