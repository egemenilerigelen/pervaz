# 0003 — Hesap ya da anahtar istemeyen veri kaynakları

Durum: kabul edildi (2026-11-02)

## Bağlam

Panel bir masaüstü yardımcısıdır; kullanıcıdan hesap bağlamasını, anahtar almasını ya da
kimlik bilgisi saklamasını istemek hem kurulumu zorlaştırır hem de saklanan sırların güvenliği
sorumluluğunu getirir. Bir de hesaplı API'lerin kotaları ve ücretli kademeleri vardır.

## Karar

Hiçbir kart hesap, token ya da API anahtarı istemez. Kaynaklar şöyle seçildi:

| Kart | Kaynak | Not |
| --- | --- | --- |
| Spotify | Windows'un medya oturumu (GSMTC) ve ses katmanı (WASAPI/pycaw) | Spotify Web API'si değil. OAuth, Premium şartı ve ağ gecikmesi yok; yalnızca masaüstü uygulamasını izler |
| GitHub | herkese açık profilin katkı parçası (`github.com/users/<ad>/contributions`) | Token yok; resmi API değil, biçim değişirse okuma başarısız olur |
| Finans | Truncgil, yedek olarak Altınkaynak | İki ücretsiz, anahtarsız kaynak; biri düşünce diğerine geçilir (`FallbackFetcher`) |
| Hava durumu | Open-Meteo | Anahtarsız, ücretsiz |
| Telemetri | psutil, NVML (sürücüyle gelir), TCP bağlantı süresi | Ping için ICMP yönetici yetkisi ister; TCP el sıkışması aynı bilgiyi yetkisiz verir |

Hesaplı bir kaynak gerektiren bir özellik eklenmez. Gerekirse önce bu karar yeniden ele alınır.

## Sonuç

- Resmi olmayan kaynaklar (GitHub sayfa yapısı, Truncgil, Altınkaynak) beklenmedik anda
  değişebilir. Bunun maliyeti kartların son veriyi önbellekten göstermesi (`JsonCache`), başlıkta
  "eski veri" notu ve anlaşılır hata mesajıdır; kart çökmez.
- Spotify kartı yalnızca masaüstü Spotify'ı görür; tarayıcı sekmesi ya da telefonla eş zamanlı
  çalma bu yolla mümkün değildir. Bu gerekirse, hesaplı bir API kullanımı ayrı bir karar olarak
  ele alınır.
- Ayar dosyasında ve diskte sır tutulmaz.
