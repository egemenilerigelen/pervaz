# 0001 — Katmanlı mimari

Durum: kabul edildi (2026-11-02)

## Bağlam

Panel her kartla büyüyor: hava, finans, telemetri, Spotify, pano, GitHub; takvim ve pil/ses
sırada. Bağımlılıklar denetlenmezse çekirdek kartlara, kartlar birbirine ve Windows'a özgü kod
her yere yayılır; bir kartı değiştirmek ötekini bozar, test yazmak zorlaşır.

## Karar

Bağımlılık yalnızca aşağıya doğru akar:

```text
app  ->  cards/<özellik>  ->  core  ->  infra, theme
```

- `identity` (uygulamanın kimliği) hiçbir şeyi bilmez; her katman onu okuyabilir.
- `core/platform` (kısayol, fare, tek kopya kilidi...) yalnızca kendisini ve `identity`'yi bilir.
- `core` hiçbir karta ve `app`'e bağımlı olmaz; kartlar çekirdeğe yalnızca `CardSpec` ile takılır.
- Yalnızca `app` (birleştirme noktası) her şeyi bilebilir; kimse `app`'i import etmez.
- Kurallar `tests/test_architecture.py` ile her test çalışmasında denetlenir; paket içinde döngüsel
  import ve kayıtsız kart paketi de testte düşer.

## Sonuç

- Kural ihlali, kod gözden geçirmeye kalmadan testte yakalanır. Kuralı gevşetmek yerine kod doğru
  katmana taşınır; bu test asla gevşetilmez.
- Birden çok kartın ihtiyaç duyduğu yardımcı çekirdeğe ya da `infra`'ya çıkar (`Poller`, `ElidedLabel`,
  `JsonCache`). Bu bilinçli bir bedeldir: kartlar arası kopyalama yerine paylaşılan, test edilmiş kod.
- Windows'a özgü kod iki yerde toplanır: `core/platform` ve kartın kendi `windows.py` dosyası.
