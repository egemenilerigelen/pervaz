# CLAUDE.md

Pervaz: ekranın kenarındaki tutamaçtan açılan, kartlardan oluşan modüler bir **Windows** paneli
(PySide6). Her bilgi (hava, finans, telemetri, Spotify, pano, GitHub) bağımsız bir kart paketidir.
Yalnızca Windows'ta çalışır. Kullanıcı Türkçe konuşur: yanıtlar, arayüz metinleri, docstring'ler
ve yorumlar Türkçe olur.

Ayrıntı `docs/` altındadır: [mimari](docs/architecture.md), [yeni kart](docs/adding-a-card.md),
[ayarlar](docs/settings.md), [geliştirme](docs/development.md), [kartlar](docs/cards),
[kararlar](docs/decisions).

## Komutlar

```bash
pip install -e ".[dev]"                                    # kurulum
python -m pytest -q                                        # testler (Qt ekransız)
python -m ruff check .                                     # lint
python -m ruff format .                                    # biçim
python -m PyInstaller --noconfirm packaging/pervaz.spec    # dist\Pervaz.exe
```

Commit öncesi `ruff check .`, `ruff format --check .` ve `pytest -q` temiz olmalı.

## Mimari kurallar

- Bağımlılık yönü: `app -> cards/<kart> -> core -> infra, theme`. `core/platform` yalnızca
  kendini ve `identity`'yi bilir.
- **Kartlar birbirini import etmez.** `core` hiçbir kartı bilmez. Ortak ihtiyaç `core`'a ya da
  `infra`'ya taşınır.
- Windows'a özgü kod `core/platform` ya da kartın kendi `windows.py` dosyasında durur.
- Kimlik (ad, görünen ad, AppUserModelID, veri klasörü değişkeni) yalnızca `src/pervaz/identity.py`'de
  tanımlanır; başka yerde tekrar yazılmaz.
- **`tests/test_architecture.py` asla gevşetilmez.** Kural ihlalinde kodu doğru katmana taşı.
- Her kart paketi aynı anatomiyi izler ([ADR 0006](docs/decisions/0006-kart-anatomisi.md)):
  `card.py`, `models.py`, `cache.py`... `__init__.py` yalnızca `SPEC` (ve kart sınıfını) dışa aktarır.

## Kart sözleşmesi

- `on_show`'da yoklamayı/zamanlayıcıyı başlat, `on_hide`'da durdur, `shutdown`'da bırak.
- Beklenen hatayı `fail("mesaj")` ile bildir, düzelince `clear_error()`. Sinyal yuvalarını ve
  zamanlayıcı geri çağrılarını `@guarded` ile sar: istisnayı yutma ama paneli de çökertme.
- Dış bağımlılıklar kurucudan ve `Protocol` ile gelir (kaynak, önbellek, saat, pano, arka uç).
- Önbellek `infra.storage.JsonCache`'ten türer. Modeller `@dataclass(frozen=True)`'dir.
- Yoklama gereken kart `core.polling.Poller`'ı kullanır; kendi iş parçacığı kodunu yazmaz.
- Yeni kart = yeni paket + `CARDS`'a bir satır. Sözleşme testi kartı kendiliğinden kapsar.

## Görünüm

- Kartlarda **sabit renk ya da ölçü yok**; her şey `theme/tokens.py`'den (`look.theme`,
  `look.metrics.sp()`) ve stil sayfası rollerinden gelir.
- Açık ve koyu tema ikisi de desteklenir; metin her zeminde okunur kalır (kontrast testleri var).
- Arayüz **zıplamaz:** katlama, kaydırma çubuğu ve değişen metin yerleşimi kaydırmamalı. Geçmişte
  düzeltilen hatalar: art arda katlamada zıplama, kaydırma çubuğunun yer değiştirmesi.
- Başlık bilgisi (`set_info`) varsayılan boştur; yalnızca anlamlıysa görünür.

## Ayarlar

`settings.json` elle düzenlenebilir. Bozuk ya da tanınmayan değer **sessizce varsayılana döner**;
uygulama bu yüzden asla açılmaz hale gelmez. Kart ayarlarını (`config`) da aynı şekilde doğrula.

## Gizlilik ve veri

- Hesap ya da token isteyen kaynak eklenmez ([ADR 0003](docs/decisions/0003-hesapsiz-veri-kaynaklari.md)).
- Pano geçmişi diske yazılmaz; parola işaretli pano içeriği atlanır
  ([ADR 0004](docs/decisions/0004-pano-gecmisi-diske-yazilmaz.md)).
- Dosya yazmaları atomiktir (`write_json`). Kullanıcı verisi `%APPDATA%\Pervaz\` altındadır.

## Performans

- Panel kapalıyken zamanlayıcı yok; boşta işlemci ~%0. (Bilerek arka planda yenileyen hava ve
  GitHub kartları ve olay tabanlı pano kartı istisnadır.)
- Ağır iş (ağ, sistem okuma, Windows API) arayüz iş parçacığında yapılmaz.
- Exe boyutu ~28 MB hedefli; yeni Qt modülü ya da bağımlılık eklemeden önce boyutu ölç.

## Kod stili

Python ≥ 3.11, ruff (satır 100), tip ipuçları, `from __future__ import annotations`. Arayüz
metinleri, docstring'ler ve yorumlar **Türkçe**; sınıf, fonksiyon ve değişken adları İngilizce.
YAGNI: soyutlama yalnızca gerçek bir tekrarı kaldırıyorsa ya da test edilebilirliği artırıyorsa.

## Testler

- Qt offscreen. **Gerçek ağ, `%APPDATA%`, pano, ses cihazı ya da Spotify yok.** Veri klasörü
  `PERVAZ_DATA_DIR` ile geçici klasöre yönlendirilir (`conftest.py`).
- HTTP yanıtları `tests/fixtures/`'tan gelir.
- Testler `src` yapısını aynalar. Yeni kartın kendi testleri `tests/cards/<kart>/` altındadır.
- Test assertion'ını "geçsin diye" değiştirme; kodu düzelt.
- Zamanlama testlerinde sabit kısa `sleep` yerine `qtbot.waitUntil` kullan.

## Commit ve iş akışı

- Türkçe Conventional Commits, kapsam = katman ya da kart: `feat(spotify): ...`, `fix(core): ...`.
- Küçük, atomik, her commit yeşil. Taşımayı (`git mv`) ve davranış değişikliğini ayrı commit'lere koy.
- Özellik değişince ilgili `docs/cards/*.md` ve gerekirse README **aynı değişiklikte** güncellenir.
  Panel görünümü değişince `docs/images/panel.png` yenilenir.
- Kullanıcı açıkça istemedikçe commit atma ve push'lama.

## Yapma listesi

- Kartlar arası import.
- Mimari testi gevşetmek.
- Test assertion'ını "geçsin diye" değiştirmek.
- Sabit renk ya da ölçü yazmak.
- Sormadan yeni bağımlılık eklemek.
- Testte gerçek sistem kaynağı (ağ, AppData, pano, ses) kullanmak.
- Sormadan force push ya da git geçmişini yeniden yazmak.
- Belgede ya da kodda ürünün eski adlarına atıf yapmak.

## Finans istisnası

`ceyrek` gibi altın türü kimlikleri (`catalog.py`, sağlayıcı eşlemeleri, fixture'lar) bir
**özelliktir**; kullanıcı ayarlarında (`items`) kullanıldığı için yeniden adlandırılmaz.
