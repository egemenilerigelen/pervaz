# Geliştirme

## Kurulum

Windows 10/11 ve Python 3.11 ya da üstü gerekir (Windows'a özgü kod vardır, başka sistemlerde
çalışmaz).

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

Uygulamayı çalıştırmak için üç yol vardır, üçü de aynı şeyi yapar:

```bash
pervaz
python -m pervaz
python packaging/launcher.py
```

Geliştirme bağımlılıkları: `pytest`, `pytest-qt`, `ruff`, `pyinstaller` ve yalnızca
`tools/make_icon.py` için `pillow`. Yeni bağımlılık (çalışma zamanı ya da geliştirme) eklemeden
önce gerekçesini düşün; exe boyutunu ve kurulumu doğrudan etkiler.

## Komutlar

```bash
python -m pytest -q                                        # testler (Qt testleri ekransız çalışır)
python -m ruff check .                                     # lint
python -m ruff format .                                    # biçimlendirme
python -m PyInstaller --noconfirm packaging/pervaz.spec    # dist\Pervaz.exe
python tools/make_icon.py                                  # src/pervaz/assets/icon.ico
```

Bir commit atmadan önce `ruff check .`, `ruff format --check .` ve `pytest -q` temiz olmalıdır.
CI aynı üç komutu çalıştırır.

## Test stratejisi

- **Qt ekransız çalışır:** `tests/conftest.py` `QT_QPA_PLATFORM=offscreen` ayarlar. Pencere,
  tepsi ve zamanlayıcı testleri `pytest-qt` (`qtbot`) ile yazılır.
- **Gerçek sisteme dokunulmaz:** gerçek `%APPDATA%`, ağ, pano, ses cihazı ve Spotify
  oturumu testlerde kullanılmaz. `conftest.py`'deki otomatik fixture `PERVAZ_DATA_DIR`'i her
  test için geçici bir klasöre yönlendirir; sözleşme testi ayrıca ağ bağlantısını engeller.
- **Bağımlılıklar kurucudan verilir:** fare (`Pointer`), saat, önbellek, HTTP kaynağı, sistem
  okuyucusu, pano, Windows arka ucu gibi dış dünya kurucudan alınır; testler sahte nesne verir.
  Örnekler: `AppController(specs=..., hotkeys=..., store=..., pointer=...)`,
  `PanelAutoClose(..., clock=...)`, `SpotifyCard(context, backend, clock, cache)`.
- **Hazır yanıtlar** `tests/fixtures/` altındadır (`truncgil_v3.json`, `altinkaynak.json`,
  `open_meteo.json`, `github_contributions.html`). Ayrıştırıcılar bu dosyalarla sınanır;
  `conftest.load_fixture(ad)` JSON'u okur.
- **Testler `src` yapısını aynalar:** `tests/app`, `tests/core/...`, `tests/cards/<kart>`,
  `tests/infra`, `tests/theme`.
- **Sözleşme testi** (`tests/core/cards/test_card_contract.py`) `CARDS` içindeki her kartı kurar,
  gösterir, gizler, yeniden gösterir ve kapatır; gizlendikten sonra zamanlayıcı kalmadığını,
  kapanınca zamanlayıcı ve iş parçacığı kalmadığını denetler. Yeni kart buraya kendiliğinden
  girer; gerçek sistem kaynağı kullanan bir kart için `BUILDERS` sözlüğüne sahte
  bağımlılıklarıyla bir satır eklenir.
