# SENLIS Lab (deneysel dal)

Bu dal `feature/senlis-premium-foundation` üzerindeki v0.6.0-dev uygulamasından türetilmiş
**deneme** sürümüdür. Katalog veritabanına (`app/src/main/assets/catalogue.*`, `docs/`,
`service/`, `data/`, `IndexedCatalog`) dokunulmadı; yalnızca uygulama arayüzü ve yerel
eşleştirme mantığı değişti.

- Paket adı `com.innative.senlis.lab`, uygulama adı **SENLIS Lab**, sürüm `0.7.0-lab`.
  Mevcut önizleme uygulamasının yanına ayrı uygulama olarak kurulur.
- APK, `.github/workflows/lab-apk.yml` ile GitHub Actions'ta derlenir, API 23 ve 35
  emülatörlerinde `ci/lab_smoke.py` ile denenir ve **Releases** altında `lab-v0.7.0-rN`
  adıyla ön sürüm (pre-release) olarak yayımlanır.

## Denenen fikirler

| Özellik | Nerede | Not |
|---|---|---|
| Bugünün kokusu | Keşfet | Mevsim ve günün saatine göre, profil sıralamasından günlük seçim. Aynı gün aynı öneri. |
| Koku günlüğü | Detay → "Bugün bunu sıktım", Profil | Son 7 gün, üst üste gün serisi. Yalnızca cihazda (`senlis_lab_diary`). |
| Karşılaştır | Detay → "Karşılaştırmaya ekle" | Ortak ve farklı notalar, nota benzerlik yüzdesi, iki koku için ayrı uyum. |
| Dokunulabilir notalar | Detay → Koku notaları | Dokun: o notayı ara. Basılı tut: sevdiklerine veya kaçındıklarına ekle. |
| Koku DNA'n | Profil | Seçilen notalar, favoriler ve günlükten nota dağılımı; metin olarak paylaşılabilir. |
| Eşleştirme modeli v2 | `MatchEngine` | "vanilya" artık "karamelize vanilya" gibi bileşik nota adlarını da bulur; kaçınılan notalarda da geçerli. Yalnızca tam kelime eşleşir ("nar" ≠ "narenciye"). |
| Arayüz | Genel | Ekran geçişinde yumuşak geçiş, alt menüde aktif sekme çizgisi, seçimlerde dokunsal geri bildirim. |

## Bilinen sınırlar

- Firebase ayarı yok; topluluk, puan ve haber bölümleri önizlemedeki gibi "yapılandırılmadı" der.
- Her CI derlemesi farklı bir debug anahtarıyla imzalanır; yeni bir lab sürümü kurmadan önce
  eskisini kaldırmak gerekebilir.
- Paketlenmiş katalog hâlâ 10 üründür.
