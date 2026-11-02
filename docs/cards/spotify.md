# Spotify kartı

Spotify masaüstü uygulamasında çalan şarkıyı gösterir ve yönetir: kapak, şarkı, sanatçı,
ilerleme çubuğu (istediğin yere tıklayıp atlanır), önceki / oynat-duraklat /
sonraki, karıştır, tekrarla, ses düzeyi ve ses çıkışı. Hesap bağlamak gerekmez; veri
Windows'un medya oturumundan gelir, bu yüzden yalnızca Spotify'ı izler (tarayıcı
sekmelerini ya da başka çalarları değil) ve Premium şartı yoktur. Panel açıkken saniyede
bir okunur.

- **Spotify kapalıyken** en son kalan şarkı (kapağı ve konumuyla) görünür; uygulama
  Spotify kapalıyken açılsa da böyle olur. Oynat/atla düğmeleri pasifleşir; Spotify açılınca
  güncel şarkı gelir.
- **Kapak** yalnızca albüm görselidir; Spotify'ın görsele eklediği logo bandı kırpılır.
- **Renkler kapağı izler:** kartın arka planındaki yumuşak ışık kapağın baskın tonunu yansıtır;
  şarkı çubuğu, açık karıştır/tekrarla düğmeleri ve oynat dolgusu da aynı tonu alır. Renk,
  algısal OKLCH uzayında seçilir: siyah, beyaz ve gri alanlar oy kullanmaz, her kapakta ışıma
  eşit güçte görünür, çubuk gerçek zemininde okunur kalır. Gri kapağa renk uydurulmaz. Kapak
  yoksa temanın vurgu rengi (altın) kalır.
- **Arka plan panele oturur:** kartın ayrı bir açık yüzeyi yoktur, panelin zemini doğrudan
  görünür. Üzerine, kapaktan uzaklaştıkça irileşen dalgalı bir nokta deseni çok hafifçe biner.
- **Oynat düğmesi** çalarken sade (yalnızca duraklat simgesi), duraklayınca soluk dolgulu
  görünür.
- **Katlıyken** başlık satırında "Sanatçı – Şarkı" özeti görünür.
- **Ses çubuğu** Windows'un sistem sesini (görev çubuğundaki hoparlör) ayarlar; Spotify
  kapalıyken de çalışır. Spotify'ın uygulama içi ses çubuğu dışarıdan ayarlanamaz.
- **Çıkış cihazı** düğmesi, bağlı hoparlör ve kulaklıkları listeler; seçilen, Windows'un
  **varsayılan** çıkışı olur (yalnızca Spotify'ı değil tüm sistemi etkiler).
- Reklam sırasında Spotify atlamayı ve şarkı geçmeyi kapatır; düğmeler de pasif görünür.

Komuttan hemen sonra düğmeler anında tepki verir (örneğin duraklat basılınca simge hemen
değişir); Spotify'ın yeni durumu bildirmesi 1–2 saniye sürebilir ve bu sürede okumadan gelen
eski durum, yapılan değişikliği geri almaz.

## Ayarlar

Kartın `config` alanı yoktur. Açılıp kapanma ve katlanma durumu genel kart ayarlarındadır.

## Geliştirici notları

```text
cards/spotify/
├── __init__.py   # SPEC
├── card.py       # SpotifyCard: parçaları birleştirir, yoklama, komutlar
├── controls.py   # ProgressRow, TransportRow, AudioRow: denetim satırları
├── state.py      # Hold, CommandHold, PendingVolume: komut sonrası tutma mantığı (Qt'siz)
├── backend.py    # SpotifyBackend (Protocol): kartın Windows'tan beklediği arayüz
├── windows.py    # WindowsBackend: medya oturumu (WinRT) + ses (pycaw/WASAPI)
├── worker.py     # Worker: tek, uzun ömürlü arka plan iş parçacığı
├── cache.py      # LastPlayedCache (JsonCache) + LastPlayedStore: spotify.json, spotify_cover.bin
├── models.py     # Track, NowPlaying, Volume, AudioOutput, Reading, Repeat
├── palette.py    # kapaktan OKLCH ile renk seçimi
├── backdrop.py   # kapak tonlu arka plan ve nokta deseni
├── widgets.py    # JumpSlider, CoverView, art_rect (logo bandını kırpar)
├── logo.py       # başlık simgesi (Spotify logosu)
└── formatting.py # süre ve katlı başlık özeti
```

**Veri akışı:** `Worker` (COM/WinRT çağrılarının hepsi bu tek iş parçacığında) ->
`SpotifyBackend.read()` -> `Reading` -> `done` sinyali -> `SpotifyCard._apply` -> arayüz.
Komutlar (oynat, atla, ses...) aynı `Worker` kuyruğuna girer, böylece komuttan sonraki okuma
yeni durumu görür.

**Neden tek iş parçacığı:** COM nesneleri ve WinRT çağrıları kurulduğu iş parçacığına bağlıdır.
İş parçacığı daemon'dur: bloklanan bir çağrı uygulamanın kapanmasını geciktirmez.

**`windows.py` tembel içe aktarılır:** `SPEC.factory` onu kart kurulurken içe aktarır. WinRT ya
da pycaw yüklenemezse yalnızca bu kart başlatılamaz, panel etkilenmez.

**Yaşam döngüsü:** `on_show` yoklamayı (1 sn) ve ilerleme akıtmayı (250 ms) başlatır; `on_hide`
ikisini durdurur ve son konumu diske yazar. `shutdown` zamanlayıcıları ve `Worker`'ı durdurur.

**Test:** `FakeBackend` ve sahte saat ile çalışır; gerçek Spotify, ses cihazı ya da medya
oturumu kullanılmaz.