- **Mimari testi** (`tests/test_architecture.py`) katman kurallarını, döngüsel importları ve kart
  kaydını denetler (bkz. [mimari](architecture.md#katmanlar)). Gevşetilmez.
- **Bekleme:** sabit `sleep` yerine `qtbot.waitUntil(koşul)` kullan. Düzenin oturmasını
  bekleyen testlerde olay döngüsüne yeterli süre tanı (`qtbot.wait(30)`); 1 ms gibi kısa
  beklemeler aralıklı düşen testlere yol açar.

Tek bir testi çalıştırmak için: `python -m pytest -q tests/cards/spotify/test_spotify_card.py -k volume`.

## Lint ve biçim

`ruff`, `pyproject.toml` içinde yapılandırılmıştır: satır uzunluğu 100, hedef Python 3.11,
kurallar `E, F, W, I, UP, B, SIM, RUF`. Arayüz metinleri Türkçe olduğu için `RUF001`–`RUF003`
(belirsiz Unicode karakter) kapalıdır.

Satır sonları depoda ve çalışma klasöründe LF'dir (`.gitattributes`); `ruff format` ile CI
arasında satır sonu farkı çıkmasın diye.

## Exe ve boyut bütçesi

```bash
python -m PyInstaller --noconfirm packaging/pervaz.spec
```

Çıktı `dist\Pervaz.exe`'dir (tek dosya, pencereli). `packaging/launcher.py` giriş betiğidir ve
`src/` yolunu ekler; spec içindeki yollar `SPECPATH`'e göredir, yani komut proje kökünden
çalıştırılır ama başka bir klasörden de çalışır.

Exe yaklaşık **28 MB**'tır. PyInstaller'ın PySide6 kancası yalnızca import edilen modülleri
toplar; spec'teki iki liste boyutu bu düzeyde tutar:

- `EXCLUDES`: widget uygulamasının kullanmadığı Qt modülleri (WebEngine, QML/Quick, Pdf,
  Multimedia, Charts, Network, OpenGL, Sql, Svg...) ve Python kütüphaneleri (`tkinter`,
  `unittest`...).
- `DROP_PATTERNS`: Qt eklentilerinin dolaylı çektiği ama kullanılmayan kütüphaneler. Tek başına
  `opengl32sw.dll` (yazılımsal OpenGL, raster çizim yapan bir QWidget uygulamasına gerekmez)
  yaklaşık 20 MB tutar.

Yeni bir Qt modülü kullanmadan önce boyuta etkisini ölç: exe'yi derleyip boyutu karşılaştır
(±%5 içinde kalmalı). Bir modülü `EXCLUDES`'tan çıkarman gerekiyorsa nedenini commit mesajına
yaz.

## CI

`.github/workflows/ci.yml`, `main`'e her push'ta ve her pull request'te çalışır:

1. **test** (`windows-latest`, Python 3.11 ve 3.12): bağımlılıkları kurar, `ruff check`,
   `ruff format --check` ve `pytest` çalıştırır (Qt ekransız).
2. **build** (test geçince, Python 3.12): exe'yi derler ve `Pervaz-exe` adıyla 14 gün saklanan
   bir artefakt olarak yükler. Hazır exe'yi ilgili çalıştırmanın sayfasından indirebilirsin.

## Sürümleme

Sürüm tek yerde, `src/pervaz/__init__.py` içindeki `__version__`'dadır. `pyproject.toml` onu
`[tool.setuptools.dynamic]` ile okur; uygulama logda, `QApplication` sürümünde ve HTTP
`User-Agent`'ında aynı değeri kullanır. Kullanıcıya görünen bir değişiklik ya da kimlik/ayar
uyumsuzluğu olduğunda sürümü yükselt.

## Commit kuralları

- **Türkçe Conventional Commits:** `feat`, `fix`, `refactor`, `docs`, `test`, `build`, `ci`,
  `chore`. Kapsam katman ya da kart adıdır: `feat(spotify): ...`, `fix(core): ...`,
  `refactor(infra): ...`. Kırıcı değişiklik `!` ile işaretlenir (`refactor!: ...`). Mesaj kısa
  ve "ne değişti"yi anlatır.
- **Küçük ve atomik:** her commit tek bir konudur, tek başına derlenir ve testleri geçer.
- **Taşıma ile değişiklik ayrı commit:** dosyayı `git mv` ile taşı (geçmiş izlenebilsin), içeriğini
  sonraki commit'te değiştir. Yalnızca büyük/küçük harfi değişen adlar iki adımda yapılır.
- **Davranış değişikliğini taşımayla karıştırma.**
- **Belgeyi aynı değişiklikte güncelle:** bir kartın özelliği değişince ilgili
  `docs/cards/*.md` ve gerekirse README aynı commit'te güncellenir. Panelin görünümü değişince
  `docs/images/panel.png` yenilenir.

## Simge

`src/pervaz/assets/icon.ico` elle çizilmiş bir dosya değil, `tools/make_icon.py`'nin çıktısıdır:
koyu, yuvarlatılmış kare zeminde sağ kenara yaslı vurgu şeridi ve solunda üst üste kartlar.
Renkleri koyu temanın belirteçlerinden gelir; 16 ve 24 px için ayrı, sadeleştirilmiş bir yerleşim
kullanır. Değiştirmek için betiği düzenleyip çalıştır; betik ve çıktı aynı commit'te olsun.

## Sorun ayıklama

- Log: `%APPDATA%\Pervaz\logs\app.log` (dönen dosya, 3 yedek).
- Gerçek verini bozmadan denemek için `PERVAZ_DATA_DIR` ile başka bir klasör ver:
  `$env:PERVAZ_DATA_DIR = "C:\gecici\pervaz"; pervaz`.
- Aynı anda tek kopya çalışır (`instance.lock`); ikinci kopya "Uygulama zaten çalışıyor" der.
  Çöken bir kopyanın kilidi Qt tarafından kendiliğinden temizlenir.
