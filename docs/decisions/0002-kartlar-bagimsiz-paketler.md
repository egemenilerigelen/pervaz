# 0002 — Kartlar bağımsız paketlerdir

Durum: kabul edildi (2026-11-02)

## Bağlam

Panelin değeri, kart eklemenin ve bir kartı bozmadan değiştirmenin kolay olmasındadır. Ayrıca bir
kartın hatası (ağ yok, kütüphane yüklenemedi, beklenmedik istisna) panelin ve diğer kartların
çalışmasını durdurmamalıdır.

## Karar

- Her kart `cards/<ad>/` altında kendi paketidir ve `__init__.py`'den bir `SPEC` (`CardSpec`)
  dışa aktarır. Kart kaydı `cards/__init__.py` içindeki `CARDS` demetidir; sıra varsayılan sıradır.
- Bir kart yalnızca kendi paketini, `core`, `infra` ve `theme`'i kullanır; **başka bir kartı import
  etmez**.
- Kartın dış dünyası (veri kaynağı, önbellek, saat, platform arka ucu) bir `typing.Protocol` ile
  tanımlanır ve kurucudan verilir.
- Hata izolasyonu üç noktadadır: `CardManager` fabrika hatasını yakalar, `CardHost` yaşam
  döngüsü çağrılarını yakalar, kartın sinyal yuvaları `@guarded` ile sarılır. Hata yalnızca o
  kartın içinde görünür.
- Zor yüklenen bağımlılıklar kartın fabrikasında tembel içe aktarılır (Spotify'ın WinRT ve pycaw
  bağımlılıkları): yüklenemezse yalnızca o kart başlatılamaz.
- Kart sözleşmesi (`on_show` başlat, `on_hide` durdur, `shutdown` bırak) tüm kartlar için tek bir
  parametreli sözleşme testiyle sınanır.

## Sonuç

- Yeni kart = yeni paket + `CARDS`'a bir satır; çekirdeğe dokunulmaz.
- İki kartın ortak ihtiyacı çekirdeğe ya da `infra`'ya taşınır, kartlar arasında paylaşılmaz.
- Ağır ya da yavaş bir kart panelin açılışını geciktirmesin diye iş arka plan iş parçacığında yapılır
  ve kart kurulumu hafif tutulur.
- Uygulama kurucudan bağımlılık aldığı için testler gerçek ağ, pano, ses cihazı ya da Spotify
  oturumu kullanmaz.
