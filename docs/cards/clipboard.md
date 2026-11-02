# Pano kartı

Son 5 kopyalanan metni, en yenisi üstte, listeler. Satırın herhangi bir yerine tıklamak
(başındaki kopyalama simgesi dahil) metni panoya geri koyar (bir an onay işareti görünür) ve
satırı en üste taşır; aynı metin tekrar kopyalanırsa ikinci satır açılmaz, var olan satır
yukarı çıkar. Fare satırın üzerindeyken sağda sönük bir çarpı belirir; çarpının üstüne gelince
aydınlanır, tıklayınca satır geçmişten silinir (panodaki metne dokunmaz).

- **Panel kapalıyken de kopyalananlar yakalanır:** kart panoyu olay olarak dinler, yoklama
  yoktur, boşta işlemci kullanmaz. Uygulama açılırken panoda duran metin de listelenir.
- **Yalnızca metin:** resimler ve Explorer'da kopyalanan dosyalar listeye girmez; tarayıcıdan
  kopyalanan bağlantı metindir, girer.
- **Parolalar atlanır:** parola yöneticilerinin panoya koyarken ekledikleri "geçmişe alma"
  işaretini taşıyan içerik listeye hiç girmez.
- **Satırlar tek satıra indirilir:** çok satırlı metin boşluklarla birleşik gösterilir,
  sığmayan kısım `…` ile kesilir (üzerine gelince tamamı görünür). Kopyalanan metin değişmez,
  satır sonlarıyla olduğu gibi geri gelir.
- **Geçmiş diske yazılmaz:** yalnızca bellektedir; uygulama kapanınca silinir. Pano parola ya da
  gizli bilgi taşıyabileceği için bilerek böyle.

## Ayarlar

Kartın `config` alanı yoktur. Satır sayısı (5) ve önizleme uzunluğu (200 karakter) kodda sabittir
(`history.py`).

## Geliştirici notları

```text
cards/clipboard/
├── __init__.py   # SPEC
├── card.py       # ClipboardCard, ClipRow: arayüz ve pano olayı
├── history.py    # ClipboardHistory (Qt'siz): sıra, tekrar ve silme kuralları; preview()
└── icon.py       # başlık simgesi (QPainter)
```

**Veri akışı:** `QClipboard.dataChanged` -> `ClipboardCard._capture` -> `_read` (yalnızca
`text/plain` biçimi; parola yöneticisi işaretini taşıyan içerik atlanır) ->
`ClipboardHistory.add` -> satırlar.

**Neden `hasText()` değil `hasFormat("text/plain")`:** Qt, Explorer'da kopyalanan dosya
listelerini de metin sayar; dosya yolları geçmişe girmesin.

**Önbellek yoktur.** Bu bilinçli bir karardır ([ADR 0004](../decisions/0004-pano-gecmisi-diske-yazilmaz.md)).

**Yaşam döngüsü:** pano dinleyicisi kart kurulurken bağlanır ve `shutdown`'da kopar; `on_hide`
yalnızca onay işareti zamanlayıcısını durdurur.

**Dış bağımlılık:** `clipboard` kurucudan gelir (`QClipboard`); testler kendi panolarını verir
ve gerçek panoya dokunmaz.
