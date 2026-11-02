# 0005 — Kimlik: Pervaz

Durum: kabul edildi (2026-11-02)

## Bağlam

Ürünün kapsamı genişledi. Başlangıçta tek bir bilgiyi gösteren küçük bir pencereydi; bugün
ekranın kenarından açılan, hava, piyasa, sistem, müzik, pano ve GitHub kartları taşıyan
modüler bir paneldir ve yeni kartlar eklenecektir. Ad, paket, exe, simge ve veri klasörü artık
bu kapsamı anlatmıyordu.

## Karar

Ürünün adı **Pervaz**: pencerenin kenarı. Panel ekranın kenarından açıldığı için. Kısa, Türkçe ve
ayırt edicidir.

| Alan | Değer |
| --- | --- |
| Görünen ad ve teknik ad | `Pervaz` |
| Python paketi, dağıtım adı, komut | `pervaz` |
| Exe | `Pervaz.exe` (`packaging/pervaz.spec`) |
| Kullanıcı verisi | `%APPDATA%\Pervaz\` |
| Veri klasörü ortam değişkeni | `PERVAZ_DATA_DIR` |
| Windows görev çubuğu kimliği | `Pervaz.Panel` |
| CI artefaktı | `Pervaz-exe` |
| Simge | koyu zeminde vurgu şeridi ve üst üste kartlar (`tools/make_icon.py`) |

Bu değerler **yalnızca `src/pervaz/identity.py` içinde** tanımlanır (`APP_NAME`,
`APP_DISPLAY_NAME`, `APP_USER_MODEL_ID`, `DATA_DIR_ENV`, `APP_URL`); başka hiçbir dosya bu metinleri
tekrar yazmaz, oradan import eder. `identity` paket kökü gibi davranır: her katman onu okuyabilir.

**Özellik olan adlar kalır:** finans kartındaki çeyrek altın satırı (`ceyrek` kimliği, "Çeyrek
Altın" etiketi, sağlayıcı eşlemeleri ve test fixture'ları) bir finans özelliğidir, kimliğin bir izi
değildir. Kimlik kullanıcıların `settings.json` dosyalarındaki `items` listesinde yaşar ve
değişirse ayarları bozulur; bu yüzden yeniden adlandırılmaz.

## Sonuç

- Kimliği değiştirmek tek dosyayı değiştirmektir; testler veri klasörünü `PERVAZ_DATA_DIR` ile
  yönlendirir.
- Kodda başka bir adla çalışmış bir sürümden veri taşıyan bir göç mantığı yoktur. Kullanıcı
  verisinin taşınması, gerekirse, kod dışında elle yapılır.
- Sürüm 0.2.0'dır (kimlik değişti).
