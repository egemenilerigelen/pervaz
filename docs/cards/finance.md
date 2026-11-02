# Finans kartı

Dolar, euro, sterlin, gram altın ve çeyrek altın satış fiyatlarını (ve
günlük değişimi) yalnızca yazı olarak gösterir. Veri, panel açıkken dakikada bir
Truncgil'den çekilir; ulaşılamazsa Altınkaynak denenir. Başlıktaki bilgi normalde boştur;
yalnızca yedek kaynak devredeyse kaynağın adı (fiyatlar kaynağa göre değişir), veri 15
dakikadan eskiyse (hafta sonu, kapalı piyasa) saati, güncelleme başarısızsa "eski veri"
notu yazar.

Hesap ya da anahtar gerekmez.

## Ayarlar

Gösterilecek satırlar `cards` içindeki `finance` ayarında `items` ile seçilir (sıra
korunur): `usd`, `eur`, `gbp`, `chf`, `gram`, `gram_has`, `ceyrek`, `yarim`, `tam`,
`cumhuriyet`, `ata`, `resat`, `hamit`, `ikibucuk`, `gremse`, `besli`, `ayar14`, `ayar18`,
`bilezik22`, `ons`, `gumus`. Ons ve gümüş varsayılanda gösterilmez, `items` ile eklenir.
Altınkaynak'ta karşılığı olmayan satırlar (ör. `cumhuriyet`) o kaynağa düşülünce `—`
görünür.

| Alan | Tür | Varsayılan | Anlamı |
| --- | --- | --- | --- |
| `items` | metin listesi | `["usd", "eur", "gbp", "gram", "ceyrek"]` | Satırlar ve sırası. Tanınmayan kimlikler ve tekrarlar atılır; geçerli hiçbir şey kalmazsa varsayılan liste kullanılır |

Örnek: `{"items": ["usd", "eur", "ceyrek", "gumus"]}`.

> `ceyrek` gibi altın türü kimlikleri birer özelliktir (çeyrek altın satırı); ayar dosyalarında
> kullanıldıkları için yeniden adlandırılmazlar.

## Görünüm

- Fiyatlar Türkçe yazılır (`10.632 ₺`; bin ve üstünde kuruş yazılmaz, ons altın `$` ile).
- Günlük değişim yeşil (artış), kırmızı (düşüş) ya da soluk (yok/bilinmiyor) renktedir.
- Satır simgeleri döviz için para işareti, madenler için çizimdir: külçe (gram), sikke, yüzük,
  ağırlık (ons), elmas (gümüş).
- Servis kaynaklara ulaşamıyor ve hiç veri yoksa kartta `Piyasa verilerine ulaşılamıyor` yazar.

## Geliştirici notları

```text
cards/finance/
├── __init__.py     # SPEC
├── card.py         # FinanceCard: satırlar, başlık bilgisi, servis bağlantısı
├── catalog.py      # Instrument kataloğu (21 tür), DEFAULT_ITEMS
├── models.py       # Quote, Snapshot, FeedStatus, FeedState
├── formatting.py   # Türkçe sayı ayrıştırma ve biçimlendirme (parse_tr_number, format_price...)
├── service.py      # PriceService: Poller üstünde durum makinesi (LOADING/LIVE/STALE/OFFLINE)
├── cache.py        # SnapshotCache (JsonCache) + SnapshotStore (Protocol): finance.json
├── icon.py         # SymbolBadge: satır simgeleri
└── providers/
    ├── base.py         # PriceProvider (Protocol)
    ├── truncgil.py     # Truncgil v3 today.json
    ├── altinkaynak.py  # Altınkaynak altın ve döviz listeleri
    └── __init__.py     # FallbackFetcher, build_fetcher, create_providers, DEFAULT_PROVIDER
```

**Veri akışı:** `Poller` (60 sn) -> `FallbackFetcher` (kaynakları sırayla dener) -> `Snapshot` ->
`PriceService.snapshot_changed` -> `FinanceCard._on_snapshot` -> satırlar ve önbellek. Durum
(`FeedState`) ayrı bir sinyalle gelir ve başlık bilgisini/hatayı belirler.

**Kaynak eklemek:** `providers/` altına `PriceProvider` (`id`, `name`, `fetch() -> Snapshot`)
uygulayan bir sınıf yazıp `create_providers()` içine eklemek yeterlidir; katalogdaki kimliklere
eşleme sağlayıcının kendi dosyasındadır.

**Bayatlık:** son başarılı veri 3 yenileme aralığından eskiyse servis 15 sn'lik ayrı bir
zamanlayıcıyla bunu fark edip yeniden ister (uykudan dönüş gibi durumlar).

**Yaşam döngüsü:** `on_show` servisi başlatır ve hemen tazeler; `on_hide` ve `shutdown` durdurur.
Panel kapalıyken ağ isteği yapılmaz.

Testler `tests/fixtures/truncgil_v3.json` ve `altinkaynak.json` dosyalarını kullanır; gerçek ağ
kullanılmaz.
