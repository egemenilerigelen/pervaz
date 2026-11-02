# Ayarlar

Tek dosya: `%APPDATA%\Pervaz\settings.json`. Uygulama bu dosyayı kendisi de yazar (sabitleme,
katlanma ve kart ayarları değişince ve çıkışta), bu yüzden **elle düzenlemeyi uygulama
kapalıyken yap**; açıkken yaptığın değişiklik çıkışta üzerine yazılır. Dosya yoksa ya da
bozuksa varsayılanlarla başlanır.

## Bozuk değerler

Bozuk ya da tanınmayan her değer **sessizce varsayılana** döner; elle düzenlenen bir dosya
yüzünden uygulama açılmaz hale gelmez:

- Tür yanlışsa (sayı yerine metin gibi) ya da sayı aralık dışındaysa o alan varsayılan olur,
  diğer alanlar etkilenmez.
- Tam sayı alanına ondalıklı sayı verilirse tam sayıya yuvarlanmadan kesilir (`200.7` -> `200`).
  `true`/`false` sayı olarak kabul edilmez.
- Dosyanın en üst düzeyi bir nesne değilse tüm ayarlar varsayılan olur.
- Dosyada bulunmayan ya da tanınmayan üst düzey alanlar yok sayılır ve bir sonraki kayıtta
  silinir. `cards` içindeki `config` anahtarları ise olduğu gibi korunur.

## Alanlar

### Açılış ve kapanış

| Alan | Tür | Aralık | Varsayılan | Anlamı |
| --- | --- | --- | --- | --- |
| `open_mode` | metin | `hover`, `click` | `hover` | `hover`: tutamacın üzerine gelince açılır; `click`: yalnızca tıklayınca. Tıklama her modda açar |
| `hover_delay_ms` | tam sayı | 0–3000 | `200` | `hover` modunda açılmadan önce beklenen süre |
| `close_on_outside_click` | `true`/`false` | | `true` | Panelin dışına tıklayınca kapanır |
| `leave_close_seconds` | sayı | 0–60 | `3.0` | Fare panelden ayrıldıktan bu kadar saniye sonra kapanır; `0` = kapalı |
| `pinned` | `true`/`false` | | `false` | Sabitlenmiş panel dışarı tıklama ve fare ayrılmasıyla kapanmaz; durum hatırlanır |
| `animations` | `true`/`false` | | `true` | Panelin kara delik efekti ve kartların katlanması animasyonlu olur; `false` iken panel anında açılıp kapanır |
| `animation_ms` | tam sayı | 50–1000 | `220` | Animasyonların temel süresi. Kara delik efekti okunabilsin diye bu değerin iki katı sürer (varsayılan 440 ms) |
| `panel_width` | tam sayı | 240–640 | `280` | Panelin genişliği (mantıksal px). Yazı ölçeği 1'den büyükse panel orantılı genişler |

### Kısayol ve ekran

| Alan | Tür | Aralık | Varsayılan | Anlamı |
| --- | --- | --- | --- | --- |
| `hotkey` | metin | bkz. aşağısı | `win+alt+p` | Paneli açıp kapatan genel kısayol; boş = kısayol yok |
| `hotkey_screen` | metin | `cursor`, `primary` | `cursor` | Kısayolla açılınca panelin hangi ekranda görüneceği: fare imlecinin ekranı ya da ana ekran |
| `trigger_screen` | metin | `primary` ya da ekran adı | `primary` | Tutamacın göründüğü ekran (ör. `\\.\DISPLAY2`). Bilinmeyen ad ana ekrana düşer |

**Kısayol biçimi:** `değiştirici+...+tuş`, küçük harfle. En az bir değiştirici gerekir.
Değiştiriciler: `alt`, `ctrl` (ya da `control`), `shift`, `win` (ya da `meta`, `super`).
Tuş: tek bir harf ya da rakam, `f1`–`f24` ya da `space`, `enter`, `tab`, `esc`, `backspace`,
`home`, `end`, `pageup`, `pagedown`, `insert`, `delete`, `left`, `up`, `right`, `down`.
Geçersiz bir kısayol loga uyarı olarak yazılır ve kaydedilmez. `Win+Alt+W` gibi bazı kısayollar
başka uygulamalarca tutulmuş olabilir; kayıt başarısız olursa tepsiden uyarı gelir ve paneli
tutamaçtan ya da tepsi simgesinden açabilirsin.

