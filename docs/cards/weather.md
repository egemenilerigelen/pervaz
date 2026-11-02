# Hava durumu kartı

Anlık sıcaklığı, hissedilen sıcaklığı, nem, rüzgâr ve yağış kutularını ve üç günlük tahmini
gösterir. Kartın arka planı havaya göre hafifçe renklenir (açık hava sıcak, yağmur soğuk tonlu,
yağmurda çizgiler, karda noktalar); renk katmanları metni bozmayacak kadar düşük saydamlıktadır.

Veri [Open-Meteo](https://open-meteo.com)'dan gelir: hesap ya da anahtar gerekmez.

## Kullanım

- **Konum seçmek:** başlık satırındaki konum adına tıkla; açılan menüde Aydın, Urla ve İzmir
  vardır. Seçim hatırlanır.
- **Başlık bilgisi:** veri gelmeden önce seçili konum, geldikten sonra konumun adı yazar.
  Güncelleme başarısız olursa eski veri gösterilmeye devam eder ve başlığa `· eski veri 14:05`
  (son başarılı okumanın saati) eklenir. Hiç veri yoksa kartta `Hava durumuna ulaşılamıyor`
  yazar.
- **Yağış kutusu** bugünün toplam yağışını gösterir (mm).
- Hava durumu panel kapalıyken de seyrek (varsayılan 20 dakikada bir) yenilenir; panel
  açıldığında veri bayatsa hemen tazelenir.

## Ayarlar

`settings.json` içinde `cards` listesindeki `weather` girdisinin `config` alanı:

| Alan | Tür | Aralık | Varsayılan | Anlamı |
| --- | --- | --- | --- | --- |
| `city` | metin | menüdeki üç ad ya da herhangi bir yer adı | `Urla` | Konum. Menüdeki adlarda koordinatlar sabittir; başka bir ad Open-Meteo'dan aranır (ör. `{"city": "Ankara"}`) |
| `refresh_minutes` | tam sayı | 5–180 | `20` | Yenileme aralığı. Aralık dışı ya da sayı olmayan değer varsayılana döner |

Konum değişince önbellekteki eski şehrin verisi atılır.

## Geliştirici notları

```text
cards/weather/
├── __init__.py   # SPEC
├── card.py       # WeatherCard: arayüz, yoklama bağlantısı, konum menüsü
├── models.py     # Place, DayForecast, Weather (donmuş dataclass, to_dict/from_dict)
├── api.py        # Open-Meteo: konum arama, tahmin, WMO kodu -> metin; WeatherSource + OpenMeteoSource
├── cache.py      # WeatherCache (JsonCache) + WeatherStore (Protocol): weather.json
├── places.py     # menüdeki konumlar ve koordinatları, DEFAULT_CITY
├── icon.py       # WeatherIcon: QPainter ile çizilen hava simgeleri
└── backdrop.py   # WeatherBackdrop: havaya göre renk lekesi ve desen (bir kez çizilip önbelleğe alınır)
```

**Veri akışı:** `Poller` (arka plan iş parçacığı) -> `WeatherCard._fetch` -> `WeatherSource`
(`find_place` + `fetch_weather`) -> `Weather` -> önbelleğe yazılır -> `succeeded` sinyali ->
`_on_success` -> arayüz. Önbellek, kart kurulurken okunur ve ilk açılışta veri hemen görünür;
`Place.query` ayardaki şehirle uyuşmazsa önbellek geçersiz sayılır.

**Dış bağımlılıklar** kurucudan gelir: `cache` (`WeatherStore`) ve `source` (`WeatherSource`).
Testler sahte nesneler verir; gerçek ağ kullanılmaz. Ayrıştırma testleri `tests/fixtures/open_meteo.json`
dosyasından beslenir.

**Yaşam döngüsü:** yoklama kart kurulurken başlar (panel kapalıyken de); `on_show` yalnızca veri
bayatsa tazeler; `shutdown` yoklamayı durdurur.
