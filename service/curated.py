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
        'variants': [{'label': '90 ml', 'size_ml': 90}, {'label': '240 ml', 'size_ml': 240}],
    },
    {
        'name': 'Cheirosa 68 Beija Flor Perfume Mist', 'brand': 'Sol de Janeiro', 'kind': 'body_mist',
        'source_url': 'https://soldejaneiro.com/products/cheirosa-68-perfume-mist',
        'notes': ['ejder meyvesi', 'liçi', 'yasemin', 'okyanus havası', 'hibiskus', 'vanilya', 'misk'],
        'family': 'çiçeksi',
        'verified_at': '2026-09-27T00:00:00+00:00',
        'variants': [{'label': '90 ml', 'size_ml': 90}, {'label': '240 ml', 'size_ml': 240}],
    },
    {
        'name': 'Cheirosa 71 Perfume Mist', 'brand': 'Sol de Janeiro', 'kind': 'body_mist',
        'source_url': 'https://soldejaneiro.com/products/cheirosa-71-body-fragrance-mist',
        'notes': ['karamelize vanilya', 'deniz tuzu', 'kavrulmuş makademya', 'beyaz çikolata',
                  'tonka fasulyesi', 'hindistan cevizi çiçeği'],
        'family': 'gurme', 'verified_at': '2026-09-28T00:00:00+00:00',
        'variants': [{'label': '90 ml', 'size_ml': 90}, {'label': '240 ml', 'size_ml': 240}],
    },
    {
        'name': 'Cheirosa 40 Bom Dia Bright Perfume Mist', 'brand': 'Sol de Janeiro', 'kind': 'body_mist',
        'source_url': 'https://soldejaneiro.com/collections/fragrances/products/cheirosa-40-hair-body-fragrance-mist',
        'notes': ['siyah amber erik', 'frenk üzümü likörü', 'yasemin çiçekleri',
                  'brezilya orkidesi', 'vanilya odunları', 'sıcak misk'],
        'family': 'çiçeksi', 'verified_at': '2026-09-28T00:00:00+00:00',
        'variants': [{'label': '90 ml', 'size_ml': 90}, {'label': '240 ml', 'size_ml': 240}],
    },
    {
        'name': 'Cheirosa 48 Perfume Mist', 'brand': 'Sol de Janeiro', 'kind': 'body_mist',
        'source_url': 'https://soldejaneiro.com/products/cheirosa-48-perfume-mist',
        'notes': ['guava nektarı', 'hindistan cevizi suyu', 'orkide', 'limon',
                  'iris', 'pembe misk', 'vanilya'],
        'family': 'gurme', 'verified_at': '2026-09-28T00:00:00+00:00',
        'variants': [{'label': '90 ml', 'size_ml': 90}, {'label': '240 ml', 'size_ml': 240}],
    },
    {
        'name': 'Cheirosa 59 Delícia Drench Perfume Mist', 'brand': 'Sol de Janeiro',
        'kind': 'body_mist',
        'source_url': 'https://soldejaneiro.com/products/cheirosa-59-perfume-mist',
        'notes': ['erik', 'şekerli menekşe', 'vanilya orkidesi', 'amber',
                  'sandal ağacı', 'vetiver'],
        'family': 'gurme', 'verified_at': '2026-09-28T00:00:00+00:00',
        'variants': [{'label': '90 ml', 'size_ml': 90}, {'label': '240 ml', 'size_ml': 240}],
    },
    {
        'name': 'Cheirosa 59 Intense Perfume Mist', 'brand': 'Sol de Janeiro',
        'kind': 'body_mist',
        'source_url': 'https://soldejaneiro.com/products/cheirosa-59-intense-perfume-mist',
        'notes': ['beyaz orkide', 'makademya', 'menekşe', 'sambak yasemini',
                  'sandal ağacı', 'toffee', 'paçuli', 'amber akoru', 'vetiver', 'misk'],
        'family': 'gurme', 'verified_at': '2026-09-28T00:00:00+00:00',
        'variants': [{'label': '90 ml', 'size_ml': 90}],
    },
    {
        'name': 'Cheirosa 76 Perfume Mist', 'brand': 'Sol de Janeiro', 'kind': 'body_mist',
        'source_url': 'https://soldejaneiro.com/products/cheirosa-76-perfume-mist',
        'notes': ['siyah frenk üzümü', 'armut nektarı', 'yasemin',
                  'vanilya kreması', 'frezya', 'amber odunları', 'karamelize paçuli'],
        'family': 'çiçeksi', 'verified_at': '2026-09-28T00:00:00+00:00',
        'variants': [{'label': '90 ml', 'size_ml': 90}, {'label': '240 ml', 'size_ml': 240}],
    },
    {
        'name': 'Libre Eau de Parfum', 'brand': 'Yves Saint Laurent Beauty', 'kind': 'perfume',
        'source_url': 'https://www.yslbeautyus.com/fragrance/womens-fragrances/libre/libre-eau-de-parfum/109YSL.html',
        'notes': ['lavanta', 'portakal çiçeği', 'misk', 'vanilya'],
        'family': 'çiçeksi',
        'verified_at': '2026-09-27T00:00:00+00:00',
        'variants': [{'label': '10 ml EDP', 'size_ml': 10, 'concentration': 'EDP'},
                     {'label': '30 ml EDP', 'size_ml': 30, 'concentration': 'EDP'},
                     {'label': '50 ml EDP', 'size_ml': 50, 'concentration': 'EDP'},
                     {'label': '90 ml EDP', 'size_ml': 90, 'concentration': 'EDP'},
                     {'label': '100 ml Refill EDP', 'size_ml': 100, 'concentration': 'EDP'},
                     {'label': '150 ml EDP', 'size_ml': 150, 'concentration': 'EDP'}],
    },
    {
        'name': 'Peony & Blush Suede Cologne', 'brand': 'Jo Malone London', 'kind': 'perfume',
        'source_url': 'https://www.jomalone.com/product/25946/27028/colognes/peony-blush-suede-cologne',
        'notes': ['şakayık', 'kırmızı elma', 'yasemin', 'gül', 'süet'],
        'family': 'çiçeksi',
        'verified_at': '2026-09-27T00:00:00+00:00',
        'variants': [{'label': '9 ml Cologne', 'size_ml': 9, 'concentration': 'Cologne'},
                     {'label': '30 ml Cologne', 'size_ml': 30, 'concentration': 'Cologne'},
                     {'label': '50 ml Cologne', 'size_ml': 50, 'concentration': 'Cologne'},
                     {'label': '100 ml Cologne', 'size_ml': 100, 'concentration': 'Cologne'}],
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
