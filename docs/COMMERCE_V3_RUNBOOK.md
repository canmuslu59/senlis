# SENLIS tam katalog fiyat bağlantısı taraması — v3.1

## Kapsam ve çalışma

174.259 benzersiz master ürün ID'si, marka filtresi olmadan 192 parçaya ayrılır. Dört parça aynı anda, 48 sıralı dalgada çalışır. Her parçada iki ürün işçisi vardır. Önceki bağlantılar sadece başlangıç adresidir; eski fiyatlar doğrulanmış fiyat olarak aktarılmaz.

Tam taramanın ön koşulları: regresyon testleri, sonuç dalına yazma/okuma denemesi, gerçek arama motorundan ilgili sonuç ve 10 ürünlük canlı denemede en az iki sayfadan doğrulanmış TL fiyatı. Yerel canlı deneme 4 Ekim 2026 tarihinde 161,3 saniyede 7 doğrulanmış fiyat, 2 bulunamayan ve 1 ertelenen kayıt üretti. Bu oran 174.259 ürüne genellenmez.

## Bekleme ve hata yönetimi

- Aynı alan adına dört çalışma şeridi arasında 2,5 saniyelik ayrı zaman aralıkları; 0–0,4 saniye ek rastgele bekleme. Aynı şerit aynı alan adına yaklaşık 10 saniyeden sık istek göndermez. Yönlendirmeler de kurala dahildir.
- Bağlanma/okuma zaman aşımı 10/25 saniye, gövde okuma üst sınırı yaklaşık 45 saniye ve 6 MiB.
- HTTP 429 için sunucunun Retry-After değeri ve en az 60 saniye; geçici hatalarda artan bekleme; 403 veya aktif doğrulama engelinde en az 15 dakika alan adı molası.
- Bir üründe en fazla üç deneme; erişilemeyen ürün `deferred_search`, `deferred_page` veya `worker_error` kalır. Bunlar tamamlanmış/bulunamamış sayılmaz.
- Parça başına beş saatlik yumuşak süre sınırı. Bitmeyen kayıtlar sonraki çalıştırmada kaldığı yerden devam eder.

Bekleme kuralları sitelerin istekleri kabul etmesini garanti etmez. Ek engeller tamamlanma süresini uzatabilir. Ücretsiz arama motorlarının HTML sonuçları DDG, Bing ve Yahoo sırasıyla değerlendirilir; engeller aşılmaya çalışılmaz.

## Kayıt ve yeniden başlatma

Özellik dalı: `feature/commerce-full-v3-20261004`.
Kalıcı veri dalı: `data/commerce-v3-20261004`.
Parça kayıtları: `data/commerce_v3_checkpoints/v3.1/part_NNN/*.jsonl.gz`.

Her sonuç yerel günlüğe fsync ile eklenir. Her 50 sonuçta veya beş dakikada bir sıkıştırılmış, içerik özetiyle adlandırılmış ek kayıt sonuç dalına yüklenir. Aynı parçanın önceki tamamlanmış ID'leri tekrar işlenmez. Sonuç dosyaları ayrıca her işin sonunda GitHub Actions artifacts alanına yüklenir ve 30 gün tutulur.

GitHub Actions içindeki **SENLIS Full Commerce v3** çalışmasının **Re-run all jobs** komutu tüm parçaları kalıcı kayıtlardan devam ettirir. Tamamlanmış parçalar hızlıca atlanır, ertelenen/eksik kayıtlar yeniden denenir. Çalışmanın iptali en son uzaktan kayıttan sonraki en fazla yaklaşık beş dakikalık ilerlemeyi yeniden gerektirebilir.

Son birleştirme tüm ID'leri koruyan CSV, JSONL ve `SENLIS_commerce_full_v3.sqlite` üretir. SQLite `commerce` tablosu ürün ID'si ile JSON kaydını taşır. Eksik kayıt varsa son adım hata verir ve eksikliği açıkça raporlayan dosyaları yine yükler. Ana ürün veritabanı silinmez veya değiştirilmez; bu çıktı ürün ID'si üzerinden eşleştirilen fiyat/bağlantı veri setidir.

## Durum ve süre

Canlı günlükte START, CHECKPOINT ve SUMMARY satırları kapsamı, tamamlanan/ertelenen kayıtları, doğrulanmış fiyatları ve HTTP sayaçlarını gösterir. GitHub iş özetleri ve kalıcı parça dosyaları ilerleme kanıtıdır.

Başlangıç tahmini: 120–190 saat, yaklaşık 150 saat (6 gün). 174.259 birincil aramanın tek arama alan adına 2,5 saniye arayla yapılması tek başına yaklaşık 121 saat; ilave sorgular, sayfa okumaları, önceden bilinen adresler ve sağlayıcı molaları gerçek süreyi değiştirir. İlk tamamlanan parçalarla yeniden hesaplanmalıdır. Engeller ve tekrar çalıştırma gereksinimi bu aralığı aşabilir. Dört şeritlik her dalga en fazla yaklaşık beş saat çalıştığından ilk geçişin planlanan üst bütçesi yaklaşık 240 saat artı kurulumdur; bu bütün ürünlerin sonuçlandığı anlamına gelmez.

`verified_price` ürün sayfasındaki eşleşen ürün ve açık TRY fiyat kanıtıdır. Sepete ekleme/ödeme testi yapılmaz (`checkout_verified=false`). Stok ayrı tutulur; `unknown` mevcut stok diye gösterilmez. Sonuçlar yakalandıkları `checked_at` anını temsil eder.
