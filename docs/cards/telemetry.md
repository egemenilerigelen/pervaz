# Telemetri kartı

İşlemci, bellek, ekran kartı ve ağın canlı durumunu gösterir. Her satır tek satırdır: simge ve ad,
sönük kısa bir ayrıntı (ör. `4,68 GHz`), çizgi grafik ya da doluluk çubuğu ve renkli bir değer.
Satırın üzerine gelince tam bilgi ipucunda görünür (ör. `Ryzen 5 7500F · 4,68 GHz`). Veri panel açıkken saniyede bir okunur; panel kapanınca ya da
kart katlanınca okuma durur.

| Satır (`items` adı) | Ayrıntı (ipucunda tamamı) | Değer |
| --- | --- | --- |
| İşlemci (`cpu`) | model · saat hızı | kullanım % |
| Bellek (`ram`) | kullanılan / toplam | doluluk % |
| Ekran Kartı (`gpu`) | model · sıcaklık | kullanım % |
| Video Belleği (`vram`) | kullanılan / toplam | doluluk % |
| GPU Güç (`gpu_power`) | çekirdek hızı · fan | çekilen güç (W); çubuk güç sınırına oranı |
| Ağ (`net`) | ↓ indirme ↑ yükleme (bit/sn) | ping (ms); grafik pingin geçmişi |

- **Renkler:** her satırın kendi tonu vardır; doluluk %75'i geçince değer ve grafik turuncuya,
  %90'ı geçince kırmızıya döner. Ping 100 ms'den sonra turuncu, 250 ms'den sonra (ya da yanıt
  yoksa) kırmızıdır. Tonlar `theme/tokens.py` içinde, açık ve koyu tema için ayrı tanımlıdır.
- **Ekran kartı** yalnızca NVIDIA'dan (sürücüyle gelen NVML) okunur. NVIDIA kartı ya da sürücüsü
  yoksa üç GPU satırı hiç görünmez; kartın fan ya da güç bilgisi vermeyen bir modeli için yalnızca
  o veri atlanır.
- **Ping,** `1.1.1.1:443` adresine TCP bağlantısı kurma süresidir (ICMP yetki ister); sistem
  okumalarından ayrı çalışır, yanıt gelmezse diğer değerler gecikmez.
- **Satırları seçmek:** `cards` içindeki `telemetry` ayarında `items` ile (sıra korunur),
  ör. `{"items": ["cpu", "ram", "net"]}`. Kaldırılan disk satırları (`disk_io`, `drives`) eski
  ayar dosyalarında kalsa da yok sayılır.

## Ayarlar

| Alan | Tür | Varsayılan | Anlamı |
| --- | --- | --- | --- |
| `items` | metin listesi | `["cpu", "ram", "gpu", "vram", "gpu_power", "net"]` | Satırlar ve sırası. Tanınmayan adlar ve tekrarlar atılır; geçerli bir şey kalmazsa varsayılan liste kullanılır |

Okuma bir hata verirse kartta `Sistem bilgisi okunamıyor` yazar ve sonraki başarılı okumada kalkar.

## Geliştirici notları

```text
cards/telemetry/
├── __init__.py    # SPEC
├── card.py        # TelemetryCard: satır tanımları (ROWS), eşikler, yoklama
├── models.py      # GpuReading, Sample
├── sampler.py     # SystemSource (Protocol) + Sampler: psutil; hızlar iki okuma farkından
├── gpu.py         # NvidiaReader: NVML; yoksa kendini kapatır
├── ping.py        # tcp_ping: TCP bağlantı süresi
├── windows.py     # işlemci adı (kayıt defteri)
├── widgets.py     # Sparkline, Meter, MetricRow
├── formatting.py  # Türkçe birimler: "15,2 GB", "6 Kbps"
└── icon.py        # satır ve başlık simgeleri (QPainter)
```

**Veri akışı:** iki `Poller` (1 sn): biri `SystemSource.sample()` çağırır (CPU, bellek, ağ hızı,
GPU), ayrısı `ping` çağırır. Böylece yanıtsız bir sunucu sistem okumalarını geciktirmez.
Sonuçlar `Sample` ve ping geçmişi olarak satırlara dağıtılır.

**Yaşam döngüsü:** okuma yalnızca panel açıkken ve kart katlı değilken çalışır (`on_show`,
`on_hide`, `on_collapsed`). Okuma yeniden başlarken `Sampler.reset()` çağrılır ve geçmiş
temizlenir: uzun kapalılıktan sonra ilk okuma, saatlerin ortalamasını anlık hız diye
göstermesin. `shutdown` yoklamaları durdurur ve NVML'yi kapatır.

**Dış bağımlılıklar** kurucudan gelir: `sampler` (`SystemSource`) ve `ping` (bir fonksiyon).
`Sampler` kendi içinde `psutil`, GPU okuyucusu, saat ve işlemci adı okuyucusunu da
dışarıdan alabilir; testler gerçek sisteme, ağa ve ekran kartına dokunmaz.
