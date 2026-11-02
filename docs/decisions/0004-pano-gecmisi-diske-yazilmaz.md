# 0004 — Pano geçmişi diske yazılmaz

Durum: kabul edildi (2026-11-02)

## Bağlam

Pano kartı son kopyalanan metinleri listeler. Pano parola, anahtar, kişisel mesaj gibi gizli
şeyler taşıyabilir. Diğer kartların aksine bu verinin uygulama kapandıktan sonra bile diskte
durması bir risktir ve kullanıcı bunu beklemez.

## Karar

- Geçmiş yalnızca bellekte tutulur (`ClipboardHistory`); uygulama kapanınca silinir. Karta
  önbellek dosyası eklenmez.
- Yalnızca metin alınır (`text/plain`). Resimler ve Explorer'da kopyalanan dosyalar (Qt bunları da
  metin sayar) geçmişe girmez.
- Parola yöneticilerinin panoya koyarken eklediği "geçmişe alma" işaretini
  (`ExcludeClipboardContentFromMonitorProcessing`) taşıyan içerik hiç alınmaz.
- Kart panoyu olay olarak dinler (`dataChanged`); yoklama yoktur, panel kapalıyken de yakalar.
- Satırlar tek satıra indirilir ve en fazla 5 madde tutulur.

## Sonuç

- Uygulama yeniden açılınca yalnızca o anda panoda duran metin listelenir; önceki geçmiş yoktur.
  Bu bilinçli bir bedeldir.
- Pano kartına diske yazan bir özellik (kalıcı geçmiş, sabitlenen maddeler) eklenecekse önce bu
  karar yeniden değerlendirilir; "yazmalar atomiktir" kuralı ve gizlilik notu birlikte
  güncellenir.
