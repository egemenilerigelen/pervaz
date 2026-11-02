"""Hava durumunun son başarılı yanıtı; internet yokken eski veriyi göstermek için diske yazılır."""

from __future__ import annotations

import logging
from typing import Any, Protocol

from pervaz.cards.weather.models import Place, Weather
from pervaz.infra.storage import JsonCache

logger = logging.getLogger(__name__)

Cached = tuple[Place | None, Weather | None]


class WeatherStore(Protocol):
    """Kartın ihtiyaç duyduğu önbellek arayüzü; testlerde ve başka depolarda değiştirilebilir."""

    def load(self) -> Cached: ...

    def save(self, place: Place, weather: Weather) -> None: ...


class WeatherCache(JsonCache[Cached]):
    """Son başarılı yanıt. Kartın arayüzü `WeatherStore`: konum ve hava iki ayrı değerdir."""

    file_name = "weather.json"
    invalid_message = "Hava durumu önbelleği geçersiz: %s"
    write_failed_message = "Hava durumu önbelleği yazılamadı: %s"

    def encode(self, value: Cached) -> dict[str, Any]:
        place, weather = value
        return {
            "place": {
                "query": place.query,
                "name": place.name,
                "latitude": place.latitude,
                "longitude": place.longitude,
            },
            "weather": weather.to_dict(),
        }

    def decode(self, data: dict[str, Any]) -> Cached:
        # Hava verisi bozuk olsa da okunabilen konum kullanılır; hata burada yakalanır.
        place = weather = None
        try:
            if p := data.get("place"):
                place = Place(p["query"], p["name"], float(p["latitude"]), float(p["longitude"]))
            if w := data.get("weather"):
                weather = Weather.from_dict(w)
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning(self.invalid_message, exc)
        return place, weather

    def load(self) -> Cached:
        return super().load() or (None, None)

    def save(self, place: Place, weather: Weather) -> None:
        super().save((place, weather))
