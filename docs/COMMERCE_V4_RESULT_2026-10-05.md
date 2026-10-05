# SENLIS — Kanıtlı arama denemesi

5 Ekim 2026, 20:07 Türkiye saati. GitHub koşusu: https://github.com/canmuslu59/senlis/actions/runs/37344960846

Eski tam tarama ve kuyruğu durduruldu. Yeni sistem, yalnızca 10 ürün ve 2 olumsuz kontrol üzerinde tek iş olarak denendi. Ana veritabanına yazılmadı; yeni tam tarama sıraya konmadı. Betik 525,3 saniye (yaklaşık 9 dakika) sürdü.

## Sonuç

| Ölçüm | Sonuç |
|---|---:|
| Arama kanıtı oluşan ürün | 10/10 |
| Tam okunmuş kaynak kataloğu | 5/5 |
| Kaynaklardaki toplam ürün kaydı | 10.812 |
| Fiyatı kabul edilen ürün | 3 |
| Stokta fiyatı bulunan ürün | 2 |
| Yalnızca stok dışı fiyatı bulunan ürün | 1 |
| Bu kataloglarda eşleşme çıkmayan ürün | 4 |
| Adayı bulunan, doğrulama kuralına takılan ürün | 2 |
| Aday sayfasına erişilemeyen ürün | 1 |
| Doğru reddedilen dekant/muadil kontrolleri | 2/2 |

“Arama kanıtı”, seçilen kaynak kataloglarının okunması, ürün kimliğiyle çalıştırılan sorgunun ve adaylarının kaydedilmesidir. Bütün internetin tarandığını veya eşleşmeyen ürünün hiçbir yerde satılmadığını göstermez. Perfume Point ve Yes Parfümeri bütün hedeflerde; Caudalie, MAD ve INNATIVE ilgili marka hedeflerinde kullanıldı. Toplam 23 ürün-kaynak sorgusu var.

## Kaynak kapsamı

| Kaynak | Katalog kaydı |
|---|---:|
| Perfume Point | 5.991 |
| Yes Parfümeri | 3.918 |
| Caudalie | 103 |
| MAD | 749 |
| INNATIVE | 51 |

INNATIVE'nin 51 ürün başlığı canlı sayfalardan okundu; eski URL adları güncel ürün adı olarak kabul edilmedi. Önceki bulunan bağlantılar keşif girdisi yapılmadı. Aramalar arasında aynı site için bekleme ve hata sonrası soğuma uygulandı.

## On ürünün durumu

| ID | Ürün | Durum |
|---|---|---|
| 3045 | Acqua di Parma — Blu Mediterraneo Arancia di Capri | Kapsamdaki kataloglarda eşleşme yok |
| 3431 | Adidas — Action Adidas 1997 After Shave | Kapsamdaki kataloglarda eşleşme yok |
| 36013 | Caudalie — Ange des Vignes | Aday bulundu; doğrulama reddetti |
| 50275 | DSQUARED² — 2 Wood | Kapsamdaki kataloglarda eşleşme yok |
| 77267 | INNATIVE — BERRY AURA EDP | Aday bulundu; doğrulama reddetti |
| 77787 | Issey Miyake — A Drop d’Issey EDP | Aday bulundu; sayfada zaman aşımı |
| 90677 | Lalique — Amethyst | Fiyat doğrulandı; stok dışı |
| 97100 | Loris — Almamlaka | Kapsamdaki kataloglarda eşleşme yok |
| 100781 | Mad Parfumeur — 1923 | Fiyat doğrulandı; stokta |
| 113828 | Narciso Rodriguez — All Of Me | Fiyat doğrulandı; stokta |

## Kabul edilen örnek fiyatlar

Fiyat ve stok bilgisi koşu anına aittir. Üç ürün için farklı hacim/satıcılarda toplam 6 teklif kabul edildi; aşağıda results.csv ile aynı seçili teklifler var.

| Ürün | Hacim | Fiyat | Stok | Satıcı |
|---|---|---:|---|---|
| Lalique Amethyst | 100 ml | 3.162,50 TL | Yok | Perfume Point |
| MAD 1923 erkek | 100 ml | 1.999,99 TL | Var | MAD |
| Narciso Rodriguez All Of Me | 50 ml | 3.857,50 TL | Var | Perfume Point |

Bağlantılar:
- https://www.perfumepoint.com.tr/lalique-amethyst-edp-100-ml
- https://www.madparfum.com/urun/mad-1923-erkek-100-ml-parfum-mad-tff-1923-for-men/
- https://www.perfumepoint.com.tr/narciso-rodriguez-all-of-me-edp-50-ml

## Açık kalan noktalar

Caudalie ve INNATIVE ürünleri “bulunamadı” değildir. Saklanan HTML ile kodun birlikte incelenmesi, iki muhafazakâr ret nedenine işaret ediyor: Caudalie başlığındaki kategori öneki ve INNATIVE teklif URL'sindeki ürün varyantı parametresi. Kimlik/hacim korumaları korunarak ayrı düzeltme ve test gerektiriyor. Bu iki sayfanın fiyatı pilotun doğrulanmış sonuçlarına eklenmedi.

Issey Miyake'nin 50 ml adayında zaman aşımı oldu; aynı sitenin sonraki istekleri soğuma nedeniyle atlandı. Bu durum sayfa erişim hatası olarak kaldı, ürün yokluğu sayılmadı. Lalique için de aynı sitede atlanan aday var; kabul edilen fiyat başka satıcının sayfasından geldi.

Dekant ve muadil olarak önceki çalışmada yanlış kabul edilen iki sayfa bu kez doğru reddedildi.

## Kanıtın yeniden doğrulanması

- Beş katalog dosyasının içerik özeti ve kayıt sayısı yeniden hesaplandı.
- 83 yanıt kopyası referansının SHA-256 özeti kontrol edildi.
- On ürünün 23 kaynak sorgusu saklanan kataloglar üzerinde yeniden çalıştırıldı; aday URL listeleri aynı çıktı.
- Kabul edilen 6 teklif saklanan ürün sayfalarından yeniden ayrıştırıldı; URL, fiyat, para birimi ve hacim aynı çıktı.
- Paket bütünlük kontrolü geçti. Ayrıntılı makine çıktısı: DOGRULAMA.json.

Pilotun GitHub test kapısında 45 test geçti. Sonraki hata yanıtı gövdesini koruma iyileştirmesinden sonra yerelde 47 test geçti. Pilot, bu iyileştirmeden önce başlamıştı; bu koşudaki başarısız isteklerde HTTP yanıt gövdesi gelmedi (zaman aşımı/soğuma). Gelecek koşularda gelen hata/engel yanıtlarının gövdesi de boyut sınırı belirtilerek korunuyor.

Koşu kaynak commit'i: 53d38d878e1a05d957bed0c6db76187313180aad
Hata gövdesi iyileştirmesi commit'i: b7c64589c3d5955c6c1d1109c6cd0ab6b6774b19
Dal: feature/commerce-evidence-v4-20261005
GitHub artifact ID: 11360242751
Orijinal GitHub ZIP SHA-256: a968737ce08d8991b449d29a3402fa3804fd176606ab7f1473eaa60190428c54

Bu küçük pilotun süresi, tüm veritabanına doğrusal biçimde çarpılarak güvenilir tamamlanma süresi vermez. Tam tarama kapalı; kapsam, bu iki doğrulama kuralı ve erişim hatası çözülmeden büyük kuyruğa geçilmedi.
