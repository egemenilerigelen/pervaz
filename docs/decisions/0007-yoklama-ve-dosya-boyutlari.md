# 0007 — Ortak yoklama altyapısı ve büyük dosyalar

Durum: kabul edildi (2026-11-02)

## Bağlam

Periyodik veri çeken kartlar aynı sorunu çözer: ağ isteğini arayüzü dondurmadan, kapanışı
geciktirmeden ve süre giderken kaynak ya da durum değişse bile yanlış sonucu göstermeden
yapmak. Bu mantık iki yerde ayrı ayrı yazılmıştı (`core/polling.py` ve finansın `PriceService`'i).
Ayrıca birkaç dosya okunabilirlik eşiği olan ~300 satırı aşıyor.

## Karar

- **Yoklama tek yerdedir:** `core/polling.py` içindeki `Poller` arka plan iş parçacığını (daemon),
  nesil numaralarını, durdurup yeniden başlatmayı ve hata sonrası yeniden denemeyi yönetir.
  `PriceService` ona dayanır ve yalnızca durum makinesini (`FeedState`) ve bayatlık denetimini
  taşır; bunun için `Poller`'a istisnanın kendisini veren `raised` sinyali ve `failures` sayacı
  eklendi.
- **Spotify kendi `Worker`'ını korur:** COM ve WinRT çağrıları kurulduğu iş parçacığına bağlıdır,
  bu yüzden hepsi tek, uzun ömürlü bir iş parçacığında sırayla çalışır; komutlar ve okumalar aynı
  kuyruğa girer. İstekten istek yeni iş parçacığı açan `Poller` buna uymaz.
- **`core/settings.py` bölünmedi** (196 satır): model, doğrulama yardımcıları ve depo birbirine
  sıkı bağlı ve dosya okunmayı zorlaştırmıyor. Bölme, dosya gerçekten zorlaştığında yapılır.
- **~300 satırı aşan kaynak dosyalar:**
  - `cards/spotify/card.py` (438 satır): denetim satırları `controls.py`'ye, komut sonrası tutma
    mantığı `state.py`'ye çıkarıldı; kalan, kartın yoklama, komut ve çizim bağlantısıdır ve tek
    bir sorumluluk altındadır. Daha fazla bölmek bağlantıyı dosyalar arasına dağıtırdı.
  - `cards/telemetry/card.py` (304 satır): satır tanımları ve altı boyama metodu bir arada
    okunuyor; bölmek okunabilirliği artırmazdı.
- **Testler:** `tests/cards/spotify/test_spotify_card.py` (668 satır) tek bir kartın tüm davranışını
  kapsar; konular bölünürse ortak sahte nesneler (saat, arka uç, depo) tekrar edilmek zorunda kalır.

## Sonuç

- Yeni bir yoklayan kart `Poller` kullanır; kendi iş parçacığı kodunu yazmaz.
- `Poller`'ın sözleşmesi (`succeeded`, `failed`, `raised`, `stop` sonrası geç sonucu yok sayma)
  `tests/core/test_polling.py` ile sınanır.
- Bu dosyalar belirgin biçimde büyür ya da yeni bir sorumluluk kazanırsa bu karar gözden geçirilir.