### Tutamaç

| Alan | Tür | Aralık | Varsayılan | Anlamı |
| --- | --- | --- | --- | --- |
| `trigger_kind` | metin | `handle` | `handle` | Tetikleyici türü. Şimdilik yalnızca tutamaç vardır; tanınmayan değer tutamaç olur |
| `handle_thickness` | tam sayı | 2–24 | `6` | Tutamacın ekranın içine girdiği derinlik (px) |
| `handle_length` | tam sayı | 24–600 | `96` | Tutamacın uzunluğu (px); uçları kenarda sönerek biter |
| `handle_position` | sayı | 0–1 | `0.5` | Tutamacın dikey konumu: 0 üst, 1 alt |

Tutamacın koyu kahve tonları `theme/tokens.py` içindeki `HOLE`'dan gelir; masaüstünün üstünde
durduğu için tema ve `accent` ayarına göre değişmez.

### Görünüm

| Alan | Tür | Aralık | Varsayılan | Anlamı |
| --- | --- | --- | --- | --- |
| `theme` | metin | `dark`, `light` | `dark` | Renk teması |
| `accent` | metin ya da `null` | `#rrggbb` | `null` | Vurgu rengi; `null` ya da geçersiz değer temanın kendi vurgusunu kullanır |
| `density` | metin | `compact`, `normal`, `relaxed` | `normal` | Boşluk yoğunluğu (çarpan 0,86 / 1 / 1,16) |
| `font_scale` | sayı | 0.8–1.6 | `1.0` | Yazı ölçeği |
| `glass_opacity` | sayı | 0.3–1.0 | `0.92` | Panel zemininin opaklığı; düşürdükçe arkadaki pencereler daha çok görünür |

Renkler ve boyutlar `theme/tokens.py` içinde tek yerdedir; kartlarda sabit renk yoktur.

### Kartlar

`cards` bir liste olarak her kart için bir girdi tutar:

```json
"cards": [
  { "id": "weather", "enabled": true, "collapsed": false, "config": { "city": "Ankara" } },
  { "id": "finance", "enabled": true, "collapsed": false, "config": { "items": ["usd", "eur", "ceyrek"] } }
]
```

| Alan | Tür | Varsayılan | Anlamı |
| --- | --- | --- | --- |
| `id` | metin | zorunlu | Kartın kimliği (`weather`, `finance`, `telemetry`, `spotify`, `clipboard`, `github`) |
| `enabled` | `true`/`false` | `true` | `false` ise kart hiç kurulmaz |
| `collapsed` | `true`/`false` | `false` | Katlı mı; kart başlığına tıklayınca değişir ve hatırlanır |
| `config` | nesne | `{}` | Karta özel ayarlar |

- **Sıra:** panelde kartlar listedeki sırayla görünür. Listeyi yeniden sıralamak panelin sırasını
  değiştirir.
- **Eksik ve fazla girdiler:** listede olmayan yeni bir kart sona eklenir; artık var olmayan bir
  kimlik atılır. Aynı kimlik iki kez varsa ilki geçerlidir. `id`'si metin olmayan girdi yok sayılır.
- **Kart ayarları:** her kartın `config` alanlarının tam listesi kendi sayfasındadır:
  [hava durumu](cards/weather.md#ayarlar), [finans](cards/finance.md#ayarlar),
  [telemetri](cards/telemetry.md#ayarlar), [GitHub](cards/github.md#ayarlar). Spotify ve pano
  kartlarının `config` alanı yoktur.

## Veri klasörü

Ayarlar ve önbellekler `%APPDATA%\Pervaz\` altında tutulur (içeriği için bkz.
[README](../README.md#kullanıcı-verisi-ve-gizlilik)). `PERVAZ_DATA_DIR` ortam değişkeni
verilirse bu klasör yerine o kullanılır; testler bunu geçici klasöre yönlendirir.
