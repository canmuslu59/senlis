# Kanıtlı katalog araması — sınırlı pilot

Kullanıcı 5 Ekim 2026'da eski çalışmanın ve kuyruğunun durdurulmasını, gerçekten arandığını kanıtlayabileceğimiz yeni bir düzenle deneme yapılmasını istedi. Eski run 37279015036 cancelled olarak doğrulandı; tam tarama iş akışı duraklatıldı. Sonuç dalı korundu.

Başarı ölçütü: aynı 10 ürün için hangi kaynakta, hangi ad/marka ile, kaç ürün kaydı üzerinde arama yapıldığı ve adayların neden kabul/reddedildiği tekrar üretilebilir olmalı. Fiyat bulmak ile arama yapıldığını kanıtlamak ayrı ölçülür. Bütün internette veya bütün mağazalarda arandığı iddia edilmez.

Yeni yöntem: Perfume Point ve Yes Parfümeri'nin yayınladığı ürün site haritaları; eşleşen markalar için Caudalie, MAD ve INNATIVE resmi ürün listeleri. Site haritasındaki ürün başlıkları ve URL'leri yerel indekslenir. Küçük INNATIVE listesinin ürün başlıkları canlı sayfalardan tamamlanır; eski URL adları güncel ürün adı sayılmaz. Önceki 933 bağlantı veya fiyatlar keşif girdisi değildir; yalnızca test ürün ID'leri ve doğrulanmış kimlik ayrımları kullanılır.

Her kaynak kök XML'i ve tüm ürün alt haritaları başarıyla okunmadan tamamlandı sayılmaz. HTTP 200 tek başına yeterli değildir. Ham cevapların SHA-256 özeti/sıkıştırılmış kopyası, HTTP durumu, katalog girdileri, sorgu ve aday listesi artifacts olarak saklanır. İki satıcı + ürüne uygun resmi kaynaklar ayrı ayrı görünür. Eksik kaynak `search_unproven`; kapsam içindeki tamamlanmış listede eşleşme yoksa `no_catalog_match` olur; bunlar global `not_found` değildir.

Fiyat kabulü: canlı ürün kimliği, form/konsantrasyon/cinsiyet, seçilen hacim ve TRY fiyatı aynı sayfada doğrulanır. Muadil ve dekant reddedilir; belirsiz hacim fiyat doğrulamasını engeller. Önceki hatalı iki gerçek sayfa negatif kontrol olarak yeniden okunur. Kayıtlar ana veritabanına yazılmaz.

Çalışma: tek GitHub işi, en fazla 25 dakika, 10 hedef + 2 negatif kontrol; aynı siteye en az 5 saniye bekleme; 403/429 ve engellerde mevcut artan bekleme kuralları. Sadece bu pilot çalışır, sonraki tam katalog kuyruğu yoktur. İlk pilot tüm kaynakları/aramaları kanıtlayamazsa başarısız raporlanır ve artifacts yine yüklenir. Büyük katalog için süre tahmini verilmeden bu sonuçlar değerlendirilir.
