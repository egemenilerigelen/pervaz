# 0006 — Kart anatomisi

Durum: kabul edildi (2026-11-02)

## Bağlam

Her kart aynı türden işleri yapar (veri getirmek, saklamak, çizmek) ama kartlar farklı zamanlarda
yazıldığı için dosya adları tutarsızdı. Bir kartı okuyan biri diğerinde kaybolmamalı: **aynı iş
hep aynı adı taşımalı**.

## Karar

Standart iskelet ([yeni kart rehberi](../adding-a-card.md#1-paket-anatomisi)): `card.py`,
`models.py`, `source.py`, `cache.py`, `service.py`, `widgets.py`, `icon.py`, `formatting.py`,
`windows.py`. Gereksiz olan dosya oluşturulmaz. `card.py` yalnızca görünüm ve sinyal
bağlantısıdır; saf mantık Qt'siz ayrı bir dosyaya çıkar.

Mevcut kartların bu iskelete eşlemesi:

| Rol | weather | finance | telemetry | spotify | clipboard | github |
| --- | --- | --- | --- | --- | --- | --- |
| `card.py` | evet | evet | evet | evet | evet | evet |
| `models.py` | evet | evet | evet | evet | `history.py` | evet |
| Veri kaynağı | `api.py` | `providers/` | `sampler.py`, `gpu.py`, `ping.py` | `backend.py` (Protocol) + `windows.py` | yok (Qt panosu) | `api.py` |
| `cache.py` | evet | evet | yok (anlık veri) | evet | yok ([ADR 0004](0004-pano-gecmisi-diske-yazilmaz.md)) | evet |
| `service.py` | yok (`Poller`) | evet | yok (`Poller`) | `worker.py` | yok | yok (`Poller`) |
| `widgets.py` | yok | yok | evet | evet | `card.py` içinde | evet |
| `icon.py` | evet | evet | evet | `logo.py` | evet | evet |
| `formatting.py` | yok | evet | evet | evet | `history.py` içinde | yok |
| `windows.py` | yok | yok | evet | evet | yok | yok |

Karta özgü ek dosyalar adlarını korur: `weather/places.py`, `weather/backdrop.py`,
`spotify/controls.py`, `spotify/state.py`, `spotify/palette.py`, `spotify/backdrop.py`.

### Sapmalar

- **`source.py` yok.** Okunabilirliği artırmayan yeniden adlandırma yapılmadı: `weather/api.py` ve
  `github/api.py` hem ayrıştırmayı hem kaynak `Protocol`'ünü ve gerçek uygulamayı taşır
  (`WeatherSource` + `OpenMeteoSource`, `ContributionSource` + `GithubProfileSource`). Finansın
  birden çok kaynağı `providers/` paketindedir. Telemetrinin `sampler`/`gpu`/`ping` ayrımı
  anlamlı olduğu için korundu; hepsi kartta tek bir `SystemSource` Protocol'ü (ve ayrı ping
  fonksiyonu) arkasında toplanır. Spotify'ın Protocol'ü `backend.py`, gerçek uygulaması
  `windows.py`'dir.
- **Gerçek uygulama `SPEC.factory`'de değil, kurucu varsayılanında seçilir** (`source or
  OpenMeteoSource()`). Fabrika tek satır kalır, testler kartı sahte bağımlılıkla doğrudan kurar.
  Tek istisna Spotify'dır: `WindowsBackend` ağır ve yüklenemeyebilir olduğu için fabrikada tembel
  içe aktarılıp verilir.
- **Telemetride ping bir `Protocol` değil bir fonksiyondur** (`Callable[[], float | None]`): tek
  yöntemli bir arayüz için ayrı sınıf gereksizdi.
- **Her kart `__init__.py`'si aynıdır:** `SPEC` ve kart sınıfı dışa aktarılır, `__all__` listelenir.
  Mimari testi `SPEC` ve `CARDS` kaydını denetler.
