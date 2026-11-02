# GitHub kartı

GitHub katkı tablosunu gösterir: panele sığan en yeni haftalar, pazartesi üstte olacak şekilde
kare kare; yeni hafta sağ kenardadır. Karenin üzerine gelince katkı sayısı ve tarih ipucunda
görünür. Altında son bir yılın toplam katkısı (GitHub profilindeki sayıyla aynıdır) ve bugünde
biten seri yazar; bugün henüz katkı yoksa seri bozulmuş sayılmaz, dünden geriye sayılır.

- **Hesap ya da token gerekmez:** veri, kullanıcının herkese açık profil sayfasındaki katkı
  parçasından okunur (`github.com/users/<ad>/contributions`). Özel depo katkıları, profilinde
  "Private contributions" açık değilse görünmez.
- **Kullanıcı adı:** `cards` içindeki `github` ayarında `username` ile verilir (varsayılan
  `egemenilerigelen`), ör. `{"username": "octocat"}`. Yenileme aralığı `refresh_minutes` ile
  (5–720, varsayılan 30) değişir. Katkılar yavaş değiştiği için panel kapalıyken de seyrek yenilenir.
- **Renkler:** karelerin tonu GitHub'ın kendi 0–4 yoğunluk basamağını izler ve temanın vurgu
  rengini kullanır (`accent` ile değişir); katkısız günler soluk bir iz rengindedir.
- **Resmi API değil:** GitHub sayfa yapısını değiştirirse okuma başarısız olur; kart son tabloyu
  başlıkta "eski veri" notuyla göstermeye devam eder, hiç veri yoksa kartta hata yazar.

## Ayarlar

`settings.json` içinde `cards` listesindeki `github` girdisinin `config` alanı:

| Alan | Tür | Aralık | Varsayılan | Anlamı |
| --- | --- | --- | --- | --- |
| `username` | metin | GitHub kullanıcı adı kuralları (harf, rakam, tire; en çok 39 karakter) | `egemenilerigelen` | Tablosu gösterilecek hesap. Geçersiz ad okuma sırasında hata verir |
| `refresh_minutes` | tam sayı | 5–720 | `30` | Yenileme aralığı. Aralık dışı değer varsayılana döner |

Kullanıcı adı değişince önbellekteki eski tablo atılır. Başlık bilgisi `@kullanıcı` yazar;
güncelleme başarısız olursa `@kullanıcı · eski veri 14:05` olur. Hiç veri yoksa kartta
`GitHub'a ulaşılamıyor` yazar.

## Geliştirici notları

```text
cards/github/
├── __init__.py   # SPEC
├── card.py       # GithubCard: özet satırı, yoklama bağlantısı
├── models.py     # ContributionDay, Contributions (toplam, seri)
├── api.py        # profil sayfası ayrıştırıcı; ContributionSource + GithubProfileSource
├── cache.py      # ContributionCache (JsonCache) + ContributionStore (Protocol): github.json
├── widgets.py    # ContributionGraph: haftalar sütun, günler satır
└── icon.py       # başlık simgesi (QPainter)
```

**Veri akışı:** `Poller` (30 dk) -> `GithubCard._fetch` -> `ContributionSource.fetch` ->
`Contributions` -> önbelleğe yazılır -> `succeeded` -> `ContributionGraph` + özet.

**Ayrıştırma:** her gün için bir `<td data-date data-level>` hücresi ve hücreye `for` ile bağlı
bir `<tool-tip>` ("3 contributions on May 5th.") okunur. İpucu metni `Accept-Language`'e göre
yerelleştirildiği için istek `en-US` ile yapılır. Biçim tanınmazsa `ProviderError` fırlatılır.

**Yaşam döngüsü:** yoklama kart kurulurken başlar (panel kapalıyken de); `on_show` veri bayatsa
tazeler; `shutdown` durdurur.

**Dış bağımlılıklar** kurucudan gelir: `cache` ve `source`. Ayrıştırma testleri
`tests/fixtures/github_contributions.html` dosyasından beslenir; gerçek ağ kullanılmaz.
